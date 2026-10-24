"""Montagem da checagem da pauta: as reuniões da janela com seus itens. Puro: sem rede nem disco.

Contrato do resultado: specs/007-pauta-reunioes/contracts/pauta-json.md (`checagem.reunioes`).
"""

from dataclasses import dataclass
from datetime import date, timedelta

from ..estoque import ETIQUETA_AUTOR_HOJE, ETIQUETA_AUTORIA, link_oficial
from .etiquetas import apensados_do_novo, etiquetas
from .regras import (
    REUNIAO_DELIBERATIVA,
    chave,
    grupo,
    identificacao,
    proposicao_do_item,
    situacao,
)

DIAS_DA_JANELA = 7
LINK_EVENTO = "https://www.camara.leg.br/evento-legislativo/"


@dataclass(frozen=True)
class Contexto:
    """O que a montagem precisa além dos eventos e das pautas."""

    hoje: date  # dia da checagem em Brasília
    checada_em: str  # ISO com fuso de Brasília
    proposicoes_indice: dict  # `proposicoes` do índice de autoria
    ids_novo: frozenset[int]  # deputados do NOVO em exercício
    inventario: list[dict]  # itens do `atual.json`


def janela(hoje: date) -> tuple[date, date]:
    """De D−7 a D+7, inclusive."""
    return hoje - timedelta(days=DIAS_DA_JANELA), hoje + timedelta(days=DIAS_DA_JANELA)


def _resumo(proposicao: dict | None) -> dict | None:
    if proposicao is None:
        return None
    return {
        "id": proposicao["id"],
        "identificacao": identificacao(proposicao),
        "link": link_oficial(proposicao["id"]),
    }


def _proposicao(proposicao: dict) -> dict:
    return {
        "id": proposicao["id"],
        "tipo": proposicao["siglaTipo"],
        "numero": int(proposicao["numero"]),
        "ano": int(proposicao["ano"]),
        "identificacao": identificacao(proposicao),
        "ementa": proposicao.get("ementa"),
        "link": link_oficial(proposicao["id"]),
    }


def _relator(relator: dict | None) -> dict | None:
    if relator is None:
        return None
    return {"id": relator["id"], "nome": relator["nome"], "partido": relator.get("siglaPartido")}


def _item(item: dict, proposicao: dict, contexto: Contexto) -> dict:
    eh_req = proposicao["siglaTipo"] == "REQ"
    relator = _relator(item["relator"])
    nomes, nao_verificada = etiquetas(
        proposicao["id"], relator, contexto.proposicoes_indice, contexto.ids_novo
    )
    return {
        "ordem": item["ordem"],
        "titulo": item["titulo"],
        "regime": item.get("regime"),
        "proposicao": _proposicao(proposicao),
        "relacionada": _resumo(item["proposicaoRelacionada_"]) if eh_req else None,
        "relator": relator,
        "etiquetas": nomes,
        "autoria_nao_verificada": nao_verificada,
        "leva_apensado_do_novo": apensados_do_novo(proposicao["id"], contexto.inventario),
        "resultado": None,
    }


def _do_novo(item: dict) -> bool:
    """Grupo do NOVO: etiqueta ou apensado do NOVO. "Autoria não verificada" não conta."""
    return bool(item["etiquetas"] or item["leva_apensado_do_novo"])


def _req_listado(item: dict) -> bool:
    """REQ com autoria ou sem autoria verificada. A relatoria NOVO sozinha não lista o REQ."""
    autoria = {ETIQUETA_AUTORIA, ETIQUETA_AUTOR_HOJE} & set(item["etiquetas"])
    return bool(autoria) or item["autoria_nao_verificada"]


def _reuniao(evento: dict, comissao: str, itens_da_pauta: list[dict], contexto: Contexto) -> dict:
    itens_da_pauta = sorted(itens_da_pauta, key=lambda i: i["ordem"])
    listados, requerimentos_listados, requerimentos, outros = [], [], 0, 0
    pauta = []
    for item in itens_da_pauta:
        proposicao = proposicao_do_item(item)
        tipo = proposicao["siglaTipo"] if proposicao is not None else None
        classe = grupo(tipo)
        if classe == "listado":
            listados.append(_item(item, proposicao, contexto))
        elif classe == "req":
            requerimentos += 1
            requerimento = _item(item, proposicao, contexto)
            if _req_listado(requerimento):
                requerimentos_listados.append(requerimento)
        else:
            outros += 1
        pauta.append(
            {
                "chave": chave(item),
                "ordem": item["ordem"],
                "titulo": item["titulo"],
                "proposicao": _resumo(proposicao),
            }
        )
    return {
        "id": evento["id"],
        "comissao": comissao,
        "inicio": evento["dataHoraInicio"],
        "situacao": situacao(evento["situacao"]),
        "situacao_camara": evento["situacao"],
        "link": f"{LINK_EVENTO}{evento['id']}",
        "vista_desde": contexto.checada_em,
        "itens": sorted(listados, key=lambda i: (not _do_novo(i), i["ordem"])),
        "requerimentos": {"total": requerimentos, "listados": requerimentos_listados},
        "outros": {"total": outros},
        "pauta": pauta,
    }


def eh_reuniao_da_comissao(evento: dict, id_orgao: int, inicio: date, fim: date) -> bool:
    """Reunião deliberativa do órgão, com a data de início na janela."""
    dia = date.fromisoformat(evento["dataHoraInicio"][:10])
    return (
        evento["descricaoTipo"] == REUNIAO_DELIBERATIVA
        and any(orgao["id"] == id_orgao for orgao in evento["orgaos"])
        and inicio <= dia <= fim
    )


def selecionar(
    eventos_por_comissao: dict[str, tuple[int, list[dict]]], hoje: date
) -> list[tuple[str, dict]]:
    """Os pares (comissão, evento) que entram na checagem, sem repetir um evento na comissão."""
    inicio, fim = janela(hoje)
    escolhidos = []
    for comissao, (id_orgao, eventos) in eventos_por_comissao.items():
        vistos: set[int] = set()
        for evento in eventos:
            if evento["id"] not in vistos and eh_reuniao_da_comissao(evento, id_orgao, inicio, fim):
                vistos.add(evento["id"])
                escolhidos.append((comissao, evento))
    return escolhidos


def montar_reunioes(
    eventos_por_comissao: dict[str, tuple[int, list[dict]]],
    pautas: dict[int, list[dict]],
    contexto: Contexto,
) -> list[dict]:
    """As reuniões da janela, na ordem `inicio`, comissão (da configuração) e `id`.

    `eventos_por_comissao`: sigla → (id do órgão, eventos da lista do órgão), na ordem da
    configuração. `pautas`: id do evento → itens da pauta (formato da API).
    """
    ordem_comissao = {sigla: posicao for posicao, sigla in enumerate(eventos_por_comissao)}
    reunioes = [
        _reuniao(evento, comissao, pautas[evento["id"]], contexto)
        for comissao, evento in selecionar(eventos_por_comissao, contexto.hoje)
    ]
    return sorted(reunioes, key=lambda r: (r["inicio"], ordem_comissao[r["comissao"]], r["id"]))
