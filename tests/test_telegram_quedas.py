"""Quedas de conexão do http.client e filtro de segredos (AVI; revisão, rodada 2)."""

import http.client
import io
import urllib.error
from email.message import Message

import pytest

from monitor_comissoes.aviso import executar_envio
from monitor_comissoes.erros import FalhaDeEnvio
from test_aviso import AGORA, CONFIG, fabrica, preparar
from test_telegram import CHAT, TOKEN, URL, Rede, cliente, ok, tudo_que_a_falha_mostra


class Falso:
    def __init__(self, falha):
        self.enviados = []
        self.falha = falha

    def enviar(self, texto):
        raise self.falha


def test_remote_disconnected_e_a_queda_mais_comum_e_deve_ser_repetida():
    queda = http.client.RemoteDisconnected("Remote end closed connection without response")
    rede = Rede(queda, ok())
    c, esperas = cliente(rede)

    c.enviar("x")

    assert len(rede.pedidos) == 2 and esperas == [5]


@pytest.mark.parametrize(
    "queda",
    [
        http.client.BadStatusLine("''"),
        http.client.CannotSendRequest(),
        http.client.IncompleteRead(b"p"),
    ],
)
def test_outras_quedas_de_conexao_do_http_client_tambem_repetem(queda):
    rede = Rede(queda, queda, queda)
    c, esperas = cliente(rede)

    with pytest.raises(FalhaDeEnvio, match=r"3 tentativas.*conexão interrompida"):
        c.enviar("x")

    assert len(rede.pedidos) == 3 and esperas == [5, 15]


def test_queda_que_repete_nao_mostra_o_texto_da_excecao():
    queda = http.client.BadStatusLine(f"{URL} {CHAT}")
    c, _ = cliente(Rede(queda, queda, queda))

    with pytest.raises(FalhaDeEnvio) as erro:
        c.enviar("x")

    saida = tudo_que_a_falha_mostra(erro.value)
    assert TOKEN not in saida and CHAT not in saida and "BadStatusLine" in saida


def test_pedido_invalido_nao_repete():
    rede = Rede(http.client.InvalidURL("url ruim"), ok())
    c, esperas = cliente(rede)

    with pytest.raises(FalhaDeEnvio, match="não foi possível montar o pedido"):
        c.enviar("x")

    assert len(rede.pedidos) == 1 and esperas == []


def test_corpo_de_erro_interrompido_nao_escapa_como_excecao_generica():
    class Interrompido(io.BytesIO):
        def read(self, n=-1):
            raise http.client.IncompleteRead(b"")

    erro = urllib.error.HTTPError(URL, 502, "erro", Message(), Interrompido())
    c, esperas = cliente(Rede(erro, ok()))

    c.enviar("x")

    assert esperas == [5]


def test_excecao_inesperada_com_segredo_colado_com_quebra_de_linha_nao_vaza(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    cliente_falso = Falso(RuntimeError(f"estourou com {TOKEN} e {CHAT}"))
    ambiente = {"TELEGRAM_BOT_TOKEN": TOKEN + "\n", "TELEGRAM_CHAT_ID": CHAT + "\n"}

    codigo = executar_envio(caminhos, CONFIG, lambda: AGORA, ambiente, fabrica(cliente_falso))

    erro = capsys.readouterr().err
    assert codigo == 1 and "RuntimeError" in erro
    assert TOKEN not in erro and CHAT not in erro
