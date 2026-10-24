"""Etiquetas do item da pauta, "autoria não verificada" e "leva apensado do NOVO" (§5.8)."""

import json

from monitor_comissoes.pauta.etiquetas import apensados_do_novo, etiquetas
from pauta_sinteticos import PAUTA

NOVO = frozenset({204455, 204528})
LUIZ_LIMA = {"id": 204455, "nome": "Luiz Lima", "partido": None}
OUTRO = {"id": 1, "nome": "Outro", "partido": "PT"}


def test_autoria_novo_pelo_indice():
    assert etiquetas(10, None, {"10": [1, [999]]}, NOVO) == (["autoria NOVO"], False)


def test_autor_hoje_no_novo_mesmo_com_autoria_por_outro_partido():
    assert etiquetas(10, None, {"10": [0, [204528, 999]]}, NOVO) == (["autor hoje no NOVO"], False)


def test_relatoria_novo_pelo_relator_da_pauta_mesmo_sem_partido():
    assert etiquetas(10, LUIZ_LIMA, {"10": [0, []]}, NOVO) == (["relatoria NOVO"], False)
    assert etiquetas(10, OUTRO, {"10": [0, []]}, NOVO) == ([], False)


def test_ordem_fixa_das_tres():
    resultado = etiquetas(10, LUIZ_LIMA, {"10": [1, [204528]]}, NOVO)

    assert resultado == (["autoria NOVO", "autor hoje no NOVO", "relatoria NOVO"], False)


def test_fora_do_indice_e_autoria_nao_verificada_e_a_relatoria_continua():
    assert etiquetas(10, None, {}, NOVO) == ([], True)
    assert etiquetas(10, LUIZ_LIMA, {"11": [1, [204528]]}, NOVO) == (["relatoria NOVO"], True)


def _item_inventario(id, apensado_a=None, etiquetas_=("autoria NOVO",)):
    return {
        "id": id,
        "identificacao": f"PL {id}/2020",
        "link": f"https://www.camara.leg.br/propostas-legislativas/{id}",
        "etiquetas": list(etiquetas_),
        "apensado_a": None if apensado_a is None else {"id": apensado_a},
    }


def test_apensados_do_novo_ordenados_por_id_sem_a_propria():
    inventario = [
        _item_inventario(30, apensado_a=5, etiquetas_=("relatoria NOVO",)),
        _item_inventario(5),
        _item_inventario(12, apensado_a=5),
        _item_inventario(40, apensado_a=6),
    ]

    assert apensados_do_novo(5, inventario) == [
        {
            "id": 12,
            "identificacao": "PL 12/2020",
            "link": "https://www.camara.leg.br/propostas-legislativas/12",
            "etiquetas": ["autoria NOVO"],
        },
        {
            "id": 30,
            "identificacao": "PL 30/2020",
            "link": "https://www.camara.leg.br/propostas-legislativas/30",
            "etiquetas": ["relatoria NOVO"],
        },
    ]
    assert apensados_do_novo(7, inventario) == []


def test_pl_5432_2016_leva_o_pl_3701_2020_no_inventario_salvo():
    inventario = json.loads((PAUTA / "atual.json").read_text(encoding="utf-8"))["itens"]

    assert apensados_do_novo(2086175, inventario) == [
        {
            "id": 2257023,
            "identificacao": "PL 3701/2020",
            "link": "https://www.camara.leg.br/propostas-legislativas/2257023",
            "etiquetas": ["autoria NOVO", "autor hoje no NOVO"],
        }
    ]
