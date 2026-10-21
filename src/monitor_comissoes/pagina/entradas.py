"""Leitura e conferência das entradas da página pública (PAG): atual, status e mudanças.

A página só exibe o que esses arquivos trazem: nenhuma regra de domínio é recalculada aqui. Qualquer
arquivo ausente, ilegível, de versão desconhecida ou incoerente com os demais levanta
`FalhaDePagina` com o nome do arquivo (constituição, III): nunca vira uma página vazia ou parcial.
"""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .. import mudancas as mud
from ..erros import FalhaDePagina
from ..estoque import BRASILIA
from ..status import ler_status

VERSOES_DO_ATUAL = (2, 3)  # as que trazem relator, identificacao, link e principal_nao_localizada
DIAS_DA_JANELA = 7
LINK_OFICIAL = "https://www.camara.leg.br/"


def _lido(caminho: Path, o_que: str) -> dict:
    """O objeto JSON do arquivo; `FalhaDePagina` com o nome do arquivo se não for possível."""
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except FileNotFoundError as erro:
        raise FalhaDePagina(f"{o_que} {caminho} não existe") from erro
    except (OSError, UnicodeDecodeError) as erro:
        raise FalhaDePagina(f"não foi possível ler {o_que} {caminho}: {erro}") from erro
    try:
        documento = json.loads(texto)
    except ValueError as erro:
        raise FalhaDePagina(f"{o_que} {caminho} não é um JSON válido: {erro}") from erro
    if not isinstance(documento, dict):
        raise FalhaDePagina(f"{o_que} {caminho} deve conter um objeto JSON")
    return documento


def _texto(valor) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _instante(valor) -> bool:
    if not isinstance(valor, str):
        return False
    try:
        datetime.fromisoformat(valor)
    except ValueError:
        return False
    return True


def _oficial(valor) -> bool:
    return _texto(valor) and valor.startswith(LINK_OFICIAL)


def _validar_meta(meta, caminho: Path) -> None:
    versao = meta.get("versao_formato") if isinstance(meta, dict) else None
    if isinstance(versao, bool) or versao not in VERSOES_DO_ATUAL:
        raise FalhaDePagina(
            f"{caminho}: meta.versao_formato {versao!r} não suportada (esperada uma de "
            f"{list(VERSOES_DO_ATUAL)})"
        )
    for campo in ("gerado_em", "dados_camara_em"):
        if not _instante(meta.get(campo)):
            raise FalhaDePagina(f"{caminho}: meta.{campo} ausente ou inválido")
    comissoes = meta.get("comissoes")
    if not isinstance(comissoes, list) or not comissoes or not all(_texto(c) for c in comissoes):
        raise FalhaDePagina(f"{caminho}: meta.comissoes ausente ou inválido")
    por_comissao = meta.get("total_por_comissao")
    if not isinstance(por_comissao, dict) or not all(_inteiro(n) for n in por_comissao.values()):
        raise FalhaDePagina(f"{caminho}: meta.total_por_comissao ausente ou inválido")
    if not _inteiro(meta.get("total_itens")):
        raise FalhaDePagina(f"{caminho}: meta.total_itens ausente ou inválido")


def _validar_item(item, posicao: int, caminho: Path) -> None:
    onde = f"{caminho}: itens[{posicao}]"
    if not isinstance(item, dict):
        raise FalhaDePagina(f"{onde} deve ser um objeto")

    def invalido(campo: str) -> FalhaDePagina:
        return FalhaDePagina(f"{onde}.{campo} ausente ou inválido")

    if not _inteiro(item.get("id")):
        raise invalido("id")
    for campo in ("identificacao", "ementa", "comissao", "situacao"):
        if not _texto(item.get(campo)):
            raise invalido(campo)
    if not _oficial(item.get("link")):
        raise FalhaDePagina(f"{onde}.link não é um link oficial ({LINK_OFICIAL}…)")
    autores = item.get("autores")
    if not isinstance(autores, list):
        raise invalido("autores")
    for i, autor in enumerate(autores):
        if not isinstance(autor, dict) or not _texto(autor.get("nome")):
            raise invalido(f"autores[{i}].nome")
        # autor que não é deputado (uma comissão especial, por exemplo) vem sem partido: ""
        if not isinstance(autor.get("partido_na_data"), str):
            raise invalido(f"autores[{i}].partido_na_data")
    etiquetas = item.get("etiquetas")
    if not isinstance(etiquetas, list) or not all(_texto(e) for e in etiquetas):
        raise invalido("etiquetas")
    if not _inteiro(item.get("parado_ha_dias")):
        raise invalido("parado_ha_dias")
    if not isinstance(item.get("principal_nao_localizada"), bool):
        raise invalido("principal_nao_localizada")
    if "apensado_a" not in item:
        raise invalido("apensado_a")
    apensado = item["apensado_a"]
    if apensado is not None:
        if not isinstance(apensado, dict) or not _texto(apensado.get("identificacao")):
            raise invalido("apensado_a.identificacao")
        if not _oficial(apensado.get("link")):
            raise FalhaDePagina(f"{onde}.apensado_a.link não é um link oficial ({LINK_OFICIAL}…)")
    if "relator" not in item:
        raise invalido("relator")
    relator = item["relator"]
    if relator is not None:
        if not isinstance(relator, dict) or not _texto(relator.get("nome")):
            raise invalido("relator.nome")
        partido = relator.get("partido_hoje")
        if partido is not None and not isinstance(partido, str):
            raise invalido("relator.partido_hoje")
        if not _oficial(relator.get("fonte")):
            raise FalhaDePagina(f"{onde}.relator.fonte não é um link oficial ({LINK_OFICIAL}…)")
    if "relator_indeterminado" not in item:
        raise invalido("relator_indeterminado")


def ler_atual(caminho: Path) -> dict:
    """O `atual.json` conferido: versão, `meta`, lista de itens não vazia e links oficiais."""
    documento = _lido(caminho, "atual.json")
    meta = documento.get("meta")
    _validar_meta(meta, caminho)
    itens = documento.get("itens")
    if not isinstance(itens, list) or not itens:
        raise FalhaDePagina(f"{caminho}: itens deve ser uma lista não vazia")
    if meta["total_itens"] != len(itens):
        raise FalhaDePagina(
            f"{caminho}: meta.total_itens {meta['total_itens']} difere do tamanho de itens "
            f"({len(itens)})"
        )
    for posicao, item in enumerate(itens):
        _validar_item(item, posicao, caminho)
    return documento


def ler_status_do_dia(caminho: Path) -> dict:
    """O `status.json` da última execução. Obrigatório: sem ele não há como dizer se deu certo."""
    try:
        status = ler_status(caminho)
    except ValueError as erro:
        raise FalhaDePagina(f"status.json {caminho}: {erro}") from erro
    if status is None:
        raise FalhaDePagina(f"status.json {caminho} não existe")
    return status


def conferir(atual: dict, status: dict, caminho_atual: Path = Path("atual.json")) -> None:
    """Confere que o `atual.json` é o retrato bom que o `status.json` descreve.

    Em sucesso o retrato é o que a execução acabou de gravar; em falha é o retrato mantido. Em
    qualquer dos dois, um `atual.json` de outro momento seria exatamente o caso que a faixa de
    erro poderia esconder.
    """
    bom = status["ultimo_retrato_bom"]
    if bom is None:
        raise FalhaDePagina(
            f"status.json: resultado {status['resultado']} sem ultimo_retrato_bom para conferir "
            f"com {caminho_atual}"
        )
    meta = atual["meta"]
    for campo in ("dados_camara_em", "gerado_em"):
        if meta[campo] != bom[campo]:
            raise FalhaDePagina(
                f"{caminho_atual}: meta.{campo} {meta[campo]!r} difere do ultimo_retrato_bom "
                f"do status.json ({bom[campo]})"
            )


def dia_do_retrato(atual: dict) -> date:
    """O dia (Brasília) em que o retrato exibido foi gerado: o fim da janela de mudanças."""
    return datetime.fromisoformat(atual["meta"]["gerado_em"]).astimezone(BRASILIA).date()


def _mudancas_do_dia(pasta: Path, dia: date, atual: dict) -> dict | None:
    caminho = Path(pasta) / mud.nome_do_arquivo(dia)
    if not caminho.exists():
        return None
    documento = _lido(caminho, "arquivo de mudanças")
    meta = documento.get("meta")
    versao = meta.get("versao_formato") if isinstance(meta, dict) else None
    if versao != mud.VERSAO_FORMATO:
        raise FalhaDePagina(
            f"arquivo de mudanças {caminho}: versao_formato {versao!r} não suportada "
            f"(esperada {mud.VERSAO_FORMATO})"
        )
    try:
        mud.validar_arquivo(documento)
    except Exception as erro:  # validar_arquivo levanta FalhaDeColeta(INTERNA) com o motivo
        motivo = getattr(erro, "motivo", str(erro))
        raise FalhaDePagina(f"arquivo de mudanças {caminho} fora do contrato: {motivo}") from erro
    if meta["data"] != dia.isoformat():
        raise FalhaDePagina(
            f"arquivo de mudanças {caminho}: data {meta['data']} difere do nome do arquivo "
            f"({dia.isoformat()})"
        )
    if dia == dia_do_retrato(atual):
        esperado = _utc(atual["meta"]["dados_camara_em"])
        if _utc(meta["retrato"]["dados_camara_em"]) != esperado:
            raise FalhaDePagina(
                f"arquivo de mudanças {caminho}: dados_camara_em "
                f"{meta['retrato']['dados_camara_em']} difere do atual.json "
                f"({atual['meta']['dados_camara_em']})"
            )
    return documento


def _utc(instante: str) -> datetime:
    return datetime.fromisoformat(instante).astimezone(UTC)


def ler_janela(pasta: Path, atual: dict) -> list[tuple[date, dict | None]]:
    """Os 7 dias que terminam no dia do retrato, do mais recente ao mais antigo.

    Cada elemento é `(dia, documento)`; `documento` é `None` quando não há arquivo do dia. Só os
    arquivos da janela são lidos: um arquivo antigo corrompido não derruba a página de hoje.
    """
    fim = dia_do_retrato(atual)
    dias = [fim - timedelta(days=i) for i in range(DIAS_DA_JANELA)]
    return [(dia, _mudancas_do_dia(pasta, dia, atual)) for dia in dias]
