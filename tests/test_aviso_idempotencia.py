"""Registro de envio e idempotência do aviso (AVI, US5): uma mensagem por dia e tipo."""

import json
from datetime import timedelta

import pytest

import aviso_sinteticos as a
from monitor_comissoes import aviso
from monitor_comissoes.erros import FalhaDeEnvio
from test_aviso import AGORA, CONFIG, ClienteFalso, dados, gravar, preparar, rodar


def registro(caminhos):
    return json.loads(caminhos.envio.read_text(encoding="utf-8"))["ultimo_envio"]


def test_primeiro_envio_manda_uma_vez_e_grava_o_registro(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()

    assert rodar(caminhos, cliente) == 0

    assert len(cliente.enviados) == 1
    assert registro(caminhos) == {"normal": "2026-10-20", "erro": None}


def test_segunda_execucao_no_mesmo_dia_nao_envia_e_sai_com_zero(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()
    rodar(caminhos, cliente)
    capsys.readouterr()
    antes = caminhos.envio.read_bytes()

    codigo = rodar(caminhos, cliente)

    assert codigo == 0 and len(cliente.enviados) == 1
    assert capsys.readouterr().out == "JÁ ENVIADO: mensagem normal de 20/10\n"
    assert caminhos.envio.read_bytes() == antes


def test_ja_enviado_nao_exige_credenciais(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    rodar(caminhos, ClienteFalso())

    assert rodar(caminhos, ClienteFalso(), ambiente={}) == 0


def test_lote_regenerado_no_mesmo_dia_nao_reenvia(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()
    rodar(caminhos, cliente)
    gravar(caminhos.mudancas / "2026-10-20.json", a.mudancas([a.evento("parecer", "ce_a")]))

    assert rodar(caminhos, cliente) == 0

    assert len(cliente.enviados) == 1


def test_falha_de_envio_nao_grava_o_registro_e_a_proxima_execucao_envia(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    assert rodar(caminhos, ClienteFalso(FalhaDeEnvio("a Bot API recusou"))) == 1
    assert not caminhos.envio.exists()

    cliente = ClienteFalso()
    assert rodar(caminhos, cliente) == 0
    assert len(cliente.enviados) == 1


def test_erro_do_dia_enviado_e_depois_sucesso_envia_a_normal_e_guarda_os_dois(tmp_path):
    caminhos = preparar(tmp_path, "falha")
    cliente = ClienteFalso()
    rodar(caminhos, cliente)
    assert cliente.enviados[0].startswith("⚠ ERRO")

    caminhos.mudancas.mkdir(exist_ok=True)
    gravar(caminhos.status, a.status_ok())
    gravar(caminhos.mudancas / "2026-10-20.json", a.completo())

    assert rodar(caminhos, cliente) == 0

    assert len(cliente.enviados) == 2 and cliente.enviados[1].startswith("Monitor de comissões")
    assert registro(caminhos) == {"normal": "2026-10-20", "erro": "2026-10-20"}


def test_normal_enviada_e_depois_falha_real_do_mesmo_dia_envia_o_erro(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()
    rodar(caminhos, cliente)
    gravar(caminhos.status, a.status_falha())

    assert rodar(caminhos, cliente) == 0

    assert cliente.enviados[1].startswith("⚠ ERRO")
    assert registro(caminhos) == {"normal": "2026-10-20", "erro": "2026-10-20"}


def test_erro_enviado_duas_vezes_no_mesmo_dia_so_vai_uma(tmp_path, capsys):
    caminhos = preparar(tmp_path, "falha")
    cliente = ClienteFalso()
    rodar(caminhos, cliente)
    capsys.readouterr()

    assert rodar(caminhos, cliente) == 0

    assert len(cliente.enviados) == 1
    assert capsys.readouterr().out == "JÁ ENVIADO: mensagem de erro de 20/10\n"


def test_o_dia_seguinte_envia_de_novo(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()
    rodar(caminhos, cliente)
    gravar(
        caminhos.status,
        a.status_ok(dia="2026-10-21", dados_camara_em="2026-10-21T04:31:26+00:00"),
    )
    gravar(
        caminhos.mudancas / "2026-10-21.json",
        a.mudancas(
            dia="2026-10-21",
            retrato={"dia": "2026-10-21", "dados_camara_em": "2026-10-21T04:31:26+00:00"},
        ),
    )

    assert rodar(caminhos, cliente, agora=AGORA + timedelta(days=1)) == 0

    assert len(cliente.enviados) == 2
    assert registro(caminhos)["normal"] == "2026-10-21"


@pytest.mark.parametrize("conteudo", ["{ lixo", '{"versao_formato": 7, "ultimo_envio": {}}', "[]"])
def test_registro_invalido_falha_sem_enviar_e_sem_sobrescrever(tmp_path, capsys, conteudo):
    caminhos = preparar(tmp_path, "completo")
    caminhos.envio.write_text(conteudo, encoding="utf-8")
    cliente = ClienteFalso()

    codigo = rodar(caminhos, cliente)

    assert codigo == 1 and cliente.enviados == []
    assert caminhos.envio.read_text(encoding="utf-8") == conteudo
    assert "registro de envio inválido" in capsys.readouterr().err


def test_falha_ao_gravar_o_registro_depois_do_envio_diz_que_a_mensagem_foi_enviada(
    tmp_path, capsys, monkeypatch
):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()

    def falha(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(aviso, "gravar_registro", falha)

    codigo = rodar(caminhos, cliente)

    assert codigo == 1 and len(cliente.enviados) == 1
    erro = capsys.readouterr().err
    assert "FOI enviada" in erro and "disco cheio" in erro
    assert not caminhos.envio.exists()


def test_o_envio_nao_altera_os_arquivos_de_coleta(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    antes = dados(caminhos)

    rodar(caminhos, ClienteFalso())
    rodar(caminhos, ClienteFalso())

    assert dados(caminhos) == antes


def test_config_e_a_mesma_do_modulo_de_apoio():
    assert CONFIG.comissoes == ("CE", "CREDN")
