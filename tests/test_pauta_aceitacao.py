"""Casos de aceitação da PAU com as pautas reais salvas, ponta a ponta pela CLI (SC-001 a SC-004).

O índice tem todas as proposições das pautas salvas; as autorias vêm do inventário de 24/10/2026
(o mesmo lote), quando a proposição está nele. Os deputados do NOVO em exercício são os da
fixture (Luiz Lima, 204455, entre eles). O manifesto das fixtures é conferido em
test_pauta_sinteticos.py.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from monitor_comissoes.pauta.cli import main
from pauta_sinteticos import PAUTA, TransportePauta, indice
from test_pauta_cli import JANELA_CREDN, MANHA, TARDE, ler, preparar_ambiente

BRASILIA = timezone(timedelta(hours=-3))
DIA_DE_ABRIL = datetime(2026, 4, 15, 15, 17, 2, tzinfo=BRASILIA)
DIA_DE_DEZEMBRO = datetime(2025, 12, 3, 15, 17, 2, tzinfo=BRASILIA)
ROTULOS = {
    "retirado de pauta",
    "vista",
    "aprovado",
    "rejeitado",
    "não apreciado",
    "sem registro",
    "outro",
}
LINK = "https://www.camara.leg.br/"
PL_5432, PL_3701, REQ_17 = 2086175, 2257023, 2615445


def indice_do_lote():
    """As proposições das pautas salvas; autoria e autores do inventário, se estiverem nele."""
    from monitor_comissoes.pauta.regras import proposicao_do_item

    inventario = {
        item["id"]: item
        for item in json.loads((PAUTA / "atual.json").read_text(encoding="utf-8"))["itens"]
    }
    proposicoes = {}
    for arquivo in (PAUTA / "pautas").glob("*.json"):
        for item in json.loads(arquivo.read_text(encoding="utf-8"))["dados"]:
            proposicao = proposicao_do_item(item)
            if proposicao is None:
                continue
            do_inventario = inventario.get(proposicao["id"])
            if do_inventario is None:
                proposicoes[proposicao["id"]] = (0, [])
            else:
                proposicoes[proposicao["id"]] = (
                    int("autoria NOVO" in do_inventario["etiquetas"]),
                    [autor["id_deputado"] for autor in do_inventario["autores"]],
                )
    return indice(proposicoes)


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    preparar_ambiente(tmp_path)
    (tmp_path / "cache" / "indice-autoria.json").write_text(
        json.dumps(indice_do_lote()), encoding="utf-8"
    )
    return tmp_path


def checar(raiz, agora, transporte=None):
    assert main(["checar"], transporte=transporte or TransportePauta(), agora=agora) == 0
    data = agora.astimezone(BRASILIA).date().isoformat()
    return ler(raiz / "data" / "pautas" / f"{data}.json")


def transporte_de_outubro():
    transporte = TransportePauta()
    transporte.respostas[JANELA_CREDN] = {"dados": [], "links": []}
    transporte.cabecalhos[JANELA_CREDN] = {"x-total-count": "0"}
    return transporte


def reuniao(arquivo, id_evento):
    return next(r for r in arquivo["checagem"]["reunioes"] if r["id"] == id_evento)


def item_de(reuniao_, id_proposicao):
    return next(i for i in reuniao_["itens"] if i["proposicao"]["id"] == id_proposicao)


def links(no):
    """Todos os valores de `link` do documento, em qualquer profundidade."""
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave == "link":
                yield valor
            else:
                yield from links(valor)
    elif isinstance(no, list):
        for valor in no:
            yield from links(valor)


# --- (a) a CE em 24/10/2026 -----------------------------------------------------------------


def test_a_reuniao_de_28_10_com_19_pl_listados_e_1_req_contado(ambiente, capsys):
    arquivo = checar(ambiente, MANHA, transporte_de_outubro())

    [r83091] = arquivo["checagem"]["reunioes"]
    assert r83091["id"] == 83091 and r83091["comissao"] == "CE"
    assert r83091["situacao"] == "convocada" and r83091["inicio"].startswith("2026-10-28")
    assert len(r83091["itens"]) == 19
    assert {i["proposicao"]["tipo"] for i in r83091["itens"]} == {"PL"}
    assert r83091["requerimentos"] == {"total": 1, "listados": []}
    assert all(i["proposicao"]["link"].startswith(LINK) for i in r83091["itens"])
    assert all(i["resultado"] is None for i in r83091["itens"])  # ainda não realizada


# --- (b) a CE em 15/04/2026 -----------------------------------------------------------------


def test_o_pl_5432_leva_o_apensado_do_novo_e_vem_primeiro(ambiente, capsys):
    r81555 = reuniao(checar(ambiente, DIA_DE_ABRIL), 81555)

    pl_5432 = item_de(r81555, PL_5432)
    assert pl_5432["proposicao"]["identificacao"] == "PL 5432/2016"
    [apensado] = pl_5432["leva_apensado_do_novo"]
    assert apensado["id"] == PL_3701 and apensado["identificacao"] == "PL 3701/2020"
    assert apensado["etiquetas"] == ["autoria NOVO", "autor hoje no NOVO"]
    assert apensado["link"] == f"{LINK}propostas-legislativas/{PL_3701}"
    do_novo = [i for i in r81555["itens"] if i["etiquetas"] or i["leva_apensado_do_novo"]]
    assert r81555["itens"][: len(do_novo)] == do_novo
    assert pl_5432 in do_novo


def test_o_req_17_so_contado(ambiente, capsys):
    r81555 = reuniao(checar(ambiente, DIA_DE_ABRIL), 81555)

    assert r81555["requerimentos"]["total"] == 5
    assert REQ_17 not in {r["proposicao"]["id"] for r in r81555["requerimentos"]["listados"]}
    assert REQ_17 not in {i["proposicao"]["id"] for i in r81555["itens"]}


def test_o_pl_3464_com_relatoria_do_novo(ambiente, capsys):
    r81555 = reuniao(checar(ambiente, DIA_DE_ABRIL), 81555)

    item = next(i for i in r81555["itens"] if i["proposicao"]["identificacao"] == "PL 3464/2025")
    assert item["relator"]["id"] == 204455 and item["relator"]["nome"] == "Luiz Lima"
    assert "relatoria NOVO" in item["etiquetas"]


def test_todo_item_das_realizadas_tem_resultado_com_texto(ambiente, capsys):
    arquivo = checar(ambiente, DIA_DE_ABRIL)

    realizadas = [r for r in arquivo["checagem"]["reunioes"] if r["situacao"] == "realizada"]
    assert {r["id"] for r in realizadas} >= {81555}
    for r in realizadas:
        for item in r["itens"]:
            assert item["resultado"]["rotulo"] in ROTULOS
            assert "texto" in item["resultado"]
    pl_5432 = item_de(reuniao(arquivo, 81555), PL_5432)
    assert pl_5432["resultado"]["rotulo"] == "retirado de pauta"
    assert pl_5432["resultado"]["texto"].startswith("Retirado de pauta")


# --- (c) a reunião cancelada e a CREDN ------------------------------------------------------


def test_a_reuniao_cancelada_e_registrada(ambiente, capsys):
    arquivo = checar(ambiente, DIA_DE_DEZEMBRO)

    cancelada = reuniao(arquivo, 80732)
    assert cancelada["situacao"] == "cancelada" and cancelada["comissao"] == "CE"
    assert all(i["resultado"] is None for i in cancelada["itens"])
    termo = reuniao(arquivo, 80594)
    assert termo["situacao"] == "realizada" and termo["comissao"] == "CREDN"
    assert {i["resultado"]["rotulo"] for i in termo["itens"]} == {"sem registro"}


def test_a_credn_com_msc_e_pdl_listados(ambiente, capsys):
    r81483 = reuniao(checar(ambiente, DIA_DE_ABRIL), 81483)

    assert r81483["comissao"] == "CREDN"
    tipos = [i["proposicao"]["tipo"] for i in r81483["itens"]]
    assert tipos.count("MSC") == 3 and tipos.count("PDL") == 1


# --- (d) links oficiais ---------------------------------------------------------------------


@pytest.mark.parametrize("agora", [DIA_DE_ABRIL, DIA_DE_DEZEMBRO])
def test_todo_link_e_da_camara(ambiente, capsys, agora):
    arquivo = checar(ambiente, agora)

    reunioes = arquivo["checagem"]["reunioes"]
    assert reunioes
    for r in reunioes:
        assert r["link"].startswith(f"{LINK}evento-legislativo/")
        for item in r["itens"]:
            assert item["proposicao"]["link"].startswith(f"{LINK}propostas-legislativas/")
            for apensado in item["leva_apensado_do_novo"]:
                assert apensado["link"].startswith(f"{LINK}propostas-legislativas/")
    assert all(link.startswith(LINK) for link in links(arquivo))


def test_toda_alteracao_tem_link_da_camara(ambiente, capsys):
    checar(ambiente, MANHA, transporte_de_outubro())
    transporte = transporte_de_outubro()
    itens = json.loads((PAUTA / "pautas" / "83091.json").read_text(encoding="utf-8"))["dados"]
    transporte.respostas["pautas/83091"] = {"dados": itens[1:], "links": []}

    arquivo = checar(ambiente, TARDE, transporte)

    [alteracao] = arquivo["alteracoes"]
    assert alteracao["tipo"] == "item_saiu"
    assert alteracao["reuniao"]["link"] == f"{LINK}evento-legislativo/83091"
    assert all(link.startswith(LINK) for link in links(alteracao))
