"""Mensagem do commit do registro de envio (`aviso mensagem`), usada pelo workflow."""

import json

import pytest

from monitor_comissoes.aviso import main
from monitor_comissoes.envio import mensagem_do_commit

NADA = {"normal": None, "erro": None}


def test_normal_enviada_hoje():
    assert (
        mensagem_do_commit(NADA, {"normal": "2026-10-20", "erro": None})
        == "aviso: 2026-10-20 · normal"
    )


def test_erro_enviado_hoje_com_normal_de_ontem_preservada():
    antes = {"normal": "2026-10-19", "erro": None}

    assert (
        mensagem_do_commit(antes, {"normal": "2026-10-19", "erro": "2026-10-20"})
        == "aviso: 2026-10-20 · erro"
    )


def test_normal_de_hoje_depois_de_erro_de_hoje():
    antes = {"normal": None, "erro": "2026-10-20"}

    assert (
        mensagem_do_commit(antes, {"normal": "2026-10-20", "erro": "2026-10-20"})
        == "aviso: 2026-10-20 · normal"
    )


@pytest.mark.parametrize(
    "depois",
    [NADA, {"normal": "2026-10-20", "erro": "2026-10-20"}],
)
def test_registro_sem_mudanca_ou_com_duas_e_erro(depois):
    from monitor_comissoes.erros import FalhaDeEnvio

    with pytest.raises(FalhaDeEnvio, match="um único tipo"):
        mensagem_do_commit(NADA, depois)


def escrever(caminho, normal=None, erro=None):
    caminho.write_text(
        json.dumps({"versao_formato": 1, "ultimo_envio": {"normal": normal, "erro": erro}}),
        encoding="utf-8",
    )


def test_cli_mensagem_compara_com_o_registro_de_antes(tmp_path, capsys):
    escrever(tmp_path / "antes.json", normal="2026-10-19")
    escrever(tmp_path / "envio.json", normal="2026-10-20")

    codigo = main(
        [
            "mensagem",
            "--envio",
            str(tmp_path / "envio.json"),
            "--antes",
            str(tmp_path / "antes.json"),
        ]
    )

    assert codigo == 0
    assert capsys.readouterr().out == "aviso: 2026-10-20 · normal\n"


def test_cli_mensagem_sem_arquivo_de_antes_conta_como_nada_enviado(tmp_path, capsys):
    escrever(tmp_path / "envio.json", erro="2026-10-20")

    codigo = main(
        ["mensagem", "--envio", str(tmp_path / "envio.json"), "--antes", str(tmp_path / "x.json")]
    )

    assert codigo == 0
    assert capsys.readouterr().out == "aviso: 2026-10-20 · erro\n"


def test_cli_mensagem_sem_antes_usa_o_registro_inteiro(tmp_path, capsys):
    escrever(tmp_path / "envio.json", normal="2026-10-20")

    codigo = main(["mensagem", "--envio", str(tmp_path / "envio.json")])

    assert codigo == 0  # sem --antes, o registro inteiro é "novo"
    assert capsys.readouterr().out == "aviso: 2026-10-20 · normal\n"
