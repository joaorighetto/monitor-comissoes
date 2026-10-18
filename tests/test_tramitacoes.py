"""Leitura e validação das tramitações da API (research R1, contracts/api-camara.md)."""

import json

import pytest

from conftest import FIXTURES
from monitor_comissoes.erros import FONTE_INDISPONIVEL, FORMATO_ALTERADO, FalhaDeColeta
from monitor_comissoes.tramitacoes import obter_tramitacoes

URL_BASE = "https://dadosabertos.camara.leg.br"
PL_937_2022 = 2319917
PL_1843_2022 = 2331032


def alterar(transporte, id_proposicao, funcao):
    """Variante DERIVADA da resposta real: `funcao` altera o JSON já lido. Só existe no teste."""

    def transformar(corpo: bytes) -> bytes:
        documento = json.loads(corpo)
        resultado = funcao(documento)
        return json.dumps(documento if resultado is None else resultado).encode()

    transporte.transformar_json[f"tramitacoes/{id_proposicao}"] = transformar


def test_le_as_tramitacoes_reais_ordenadas_por_sequencia(transporte):
    tramitacoes = obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    sequencias = [t.sequencia for t in tramitacoes]
    assert sequencias == sorted(sequencias)
    assert len(tramitacoes) == 17
    assert transporte.pedidos == [f"{URL_BASE}/api/v2/proposicoes/{PL_937_2022}/tramitacoes"]
    ultima = tramitacoes[-1]
    assert (ultima.sequencia, ultima.orgao, ultima.codigo) == (28, "CE", "507")


def test_so_a_designacao_traz_o_id_do_relator(transporte):
    tramitacoes = obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    designacoes = [t for t in tramitacoes if t.codigo == "320"]
    assert [t.id_relator for t in designacoes] == [220608, 204455, 204455]
    # uriUltimoRelator se repete nas tramitações seguintes, mas não vale como relator.
    assert all(t.id_relator is None for t in tramitacoes if t.codigo != "320")


def test_le_o_despacho_real_de_cada_tramitacao(transporte):
    tramitacoes = {t.sequencia: t for t in obter_tramitacoes(transporte, URL_BASE, PL_937_2022)}

    assert tramitacoes[28].despacho == "Devolvida pelo Relator sem Manifestação."
    assert tramitacoes[16].despacho == "Designada Relatora, Dep. Cristiane Lopes (UNIÃO-RO)"


def test_despacho_nulo_ou_ausente_vira_texto_vazio(transporte):
    def apagar(documento):
        documento["dados"][0]["despacho"] = None
        del documento["dados"][1]["despacho"]

    alterar(transporte, PL_937_2022, apagar)

    tramitacoes = obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    por_sequencia = {t.sequencia: t for t in tramitacoes}
    assert sum(1 for t in tramitacoes if t.despacho == "") == 2
    assert all(isinstance(t.despacho, str) for t in por_sequencia.values())


@pytest.mark.parametrize("valor", [5, True, ["x"], {"a": 1}])
def test_despacho_que_nao_e_texto_e_formato_alterado(transporte, valor):
    def estragar(documento):
        documento["dados"][3]["despacho"] = valor

    alterar(transporte, PL_937_2022, estragar)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "despacho" in erro.value.motivo


def test_designacao_sem_relator_fica_com_id_nulo(transporte):
    def sem_relator(documento):
        for t in documento["dados"]:
            if t["codTipoTramitacao"] == "320":
                t["uriUltimoRelator"] = None

    alterar(transporte, PL_937_2022, sem_relator)

    tramitacoes = obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert all(t.id_relator is None for t in tramitacoes)


def test_a_ordem_da_resposta_nao_importa(transporte):
    def inverter(documento):
        documento["dados"].reverse()

    alterar(transporte, PL_1843_2022, inverter)

    tramitacoes = obter_tramitacoes(transporte, URL_BASE, PL_1843_2022)

    sequencias = [t.sequencia for t in tramitacoes]
    assert sequencias == sorted(sequencias)


# --- falhas: rede e HTTP ------------------------------------------------------------------


def test_erro_de_rede_ou_http_mantem_fonte_indisponivel_e_diz_a_proposicao(transporte):
    transporte.erro_json[f"tramitacoes/{PL_937_2022}"] = FalhaDeColeta(
        FONTE_INDISPONIVEL, "tramitacoes: HTTP 503"
    )

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FONTE_INDISPONIVEL
    assert str(PL_937_2022) in erro.value.motivo
    assert "503" in erro.value.motivo


# --- falhas: formato ----------------------------------------------------------------------


def corpo_invalido(transporte, corpo: bytes):
    transporte.transformar_json[f"tramitacoes/{PL_937_2022}"] = lambda _: corpo


@pytest.mark.parametrize(
    "corpo",
    [
        b"<html>erro</html>",
        b"[]",
        b'{"links": []}',
        b'{"dados": {}, "links": []}',
        b'{"dados": [], "links": []}',
    ],
)
def test_resposta_que_nao_e_a_lista_esperada_ou_vazia_e_formato_alterado(transporte, corpo):
    corpo_invalido(transporte, corpo)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert str(PL_937_2022) in erro.value.motivo


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("sequencia", None),
        ("sequencia", "15"),
        ("sequencia", True),
        ("siglaOrgao", None),
        ("codTipoTramitacao", 320),
        ("codTipoTramitacao", None),
        ("dataHora", None),
        ("descricaoTramitacao", 5),
        ("uriUltimoRelator", 204455),
    ],
)
def test_campo_com_tipo_errado_e_formato_alterado(transporte, campo, valor):
    def estragar(documento):
        documento["dados"][4][campo] = valor

    alterar(transporte, PL_937_2022, estragar)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert campo in erro.value.motivo


@pytest.mark.parametrize("campo", ["sequencia", "siglaOrgao", "codTipoTramitacao", "dataHora"])
def test_campo_obrigatorio_ausente_e_formato_alterado(transporte, campo):
    def remover(documento):
        del documento["dados"][2][campo]

    alterar(transporte, PL_937_2022, remover)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert campo in erro.value.motivo


def test_sequencia_repetida_e_formato_alterado(transporte):
    def repetir(documento):
        documento["dados"][3]["sequencia"] = documento["dados"][2]["sequencia"]

    alterar(transporte, PL_937_2022, repetir)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "sequencia" in erro.value.motivo


def test_paginacao_inesperada_e_formato_alterado(transporte):
    def com_proxima(documento):
        documento["links"].append({"rel": "next", "href": f"{URL_BASE}/api/v2/x?pagina=2"})

    alterar(transporte, PL_937_2022, com_proxima)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "paginação" in erro.value.motivo


@pytest.mark.parametrize(
    "href", ["https://outro-host.example/api/v2/x", "file:///etc/passwd", f"{URL_BASE}/fora"]
)
def test_link_fora_da_api_da_camara_e_formato_alterado(transporte, href):
    def com_link(documento):
        documento["links"].append({"rel": "self", "href": href})

    alterar(transporte, PL_937_2022, com_link)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO


@pytest.mark.parametrize("uri", ["https://x/deputados/abc", "https://x/deputados/", ""])
def test_designacao_com_uri_de_relator_invalida_e_formato_alterado(transporte, uri):
    def estragar(documento):
        for t in documento["dados"]:
            if t["codTipoTramitacao"] == "320":
                t["uriUltimoRelator"] = uri

    alterar(transporte, PL_937_2022, estragar)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "uriUltimoRelator" in erro.value.motivo


def test_fixtures_reais_de_todas_as_referencias_passam_na_validacao(transporte):
    manifesto = json.loads((FIXTURES / "manifesto.json").read_text(encoding="utf-8"))
    ids = manifesto["selecao"]["referencias_com_tramitacoes"]

    for id_proposicao in ids:
        assert obter_tramitacoes(transporte, URL_BASE, id_proposicao)


# --- revisão independente: validação mais firme (M1) -----------------------------------------


@pytest.mark.parametrize(
    "uri",
    [
        "https://dadosabertos.camara.leg.br/api/v2/deputados/²",
        "https://dadosabertos.camara.leg.br/api/v2/deputados/٣",
        "https://dadosabertos.camara.leg.br/api/v2/orgaos/55",
        "https://dadosabertos.camara.leg.br/api/v2/deputados",
    ],
)
def test_uri_do_relator_precisa_ser_de_deputado_com_id_inteiro_ascii(transporte, uri):
    def estragar(documento):
        for t in documento["dados"]:
            if t["codTipoTramitacao"] == "320":
                t["uriUltimoRelator"] = uri

    alterar(transporte, PL_937_2022, estragar)

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO


@pytest.mark.parametrize(
    "data_hora",
    ["ontem", "2026-10-18", "18/10/2026 10:00", "", "٢٠٢٦-١٠-١٨T١٠:٠٠"],  # dígitos árabes
)
def test_data_hora_fora_do_formato_e_formato_alterado(transporte, data_hora):
    alterar(transporte, PL_937_2022, lambda d: d["dados"][0].update(dataHora=data_hora))

    with pytest.raises(FalhaDeColeta) as erro:
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "dataHora" in erro.value.motivo


def test_data_hora_com_segundos_e_aceita(transporte):
    alterar(transporte, PL_937_2022, lambda d: d["dados"][0].update(dataHora="2022-04-18T15:44:07"))

    assert (
        obter_tramitacoes(transporte, URL_BASE, PL_937_2022)[0].data_hora == "2022-04-18T15:44:07"
    )
