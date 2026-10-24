"""Checagem da pauta (PAU): `python -m monitor_comissoes.pauta checar|mensagem`.

Contrato: specs/007-pauta-reunioes/contracts/pauta-cli.md. Lê a configuração, o índice de autoria,
o inventário e a última checagem; consulta a Câmara; grava o arquivo do dia e o
`status-pauta.json` juntos. Em falha, só o status é gravado. Os arquivos da coleta nunca são
gravados.
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from ..coleta import URL_BASE
from ..config import carregar_config
from ..deputados import obter_deputados_novo
from ..erros import ENTRADA_INVALIDA, INTERNA, FalhaDeColeta
from ..estoque import BRASILIA
from ..indice import ler_indice
from ..retratos import ler as ler_retrato
from ..transporte import Transporte, TransporteHttp
from .api import obter_evento, obter_eventos, obter_orgao, obter_pauta
from .arquivos import (
    gravar,
    ler_pauta,
    ler_status_pauta,
    montar_status_pauta,
    ultimo_arquivo,
)
from .checagem import (
    Contexto,
    comparar,
    janela,
    montar_arquivo,
    montar_checagem,
    montar_reunioes,
    selecionar,
)


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _ler_inventario(caminho: Path) -> dict:
    """O `atual.json` (o último inventário bom), em formato comparável."""
    try:
        texto = caminho.read_text(encoding="utf-8")
    except FileNotFoundError as erro:
        raise FalhaDeColeta(ENTRADA_INVALIDA, f"inventário {caminho}: não existe") from erro
    except (OSError, UnicodeDecodeError) as erro:
        raise FalhaDeColeta(ENTRADA_INVALIDA, f"inventário {caminho}: ilegível ({erro})") from erro
    try:
        retrato = ler_retrato(texto, caminho.name)
    except FalhaDeColeta as falha:
        raise FalhaDeColeta(ENTRADA_INVALIDA, f"inventário {caminho}: {falha.motivo}") from falha
    if not retrato.compativel:
        raise FalhaDeColeta(ENTRADA_INVALIDA, f"inventário {caminho}: versão de formato antiga")
    return retrato.documento


def _checar(args, transporte: Transporte, agora: datetime) -> tuple[dict, bool, dict]:
    """Uma checagem sem gravar nada: o arquivo do dia, se é linha de base, e as contagens."""
    momento = agora.astimezone(BRASILIA)
    hoje = momento.date()
    checada_em = momento.isoformat(timespec="seconds")
    config = carregar_config(args.config, hoje.year)
    indice = ler_indice(args.indice)
    inventario = _ler_inventario(args.atual)
    caminho_anterior = ultimo_arquivo(args.pautas, hoje)
    anterior = ler_pauta(caminho_anterior) if caminho_anterior is not None else None

    deputados = obter_deputados_novo(transporte, URL_BASE)
    inicio, fim = janela(hoje)
    eventos_por_comissao = {}
    for sigla in config.comissoes:
        id_orgao = obter_orgao(transporte, sigla)
        eventos_por_comissao[sigla] = (id_orgao, obter_eventos(transporte, id_orgao, inicio, fim))
    ids = sorted({evento["id"] for _, evento in selecionar(eventos_por_comissao, hoje)})
    pautas = {id_evento: obter_pauta(transporte, id_evento) for id_evento in ids}

    contexto = Contexto(
        hoje=hoje,
        checada_em=checada_em,
        proposicoes_indice=indice["proposicoes"],
        ids_novo=frozenset(d.id for d in deputados),
        inventario=inventario["itens"],
    )
    reunioes = montar_reunioes(eventos_por_comissao, pautas, contexto)
    novas = []
    if anterior is not None:
        novas = comparar(
            anterior["checagem"]["reunioes"],
            reunioes,
            lambda id_evento: obter_evento(transporte, id_evento),
            checada_em,
            (inicio, fim),
        )
    checagem = montar_checagem(
        checada_em,
        (inicio, fim),
        indice["dados_camara_em"],
        inventario["meta"]["gerado_em"],
        [{"id": d.id, "nome": d.nome} for d in deputados],
        reunioes,
    )
    arquivo = montar_arquivo(hoje, config.comissoes, checagem, anterior, novas)
    por_comissao = {sigla: 0 for sigla in config.comissoes}
    for reuniao in reunioes:
        por_comissao[reuniao["comissao"]] += 1
    return arquivo, anterior is None, {"por_comissao": por_comissao, "novas": len(novas)}


def _ultima_checagem_boa(caminho_status: Path, pautas: Path, hoje: date) -> str | None:
    """Do status anterior; sem ele, o `checada_em` do arquivo de pauta mais recente; ou None."""
    status = ler_status_pauta(caminho_status)
    if status is not None:
        return status["ultima_checagem_boa"]
    try:
        caminho = ultimo_arquivo(pautas, hoje)
        return ler_pauta(caminho)["checagem"]["checada_em"] if caminho is not None else None
    except FalhaDeColeta:
        return None


def _registrar_falha(categoria: str, motivo: str, args, agora: datetime) -> int:
    print(f"FALHA [{categoria}]: {motivo}", file=sys.stderr)
    try:
        hoje = agora.astimezone(BRASILIA).date()
        ultima = _ultima_checagem_boa(args.status, args.pautas, hoje)
        falha = {"categoria": categoria, "motivo": motivo}
        gravar(None, args.pautas, montar_status_pauta("falha", agora, falha, ultima), args.status)
    except Exception as erro:
        print(
            f"FALHA [{INTERNA}]: não foi possível gravar {args.status} "
            f"({type(erro).__name__}: {erro})",
            file=sys.stderr,
        )
    return 1


def checar(args, transporte: Transporte, agora: datetime) -> int:
    try:
        arquivo, linha_de_base, contagem = _checar(args, transporte, agora)
        checada_em = arquivo["checagem"]["checada_em"]
        status = montar_status_pauta("ok", agora, None, checada_em)
        gravar(arquivo, args.pautas / f"{arquivo['meta']['data']}.json", status, args.status)
    except FalhaDeColeta as falha:
        return _registrar_falha(falha.categoria, falha.motivo, args, agora)
    except Exception as erro:  # nenhuma falha pode terminar sem aviso nem status
        return _registrar_falha(INTERNA, f"{type(erro).__name__}: {erro}", args, agora)

    total = sum(contagem["por_comissao"].values())
    comissoes = ", ".join(f"{sigla}: {n}" for sigla, n in contagem["por_comissao"].items())
    alteracoes = (
        "linha de base"
        if linha_de_base
        else _plural(contagem["novas"], "alteração nova", "alterações novas")
    )
    momento = agora.astimezone(BRASILIA)
    print(
        f"OK: {_plural(total, 'reunião', 'reuniões')} ({comissoes}) · {alteracoes}"
        f" · pauta checada em {momento:%d/%m} às {momento:%Hh%M}"
    )
    return 0


def mensagem(caminho_status: Path, pautas: Path) -> str:
    """A mensagem de uma linha do commit do bot. ValueError se o status ou o arquivo faltam."""
    status = ler_status_pauta(caminho_status)
    if status is None:
        raise ValueError(f"status inválido: {caminho_status} não existe ou está ilegível")
    momento = datetime.fromisoformat(status["verificado_em"]).astimezone(BRASILIA)
    inicio = f"pauta: {momento:%Y-%m-%d %H:%M}"
    if status["resultado"] == "falha":
        return f"{inicio} · falha · {status['falha']['categoria']}"
    checada_em = status["ultima_checagem_boa"]
    dia = datetime.fromisoformat(checada_em).astimezone(BRASILIA).date()
    try:
        arquivo = ler_pauta(pautas / f"{dia.isoformat()}.json")
    except FalhaDeColeta as falha:
        raise ValueError(falha.motivo) from falha
    reunioes = _plural(len(arquivo["checagem"]["reunioes"]), "reunião", "reuniões")
    novas = sum(1 for a in arquivo["alteracoes"] if a["detectada_em"] == checada_em)
    if arquivo["meta"]["linha_de_base"] is not None and not arquivo["alteracoes"]:
        return f"{inicio} · ok · {reunioes} · linha de base"
    return f"{inicio} · ok · {reunioes} · {_plural(novas, 'alteração', 'alterações')}"


def main(
    argv: list[str] | None = None,
    transporte: Transporte | None = None,
    agora: datetime | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="monitor_comissoes.pauta", description=__doc__)
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    checar_ = subcomandos.add_parser("checar", help="checa a pauta e grava o arquivo do dia")
    checar_.add_argument("--config", type=Path, default=Path("config.toml"))
    checar_.add_argument("--pautas", type=Path, default=Path("data/pautas"))
    checar_.add_argument("--status", type=Path, default=Path("data/status-pauta.json"))
    checar_.add_argument("--atual", type=Path, default=Path("data/atual.json"))
    checar_.add_argument("--indice", type=Path, default=Path("cache/indice-autoria.json"))
    mensagem_ = subcomandos.add_parser("mensagem", help="mensagem de uma linha do commit")
    mensagem_.add_argument("--status", type=Path, default=Path("data/status-pauta.json"))
    mensagem_.add_argument("--pautas", type=Path, default=Path("data/pautas"))
    args = parser.parse_args(argv)

    if args.comando == "mensagem":
        try:
            print(mensagem(args.status, args.pautas))
        except ValueError as erro:
            print(f"FALHA [{INTERNA}]: {erro}", file=sys.stderr)
            return 1
        return 0
    return checar(args, transporte or TransporteHttp(), agora or datetime.now(BRASILIA))
