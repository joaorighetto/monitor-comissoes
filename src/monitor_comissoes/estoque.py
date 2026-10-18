"""Regras de domínio da lista: etiquetas, comissão e montagem dos itens (PRODUCT.md §5).

Sem I/O: recebe dados já lidos e devolve os itens do `atual.json`.
"""

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from .lote import Autor, Proposicao

BRASILIA = timezone(timedelta(hours=-3))  # sem horário de verão desde 2019
PARTIDO = "NOVO"
ETIQUETA_AUTORIA = "autoria NOVO"
ETIQUETA_AUTOR_HOJE = "autor hoje no NOVO"
TIPOS = ("PL", "PLP")
FORMATO_DATA = "%Y-%m-%dT%H:%M:%S"


def link_oficial(id_proposicao: int) -> str:
    return f"https://www.camara.leg.br/propostas-legislativas/{id_proposicao}"


def identificacao(proposicao: Proposicao) -> str:
    return f"{proposicao.tipo} {proposicao.numero}/{proposicao.ano}"


def etiquetar(autores: Iterable[Autor], ids_deputados_novo: set[int]) -> list[str]:
    """Etiquetas de autoria (PRODUCT.md §5.4), pelos autores da própria proposição."""
    autores = list(autores)
    etiquetas = []
    if any(a.partido_na_data == PARTIDO for a in autores):
        etiquetas.append(ETIQUETA_AUTORIA)
    if any(a.id_deputado is not None and a.id_deputado in ids_deputados_novo for a in autores):
        etiquetas.append(ETIQUETA_AUTOR_HOJE)
    return etiquetas


def _item(
    candidata: Proposicao,
    autores: list[Autor],
    etiquetas: list[str],
    referencia: Proposicao,
    hoje_brasilia,
) -> dict:
    return {
        "id": candidata.id,
        "tipo": candidata.tipo,
        "numero": candidata.numero,
        "ano": candidata.ano,
        "identificacao": identificacao(candidata),
        "ementa": candidata.ementa,
        "data_apresentacao": candidata.data_apresentacao.strftime(FORMATO_DATA),
        "link": link_oficial(candidata.id),
        "autores": [
            {
                "nome": a.nome,
                "id_deputado": a.id_deputado,
                "partido_na_data": a.partido_na_data,
                "ordem": a.ordem,
            }
            for a in sorted(autores, key=lambda a: (a.ordem, a.nome))
        ],
        "etiquetas": etiquetas,
        "comissao": referencia.orgao,
        "situacao": referencia.situacao,
        "ultimo_status_em": referencia.ultimo_status_em.strftime(FORMATO_DATA),
        "parado_ha_dias": max(0, (hoje_brasilia - referencia.ultimo_status_em.date()).days),
        "apensado_a": None,
        "principal_nao_localizada": False,
    }


def construir_itens(
    candidatas: dict[int, Proposicao],
    autores_por_id: dict[int, list[Autor]],
    ids_deputados_novo: set[int],
    comissoes: tuple[str, ...],
    agora: datetime,
) -> list[dict]:
    """PL/PLP na comissão com ao menos uma etiqueta, os parados há mais tempo primeiro."""
    hoje = agora.astimezone(BRASILIA).date()
    selecionados = []
    for candidata in candidatas.values():
        if candidata.tipo not in TIPOS:
            continue
        referencia = candidata
        if referencia.orgao not in comissoes:
            continue
        autores = autores_por_id.get(candidata.id, [])
        etiquetas = etiquetar(autores, ids_deputados_novo)
        if not etiquetas:
            continue
        selecionados.append(
            (
                (referencia.ultimo_status_em, candidata.id),
                _item(candidata, autores, etiquetas, referencia, hoje),
            )
        )
    return [item for _, item in sorted(selecionados, key=lambda par: par[0])]
