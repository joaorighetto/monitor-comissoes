"""Leitura e conferência das entradas do aviso (FR-001, FR-022; data-model.md da AVI)."""

import json

import pytest

import aviso_sinteticos as a
from monitor_comissoes.entradas import ler_itens_do_atual, ler_mudancas, ler_status_do_dia
from monitor_comissoes.erros import FalhaDeEnvio
from monitor_comissoes.saida import serializar


def gravar(tmp_path, nome, documento):
    caminho = tmp_path / nome
    caminho.write_text(
        documento if isinstance(documento, str) else serializar(documento), encoding="utf-8"
    )
    return caminho


# --- status ---------------------------------------------------------------------------------------


def test_status_ausente_devolve_none(tmp_path):
    assert ler_status_do_dia(tmp_path / "status.json") is None


def test_status_valido_e_devolvido(tmp_path):
    caminho = gravar(tmp_path, "status.json", a.status_ok())

    assert ler_status_do_dia(caminho)["resultado"] == "ok"


def test_status_invalido_vira_falha_de_envio(tmp_path):
    caminho = gravar(tmp_path, "status.json", "{ nao e json")

    with pytest.raises(FalhaDeEnvio, match="status"):
        ler_status_do_dia(caminho)


# --- mudanças -------------------------------------------------------------------------------------


def test_mudancas_validas_sao_devolvidas(tmp_path):
    caminho = gravar(tmp_path, "m.json", a.completo())

    documento = ler_mudancas(caminho, a.status_ok())

    assert documento["meta"]["total_eventos"] == 6


def test_mudancas_de_linha_de_base_sao_validas(tmp_path):
    base = a.mudancas(
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 105}, retrato_anterior=None
    )

    assert ler_mudancas(gravar(tmp_path, "m.json", base), a.status_ok())["meta"]["linha_de_base"]


def test_arquivo_de_mudancas_ausente_falha_com_o_nome(tmp_path):
    with pytest.raises(FalhaDeEnvio, match="2026-10-20.json"):
        ler_mudancas(tmp_path / "2026-10-20.json", a.status_ok())


def test_mudancas_que_nao_sao_json_falham(tmp_path):
    with pytest.raises(FalhaDeEnvio, match="JSON"):
        ler_mudancas(gravar(tmp_path, "m.json", "{ nao e json"), a.status_ok())


def test_mudancas_que_nao_sao_objeto_falham(tmp_path):
    with pytest.raises(FalhaDeEnvio, match="objeto"):
        ler_mudancas(gravar(tmp_path, "m.json", "[1]"), a.status_ok())


def test_versao_de_formato_desconhecida_falha_antes_de_ler_o_resto(tmp_path):
    documento = a.completo()
    documento["meta"]["versao_formato"] = 2
    documento["eventos"] = "outra forma"

    with pytest.raises(FalhaDeEnvio, match="versao_formato 2"):
        ler_mudancas(gravar(tmp_path, "m.json", documento), a.status_ok())


def test_data_do_arquivo_diferente_da_do_status_falha(tmp_path):
    documento = a.mudancas(dia="2026-10-19")

    with pytest.raises(FalhaDeEnvio, match="2026-10-19.*2026-10-20"):
        ler_mudancas(gravar(tmp_path, "m.json", documento), a.status_ok())


def test_retrato_diferente_do_do_status_falha(tmp_path):
    status = a.status_ok(dados_camara_em="2026-10-20T05:00:00+00:00")

    with pytest.raises(FalhaDeEnvio, match="dados_camara_em"):
        ler_mudancas(gravar(tmp_path, "m.json", a.completo()), status)


def test_contagem_que_nao_bate_falha(tmp_path):
    documento = a.completo()
    documento["meta"]["total_eventos"] = 5

    with pytest.raises(FalhaDeEnvio, match="total_eventos"):
        ler_mudancas(gravar(tmp_path, "m.json", documento), a.status_ok())


def test_evento_sem_link_falha(tmp_path):
    documento = a.completo()
    documento["eventos"][0]["link"] = ""

    with pytest.raises(FalhaDeEnvio, match="link"):
        ler_mudancas(gravar(tmp_path, "m.json", documento), a.status_ok())


def test_tipo_de_evento_desconhecido_falha(tmp_path):
    documento = a.completo()
    documento["eventos"][0]["tipo"] = "movimentacao"

    with pytest.raises(FalhaDeEnvio, match="tipo"):
        ler_mudancas(gravar(tmp_path, "m.json", documento), a.status_ok())


def test_linha_de_base_com_evento_falha(tmp_path):
    documento = a.completo()
    documento["meta"]["linha_de_base"] = {"motivo": "primeiro retrato", "total_itens": 105}

    with pytest.raises(FalhaDeEnvio, match="linha de base"):
        ler_mudancas(gravar(tmp_path, "m.json", documento), a.status_ok())


def test_mudancas_sem_retrato_bom_no_status_falha(tmp_path):
    with pytest.raises(FalhaDeEnvio, match="ultimo_retrato_bom"):
        ler_mudancas(
            gravar(tmp_path, "m.json", a.completo()), a.status_falha(com_retrato_bom=False)
        )


# --- itens do atual.json --------------------------------------------------------------------------


def test_itens_do_atual_trazem_so_o_que_o_aviso_usa(tmp_path):
    itens = ler_itens_do_atual(gravar(tmp_path, "atual.json", a.atual()))

    assert [i["principal_nao_localizada"] for i in itens] == [False, False, True, True]
    assert set(itens[0]) == {"id", "identificacao", "comissao", "link", "principal_nao_localizada"}


@pytest.mark.parametrize("versao", [2, 3])
def test_atual_nas_versoes_2_e_3_e_aceito(tmp_path, versao):
    assert ler_itens_do_atual(gravar(tmp_path, "atual.json", a.atual(versao=versao)))


@pytest.mark.parametrize("versao", [1, 4, None, "3"])
def test_atual_em_outra_versao_falha(tmp_path, versao):
    documento = a.atual()
    documento["meta"]["versao_formato"] = versao

    with pytest.raises(FalhaDeEnvio, match="versao_formato"):
        ler_itens_do_atual(gravar(tmp_path, "atual.json", documento))


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("identificacao", None),
        ("comissao", 3),
        ("link", ""),
        ("principal_nao_localizada", "sim"),
        ("principal_nao_localizada", None),
    ],
)
def test_item_do_atual_com_campo_invalido_falha(tmp_path, campo, valor):
    documento = a.atual()
    documento["itens"][1][campo] = valor

    with pytest.raises(FalhaDeEnvio, match=f"itens.1..{campo}"):
        ler_itens_do_atual(gravar(tmp_path, "atual.json", documento))


def test_item_do_atual_sem_o_campo_falha(tmp_path):
    documento = a.atual()
    del documento["itens"][0]["principal_nao_localizada"]

    with pytest.raises(FalhaDeEnvio, match="principal_nao_localizada"):
        ler_itens_do_atual(gravar(tmp_path, "atual.json", documento))


def test_atual_ausente_ou_ilegivel_falha(tmp_path):
    with pytest.raises(FalhaDeEnvio, match="atual.json"):
        ler_itens_do_atual(tmp_path / "atual.json")
    with pytest.raises(FalhaDeEnvio, match="JSON"):
        ler_itens_do_atual(gravar(tmp_path, "atual.json", "{"))
    with pytest.raises(FalhaDeEnvio, match="itens"):
        ler_itens_do_atual(
            gravar(tmp_path, "atual.json", json.dumps({"meta": {"versao_formato": 3}, "itens": 1}))
        )
