"""Tramitações de uma proposição, pela API da Câmara (contrato em contracts/api-camara.md).

A API de tramitações não anuncia total nem pagina (research R1). A completude é validada pelo
formato; qualquer desvio falha a execução inteira, sem resultado parcial.
"""

import json
import re
from typing import NamedTuple

from .erros import FORMATO_ALTERADO, FalhaDeColeta
from .transporte import Transporte

CODIGO_DESIGNACAO = "320"
PADRAO_DATA_HORA = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?")
PADRAO_URI_DEPUTADO = re.compile(r".*/deputados/([0-9]+)/?")


class Tramitacao(NamedTuple):
    sequencia: int
    data_hora: str  # AAAA-MM-DDTHH:MM, como a API entrega
    orgao: str
    codigo: str
    descricao: str
    id_relator: int | None  # só preenchido na designação (320); nas demais o campo é "pegajoso"


def _falha(id_proposicao: int, detalhe: str) -> FalhaDeColeta:
    return FalhaDeColeta(FORMATO_ALTERADO, f"tramitações da proposição {id_proposicao}: {detalhe}")


def _texto(elemento: dict, campo: str, id_proposicao: int, *, anulavel: bool = False):
    valor = elemento.get(campo)
    if isinstance(valor, str) or (anulavel and valor is None):
        return valor
    raise _falha(id_proposicao, f"formato alterado: campo {campo}")


def _id_do_relator(uri: str, id_proposicao: int) -> int:
    achado = PADRAO_URI_DEPUTADO.fullmatch(uri)
    if achado is None:
        raise _falha(id_proposicao, f"formato alterado: campo uriUltimoRelator ({uri!r})")
    return int(achado.group(1))


def _conferir_links(corpo: dict, url_base: str, id_proposicao: int) -> None:
    links = corpo.get("links", [])
    if not isinstance(links, list):
        raise _falha(id_proposicao, "formato alterado: campo links")
    for link in links:
        href = link.get("href") if isinstance(link, dict) else None
        if not isinstance(href, str) or not href.startswith(f"{url_base}/api/"):
            raise _falha(id_proposicao, f"link fora da API da Câmara: {href!r}")
        if link.get("rel") != "self":
            raise _falha(id_proposicao, f"paginação inesperada (link {link.get('rel')!r})")


def obter_tramitacoes(
    transporte: Transporte, url_base: str, id_proposicao: int
) -> list[Tramitacao]:
    """Tramitações da proposição, ordenadas por `sequencia` (a ordem da resposta é por data)."""
    url = f"{url_base}/api/v2/proposicoes/{id_proposicao}/tramitacoes"
    try:
        resposta = transporte.obter_json(url)
    except FalhaDeColeta as erro:
        raise FalhaDeColeta(
            erro.categoria,
            f"não foi possível obter as tramitações da proposição {id_proposicao}: {erro.motivo}",
        ) from erro
    try:
        corpo = json.loads(resposta.corpo)
    except ValueError as erro:
        raise _falha(id_proposicao, f"resposta não é JSON ({erro})") from erro
    if not isinstance(corpo, dict) or not isinstance(corpo.get("dados"), list):
        raise _falha(id_proposicao, "formato alterado: campo dados")
    if not corpo["dados"]:
        raise _falha(id_proposicao, "a lista veio vazia")
    _conferir_links(corpo, url_base, id_proposicao)

    tramitacoes: list[Tramitacao] = []
    vistas: set[int] = set()
    for elemento in corpo["dados"]:
        if not isinstance(elemento, dict):
            raise _falha(id_proposicao, "formato alterado: campo dados")
        sequencia = elemento.get("sequencia")
        if not isinstance(sequencia, int) or isinstance(sequencia, bool):
            raise _falha(id_proposicao, "formato alterado: campo sequencia")
        if sequencia in vistas:
            raise _falha(id_proposicao, f"sequencia repetida: {sequencia}")
        vistas.add(sequencia)
        data_hora = _texto(elemento, "dataHora", id_proposicao)
        if not PADRAO_DATA_HORA.fullmatch(data_hora):
            raise _falha(id_proposicao, f"formato alterado: campo dataHora ({data_hora!r})")
        codigo = _texto(elemento, "codTipoTramitacao", id_proposicao)
        uri = _texto(elemento, "uriUltimoRelator", id_proposicao, anulavel=True)
        tramitacoes.append(
            Tramitacao(
                sequencia=sequencia,
                data_hora=data_hora,
                orgao=_texto(elemento, "siglaOrgao", id_proposicao),
                codigo=codigo,
                descricao=_texto(elemento, "descricaoTramitacao", id_proposicao, anulavel=True)
                or "",
                id_relator=(
                    _id_do_relator(uri, id_proposicao)
                    if codigo == CODIGO_DESIGNACAO and uri is not None
                    else None
                ),
            )
        )
    return sorted(tramitacoes, key=lambda t: t.sequencia)
