"""Casos de aceitação da COL sobre as fixtures reais da Câmara (sem rede)."""

import json
from datetime import date
from pathlib import Path

import pytest

from conftest import FIXTURES
from monitor_comissoes.cli import main
from monitor_comissoes.coleta import executar

CONFIG_REPO = Path(__file__).parent.parent / "config.toml"
MANIFESTO = json.loads((FIXTURES / "manifesto.json").read_text(encoding="utf-8"))
CONTRASTE = MANIFESTO["selecao"]["contraste"]


def gerar(config, transporte, agora, tmp_path):
    saida = tmp_path / "data" / "atual.json"
    executar(config, transporte, agora, saida)
    return json.loads(saida.read_text(encoding="utf-8"))


def por_identificacao(documento):
    return {i["identificacao"]: i for i in documento["itens"]}


@pytest.fixture
def documento(config, transporte, agora, tmp_path):
    return gerar(config, transporte, agora, tmp_path)


def test_pl_1843_2022_tem_autoria_novo(documento):
    item = por_identificacao(documento)["PL 1843/2022"]

    assert item["etiquetas"] == ["autoria NOVO"]
    assert item["comissao"] == "CE"
    assert item["situacao"] == "Aguardando Parecer"
    assert item["id"] == 2331032
    assert [a["nome"] for a in item["autores"]] == ["Lucas Gonzalez"]
    assert item["autores"][0]["partido_na_data"] == "NOVO"


def test_pl_3871_2024_tem_so_autor_hoje_no_novo(documento):
    item = por_identificacao(documento)["PL 3871/2024"]

    # Luiz Lima assinou quando era do PL; hoje é deputado em exercício do NOVO.
    assert item["etiquetas"] == ["autor hoje no NOVO"]
    assert item["autores"][0]["partido_na_data"] == "PL"
    assert item["autores"][0]["id_deputado"] == 204455


def test_parado_ha_conta_a_partir_do_ultimo_status(documento):
    item = por_identificacao(documento)["PL 1843/2022"]

    esperado = (date(2026, 10, 18) - date(2025, 10, 16)).days
    assert item["ultimo_status_em"] == "2025-10-16T00:00:00"
    assert item["parado_ha_dias"] == esperado


@pytest.mark.parametrize("motivo", sorted(CONTRASTE))
def test_linhas_de_contraste_nao_entram(documento, motivo):
    # REQ e PDL na CE, PL de outro partido na CE e PL do NOVO fora das comissões.
    assert CONTRASTE[motivo] not in {i["id"] for i in documento["itens"]}


def test_todo_item_tem_link_oficial_etiqueta_e_comissao_da_lista(documento):
    assert documento["itens"]
    for item in documento["itens"]:
        assert item["link"] == f"https://www.camara.leg.br/propostas-legislativas/{item['id']}"
        assert item["etiquetas"]
        assert set(item["etiquetas"]) <= {"autoria NOVO", "autor hoje no NOVO"}
        assert item["comissao"] in ("CE", "CREDN")
        assert item["tipo"] in ("PL", "PLP")


def test_arquivo_termina_com_quebra_de_linha_e_usa_utf8(config, transporte, agora, tmp_path):
    gerar(config, transporte, agora, tmp_path)

    texto = (tmp_path / "data" / "atual.json").read_text(encoding="utf-8")

    assert texto.endswith("}\n")
    assert "\\u00" not in texto


def test_comando_imprime_resumo_e_sai_com_zero(transporte, agora, tmp_path, capsys):
    saida = tmp_path / "atual.json"

    codigo = main(
        ["--config", str(CONFIG_REPO), "--saida", str(saida)], transporte=transporte, agora=agora
    )

    linha = capsys.readouterr().out.strip()
    assert codigo == 0
    assert linha.startswith("OK: ")
    assert "CE:" in linha and "CREDN:" in linha
    assert saida.exists()
