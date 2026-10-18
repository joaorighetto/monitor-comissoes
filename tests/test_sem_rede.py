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


def test_leituras_novas_da_rel_tambem_ficam_atras_da_guarda():
    # O transporte real, sem `abrir` falso, nunca chega à rede nos testes: a guarda levanta
    # RuntimeError (não é OSError), o que tornaria visível qualquer teste que esquecesse o falso.
    from monitor_comissoes.deputados import obter_deputado
    from monitor_comissoes.tramitacoes import obter_tramitacoes
    from monitor_comissoes.transporte import TransporteHttp

    transporte = TransporteHttp(dormir=lambda s: None)
    url = "https://dadosabertos.camara.leg.br"

    with pytest.raises(RuntimeError, match="rede"):
        obter_tramitacoes(transporte, url, 2319917)
    with pytest.raises(RuntimeError, match="rede"):
        obter_deputado(transporte, url, 204455)
