"""CLI do aviso (AVI, US7): `texto` não envia, não lê credencial e não grava nada."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from monitor_comissoes.aviso import main
from monitor_comissoes.estoque import BRASILIA
from test_aviso import AMBIENTE, CHAT, TOKEN, ClienteFalso, preparar

RAIZ = Path(__file__).parent.parent
CONFIG = RAIZ / "config.toml"
AGORA = datetime(2026, 10, 20, 7, 17, tzinfo=BRASILIA)


def nunca_cria_cliente(token, chat_id):
    raise AssertionError("o comando texto não pode criar o cliente do Telegram")


def rodar_texto(caminhos, *extra, relogio=lambda: AGORA):
    return main(
        ["texto", "--config", str(CONFIG), "--atual", str(caminhos.atual), *extra],
        relogio=relogio,
        ambiente={},
        criar_cliente=nunca_cria_cliente,
    )


def test_texto_imprime_o_tipo_e_a_mensagem_sem_credenciais(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")

    codigo = rodar_texto(caminhos)

    linhas = capsys.readouterr().out.split("\n")
    assert codigo == 0
    assert linhas[0] == "TIPO: normal"
    assert linhas[1] == "Monitor de comissões · dados de 20/10 · 105 itens"


def test_texto_nao_cria_nem_altera_o_registro_de_envio(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    rodar_texto(caminhos)

    assert not caminhos.envio.exists()


def test_texto_de_um_dia_de_falha_mostra_tipo_erro(tmp_path, capsys):
    caminhos = preparar(tmp_path, "falha")

    assert rodar_texto(caminhos) == 0

    saida = capsys.readouterr().out
    assert saida.startswith("TIPO: erro\n⚠ ERRO")


def test_hoje_escolhe_o_dia_de_um_cenario_salvo(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    depois = datetime(2030, 1, 1, 7, 17, tzinfo=BRASILIA)

    assert rodar_texto(caminhos, relogio=lambda: depois) == 0
    sem_hoje = capsys.readouterr().out
    assert rodar_texto(caminhos, "--hoje", "2026-10-20", relogio=lambda: depois) == 0
    com_hoje = capsys.readouterr().out

    assert sem_hoje.startswith("TIPO: erro") and "não rodou" in sem_hoje
    assert com_hoje.startswith("TIPO: normal")


def test_hoje_invalido_e_erro_de_uso(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    with pytest.raises(SystemExit) as saida:
        rodar_texto(caminhos, "--hoje", "20/10/2026")

    assert saida.value.code == 2


def test_enviar_nao_aceita_hoje(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    with pytest.raises(SystemExit) as saida:
        main(
            ["enviar", "--atual", str(caminhos.atual), "--hoje", "2026-10-20"],
            ambiente=AMBIENTE,
            criar_cliente=lambda t, c: ClienteFalso(),
        )

    assert saida.value.code == 2


def test_sem_subcomando_e_erro_de_uso():
    with pytest.raises(SystemExit) as saida:
        main([])

    assert saida.value.code == 2


def test_enviar_pelo_main_envia_grava_o_registro_ao_lado_do_atual(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()

    codigo = main(
        ["enviar", "--config", str(CONFIG), "--atual", str(caminhos.atual)],
        relogio=lambda: AGORA,
        ambiente=AMBIENTE,
        criar_cliente=lambda t, c: cliente,
    )

    assert codigo == 0 and len(cliente.enviados) == 1
    assert (tmp_path / "envio.json").exists()
    assert capsys.readouterr().out.startswith("OK: mensagem normal de 20/10")


def test_enviar_aceita_os_caminhos_por_opcao(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    outro = tmp_path / "registro" / "meu-envio.json"

    main(
        [
            "enviar",
            "--config",
            str(CONFIG),
            "--atual",
            str(caminhos.atual),
            "--status",
            str(caminhos.status),
            "--mudancas",
            str(caminhos.mudancas),
            "--envio",
            str(outro),
        ],
        relogio=lambda: AGORA,
        ambiente=AMBIENTE,
        criar_cliente=lambda t, c: ClienteFalso(),
    )

    assert outro.exists() and not caminhos.envio.exists()


def test_enviar_le_as_credenciais_do_ambiente_do_processo_por_padrao(tmp_path, monkeypatch, capsys):
    caminhos = preparar(tmp_path, "completo")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT)
    recebido = []

    def criar(token, chat_id):
        recebido.append((token, chat_id))
        return ClienteFalso()

    codigo = main(
        ["enviar", "--config", str(CONFIG), "--atual", str(caminhos.atual)],
        relogio=lambda: AGORA,
        criar_cliente=criar,
    )

    assert codigo == 0 and recebido == [(TOKEN, CHAT)]
    assert TOKEN not in capsys.readouterr().out


def test_config_invalida_falha_com_a_mensagem_do_aviso(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    ruim = tmp_path / "config.toml"
    ruim.write_text("comissoes = []\n", encoding="utf-8")

    codigo = main(
        ["texto", "--config", str(ruim), "--atual", str(caminhos.atual)],
        relogio=lambda: AGORA,
        ambiente={},
        criar_cliente=nunca_cria_cliente,
    )

    assert codigo == 1
    assert "FALHA [envio]: " in capsys.readouterr().err


def test_texto_com_entrada_incoerente_sai_com_um(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    (caminhos.mudancas / "2026-10-20.json").unlink()

    assert rodar_texto(caminhos) == 1

    assert "FALHA [envio]: " in capsys.readouterr().err


def test_o_modulo_roda_com_python_m(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
    ambiente["PYTHONPATH"] = str(RAIZ / "src")

    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "monitor_comissoes.aviso",
            "texto",
            "--config",
            str(CONFIG),
            "--atual",
            str(caminhos.atual),
            "--hoje",
            "2026-10-20",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=ambiente,
        cwd=tmp_path,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.startswith("TIPO: normal\nMonitor de comissões")
