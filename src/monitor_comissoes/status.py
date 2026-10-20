"""data/status.json: o retrato da última execução diária (contrato em specs/002-.../contracts)."""

import json
import os
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import TypedDict

from .estoque import BRASILIA
from .plausibilidade import percentual_texto
from .saida import escrever_temporario, gravar_atomico, serializar

VERSAO_FORMATO = 1
OK = "ok"
FALHA = "falha"
CAMPOS = (
    "versao_formato",
    "resultado",
    "verificado_em",
    "data_referencia",
    "tentativas",
    "falha",
    "variacao_aceita",
    "ultimo_retrato_bom",
)
CAMPOS_RETRATO = ("gerado_em", "dados_camara_em", "total_itens", "estoque_bruto")
CAMPOS_VARIACAO = ("estoque_anterior", "estoque_novo", "variacao_percentual")


class RetratoBom(TypedDict):
    """O `atual.json` mantido. `estoque_bruto` é nulo se não há base válida para ele."""

    gerado_em: str
    dados_camara_em: str
    total_itens: int
    estoque_bruto: int | None


def _invalido(motivo: str) -> ValueError:
    return ValueError(f"status inválido: {motivo}")


def _inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _numero(valor) -> bool:
    return isinstance(valor, int | float) and not isinstance(valor, bool)


def _validar(documento) -> None:
    """Confere o formato e as invariantes do contrato; levanta ValueError se falhar."""
    if not isinstance(documento, dict):
        raise _invalido("o arquivo deve conter um objeto")
    if set(documento) != set(CAMPOS):
        raise _invalido(f"campos esperados {list(CAMPOS)}, recebidos {list(documento)}")
    if documento["versao_formato"] != VERSAO_FORMATO:
        raise _invalido(f"versao_formato {documento['versao_formato']!r} não suportada")
    resultado = documento["resultado"]
    if resultado not in (OK, FALHA):
        raise _invalido(f"resultado {resultado!r} deve ser 'ok' ou 'falha'")
    for campo in ("verificado_em", "data_referencia"):
        if not isinstance(documento[campo], str):
            raise _invalido(f"{campo} deve ser texto")
    if not _inteiro(documento["tentativas"]) or documento["tentativas"] < 0:
        raise _invalido("tentativas deve ser um inteiro maior ou igual a 0")

    falha = documento["falha"]
    if falha is not None and not (
        isinstance(falha, dict)
        and list(falha) == ["categoria", "motivo"]
        and all(isinstance(v, str) for v in falha.values())
    ):
        raise _invalido("falha deve ser null ou {categoria, motivo}")
    variacao = documento["variacao_aceita"]
    if variacao is not None and not (
        isinstance(variacao, dict) and list(variacao) == list(CAMPOS_VARIACAO)
    ):
        raise _invalido(f"variacao_aceita deve ser null ou {list(CAMPOS_VARIACAO)}")
    if variacao is not None:
        anterior, novo, percentual = (variacao[campo] for campo in CAMPOS_VARIACAO)
        sem_base = anterior is None and percentual is None
        com_base = _inteiro(anterior) and _numero(percentual)
        if not _inteiro(novo) or not (sem_base or com_base):
            raise _invalido(
                "variacao_aceita: estoque_novo inteiro, e estoque_anterior e "
                "variacao_percentual ambos preenchidos ou ambos nulos"
            )
    retrato = documento["ultimo_retrato_bom"]
    if retrato is not None:
        if not (isinstance(retrato, dict) and list(retrato) == list(CAMPOS_RETRATO)):
            raise _invalido(f"ultimo_retrato_bom deve ser null ou {list(CAMPOS_RETRATO)}")
        if not _inteiro(retrato["total_itens"]) or not (
            retrato["estoque_bruto"] is None or _inteiro(retrato["estoque_bruto"])
        ):
            raise _invalido("ultimo_retrato_bom: total_itens e estoque_bruto devem ser inteiros")

    if resultado == OK and (falha is not None or retrato is None):
        raise _invalido("resultado ok exige falha nula e ultimo_retrato_bom preenchido")
    if resultado == FALHA and (falha is None or variacao is not None):
        raise _invalido("resultado falha exige falha preenchida e variacao_aceita nula")


def montar_status(
    *,
    resultado: str,
    verificado_em: datetime,
    tentativas: int,
    falha: dict | None,
    variacao_aceita: dict | None,
    retrato: dict | None,
    data_referencia: date | None = None,
) -> dict:
    """Monta o documento na ordem fixa do contrato. `verificado_em` entra pronto (sem relógio).

    `data_referencia` é, por padrão, o dia de `verificado_em`. A execução que grava o arquivo de
    mudanças passa o dia da tentativa que o gravou, para os dois nunca divergirem se a execução
    atravessar a meia-noite.
    """
    momento = verificado_em.astimezone(BRASILIA)
    documento = {
        "versao_formato": VERSAO_FORMATO,
        "resultado": resultado,
        "verificado_em": momento.isoformat(timespec="seconds"),
        "data_referencia": (data_referencia or momento.date()).isoformat(),
        "tentativas": tentativas,
        "falha": None
        if falha is None
        else {"categoria": falha["categoria"], "motivo": falha["motivo"]},
        "variacao_aceita": (
            None
            if variacao_aceita is None
            else {campo: variacao_aceita[campo] for campo in CAMPOS_VARIACAO}
        ),
        "ultimo_retrato_bom": (
            None if retrato is None else {campo: retrato[campo] for campo in CAMPOS_RETRATO}
        ),
    }
    _validar(documento)
    return documento


def ler_status(caminho: Path) -> dict | None:
    """O status gravado, ou None se o arquivo não existe. ValueError se for inválido."""
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as erro:
        raise _invalido(f"não foi possível ler {caminho}: {erro}") from erro
    try:
        documento = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise _invalido(f"{caminho} não é um JSON válido: {erro}") from erro
    _validar(documento)
    return documento


def retrato_do_atual(caminho: Path) -> dict | None:
    """`gerado_em`, `dados_camara_em` e `total_itens` do `meta` do `atual.json`, ou None.

    None se o arquivo não existe ou não tem um `meta` válido. Nunca altera o arquivo.
    """
    try:
        meta = json.loads(Path(caminho).read_text(encoding="utf-8"))["meta"]
        retrato = {
            "gerado_em": meta["gerado_em"],
            "dados_camara_em": meta["dados_camara_em"],
            "total_itens": meta["total_itens"],
        }
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
        return None
    if not (
        isinstance(retrato["gerado_em"], str)
        and isinstance(retrato["dados_camara_em"], str)
        and _inteiro(retrato["total_itens"])
    ):
        return None
    return retrato


def base_de_comparacao(caminho_atual: Path, caminho_status: Path) -> int | None:
    """Estoque bruto do último retrato bom, se o status descrever o `atual.json` em disco.

    Só vale se o `gerado_em` registrado no status for o `meta.gerado_em` do `atual.json`: o total
    bruto nunca é comparado com um retrato que não é o que ele descreve (data-model.md da AGE).
    """
    try:
        status = ler_status(caminho_status)
    except ValueError:
        return None
    atual = retrato_do_atual(caminho_atual)
    if status is None or atual is None or status["ultimo_retrato_bom"] is None:
        return None
    retrato = status["ultimo_retrato_bom"]
    if retrato["gerado_em"] != atual["gerado_em"]:
        return None
    return retrato["estoque_bruto"]


def gravar_status(status: dict, caminho: Path) -> None:
    gravar_atomico(status, caminho)


def _restaurar(destino: Path, anterior: bytes | None) -> None:
    """Devolve `destino` ao conteúdo de antes da troca (ou o remove, se não existia)."""
    if anterior is None:
        destino.unlink(missing_ok=True)
        return
    temporario = escrever_temporario(anterior.decode("utf-8"), destino)
    try:
        os.replace(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)


def gravar_todos(escritas: Sequence[tuple[str, Path]]) -> None:
    """Grava N arquivos juntos, tudo ou nada: `escritas` é uma lista de pares (texto, destino).

    Todos os temporários são preparados primeiro, e o conteúdo anterior de todos os destinos é lido
    antes da primeira troca; só depois vêm as trocas, na ordem dada. Se algo falhar ao preparar ou
    ao ler qualquer um (serialização já feita pelo chamador; disco), nenhum destino é trocado e
    nenhum temporário sobra. Se a troca do k-ésimo falhar, os k-1 já trocados voltam,
    em ordem inversa, ao conteúdo anterior (ou são removidos, se não existiam). Uma falha ao
    restaurar um deles não impede restaurar os outros e vira nota na exceção original. Só a morte
    do processo entre duas trocas deixa arquivos trocados, e o workflow os restaura do Git.
    """
    destinos = [Path(destino) for _, destino in escritas]
    temporarios: list[Path] = []
    trocados: list[tuple[Path, bytes | None]] = []
    try:
        for (texto, _), destino in zip(escritas, destinos, strict=True):
            temporarios.append(escrever_temporario(texto, destino))
        anteriores = [d.read_bytes() if d.exists() else None for d in destinos]
        for temporario, destino, anterior in zip(temporarios, destinos, anteriores, strict=True):
            try:
                os.replace(temporario, destino)
            except BaseException as erro:
                for ja_trocado, conteudo in reversed(trocados):
                    try:
                        _restaurar(ja_trocado, conteudo)
                    except Exception as restauracao:  # a causa original continua sendo a que sobe
                        erro.add_note(f"restauração de {ja_trocado} também falhou: {restauracao!r}")
                raise
            trocados.append((destino, anterior))
    finally:
        for temporario in temporarios:
            temporario.unlink(missing_ok=True)


def gravar_par(atual: dict, caminho_atual: Path, status: dict, caminho_status: Path) -> None:
    """Grava `atual.json` e `status.json` juntos (o caso de dois arquivos de `gravar_todos`)."""
    gravar_todos([(serializar(atual), caminho_atual), (serializar(status), caminho_status)])


def mensagem_commit(status: dict) -> str:
    """Mensagem de uma linha do commit do bot (data-model.md da AGE, "Mensagem do commit")."""
    _validar(status)
    dia = status["data_referencia"]
    if status["resultado"] == FALHA:
        return f"dados: {dia} · falha [{status['falha']['categoria']}]"
    variacao = status["variacao_aceita"]
    if variacao is not None and variacao["estoque_anterior"] is None:
        estoque = variacao["estoque_novo"]
        return f"dados: {dia} · ok · aceito sem base de comparação (estoque bruto {estoque})"
    if variacao is not None:
        percentual = percentual_texto(variacao["variacao_percentual"])
        return (
            f"dados: {dia} · ok · variação aceita manualmente "
            f"({variacao['estoque_anterior']} → {variacao['estoque_novo']}, {percentual})"
        )
    retrato = status["ultimo_retrato_bom"]
    itens, estoque = retrato["total_itens"], retrato["estoque_bruto"]
    return f"dados: {dia} · ok · {itens} itens · estoque bruto {estoque}"
