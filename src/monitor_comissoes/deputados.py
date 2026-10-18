"""Deputados do NOVO em exercício, pela API da Câmara."""

import json
from typing import NamedTuple

from .erros import API_DEPUTADOS, FalhaDeColeta
from .transporte import Transporte


class Deputado(NamedTuple):
    id: int
    nome: str


def _falha(detalhe: str) -> FalhaDeColeta:
    return FalhaDeColeta(API_DEPUTADOS, f"não foi possível obter os deputados do NOVO: {detalhe}")


def obter_deputados_novo(transporte: Transporte, url_base: str) -> list[Deputado]:
    """Lista os deputados em exercício do NOVO, ordenados por id.

    Qualquer problema (rede, JSON inesperado, total diferente do anunciado, lista vazia) falha a
    execução inteira: sem a lista, `autor hoje no NOVO` ficaria silenciosamente incompleta.
    """
    url = f"{url_base}/api/v2/deputados?siglaPartido=NOVO&itens=100"
    deputados: list[Deputado] = []
    total_anunciado: int | None = None
    visitadas: set[str] = set()

    while url:
        if url in visitadas:
            raise _falha("a paginação voltou a uma página já lida")
        visitadas.add(url)
        try:
            resposta = transporte.obter_json(url)
        except FalhaDeColeta as erro:
            raise _falha(erro.motivo) from erro
        try:
            corpo = json.loads(resposta.corpo)
            dados = corpo["dados"]
            deputados.extend(Deputado(id=int(d["id"]), nome=str(d["nome"])) for d in dados)
            proxima = [link["href"] for link in corpo.get("links", []) if link.get("rel") == "next"]
        except (ValueError, KeyError, TypeError) as erro:
            raise _falha(f"resposta inesperada da API ({erro!r})") from erro
        anunciado = resposta.cabecalhos.get("x-total-count")
        if anunciado is not None and total_anunciado is None:
            try:
                total_anunciado = int(anunciado)
            except ValueError as erro:
                raise _falha(f"X-Total-Count inválido: {anunciado!r}") from erro
        url = proxima[0] if proxima else ""

    if not deputados:
        raise _falha("a lista veio vazia")
    if total_anunciado is not None and total_anunciado != len(deputados):
        raise _falha(f"a API anunciou {total_anunciado} deputados e entregou {len(deputados)}")
    return sorted(deputados)
