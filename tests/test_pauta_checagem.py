"""Montagem das reuniões da janela: filtro, ordem, itens listados, contagens e a pauta completa."""

import json
from datetime import date

import pytest

from monitor_comissoes.pauta.checagem import Contexto, janela, montar_reunioes
from pauta_sinteticos import PAUTA, evento, item_pauta, itens_reais

HOJE = date(2026, 10, 24)
CHECADA_EM = "2026-10-24T05:49:12-03:00"
CAMPOS_REUNIAO = [
    "id",
    "comissao",
    "inicio",
    "situacao",
    "situacao_camara",
    "link",
    "vista_desde",
    "itens",
    "requerimentos",
    "outros",
    "pauta",
]
CAMPOS_ITEM = [
    "ordem",
    "titulo",
    "regime",
    "proposicao",
    "relacionada",
    "relator",
    "etiquetas",
    "autoria_nao_verificada",
    "leva_apensado_do_novo",
    "resultado",
]


def contexto(hoje=HOJE, proposicoes=None, ids_novo=(), inventario=()):
    return Contexto(
        hoje=hoje,
        checada_em=CHECADA_EM,
        proposicoes_indice=proposicoes or {},
        ids_novo=frozenset(ids_novo),
        inventario=list(inventario),
    )


def eventos_salvos(nome):
    return json.loads((PAUTA / "eventos" / f"{nome}.json").read_text(encoding="utf-8"))["dados"]


def test_janela_de_d_menos_7_a_d_mais_7():
    assert janela(HOJE) == (date(2026, 10, 17), date(2026, 10, 31))


def test_reuniao_83091_com_19_pl_e_o_req_70_contado():
    eventos = {"CE": (2009, eventos_salvos("2009-2026-10-17-2026-10-31"))}

    [reuniao] = montar_reunioes(eventos, {83091: itens_reais(83091)}, contexto())

    assert list(reuniao) == CAMPOS_REUNIAO
    assert reuniao["id"] == 83091
    assert reuniao["comissao"] == "CE"
    assert reuniao["inicio"] == "2026-10-28T10:00"
    assert reuniao["situacao"] == "convocada"
    assert reuniao["situacao_camara"] == "Convocada"
    assert reuniao["link"] == "https://www.camara.leg.br/evento-legislativo/83091"
    assert reuniao["vista_desde"] == CHECADA_EM
    assert len(reuniao["itens"]) == 19
    assert all(i["proposicao"]["tipo"] == "PL" for i in reuniao["itens"])
    assert reuniao["requerimentos"]["total"] == 1
    assert reuniao["outros"] == {"total": 0}
    assert len(reuniao["pauta"]) == 20
    req = next(p for p in reuniao["pauta"] if p["chave"] == "p:2645503")
    assert req == {
        "chave": "p:2645503",
        "ordem": req["ordem"],
        "titulo": req["titulo"],
        "proposicao": {
            "id": 2645503,
            "identificacao": "REQ 70/2026",
            "link": "https://www.camara.leg.br/propostas-legislativas/2645503",
        },
    }


def test_item_listado_tem_os_campos_do_contrato():
    eventos = {"CE": (2009, eventos_salvos("2009-2026-04-08-2026-04-22"))}
    reunioes = montar_reunioes(
        eventos, {81366: itens_reais(81366), 81555: itens_reais(81555)}, contexto(date(2026, 4, 15))
    )

    reuniao = next(r for r in reunioes if r["id"] == 81555)
    item = next(i for i in reuniao["itens"] if i["proposicao"]["id"] == 2086175)

    assert list(item) == CAMPOS_ITEM
    assert list(item["proposicao"]) == [
        "id",
        "tipo",
        "numero",
        "ano",
        "identificacao",
        "ementa",
        "link",
    ]
    assert item["proposicao"]["identificacao"] == "PL 5432/2016"
    assert item["proposicao"]["numero"] == 5432 and item["proposicao"]["ano"] == 2016
    assert item["proposicao"]["link"] == "https://www.camara.leg.br/propostas-legislativas/2086175"
    assert item["relacionada"] is None  # só em REQ
    relator_lima = next(i for i in reuniao["itens"] if i["titulo"].startswith("PL 3464/2025"))
    assert relator_lima["relator"] == {"id": 204455, "nome": "Luiz Lima", "partido": None}


def test_req_17_so_contado_e_o_pl_1778_nao_vira_item():
    eventos = {"CE": (2009, eventos_salvos("2009-2026-04-08-2026-04-22"))}
    reunioes = montar_reunioes(
        eventos,
        {81366: itens_reais(81366), 81555: itens_reais(81555)},
        contexto(date(2026, 4, 15), indice_de(itens_reais(81555))),
    )

    reuniao = next(r for r in reunioes if r["id"] == 81555)

    assert 2247358 not in {i["proposicao"]["id"] for i in reuniao["itens"]}
    assert "p:2615445" in {p["chave"] for p in reuniao["pauta"]}
    assert reuniao["requerimentos"]["listados"] == []  # nenhum REQ com autoria do NOVO


def test_soma_de_listados_req_e_outros_e_o_total_da_pauta():
    eventos = {"CREDN": (2018, eventos_salvos("2018-2026-04-08-2026-04-22"))}
    pautas = {81483: itens_reais(81483), 81609: itens_reais(81609)}

    for reuniao in montar_reunioes(eventos, pautas, contexto(date(2026, 4, 15))):
        total = (
            len(reuniao["itens"]) + reuniao["requerimentos"]["total"] + reuniao["outros"]["total"]
        )
        assert total == len(reuniao["pauta"]) == len(pautas[reuniao["id"]])


def test_msc_e_pdl_sao_listados():
    eventos = {"CREDN": (2018, eventos_salvos("2018-2026-04-08-2026-04-22"))}
    pautas = {81483: itens_reais(81483), 81609: itens_reais(81609)}

    reuniao = next(
        r for r in montar_reunioes(eventos, pautas, contexto(date(2026, 4, 15))) if r["id"] == 81483
    )

    tipos = [i["proposicao"]["tipo"] for i in reuniao["itens"]]
    assert tipos.count("MSC") == 3 and tipos.count("PDL") == 1


def test_so_reuniao_deliberativa_e_so_dentro_da_janela():
    eventos = [
        evento(1, "2026-10-16T10:00"),  # D-8
        evento(2, "2026-10-17T00:00"),  # D-7
        evento(3, "2026-10-24T10:00"),  # D
        evento(4, "2026-10-31T23:59"),  # D+7
        evento(5, "2026-11-01T09:00"),  # D+8
        evento(6, "2026-10-24T09:30", tipo="Mesa Redonda"),
        evento(7, "2026-10-24T11:00", situacao="Cancelada"),
    ]
    pautas = {n: [] for n in range(1, 8)}

    reunioes = montar_reunioes({"CE": (2009, eventos)}, pautas, contexto())

    assert [r["id"] for r in reunioes] == [2, 3, 7, 4]
    assert next(r for r in reunioes if r["id"] == 7)["situacao"] == "cancelada"


def test_ordem_por_inicio_comissao_da_configuracao_e_id():
    ce = [
        evento(20, "2026-10-28T10:00"),
        evento(10, "2026-10-28T10:00"),
        evento(5, "2026-10-29T09:00"),
    ]
    credn = [evento(1, "2026-10-28T10:00", orgao=2018), evento(2, "2026-10-27T10:00", orgao=2018)]
    pautas = {n: [] for n in (1, 2, 5, 10, 20)}

    reunioes = montar_reunioes({"CE": (2009, ce), "CREDN": (2018, credn)}, pautas, contexto())

    assert [(r["id"], r["comissao"]) for r in reunioes] == [
        (2, "CREDN"),
        (10, "CE"),
        (20, "CE"),
        (1, "CREDN"),
        (5, "CE"),
    ]


def test_evento_das_duas_comissoes_aparece_uma_vez_em_cada():
    conjunta = evento(9, "2026-10-28T10:00")
    conjunta["orgaos"].append({**conjunta["orgaos"][0], "id": 2018, "sigla": "CREDN"})
    eventos = {"CE": (2009, [conjunta]), "CREDN": (2018, [conjunta])}

    reunioes = montar_reunioes(eventos, {9: []}, contexto())

    assert [(r["id"], r["comissao"]) for r in reunioes] == [(9, "CE"), (9, "CREDN")]


def test_evento_de_outro_orgao_na_lista_e_ignorado():
    reunioes = montar_reunioes(
        {"CE": (2009, [evento(9, "2026-10-28T10:00", orgao=2018)])}, {9: []}, contexto()
    )

    assert reunioes == []


def test_pauta_vazia_e_dia_sem_reuniao():
    [vazia] = montar_reunioes({"CE": (2009, [evento(1, "2026-10-28T10:00")])}, {1: []}, contexto())

    assert vazia["itens"] == [] and vazia["pauta"] == []
    assert vazia["requerimentos"] == {"total": 0, "listados": []}
    assert vazia["outros"] == {"total": 0}
    assert montar_reunioes({"CE": (2009, [])}, {}, contexto()) == []


def test_pauta_mantem_a_ordem_e_os_itens_repetidos_e_sem_proposicao():
    itens = [
        item_pauta(2, proposicao=(7, "PL 7/2020")),
        item_pauta(1, proposicao=(7, "PL 7/2020")),
        item_pauta(3),
    ]

    [reuniao] = montar_reunioes(
        {"CE": (2009, [evento(1, "2026-10-28T10:00")])}, {1: itens}, contexto()
    )

    assert [(p["chave"], p["ordem"]) for p in reuniao["pauta"]] == [
        ("p:7", 1),
        ("p:7", 2),
        ("t:Item 3", 3),
    ]
    assert reuniao["pauta"][2]["proposicao"] is None
    assert [i["ordem"] for i in reuniao["itens"]] == [1, 2]
    assert reuniao["outros"] == {"total": 1}


@pytest.mark.parametrize("tipo", ["Audiência Pública", "Reunião Deliberativa Extraordinária"])
def test_outros_tipos_de_evento_ficam_de_fora(tipo):
    assert (
        montar_reunioes(
            {"CE": (2009, [evento(1, "2026-10-28T10:00", tipo=tipo)])}, {1: []}, contexto()
        )
        == []
    )


# --- US2: etiquetas e grupo do NOVO ------------------------------------------------------------

DIA_81555 = date(2026, 4, 15)
REQ_17, PL_1778, PL_5432, PL_3464, PL_778 = 2615445, 2247358, 2086175, 2537283, 2481268


def indice_de(itens, **autorias):
    """Índice com todas as proposições dos itens em `[0, []]`, salvo `autorias` (id → entrada)."""
    from monitor_comissoes.pauta.regras import proposicao_do_item

    proposicoes = {}
    for item in itens:
        proposicao = proposicao_do_item(item)
        if proposicao is not None:
            proposicoes[str(proposicao["id"])] = [0, []]
    proposicoes.update({chave.removeprefix("p"): valor for chave, valor in autorias.items()})
    return proposicoes


def inventario_salvo():
    return json.loads((PAUTA / "atual.json").read_text(encoding="utf-8"))["itens"]


def reuniao_81555(proposicoes, ids_novo=(204455, 204528), inventario=None):
    eventos = {"CE": (2009, eventos_salvos("2009-2026-04-08-2026-04-22"))}
    ctx = contexto(
        DIA_81555,
        proposicoes,
        ids_novo,
        inventario_salvo() if inventario is None else inventario,
    )
    reunioes = montar_reunioes(eventos, {81366: itens_reais(81366), 81555: itens_reais(81555)}, ctx)
    return next(r for r in reunioes if r["id"] == 81555)


def test_grupo_do_novo_primeiro_e_a_ordem_dentro_de_cada_grupo():
    reuniao = reuniao_81555(indice_de(itens_reais(81555)))

    ordens = [i["ordem"] for i in reuniao["itens"]]
    assert ordens[:2] == [10, 28]  # PL 5432/2016 (leva apensado) e PL 3464/2025 (relatoria)
    assert ordens[2:] == sorted(ordens[2:])
    pl_5432 = reuniao["itens"][0]
    assert pl_5432["etiquetas"] == []
    assert [a["id"] for a in pl_5432["leva_apensado_do_novo"]] == [2257023]
    assert reuniao["itens"][1]["etiquetas"] == ["relatoria NOVO"]


def test_autoria_novo_e_autor_hoje_vindos_do_indice():
    proposicoes = indice_de(itens_reais(81555), p2481268=[1, [204528, 3]])

    item = next(i for i in reuniao_81555(proposicoes)["itens"] if i["proposicao"]["id"] == PL_778)

    assert item["etiquetas"] == ["autoria NOVO", "autor hoje no NOVO"]
    assert item["autoria_nao_verificada"] is False


def test_autoria_nao_verificada_nao_poe_no_grupo_do_novo():
    proposicoes = indice_de(itens_reais(81555))
    del proposicoes[str(PL_778)]

    reuniao = reuniao_81555(proposicoes)

    item = next(i for i in reuniao["itens"] if i["proposicao"]["id"] == PL_778)
    assert item["autoria_nao_verificada"] is True
    assert item["etiquetas"] == []
    assert [i["ordem"] for i in reuniao["itens"]][:2] == [10, 28]


def test_req_listado_com_autoria_e_relacionada_preenchida():
    proposicoes = indice_de(itens_reais(81555), p2615445=[1, []])

    reuniao = reuniao_81555(proposicoes)

    [req] = reuniao["requerimentos"]["listados"]
    assert req["proposicao"]["identificacao"] == "REQ 17/2026"
    assert req["etiquetas"] == ["autoria NOVO"]
    assert req["relacionada"] == {
        "id": PL_1778,
        "identificacao": "PL 1778/2020",
        "link": f"https://www.camara.leg.br/propostas-legislativas/{PL_1778}",
    }
    assert reuniao["requerimentos"]["total"] == 5
    assert PL_1778 not in {i["proposicao"]["id"] for i in reuniao["itens"]}


def test_req_com_autor_hoje_no_novo_e_listado():
    proposicoes = indice_de(itens_reais(81555), p2613776=[0, [204455]])

    [req] = reuniao_81555(proposicoes)["requerimentos"]["listados"]

    assert req["etiquetas"] == ["autor hoje no NOVO"]


def test_req_so_com_relatoria_novo_nao_e_listado():
    # O relator do REQ 17/2026 é a deputada 220629; aqui ela conta como do NOVO.
    reuniao = reuniao_81555(indice_de(itens_reais(81555)), ids_novo=(204455, 220629))

    assert reuniao["requerimentos"]["listados"] == []
    assert reuniao["requerimentos"]["total"] == 5


def test_req_fora_do_indice_e_listado_como_autoria_nao_verificada():
    proposicoes = indice_de(itens_reais(81555))
    del proposicoes[str(REQ_17)]

    [req] = reuniao_81555(proposicoes)["requerimentos"]["listados"]

    assert req["autoria_nao_verificada"] is True
    assert req["etiquetas"] == []


def test_req_listados_na_ordem_da_pauta():
    proposicoes = indice_de(itens_reais(81555), p2615445=[1, []], p2613778=[1, []])

    listados = reuniao_81555(proposicoes)["requerimentos"]["listados"]

    assert [r["ordem"] for r in listados] == [2, 5]


def test_etiqueta_nao_inclui_nem_exclui_item():
    sem = reuniao_81555(indice_de(itens_reais(81555)), ids_novo=(), inventario=[])
    com = reuniao_81555(indice_de(itens_reais(81555), p2615445=[1, [204528]]))

    for reuniao in (sem, com):
        assert len(reuniao["itens"]) == 25
        assert reuniao["requerimentos"]["total"] == 5
        assert reuniao["outros"]["total"] == 0
        assert len(reuniao["pauta"]) == 30


# --- US3: resultado só em reunião realizada ----------------------------------------------------


def test_em_reuniao_realizada_todo_item_listado_tem_resultado():
    proposicoes = indice_de(itens_reais(81555), p2615445=[1, []])

    reuniao = reuniao_81555(proposicoes)

    assert reuniao["situacao"] == "realizada"
    for item in reuniao["itens"] + reuniao["requerimentos"]["listados"]:
        assert item["resultado"]["texto"] == next(
            i["situacaoItem"] for i in itens_reais(81555) if i["ordem"] == item["ordem"]
        )
    pl_5432 = next(i for i in reuniao["itens"] if i["proposicao"]["id"] == PL_5432)
    assert pl_5432["resultado"]["rotulo"] == "retirado de pauta"
    [req] = reuniao["requerimentos"]["listados"]
    assert req["resultado"] == {"rotulo": "aprovado", "texto": "Aprovado o Requerimento."}


def test_reuniao_termo_sem_texto_e_sem_registro():
    eventos = {"CREDN": (2018, eventos_salvos("2018-2025-11-26-2025-12-10"))}
    pautas = {n: itens_reais(n) for n in (80375, 80376, 80594, 80712)}

    reunioes = montar_reunioes(eventos, pautas, contexto(date(2025, 12, 3)))

    termo = next(r for r in reunioes if r["id"] == 80594)
    assert termo["situacao_camara"] == "Encerrada (Termo)"
    assert {i["resultado"]["rotulo"] for i in termo["itens"]} == {"sem registro"}


@pytest.mark.parametrize("texto_situacao", ["Convocada", "Cancelada", "Em Andamento"])
def test_fora_de_reuniao_realizada_o_resultado_e_nulo(texto_situacao):
    itens = [item_pauta(1, proposicao=(7, "PL 7/2020"), situacao_item="Aprovado o Parecer.")]
    reuniao_evento = evento(1, "2026-10-24T10:00", situacao=texto_situacao)

    [reuniao] = montar_reunioes({"CE": (2009, [reuniao_evento])}, {1: itens}, contexto())

    assert reuniao["itens"][0]["resultado"] is None
