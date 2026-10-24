"""API da pauta: órgão, eventos da janela (paginação), evento por id e pauta, com validação."""

from datetime import date

import pytest

from monitor_comissoes.erros import FONTE_INDISPONIVEL, FORMATO_ALTERADO, FalhaDeColeta
from monitor_comissoes.pauta.api import obter_evento, obter_eventos, obter_orgao, obter_pauta
from pauta_sinteticos import (
    API,
    TransportePauta,
    evento,
    falha_http,
    item_pauta,
    lista_eventos,
    pauta,
)

INICIO, FIM = date(2026, 10, 17), date(2026, 10, 31)
CHAVE_JANELA = "eventos/2009-2026-10-17-2026-10-31"


def _falha(funcao, *args, categoria=FORMATO_ALTERADO):
    with pytest.raises(FalhaDeColeta) as erro:
        funcao(*args)
    assert erro.value.categoria == categoria
    return erro.value.motivo


# --- órgão ------------------------------------------------------------------------------------


def test_orgao_pela_sigla():
    transporte = TransportePauta()

    assert obter_orgao(transporte, "CE") == 2009
    assert obter_orgao(transporte, "CREDN") == 2018
    assert transporte.pedidos_por_chave() == ["orgaos/CE", "orgaos/CREDN"]


@pytest.mark.parametrize(
    "dados",
    [
        [],
        [{"id": 2009, "sigla": "CE"}, {"id": 2010, "sigla": "CE"}],
        [{"id": 2009, "sigla": "CEX"}],
        [{"id": "2009", "sigla": "CE"}],
    ],
    ids=["sem-orgao", "dois", "sigla-diferente", "id-texto"],
)
def test_orgao_fora_do_esperado_e_formato_alterado(dados):
    transporte = TransportePauta()
    transporte.respostas["orgaos/CE"] = {"dados": dados, "links": []}

    motivo = _falha(obter_orgao, transporte, "CE")

    assert "CE" in motivo


# --- eventos da janela -------------------------------------------------------------------------


def test_eventos_da_janela_pela_fixture():
    transporte = TransportePauta()

    eventos = obter_eventos(transporte, 2009, INICIO, FIM)

    assert [e["id"] for e in eventos] == [83091, 83092]
    url = transporte.pedidos[0]
    assert url.startswith(f"{API}/orgaos/2009/eventos?")
    assert "dataInicio=2026-10-17" in url
    assert "dataFim=2026-10-31" in url
    assert "itens=100" in url


def test_eventos_seguem_a_paginacao_dos_links():
    transporte = TransportePauta()
    pagina2 = (
        f"{API}/orgaos/2009/eventos?dataInicio=2026-10-17&dataFim=2026-10-31&pagina=2&itens=100"
    )
    primeira = lista_eventos([evento(1, "2026-10-20T10:00")])
    primeira["links"].append({"rel": "next", "href": pagina2})
    transporte.respostas[CHAVE_JANELA] = primeira
    transporte.cabecalhos[CHAVE_JANELA] = {"x-total-count": "2"}
    transporte.respostas[pagina2] = lista_eventos([evento(2, "2026-10-21T10:00")])
    transporte.cabecalhos[pagina2] = {"x-total-count": "2"}

    eventos = obter_eventos(transporte, 2009, INICIO, FIM)

    assert [e["id"] for e in eventos] == [1, 2]
    assert transporte.pedidos[1] == pagina2


def test_semana_sem_eventos_e_lista_vazia():
    transporte = TransportePauta()
    transporte.respostas[CHAVE_JANELA] = lista_eventos([])
    transporte.cabecalhos[CHAVE_JANELA] = {"x-total-count": "0"}

    assert obter_eventos(transporte, 2009, INICIO, FIM) == []


@pytest.mark.parametrize(
    ("cabecalhos", "trecho"),
    [
        ({"x-total-count": "3"}, "anunciou 3"),
        ({}, "X-Total-Count"),
        ({"x-total-count": "x"}, "X-Total-Count"),
    ],
    ids=["total-diferente", "sem-total", "total-invalido"],
)
def test_total_de_eventos_conferido(cabecalhos, trecho):
    transporte = TransportePauta()
    transporte.respostas[CHAVE_JANELA] = lista_eventos([evento(1, "2026-10-20T10:00")])
    transporte.cabecalhos[CHAVE_JANELA] = cabecalhos

    assert trecho in _falha(obter_eventos, transporte, 2009, INICIO, FIM)


def test_link_de_paginacao_fora_da_api_ou_repetido():
    for proxima, trecho in (
        ("https://exemplo.invalido/api/v2/eventos", "fora da API"),
        (
            f"{API}/orgaos/2009/eventos?dataInicio=2026-10-17&dataFim=2026-10-31&itens=100",
            "já lida",
        ),
    ):
        transporte = TransportePauta()
        corpo = lista_eventos([evento(1, "2026-10-20T10:00")])
        corpo["links"].append({"rel": "next", "href": proxima})
        transporte.respostas[CHAVE_JANELA] = corpo
        transporte.cabecalhos[CHAVE_JANELA] = {"x-total-count": "1"}

        assert trecho in _falha(obter_eventos, transporte, 2009, INICIO, FIM)


def _sem(dicionario, campo):
    return {k: v for k, v in dicionario.items() if k != campo}


@pytest.mark.parametrize(
    ("alterar", "campo"),
    [
        (lambda e: {**e, "id": "1"}, "id"),
        (lambda e: _sem(e, "id"), "id"),
        (lambda e: {**e, "dataHoraInicio": "2026-10-20"}, "dataHoraInicio"),
        (lambda e: {**e, "dataHoraInicio": "2026-10-20T10:00:00"}, "dataHoraInicio"),
        (lambda e: {**e, "situacao": None}, "situacao"),
        (lambda e: _sem(e, "descricaoTipo"), "descricaoTipo"),
        (lambda e: {**e, "orgaos": {}}, "orgaos"),
        (lambda e: {**e, "orgaos": [{"sigla": "CE"}]}, "orgaos"),
    ],
)
def test_evento_fora_do_formato(alterar, campo):
    transporte = TransportePauta()
    transporte.respostas[CHAVE_JANELA] = lista_eventos([alterar(evento(1, "2026-10-20T10:00"))])
    transporte.cabecalhos[CHAVE_JANELA] = {"x-total-count": "1"}

    assert campo in _falha(obter_eventos, transporte, 2009, INICIO, FIM)


@pytest.mark.parametrize("corpo", [b"{nao e json", b"[]", b'{"dados": {}}'])
def test_corpo_inesperado_e_formato_alterado(corpo):
    transporte = TransportePauta()
    transporte.respostas[CHAVE_JANELA] = corpo
    transporte.cabecalhos[CHAVE_JANELA] = {"x-total-count": "0"}

    motivo = _falha(obter_eventos, transporte, 2009, INICIO, FIM)

    assert "/orgaos/2009/eventos" in motivo


def test_erro_de_rede_vira_fonte_indisponivel_com_o_endpoint():
    transporte = TransportePauta()
    url = f"{API}/orgaos/2009/eventos?dataInicio=2026-10-17&dataFim=2026-10-31&itens=100"
    transporte.erro[CHAVE_JANELA] = falha_http(url, 503)

    motivo = _falha(obter_eventos, transporte, 2009, INICIO, FIM, categoria=FONTE_INDISPONIVEL)

    assert "/orgaos/2009/eventos" in motivo
    assert "HTTP 503" in motivo


# --- evento por id -----------------------------------------------------------------------------


def test_evento_por_id_pelo_detalhe():
    evento_lido = obter_evento(TransportePauta(), 81555)

    assert evento_lido["id"] == 81555
    assert evento_lido["dataHoraInicio"] == "2026-04-15T10:00"
    assert evento_lido["situacao"] == "Encerrada (Final)"


def test_evento_inexistente_e_none():
    transporte = TransportePauta()
    transporte.erro["eventos/99999"] = falha_http(f"{API}/eventos/99999", 404)

    assert obter_evento(transporte, 99999) is None


@pytest.mark.parametrize("codigo", [400, 500])
def test_outro_erro_do_evento_propaga(codigo):
    transporte = TransportePauta()
    transporte.erro["eventos/99999"] = falha_http(f"{API}/eventos/99999", codigo)

    motivo = _falha(obter_evento, transporte, 99999, categoria=FONTE_INDISPONIVEL)

    assert "/eventos/99999" in motivo


def test_detalhe_fora_do_formato():
    transporte = TransportePauta()
    transporte.respostas["eventos/81555"] = {"dados": {"id": 81555}, "links": []}

    assert "dataHoraInicio" in _falha(obter_evento, transporte, 81555)


# --- pauta -------------------------------------------------------------------------------------


def test_pauta_real_carrega_inteira():
    itens = obter_pauta(TransportePauta(), 81555)

    assert len(itens) == 30
    req = next(i for i in itens if i["titulo"] == "REQ 17/2026 CE")
    assert req["proposicaoRelacionada_"]["numero"] == "1778"


def test_todas_as_pautas_salvas_passam_na_validacao():
    for id_evento in (80265, 80344, 80594, 80732, 81483, 81609, 81862, 83091):
        assert obter_pauta(TransportePauta(), id_evento)


def test_pauta_vazia():
    transporte = TransportePauta()
    transporte.respostas["pautas/83091"] = pauta([])

    assert obter_pauta(transporte, 83091) == []


def _com_item(item):
    transporte = TransportePauta()
    transporte.respostas["pautas/83091"] = pauta([item])
    return transporte


def test_item_minimo_e_valido():
    item = item_pauta(
        1, proposicao=(1, "PL 1/2020"), relacionada=(2, "PL 2/2021"), relator=(3, "X")
    )

    assert obter_pauta(_com_item(item), 83091) == [item]
    assert obter_pauta(_com_item(item_pauta(1)), 83091) == [item_pauta(1)]


_APAGAR = object()


def _alterado(campo, valor, sub=None):
    item = item_pauta(
        1, proposicao=(1, "PL 1/2020"), relacionada=(2, "PL 2/2021"), relator=(3, "X")
    )
    if sub is None:
        item[campo] = valor
    elif valor is _APAGAR:
        del item[campo][sub]
    else:
        item[campo][sub] = valor
    return item


@pytest.mark.parametrize(
    ("item", "campo"),
    [
        (_alterado("ordem", "1"), "ordem"),
        (_alterado("titulo", None), "titulo"),
        (_alterado("proposicao_", "PL 1/2020"), "proposicao_"),
        (_alterado("proposicao_", "1", "id"), "proposicao_.id"),
        (_alterado("proposicao_", None, "siglaTipo"), "proposicao_.siglaTipo"),
        (_alterado("proposicao_", "1a", "numero"), "proposicao_.numero"),
        (_alterado("proposicaoRelacionada_", None, "ano"), "proposicaoRelacionada_.ano"),
        (_alterado("proposicaoRelacionada_", _APAGAR, "id"), "proposicaoRelacionada_.id"),
        (_alterado("relator", [], None), "relator"),
        (_alterado("relator", _APAGAR, "nome"), "relator.nome"),
        (_alterado("situacaoItem", 3), "situacaoItem"),
    ],
)
def test_item_fora_do_formato_falha_com_o_campo(item, campo):
    motivo = _falha(obter_pauta, _com_item(item), 83091)

    assert campo in motivo
    assert "/eventos/83091/pauta" in motivo


def test_campo_ausente_do_item():
    item = item_pauta(1)
    del item["situacaoItem"]

    assert "situacaoItem" in _falha(obter_pauta, _com_item(item), 83091)


def test_pauta_com_404_e_fonte_indisponivel():
    transporte = TransportePauta()
    transporte.erro["pautas/83091"] = falha_http(f"{API}/eventos/83091/pauta", 404)

    motivo = _falha(obter_pauta, transporte, 83091, categoria=FONTE_INDISPONIVEL)

    assert "/eventos/83091/pauta" in motivo
