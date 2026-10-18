import socket
import urllib.request

import pytest


def test_guarda_bloqueia_resolucao_de_nome_externo():
    with pytest.raises(RuntimeError, match="rede"):
        socket.create_connection(("dadosabertos.camara.leg.br", 443), timeout=1)


def test_guarda_bloqueia_urlopen_para_a_camara():
    with pytest.raises(Exception, match="rede"):
        urllib.request.urlopen("https://dadosabertos.camara.leg.br/", timeout=1)


def test_guarda_bloqueia_conexao_direta_por_ip_externo():
    with pytest.raises(RuntimeError, match="rede"):
        socket.socket().connect(("203.0.113.10", 443))


def test_guarda_bloqueia_ate_localhost_que_poderia_ser_proxy_de_saida():
    with pytest.raises(RuntimeError, match="rede"):
        socket.create_connection(("127.0.0.1", 9), timeout=1)
