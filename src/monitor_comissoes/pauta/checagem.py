"""Montagem da checagem da pauta: as reuniões da janela com seus itens. Puro: sem rede nem disco.

Contrato do resultado: specs/007-pauta-reunioes/contracts/pauta-json.md (`checagem.reunioes`).
"""

import copy
from collections import Counter
from collections.abc import Callable
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
    resultado,
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


def _item(item: dict, proposicao: dict, realizada: bool, contexto: Contexto) -> dict:
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
        "resultado": resultado(item["situacaoItem"]) if realizada else None,
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
    realizada = situacao(evento["situacao"]) == "realizada"
    listados, requerimentos_listados, requerimentos, outros = [], [], 0, 0
    pauta = []
    for item in itens_da_pauta:
        proposicao = proposicao_do_item(item)
        tipo = proposicao["siglaTipo"] if proposicao is not None else None
        classe = grupo(tipo)
        if classe == "listado":
            listados.append(_item(item, proposicao, realizada, contexto))
        elif classe == "req":
            requerimentos += 1
            requerimento = _item(item, proposicao, realizada, contexto)
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


TIPOS_DE_ALTERACAO = ("item_entrou", "item_saiu", "data_hora", "cancelada", "retirada_da_agenda")


def _alteracao(
    tipo: str,
    reuniao: dict,
    detectada_em: str,
    *,
    item: dict | None = None,
    de: str | None = None,
    para: str | None = None,
    detalhe: str | None = None,
) -> dict:
    """Uma alteração na ordem de campos do contrato; `reuniao` é a da checagem anterior."""
    return {
        "detectada_em": detectada_em,
        "tipo": tipo,
        "reuniao": {
            "id": reuniao["id"],
            "comissao": reuniao["comissao"],
            "inicio": reuniao["inicio"],
            "link": reuniao["link"],
        },
        "item": None
        if item is None
        else {"chave": item["chave"], "titulo": item["titulo"], "proposicao": item["proposicao"]},
        "de": de,
        "para": para,
        "detalhe": detalhe,
    }


def _diferenca(de: list[dict], menos: list[dict]) -> list[dict]:
    """Os itens de `de` que sobram depois de tirar, chave a chave, os de `menos` (multiconjunto)."""
    restantes = Counter(item["chave"] for item in menos)
    sobra = []
    for item in de:
        if restantes[item["chave"]] > 0:
            restantes[item["chave"]] -= 1
        else:
            sobra.append(item)
    return sobra


def _ainda_na_janela(anterior: dict, atual: dict, detectada_em: str) -> list[dict]:
    if atual["situacao"] == "cancelada":
        return [_alteracao("cancelada", anterior, detectada_em)]
    if atual["situacao"] != "convocada":
        # Durante e depois da reunião a lista muda a hora e recebe itens "sobre a mesa": não é
        # pauta alterada (FR-015).
        return []
    alteracoes = [
        _alteracao("item_entrou", anterior, detectada_em, item=item)
        for item in _diferenca(atual["pauta"], anterior["pauta"])
    ]
    alteracoes += [
        _alteracao("item_saiu", anterior, detectada_em, item=item)
        for item in _diferenca(anterior["pauta"], atual["pauta"])
    ]
    if atual["inicio"] != anterior["inicio"]:
        alteracoes.append(
            _alteracao(
                "data_hora", anterior, detectada_em, de=anterior["inicio"], para=atual["inicio"]
            )
        )
    return alteracoes


def _sumiu(
    anterior: dict, evento: dict | None, detectada_em: str, janela_atual: tuple[date, date]
) -> list[dict]:
    """A reunião convocada que não está mais na lista, decidida pelo evento buscado por id (R6)."""
    if evento is None:
        return [_alteracao("retirada_da_agenda", anterior, detectada_em)]
    inicio, fim = janela_atual
    novo_inicio = evento["dataHoraInicio"]
    if not inicio <= date.fromisoformat(novo_inicio[:10]) <= fim:
        return [
            _alteracao("data_hora", anterior, detectada_em, de=anterior["inicio"], para=novo_inicio)
        ]
    if situacao(evento["situacao"]) == "cancelada":
        return [_alteracao("cancelada", anterior, detectada_em)]
    siglas = [orgao.get("sigla") or str(orgao["id"]) for orgao in evento["orgaos"]]
    if evento["descricaoTipo"] != REUNIAO_DELIBERATIVA or anterior["comissao"] not in siglas:
        detalhe = f"agora: {evento['descricaoTipo']} ({', '.join(siglas)})"
        return [_alteracao("retirada_da_agenda", anterior, detectada_em, detalhe=detalhe)]
    # Ainda é reunião deliberativa da comissão, na janela: a lista e o detalhe divergiram (R2).
    # Sem indício de mudança, nada é registrado.
    return []


def _ordem_da_alteracao(alteracao: dict) -> tuple:
    item = alteracao["item"]
    return (
        alteracao["detectada_em"],
        alteracao["reuniao"]["inicio"],
        alteracao["reuniao"]["id"],
        TIPOS_DE_ALTERACAO.index(alteracao["tipo"]),
        item["chave"] if item else "",
    )


def ordenar_alteracoes(alteracoes: list[dict]) -> list[dict]:
    """Na ordem do data-model: momento, início e id da reunião, tipo e chave do item."""
    return sorted(alteracoes, key=_ordem_da_alteracao)


def comparar(
    anterior: list[dict],
    reunioes: list[dict],
    buscar_evento: Callable[[int], dict | None],
    checada_em: str,
    janela_atual: tuple[date, date],
) -> list[dict]:
    """As alterações desta checagem contra as reuniões da última checagem registrada (R6).

    Só a reunião que estava `convocada` é comparada. A que sumiu da lista é buscada por id
    (`buscar_evento` devolve o evento ou None em 404); um erro da busca propaga e falha a checagem.
    """
    atuais = {(r["id"], r["comissao"]): r for r in reunioes}
    alteracoes = []
    for reuniao in anterior:
        if reuniao["situacao"] != "convocada":
            continue
        atual = atuais.get((reuniao["id"], reuniao["comissao"]))
        if atual is not None:
            alteracoes += _ainda_na_janela(reuniao, atual, checada_em)
        else:
            evento = buscar_evento(reuniao["id"])
            alteracoes += _sumiu(reuniao, evento, checada_em, janela_atual)
    return ordenar_alteracoes(alteracoes)


VERSAO_FORMATO = 1
LINHA_DE_BASE = {"motivo": "primeira checagem"}


def montar_checagem(
    checada_em: str,
    janela_atual: tuple[date, date],
    dados_camara_em: str,
    inventario_gerado_em: str,
    deputados_novo: list[dict],
    reunioes: list[dict],
) -> dict:
    """O bloco `checagem` do arquivo do dia, na ordem do contrato."""
    inicio, fim = janela_atual
    return {
        "checada_em": checada_em,
        "janela": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "lote": {"dados_camara_em": dados_camara_em},
        "inventario": {"gerado_em": inventario_gerado_em},
        "deputados_novo_em_exercicio": deputados_novo,
        "reunioes": reunioes,
    }


def montar_arquivo(
    hoje: date,
    comissoes: tuple[str, ...],
    checagem: dict,
    anterior: dict | None,
    alteracoes_novas: list[dict],
) -> dict:
    """O arquivo do dia: esta checagem e as alterações do dia, cumulativas.

    `anterior` é o arquivo de pauta mais recente (do mesmo dia ou de um dia anterior), ou None
    quando não há nenhum: então é a linha de base. O "vista desde" de cada reunião que já estava na
    checagem anterior é copiado de lá. Nada nas entradas é alterado.
    """
    vistas = {}
    alteracoes = list(alteracoes_novas)
    linha_de_base = LINHA_DE_BASE
    if anterior is not None:
        vistas = {
            (r["id"], r["comissao"]): r["vista_desde"] for r in anterior["checagem"]["reunioes"]
        }
        linha_de_base = None
        if anterior["meta"]["data"] == hoje.isoformat():
            alteracoes = anterior["alteracoes"] + alteracoes
            linha_de_base = anterior["meta"]["linha_de_base"]
    reunioes = [
        {**r, "vista_desde": vistas.get((r["id"], r["comissao"]), checagem["checada_em"])}
        for r in checagem["reunioes"]
    ]
    return copy.deepcopy(
        {
            "meta": {
                "versao_formato": VERSAO_FORMATO,
                "data": hoje.isoformat(),
                "comissoes": list(comissoes),
                "linha_de_base": linha_de_base,
            },
            "checagem": {**checagem, "reunioes": reunioes},
            "alteracoes": ordenar_alteracoes(alteracoes),
        }
    )
