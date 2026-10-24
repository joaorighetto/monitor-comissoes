"""Regras puras da pauta: situação, proposição do item (§5.8), grupo, chave e identificação."""

import pytest

from monitor_comissoes.pauta.regras import (
    TIPOS_LISTADOS,
    chave,
    grupo,
    identificacao,
    proposicao_do_item,
    situacao,
)
from pauta_sinteticos import item_pauta, item_real, itens_reais


@pytest.mark.parametrize(
    ("texto", "esperada"),
    [
        ("Convocada", "convocada"),
        ("Encerrada", "realizada"),
        ("Encerrada (Final)", "realizada"),
        ("Encerrada (Termo)", "realizada"),
        ("Cancelada", "cancelada"),
        ("Em Andamento", "outra"),
        ("Suspensa", "outra"),
        ("", "outra"),
    ],
)
def test_situacao_pela_tabela_do_r3(texto, esperada):
    assert situacao(texto) == esperada


# Pares reais (proposicao_ → proposicaoRelacionada_) das fixtures: (evento, ordem, id esperado).
@pytest.mark.parametrize(
    ("evento", "ordem", "esperado", "par"),
    [
        (80265, 13, 2328532, "PRL→PL: a relacionada"),
        (80375, 17, 2183917, "PRL→MSC: a relacionada"),
        (81483, 11, 2526896, "PRL→PDL: a relacionada"),
        (80712, 14, 2312624, "PRV→PL: a relacionada"),
        (80265, 6, 2580002, "REQ→REQ: o próprio REQ"),
        (81555, 5, 2615445, "REQ 17/2026→PL 1778/2020: o próprio REQ"),
        (80265, 12, 2580670, "REQ 217/2025→PEC 573/2006: o próprio REQ"),
        (81555, 7, 2481717, "PL sem relacionada: a proposicao_"),
    ],
)
def test_proposicao_do_item_com_pares_reais(evento, ordem, esperado, par):
    assert proposicao_do_item(item_real(evento, ordem))["id"] == esperado, par


def test_req_70_aponta_para_o_proprio_req_e_nao_para_o_req_63():
    req = next(i for i in itens_reais(83091) if "REQ" in i["titulo"])

    assert req["proposicaoRelacionada_"]["siglaTipo"] == "REQ"
    assert proposicao_do_item(req)["id"] == 2645503


def test_item_sem_proposicao():
    assert proposicao_do_item(item_pauta(1)) is None
    so_relacionada = item_pauta(1, relacionada=(9, "PL 9/2020"))
    assert proposicao_do_item(so_relacionada)["id"] == 9


@pytest.mark.parametrize(
    ("tipo", "esperado"),
    [
        ("PL", "listado"),
        ("PLP", "listado"),
        ("PEC", "listado"),
        ("MSC", "listado"),
        ("PDL", "listado"),
        ("REQ", "req"),
        ("PRL", "outro"),
        ("SOR", "outro"),
        (None, "outro"),
    ],
)
def test_grupo_pelo_tipo(tipo, esperado):
    assert grupo(tipo) == esperado
    assert TIPOS_LISTADOS == ("PL", "PLP", "PEC", "MSC", "PDL")


def test_chave_pela_proposicao_do_item_ou_pelo_titulo():
    assert chave(item_real(80265, 13)) == "p:2328532"
    assert chave(item_real(81555, 5)) == "p:2615445"
    assert chave(item_pauta(3)) == "t:Item 3"


def test_identificacao_com_numero_e_ano_em_texto_ou_inteiro():
    relacionada = item_real(81555, 5)["proposicaoRelacionada_"]
    assert relacionada["numero"] == "1778"
    assert identificacao(relacionada) == "PL 1778/2020"
    assert identificacao(item_real(81555, 5)["proposicao_"]) == "REQ 17/2026"
    assert identificacao({"siglaTipo": "PEC", "numero": "0573", "ano": "2006"}) == "PEC 573/2006"
