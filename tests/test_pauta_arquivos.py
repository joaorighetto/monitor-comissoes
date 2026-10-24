"""Arquivos da checagem da pauta: última checagem, status-pauta e gravação tudo ou nada."""

import json
import os
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from monitor_comissoes.erros import ENTRADA_INVALIDA, FalhaDeColeta
from monitor_comissoes.pauta.arquivos import (
    gravar,
    ler_pauta,
    ler_status_pauta,
    montar_status_pauta,
    ultimo_arquivo,
)
from monitor_comissoes.saida import serializar
from pauta_sinteticos import arquivo_do_dia, reuniao_gravada

BRASILIA = timezone(timedelta(hours=-3))
HOJE = date(2026, 10, 24)


def _gravar(caminho: Path, documento) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = documento if isinstance(documento, str) else serializar(documento)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


# --- último arquivo ----------------------------------------------------------------------------


def test_ultimo_arquivo_e_o_mais_recente_ate_hoje(tmp_path):
    for nome in ("2026-10-20.json", "2026-10-24.json", "2026-10-23.json", "leia-me.md", "x.json"):
        (tmp_path / nome).write_text("{}", encoding="utf-8")

    assert ultimo_arquivo(tmp_path, HOJE) == tmp_path / "2026-10-24.json"


def test_ultimo_arquivo_sem_pasta_ou_sem_arquivos(tmp_path):
    assert ultimo_arquivo(tmp_path / "pautas", HOJE) is None
    (tmp_path / "pautas").mkdir()
    assert ultimo_arquivo(tmp_path / "pautas", HOJE) is None


def test_arquivo_com_data_futura_falha_com_o_nome(tmp_path):
    for nome in ("2026-10-23.json", "2026-10-25.json"):
        (tmp_path / nome).write_text("{}", encoding="utf-8")

    with pytest.raises(FalhaDeColeta) as erro:
        ultimo_arquivo(tmp_path, HOJE)

    assert erro.value.categoria == ENTRADA_INVALIDA
    assert "2026-10-25.json" in erro.value.motivo


def test_nome_com_data_impossivel_e_ignorado(tmp_path):
    (tmp_path / "2026-13-01.json").write_text("{}", encoding="utf-8")
    (tmp_path / "2026-10-22.json").write_text("{}", encoding="utf-8")

    assert ultimo_arquivo(tmp_path, HOJE) == tmp_path / "2026-10-22.json"


# --- ler a pauta anterior ----------------------------------------------------------------------


def _valido():
    return arquivo_do_dia(
        reunioes=[reuniao_gravada(83091, chaves=("p:2645503", "t:Item sem proposição"))]
    )


def test_ler_pauta_devolve_o_documento(tmp_path):
    caminho = _gravar(tmp_path / "2026-10-24.json", _valido())

    assert ler_pauta(caminho) == _valido()


_APAGAR = object()
REUNIAO = ("checagem", "reunioes", 0)


def _alterar(caminho_campos, valor):
    documento = _valido()
    alvo = documento
    for campo in caminho_campos[:-1]:
        alvo = alvo[campo]
    if valor is _APAGAR:
        del alvo[caminho_campos[-1]]
    else:
        alvo[caminho_campos[-1]] = valor
    return documento


@pytest.mark.parametrize(
    "documento",
    [
        "{não é json",
        "[]",
        _alterar(("meta", "versao_formato"), 2),
        _alterar(("meta", "data"), "2026-10-23"),
        _alterar(("meta",), _APAGAR),
        _alterar(("checagem", "checada_em"), "2026-10-24T05:49:12"),
        _alterar(("checagem", "checada_em"), "ontem"),
        _alterar(("checagem", "reunioes"), {}),
        _alterar(("alteracoes",), _APAGAR),
        _alterar((*REUNIAO, "id"), "83091"),
        _alterar((*REUNIAO, "situacao"), "adiada"),
        _alterar((*REUNIAO, "inicio"), "2026-10-28"),
        _alterar((*REUNIAO, "vista_desde"), _APAGAR),
        _alterar((*REUNIAO, "vista_desde"), "2026-10-23T22:47:30"),
        _alterar((*REUNIAO, "pauta"), None),
        _alterar((*REUNIAO, "pauta", 0, "chave"), _APAGAR),
        _alterar((*REUNIAO, "pauta", 0, "chave"), "2645503"),
    ],
)
def test_pauta_anterior_invalida_falha_com_o_nome_do_arquivo(tmp_path, documento):
    caminho = _gravar(tmp_path / "2026-10-24.json", documento)

    with pytest.raises(FalhaDeColeta) as erro:
        ler_pauta(caminho)

    assert erro.value.categoria == ENTRADA_INVALIDA
    assert "2026-10-24.json" in erro.value.motivo


# --- status-pauta ------------------------------------------------------------------------------


def test_montar_status_ok_e_falha_na_ordem_do_contrato():
    momento = datetime(2026, 10, 24, 18, 18, 40, tzinfo=UTC)
    ok = montar_status_pauta("ok", momento, None, "2026-10-24T15:17:02-03:00")
    falha = montar_status_pauta(
        "falha",
        momento,
        {"categoria": "fonte_indisponivel", "motivo": "pauta: HTTP 503"},
        None,
    )

    assert list(ok) == [
        "versao_formato",
        "resultado",
        "verificado_em",
        "falha",
        "ultima_checagem_boa",
    ]
    assert ok == {
        "versao_formato": 1,
        "resultado": "ok",
        "verificado_em": "2026-10-24T15:18:40-03:00",
        "falha": None,
        "ultima_checagem_boa": "2026-10-24T15:17:02-03:00",
    }
    assert falha["falha"] == {"categoria": "fonte_indisponivel", "motivo": "pauta: HTTP 503"}
    assert falha["ultima_checagem_boa"] is None


def test_ler_status_pauta(tmp_path, capsys):
    momento = datetime(2026, 10, 24, 15, 18, 40, tzinfo=BRASILIA)
    documento = montar_status_pauta("ok", momento, None, "2026-10-24T15:17:02-03:00")

    assert ler_status_pauta(tmp_path / "ausente.json") is None
    assert ler_status_pauta(_gravar(tmp_path / "ok.json", documento)) == documento
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "conteudo",
    ["{quebrado", "[]", json.dumps({"versao_formato": 2}), json.dumps({"versao_formato": 1})],
)
def test_status_pauta_ilegivel_e_none_com_aviso(tmp_path, capsys, conteudo):
    caminho = _gravar(tmp_path / "status-pauta.json", conteudo)

    assert ler_status_pauta(caminho) is None
    erro = capsys.readouterr().err
    assert erro.startswith("AVISO: ")
    assert "status-pauta.json" in erro


# --- gravação ----------------------------------------------------------------------------------


def _status():
    momento = datetime(2026, 10, 24, 5, 49, 30, tzinfo=BRASILIA)
    return montar_status_pauta("ok", momento, None, "2026-10-24T05:49:12-03:00")


def test_gravar_os_dois_arquivos(tmp_path):
    dia = tmp_path / "data" / "pautas" / "2026-10-24.json"
    status = tmp_path / "data" / "status-pauta.json"

    gravar(_valido(), dia, _status(), status)

    assert dia.read_text(encoding="utf-8") == serializar(_valido())
    assert status.read_text(encoding="utf-8") == serializar(_status())


def test_gravar_so_o_status_quando_nao_ha_arquivo_do_dia(tmp_path):
    dia = tmp_path / "pautas" / "2026-10-24.json"
    status = tmp_path / "status-pauta.json"

    gravar(None, dia, _status(), status)

    assert not dia.parent.exists()
    assert status.read_text(encoding="utf-8") == serializar(_status())


def test_falha_na_troca_do_status_desfaz_o_arquivo_do_dia(tmp_path, monkeypatch):
    dia = _gravar(tmp_path / "pautas" / "2026-10-24.json", "anterior do dia\n")
    status = _gravar(tmp_path / "status-pauta.json", "status anterior\n")
    original = os.replace

    def falso(origem, destino):
        if Path(destino) == status:
            raise OSError("falha simulada na troca do status")
        return original(origem, destino)

    monkeypatch.setattr(os, "replace", falso)

    with pytest.raises(OSError):
        gravar(_valido(), dia, _status(), status)

    assert dia.read_text(encoding="utf-8") == "anterior do dia\n"
    assert status.read_text(encoding="utf-8") == "status anterior\n"
    assert sorted(p.name for p in dia.parent.iterdir()) == ["2026-10-24.json"]
