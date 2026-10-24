"""As fixtures da pauta carregam e os construtores sintéticos têm o formato das respostas reais."""

import json

import pytest

from monitor_comissoes.erros import FONTE_INDISPONIVEL, FalhaDeColeta
from pauta_sinteticos import (
    API,
    FIXTURES,
    PAUTA,
    TransportePauta,
    chave,
    deputados_novo,
    detalhe_evento,
    evento,
    falha_http,
    indice,
    item_pauta,
    lista_eventos,
)


def _ler(relativo):
    return json.loads((PAUTA / relativo).read_text(encoding="utf-8"))


def _itens_reais():
    return [
        item
        for arquivo in sorted((PAUTA / "pautas").glob("*.json"))
        for item in _ler(arquivo)["dados"]
    ]


def test_o_manifesto_lista_exatamente_as_respostas_salvas():
    manifesto = _ler("manifesto.json")
    salvos = {
        caminho.relative_to(PAUTA).as_posix()
        for pasta in ("orgaos", "eventos", "pautas")
        for caminho in (PAUTA / pasta).glob("*.json")
    }
    assert set(manifesto["arquivos"]) == salvos
    for dados in manifesto["arquivos"].values():
        assert dados["endpoint"].startswith("/")
        assert dados["capturado_em"].startswith("2026-10-24")


def test_cada_resposta_salva_e_json_com_dados():
    for relativo in _ler("manifesto.json")["arquivos"]:
        assert "dados" in _ler(relativo), relativo


def test_atual_de_24_10_tem_o_pl_3701_apensado_ao_pl_5432():
    atual = _ler("atual.json")
    assert atual["meta"]["versao_formato"] == 3
    assert atual["meta"]["gerado_em"] == "2026-10-24T08:34:13-03:00"
    apensado = next(i for i in atual["itens"] if i["identificacao"] == "PL 3701/2020")
    assert apensado["apensado_a"]["id"] == 2086175


def test_transporte_serve_cada_endpoint_pela_fixture():
    transporte = TransportePauta()
    orgao = transporte.obter_json(f"{API}/orgaos?sigla=CE&itens=10")
    janela = transporte.obter_json(
        f"{API}/orgaos/2009/eventos?dataInicio=2026-10-17&dataFim=2026-10-31&itens=100"
    )
    detalhe = transporte.obter_json(f"{API}/eventos/83091")
    itens = transporte.obter_json(f"{API}/eventos/83091/pauta")
    deputados = transporte.obter_json(f"{API}/deputados?siglaPartido=NOVO&itens=100")

    assert json.loads(orgao.corpo)["dados"][0]["id"] == 2009
    assert janela.cabecalhos == {"x-total-count": "2"}
    assert [e["id"] for e in json.loads(janela.corpo)["dados"]] == [83091, 83092]
    assert json.loads(detalhe.corpo)["dados"]["situacao"] == "Convocada"
    assert len(json.loads(itens.corpo)["dados"]) == 20
    assert deputados.cabecalhos == {"x-total-count": "5"}
    assert transporte.pedidos_por_chave() == [
        "orgaos/CE",
        "eventos/2009-2026-10-17-2026-10-31",
        "eventos/83091",
        "pautas/83091",
        "deputados-novo",
    ]


def test_transporte_sobrepoe_respostas_e_erros_por_chave():
    transporte = TransportePauta()
    transporte.respostas["pautas/83091"] = {"dados": [], "links": []}
    transporte.cabecalhos["pautas/83091"] = {"x-total-count": "0"}
    transporte.erro["eventos/99999"] = falha_http(f"{API}/eventos/99999", 404)

    resposta = transporte.obter_json(f"{API}/eventos/83091/pauta")
    assert json.loads(resposta.corpo) == {"dados": [], "links": []}
    assert resposta.cabecalhos == {"x-total-count": "0"}
    with pytest.raises(FalhaDeColeta) as erro:
        transporte.obter_json(f"{API}/eventos/99999")
    assert erro.value.categoria == FONTE_INDISPONIVEL
    assert "HTTP 404" in erro.value.motivo


def test_pagina_alem_da_primeira_so_existe_sobreposta():
    url = f"{API}/orgaos/2009/eventos?dataInicio=2026-10-17&dataFim=2026-10-31&pagina=2&itens=100"
    assert chave(url) == url
    with pytest.raises(AssertionError, match="fixture ausente"):
        TransportePauta().obter_json(url)


def test_transporte_nao_baixa_arquivos(tmp_path):
    with pytest.raises(AssertionError):
        TransportePauta().baixar(f"{API}/qualquer.csv", tmp_path / "x")


def test_falha_http_reproduz_o_transporte_real():
    for codigo in (404, 400, 503):
        falha = falha_http(f"{API}/eventos/1", codigo)
        assert isinstance(falha, FalhaDeColeta)
        assert falha.categoria == FONTE_INDISPONIVEL
        assert f"HTTP {codigo}" in falha.motivo


def test_evento_tem_as_chaves_da_lista_real():
    real = _ler("eventos/2009-2026-04-08-2026-04-22.json")
    assert list(evento(1, "2026-10-28T10:00")) == list(real["dados"][0])
    assert list(evento(1, "2026-10-28T10:00")["orgaos"][0]) == list(real["dados"][0]["orgaos"][0])
    assert list(lista_eventos([])) == list(real)
    assert [link["rel"] for link in lista_eventos([])["links"]] == [
        link["rel"] for link in real["links"]
    ]


def test_detalhe_tem_as_chaves_do_detalhe_real():
    real = _ler("eventos/81555.json")
    sintetico = detalhe_evento(1, "2026-10-28T10:00")
    assert list(sintetico) == list(real)
    assert set(sintetico["dados"]) == set(real["dados"])


def test_item_de_pauta_tem_as_chaves_do_item_real():
    reais = _itens_reais()
    com_relacionada = next(i for i in reais if i["proposicaoRelacionada_"] and i["relator"])
    sintetico = item_pauta(
        5,
        proposicao=(2615445, "REQ 17/2026"),
        relacionada=(2247358, "PL 1778/2020"),
        relator=(220629, "Dandara", "PT"),
        situacao_item="Aprovado o Requerimento.",
    )

    assert set(sintetico) == set(com_relacionada)
    assert list(sintetico["proposicao_"]) == list(com_relacionada["proposicao_"])
    assert list(sintetico["proposicaoRelacionada_"]) == list(
        com_relacionada["proposicaoRelacionada_"]
    )
    assert list(sintetico["relator"]) == list(com_relacionada["relator"])
    assert sintetico["proposicaoRelacionada_"]["numero"] == "1778"
    assert sintetico["proposicaoRelacionada_"]["ano"] == "2020"
    assert sintetico["proposicao_"]["numero"] == 17
    assert sintetico["titulo"] == "REQ 17/2026"


def test_item_de_pauta_sem_partido_do_relator_e_sem_proposicao():
    sem_partido = item_pauta(1, proposicao=(2, "PL 3464/2025"), relator=(204455, "Luiz Lima"))
    vazio = item_pauta(2)
    assert sem_partido["relator"]["siglaPartido"] is None
    assert vazio["proposicao_"] is None
    assert vazio["proposicaoRelacionada_"] is None
    assert vazio["relator"] is None
    assert vazio["situacaoItem"] is None


def test_indice_segue_o_contrato():
    documento = indice({2645503: (0, [220629]), 2267727: (1, [204528, 178929, 204528])})
    assert list(documento) == [
        "versao_formato",
        "gerado_em",
        "dados_camara_em",
        "anos_lidos",
        "tipos",
        "proposicoes",
    ]
    assert documento["proposicoes"] == {"2645503": [0, [220629]], "2267727": [1, [178929, 204528]]}


def test_deputados_novo_tem_as_chaves_da_fixture_real():
    real = json.loads((FIXTURES / "camara" / "deputados-novo.json").read_text(encoding="utf-8"))
    sintetico = deputados_novo([204455, 1])
    assert list(sintetico["dados"][0]) == list(real["dados"][0])
    assert sintetico["dados"][0]["nome"] == "Luiz Lima"
    assert sintetico["dados"][1]["nome"] == "Deputado 1"
