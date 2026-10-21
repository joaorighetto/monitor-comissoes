"""Leitura e conferência das entradas da página (PAG, R10 e R6): falha com o nome do arquivo."""

import copy
import json
from datetime import date

import pytest

import pagina_sinteticos as p
from monitor_comissoes.erros import FalhaDePagina
from monitor_comissoes.pagina import entradas
from monitor_comissoes.saida import serializar
from pagina_sinteticos import FIXTURES

REAL = FIXTURES / "atual-real.json"


def gravar(caminho, documento):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        documento if isinstance(documento, str) else serializar(documento),
        encoding="utf-8",
        newline="\n",
    )
    return caminho


def retrato_alterado(tmp_path, alterar):
    documento = copy.deepcopy(p.retrato_real())
    alterar(documento)
    return gravar(tmp_path / "atual.json", documento)


def falha_de(funcao, *args):
    with pytest.raises(FalhaDePagina) as erro:
        funcao(*args)
    return str(erro.value)


# ---------- atual.json ----------


def test_ler_atual_devolve_o_retrato_real():
    atual = entradas.ler_atual(REAL)

    assert atual["meta"]["total_itens"] == 105
    assert len(atual["itens"]) == 105


def test_ler_atual_aceita_a_versao_3(tmp_path):
    retrato = p.retrato_com([p.item_completo(id=1), p.item_completo(id=2, comissao="CREDN")])
    caminho = gravar(tmp_path / "atual.json", retrato)

    assert entradas.ler_atual(caminho)["meta"]["versao_formato"] == 3


def test_arquivo_ausente_cita_o_nome(tmp_path):
    caminho = tmp_path / "atual.json"

    motivo = falha_de(entradas.ler_atual, caminho)

    assert "atual.json" in motivo and "não existe" in motivo


def test_json_ilegivel_cita_o_nome(tmp_path):
    caminho = gravar(tmp_path / "atual.json", "{ não é json")

    motivo = falha_de(entradas.ler_atual, caminho)

    assert str(caminho) in motivo and "JSON" in motivo


def test_documento_que_nao_e_objeto_falha(tmp_path):
    caminho = gravar(tmp_path / "atual.json", "[1, 2]")

    assert "objeto" in falha_de(entradas.ler_atual, caminho)


@pytest.mark.parametrize("versao", [1, 4, None, True, "2"])
def test_versao_de_formato_desconhecida_falha(tmp_path, versao):
    caminho = retrato_alterado(tmp_path, lambda d: d["meta"].__setitem__("versao_formato", versao))

    motivo = falha_de(entradas.ler_atual, caminho)

    assert str(caminho) in motivo and "versao_formato" in motivo


def test_o_arquivo_de_formato_4_da_fixture_falha():
    motivo = falha_de(entradas.ler_atual, FIXTURES / "atual-formato-4.json")

    assert "atual-formato-4.json" in motivo and "4" in motivo


def test_sem_meta_falha(tmp_path):
    caminho = retrato_alterado(tmp_path, lambda d: d.pop("meta"))

    assert "versao_formato" in falha_de(entradas.ler_atual, caminho)


@pytest.mark.parametrize(
    "campo", ["gerado_em", "dados_camara_em", "comissoes", "total_por_comissao"]
)
def test_campo_do_meta_ausente_falha(tmp_path, campo):
    caminho = retrato_alterado(tmp_path, lambda d: d["meta"].pop(campo))

    assert f"meta.{campo}" in falha_de(entradas.ler_atual, caminho)


def test_instante_do_meta_invalido_falha(tmp_path):
    caminho = retrato_alterado(tmp_path, lambda d: d["meta"].__setitem__("gerado_em", "ontem"))

    assert "meta.gerado_em" in falha_de(entradas.ler_atual, caminho)


@pytest.mark.parametrize("itens", [None, "x", []])
def test_itens_ausentes_nao_lista_ou_vazios_falham(tmp_path, itens):
    def alterar(d):
        d["itens"] = itens
        d["meta"]["total_itens"] = 0

    caminho = retrato_alterado(tmp_path, alterar)

    assert "itens" in falha_de(entradas.ler_atual, caminho)


def test_total_itens_diferente_do_tamanho_da_lista_falha(tmp_path):
    caminho = retrato_alterado(tmp_path, lambda d: d["meta"].__setitem__("total_itens", 104))

    assert "total_itens" in falha_de(entradas.ler_atual, caminho)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("id", "1"),
        ("id", True),
        ("identificacao", ""),
        ("ementa", None),
        ("link", None),
        ("comissao", 3),
        ("situacao", " "),
        ("autores", "x"),
        ("etiquetas", None),
        ("parado_ha_dias", "10"),
        ("parado_ha_dias", True),
        ("principal_nao_localizada", "não"),
    ],
)
def test_campo_do_item_com_tipo_errado_falha(tmp_path, campo, valor):
    caminho = retrato_alterado(tmp_path, lambda d: d["itens"][3].__setitem__(campo, valor))

    motivo = falha_de(entradas.ler_atual, caminho)

    assert f"itens[3].{campo}" in motivo and str(caminho) in motivo


@pytest.mark.parametrize("campo", ["id", "ementa", "autores", "relator", "apensado_a"])
def test_campo_do_item_ausente_falha(tmp_path, campo):
    caminho = retrato_alterado(tmp_path, lambda d: d["itens"][0].pop(campo))

    assert f"itens[0].{campo}" in falha_de(entradas.ler_atual, caminho)


def test_autor_sem_nome_ou_sem_partido_falha(tmp_path):
    caminho = retrato_alterado(tmp_path, lambda d: d["itens"][2]["autores"][0].pop("nome"))

    assert "itens[2].autores[0].nome" in falha_de(entradas.ler_atual, caminho)


@pytest.mark.parametrize(
    "onde",
    [
        lambda d: d["itens"][5].__setitem__("link", "http://www.camara.leg.br/x"),
        lambda d: d["itens"][5].__setitem__("link", "javascript:alert(1)"),
        lambda d: d["itens"][5].__setitem__("link", "https://exemplo.com/x"),
        lambda d: d["itens"][5].__setitem__(
            "apensado_a",
            {"id": 1, "identificacao": "PL 1/2020", "link": "https://exemplo.com/1"},
        ),
        lambda d: d["itens"][5].__setitem__(
            "relator",
            {"id": 1, "nome": "Fulano", "partido_hoje": "NOVO", "fonte": "https://exemplo.com/1"},
        ),
    ],
)
def test_link_que_nao_e_oficial_falha(tmp_path, onde):
    caminho = retrato_alterado(tmp_path, onde)

    assert "link oficial" in falha_de(entradas.ler_atual, caminho)


def test_autor_que_nao_e_deputado_vem_sem_partido_e_e_aceito(tmp_path):
    """No retrato real, o autor de um item é uma comissão especial: `partido_na_data` vazio."""

    def alterar(d):
        d["itens"][0]["autores"] = [
            {"nome": "Comissão Especial", "id_deputado": None, "partido_na_data": "", "ordem": 1}
        ]

    assert entradas.ler_atual(retrato_alterado(tmp_path, alterar))


def test_relator_sem_partido_e_aceito(tmp_path):
    def alterar(d):
        d["itens"][0]["relator"] = {
            "id": 1,
            "nome": "Fulano",
            "partido_hoje": None,
            "designado_em": "2025-01-01T00:00:00",
            "fonte": d["itens"][0]["link"],
        }

    assert entradas.ler_atual(retrato_alterado(tmp_path, alterar))


# ---------- status.json ----------


def test_status_ausente_falha(tmp_path):
    motivo = falha_de(entradas.ler_status_do_dia, tmp_path / "status.json")

    assert "status.json" in motivo and "não existe" in motivo


def test_status_valido_e_devolvido():
    status = entradas.ler_status_do_dia(FIXTURES / "status-ok.json")

    assert status["resultado"] == "ok"


def test_status_invalido_vira_falha_de_pagina(tmp_path):
    caminho = gravar(tmp_path / "status.json", "{ nada")

    assert str(caminho) in falha_de(entradas.ler_status_do_dia, caminho)


def test_status_de_outra_versao_falha(tmp_path):
    documento = json.loads((FIXTURES / "status-ok.json").read_text(encoding="utf-8"))
    documento["versao_formato"] = 2
    caminho = gravar(tmp_path / "status.json", documento)

    assert "versao_formato" in falha_de(entradas.ler_status_do_dia, caminho)


# ---------- coerência ----------


def test_status_ok_e_retrato_do_mesmo_momento_conferem():
    entradas.conferir(
        entradas.ler_atual(REAL), entradas.ler_status_do_dia(FIXTURES / "status-ok.json")
    )


def test_status_de_falha_com_o_retrato_mantido_confere():
    entradas.conferir(
        entradas.ler_atual(REAL), entradas.ler_status_do_dia(FIXTURES / "status-falha.json")
    )


def test_retrato_e_status_de_momentos_diferentes_falham():
    atual = entradas.ler_atual(REAL)
    status = entradas.ler_status_do_dia(FIXTURES / "status-retrato-outro.json")

    motivo = falha_de(entradas.conferir, atual, status)

    assert "dados_camara_em" in motivo and "ultimo_retrato_bom" in motivo


def test_gerado_em_diferente_falha():
    atual = entradas.ler_atual(REAL)
    status = copy.deepcopy(entradas.ler_status_do_dia(FIXTURES / "status-ok.json"))
    status["ultimo_retrato_bom"]["gerado_em"] = "2026-10-20T10:00:00-03:00"

    assert "gerado_em" in falha_de(entradas.conferir, atual, status)


def test_falha_sem_retrato_bom_falha():
    atual = entradas.ler_atual(REAL)
    status = entradas.ler_status_do_dia(FIXTURES / "status-falha-sem-retrato.json")

    assert "ultimo_retrato_bom" in falha_de(entradas.conferir, atual, status)


# ---------- janela de 7 dias ----------


def retrato_do_dia_20():
    return entradas.ler_atual(REAL)


def test_o_dia_do_retrato_e_o_de_brasilia_de_gerado_em():
    assert entradas.dia_do_retrato(retrato_do_dia_20()) == date(2026, 10, 20)


def test_a_janela_tem_sete_dias_do_mais_recente_ao_mais_antigo():
    janela = entradas.ler_janela(FIXTURES / "mudancas", retrato_do_dia_20())

    assert [dia for dia, _ in janela] == [date(2026, 10, 20 - i) for i in range(7)]
    assert [dia.day for dia, doc in janela if doc is not None] == [20, 19, 18, 16]
    assert [dia.day for dia, doc in janela if doc is None] == [17, 15, 14]


def test_cada_arquivo_lido_e_o_documento_do_dia():
    janela = dict(entradas.ler_janela(FIXTURES / "mudancas", retrato_do_dia_20()))

    assert janela[date(2026, 10, 20)]["meta"]["data"] == "2026-10-20"
    assert janela[date(2026, 10, 16)]["meta"]["retrato_anterior"]["dia"] == "2026-10-14"


def test_pasta_inexistente_equivale_a_todos_os_dias_ausentes(tmp_path):
    janela = entradas.ler_janela(tmp_path / "nao-existe", retrato_do_dia_20())

    assert len(janela) == 7
    assert all(documento is None for _, documento in janela)


def test_arquivo_fora_da_janela_nunca_e_lido():
    pasta = FIXTURES / "mudancas-invalida-fora-da-janela"

    janela = dict(entradas.ler_janela(pasta, retrato_do_dia_20()))

    assert janela[date(2026, 10, 20)] is not None
    assert (pasta / "2026-10-10.json").exists()


def test_arquivo_dentro_da_janela_corrompido_falha_com_o_nome(tmp_path):
    gravar(tmp_path / "2026-10-18.json", "{ corrompido")

    motivo = falha_de(entradas.ler_janela, tmp_path, retrato_do_dia_20())

    assert "2026-10-18.json" in motivo


def test_arquivo_de_versao_desconhecida_falha(tmp_path):
    documento = p.arquivo_de_mudancas("2026-10-19", dia_anterior="2026-10-18")
    documento["meta"]["versao_formato"] = 2
    gravar(tmp_path / "2026-10-19.json", documento)

    motivo = falha_de(entradas.ler_janela, tmp_path, retrato_do_dia_20())

    assert "2026-10-19.json" in motivo and "versao_formato" in motivo


def test_arquivo_fora_do_contrato_falha(tmp_path):
    documento = p.arquivo_de_mudancas("2026-10-19", dia_anterior="2026-10-18")
    documento["meta"]["total_eventos"] = 7
    gravar(tmp_path / "2026-10-19.json", documento)

    motivo = falha_de(entradas.ler_janela, tmp_path, retrato_do_dia_20())

    assert "2026-10-19.json" in motivo and "contrato" in motivo


def test_data_do_arquivo_diferente_do_nome_falha(tmp_path):
    documento = p.arquivo_de_mudancas("2026-10-18", dia_anterior="2026-10-17")
    gravar(tmp_path / "2026-10-19.json", documento)

    motivo = falha_de(entradas.ler_janela, tmp_path, retrato_do_dia_20())

    assert "2026-10-19.json" in motivo and "2026-10-18" in motivo


def test_arquivo_do_dia_do_retrato_de_outro_retrato_falha(tmp_path):
    documento = p.arquivo_de_mudancas(
        "2026-10-20", dia_anterior="2026-10-19", dados_camara_em="2026-10-20T05:00:00+00:00"
    )
    gravar(tmp_path / "2026-10-20.json", documento)

    motivo = falha_de(entradas.ler_janela, tmp_path, retrato_do_dia_20())

    assert "2026-10-20.json" in motivo and "dados_camara_em" in motivo
