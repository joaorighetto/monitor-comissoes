"""Índice de autoria (PAU, research R8): quem assinou cada proposição do lote.

A coleta diária, que já percorre o lote, grava `cache/indice-autoria.json` com toda proposição de
MSC, PDL, PEC, PL, PLP e REQ: se algum autor assinou como NOVO e os ids dos deputados autores. A
checagem da pauta lê o índice em vez de baixar o lote. Contrato: specs/007-pauta-reunioes/
contracts/indice-autoria.md.
"""

import json
from datetime import datetime
from pathlib import Path

from .erros import ENTRADA_INVALIDA, FalhaDeColeta
from .estoque import BRASILIA
from .lote import Lote, _inteiro, _linhas

VERSAO_FORMATO = 1
TIPOS = ("MSC", "PDL", "PEC", "PL", "PLP", "REQ")
PARTIDO = "NOVO"
CAMPOS = ("versao_formato", "gerado_em", "dados_camara_em", "anos_lidos", "tipos", "proposicoes")


def construir_indice(lote: Lote, gerado_em: datetime) -> dict:
    """O índice do lote, com o `meta` igual ao do `atual.json` da mesma coleta.

    Os autores de uma proposição podem estar no arquivo de autores de outro ano, por isso todos os
    arquivos de autores são lidos contra o conjunto inteiro de ids.
    """
    autoria: dict[int, int] = {}
    deputados: dict[int, set[int]] = {}
    for ano in lote.anos:
        caminho = lote.proposicoes(ano)
        for pid, tipo in _linhas(caminho, ("id", "siglaTipo")):
            if tipo in TIPOS:
                id_proposicao = _inteiro(pid, "id", caminho.name)
                autoria[id_proposicao] = 0
                deputados[id_proposicao] = set()
    colunas = ("idProposicao", "idDeputadoAutor", "siglaPartidoAutor")
    for ano in lote.anos:
        caminho = lote.autores(ano)
        for pid, id_deputado, partido in _linhas(caminho, colunas):
            id_proposicao = _inteiro(pid, "idProposicao", caminho.name)
            if id_proposicao not in autoria:
                continue
            if partido == PARTIDO:
                autoria[id_proposicao] = 1
            if id_deputado:
                deputados[id_proposicao].add(_inteiro(id_deputado, "idDeputadoAutor", caminho.name))
    return {
        "versao_formato": VERSAO_FORMATO,
        "gerado_em": gerado_em.astimezone(BRASILIA).isoformat(timespec="seconds"),
        "dados_camara_em": lote.last_modified_min.isoformat(timespec="seconds"),
        "anos_lidos": [lote.anos[0], lote.anos[-1]],
        "tipos": list(TIPOS),
        "proposicoes": {
            str(pid): [autoria[pid], sorted(deputados[pid])] for pid in sorted(autoria)
        },
    }


def serializar_indice(indice: dict) -> str:
    """JSON compacto, sem indentação: o índice tem centenas de milhares de entradas."""
    return json.dumps(indice, ensure_ascii=False, separators=(",", ":")) + "\n"


def _invalido(caminho: Path, detalhe: str) -> FalhaDeColeta:
    return FalhaDeColeta(ENTRADA_INVALIDA, f"índice de autoria {caminho}: {detalhe}")


def _inteiro_json(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _entrada_valida(chave, valor) -> bool:
    return (
        isinstance(chave, str)
        and chave.isdigit()
        and isinstance(valor, list)
        and len(valor) == 2
        and _inteiro_json(valor[0])
        and valor[0] in (0, 1)
        and isinstance(valor[1], list)
        and all(_inteiro_json(d) for d in valor[1])
    )


def ler_indice(caminho: Path) -> dict:
    """O índice gravado pela coleta, validado. Índice antigo continua válido (último lote bom)."""
    if not caminho.exists():
        raise _invalido(caminho, "o arquivo não existe (a coleta diária ainda não o gravou?)")
    try:
        indice = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise _invalido(caminho, f"ilegível ({erro})") from erro
    if not isinstance(indice, dict):
        raise _invalido(caminho, "o conteúdo não é um objeto JSON")
    for campo in CAMPOS:
        if campo not in indice:
            raise _invalido(caminho, f"campo ausente: {campo}")
    if indice["versao_formato"] != VERSAO_FORMATO:
        raise _invalido(caminho, f"versao_formato {indice['versao_formato']!r} desconhecida")
    for campo in ("gerado_em", "dados_camara_em"):
        if not isinstance(indice[campo], str):
            raise _invalido(caminho, f"{campo} fora do formato")
    anos = indice["anos_lidos"]
    if not (isinstance(anos, list) and len(anos) == 2 and all(_inteiro_json(a) for a in anos)):
        raise _invalido(caminho, "anos_lidos fora do formato")
    if not (isinstance(indice["tipos"], list) and all(isinstance(t, str) for t in indice["tipos"])):
        raise _invalido(caminho, "tipos fora do formato")
    proposicoes = indice["proposicoes"]
    if not isinstance(proposicoes, dict):
        raise _invalido(caminho, "proposicoes fora do formato")
    for chave, valor in proposicoes.items():
        if not _entrada_valida(chave, valor):
            raise _invalido(caminho, f"proposicoes[{chave!r}] fora do formato")
    return indice
