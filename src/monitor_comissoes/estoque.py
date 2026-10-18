"""Regras de domínio da lista: etiquetas, comissão e montagem dos itens (PRODUCT.md §5).

Sem I/O: recebe dados já lidos e devolve os itens do `atual.json`.
"""

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from .deputados import DeputadoHoje
from .lote import Autor, Proposicao
from .relatoria import ResultadoRelatoria

BRASILIA = timezone(timedelta(hours=-3))  # sem horário de verão desde 2019
PARTIDO = "NOVO"
ETIQUETA_AUTORIA = "autoria NOVO"
ETIQUETA_AUTOR_HOJE = "autor hoje no NOVO"
ETIQUETA_RELATORIA = "relatoria NOVO"
TIPOS = ("PL", "PLP")
FORMATO_DATA = "%Y-%m-%dT%H:%M:%S"


def link_oficial(id_proposicao: int) -> str:
    return f"https://www.camara.leg.br/propostas-legislativas/{id_proposicao}"


def identificacao(proposicao: Proposicao) -> str:
    return f"{proposicao.tipo} {proposicao.numero}/{proposicao.ano}"


def etiquetar(
    autores: Iterable[Autor], ids_deputados_novo: set[int], id_relator: int | None = None
) -> list[str]:
    """Etiquetas (PRODUCT.md §5.4), sempre na ordem autoria, autor hoje, relatoria.

    As de autoria vêm dos autores da própria proposição; a de relatoria, do relator atual da
    referência (`id_relator`), já confirmado pelas tramitações.
    """
    autores = list(autores)
    etiquetas = []
    if any(a.partido_na_data == PARTIDO for a in autores):
        etiquetas.append(ETIQUETA_AUTORIA)
    if any(a.id_deputado is not None and a.id_deputado in ids_deputados_novo for a in autores):
        etiquetas.append(ETIQUETA_AUTOR_HOJE)
    if id_relator is not None and id_relator in ids_deputados_novo:
        etiquetas.append(ETIQUETA_RELATORIA)
    return etiquetas


class Referencia(NamedTuple):
    """Proposição de que vêm a comissão, a situação e o "parado há" de um item (§5.2).

    estado: "propria" (sem principal), "raiz" (raiz da cadeia localizada) ou
    "nao_localizada" (raiz ausente dos arquivos lidos ou ciclo; vale o status do próprio item).
    """

    estado: str
    proposicao: Proposicao
    raiz: Proposicao | None


def subir_ate_a_raiz(id_inicial: int, mapa_principal: dict[int, int]) -> int | None:
    """Id da raiz da cadeia de apensação a partir de `id_inicial`, ou None se houver ciclo.

    `mapa_principal` só tem entradas para proposições apensadas: quem não está nele é raiz
    (ou não consta dos arquivos lidos, o que o chamador descobre ao procurar a linha).
    """
    visitados = {id_inicial}
    atual = id_inicial
    while atual in mapa_principal:
        atual = mapa_principal[atual]
        if atual in visitados:
            return None
        visitados.add(atual)
    return atual


def resolver_referencia(
    candidata: Proposicao, mapa_principal: dict[int, int], proposicoes: dict[int, Proposicao]
) -> Referencia:
    if candidata.id_principal is None:
        return Referencia("propria", candidata, None)
    id_raiz = subir_ate_a_raiz(candidata.id, mapa_principal)
    raiz = proposicoes.get(id_raiz) if id_raiz is not None else None
    if raiz is None:
        return Referencia("nao_localizada", candidata, None)
    return Referencia("raiz", raiz, raiz)


def _relator(
    resultado: ResultadoRelatoria, referencia_id: int, deputados: dict[int, DeputadoHoje]
) -> dict | None:
    if resultado.relator is None:
        return None
    deputado = deputados[resultado.relator.id]
    return {
        "id": deputado.id,
        "nome": deputado.nome,
        "partido_hoje": deputado.partido,
        "designado_em": f"{resultado.relator.designado_em}:00",
        "fonte": link_oficial(referencia_id),
    }


def _item(
    candidata: Proposicao,
    autores: list[Autor],
    etiquetas: list[str],
    referencia: Referencia,
    hoje_brasilia,
    relatoria: ResultadoRelatoria,
    deputados_relator: dict[int, DeputadoHoje],
) -> dict:
    status = referencia.proposicao
    raiz = referencia.raiz
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
        "comissao": status.orgao,
        "situacao": status.situacao,
        "ultimo_status_em": status.ultimo_status_em.strftime(FORMATO_DATA),
        "parado_ha_dias": max(0, (hoje_brasilia - status.ultimo_status_em.date()).days),
        "apensado_a": (
            {"id": raiz.id, "identificacao": identificacao(raiz), "link": link_oficial(raiz.id)}
            if raiz
            else None
        ),
        "principal_nao_localizada": referencia.estado == "nao_localizada",
        "relator": _relator(relatoria, status.id, deputados_relator),
        "relator_indeterminado": (
            {"motivo": relatoria.indeterminado} if relatoria.indeterminado else None
        ),
    }


def ids_na_comissao(
    candidatas: dict[int, Proposicao],
    comissoes: tuple[str, ...],
    mapa_principal: dict[int, int] | None = None,
    proposicoes: dict[int, Proposicao] | None = None,
) -> set[int]:
    """Ids das candidatas PL/PLP cuja referência está numa das comissões (§5.3)."""
    mapa = mapa_principal or {}
    linhas = proposicoes if proposicoes is not None else candidatas
    return {
        c.id
        for c in candidatas.values()
        if c.tipo in TIPOS and resolver_referencia(c, mapa, linhas).proposicao.orgao in comissoes
    }


def construir_itens(
    candidatas: dict[int, Proposicao],
    autores_por_id: dict[int, list[Autor]],
    ids_deputados_novo: set[int],
    comissoes: tuple[str, ...],
    agora: datetime,
    mapa_principal: dict[int, int] | None = None,
    proposicoes: dict[int, Proposicao] | None = None,
    relatorias: dict[int, ResultadoRelatoria] | None = None,
    deputados_relator: dict[int, DeputadoHoje] | None = None,
) -> list[dict]:
    """PL/PLP na comissão com ao menos uma etiqueta, os parados há mais tempo primeiro.

    `mapa_principal` (id -> id da principal, só dos apensados) e `proposicoes` (as candidatas e
    as raízes de suas cadeias) permitem avaliar cada apensado pela proposição principal.
    `relatorias` (id da referência -> relator atual) vem das tramitações; `deputados_relator`
    (id -> nome e partido de hoje) tem todo relator que aparece em `relatorias`.
    """
    hoje = agora.astimezone(BRASILIA).date()
    mapa = mapa_principal or {}
    linhas = proposicoes if proposicoes is not None else candidatas
    relatorias = relatorias or {}
    deputados_relator = deputados_relator or {}
    selecionados = []
    for candidata in candidatas.values():
        if candidata.tipo not in TIPOS:
            continue
        referencia = resolver_referencia(candidata, mapa, linhas)
        if referencia.proposicao.orgao not in comissoes:
            continue
        autores = autores_por_id.get(candidata.id, [])
        relatoria = relatorias.get(referencia.proposicao.id, ResultadoRelatoria())
        id_relator = relatoria.relator.id if relatoria.relator else None
        etiquetas = etiquetar(autores, ids_deputados_novo, id_relator)
        if not etiquetas:
            continue
        selecionados.append(
            (
                (referencia.proposicao.ultimo_status_em, candidata.id),
                _item(
                    candidata, autores, etiquetas, referencia, hoje, relatoria, deputados_relator
                ),
            )
        )
    return [item for _, item in sorted(selecionados, key=lambda par: par[0])]
