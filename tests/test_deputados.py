import json

import pytest

from monitor_comissoes.deputados import obter_deputados_novo
from monitor_comissoes.erros import API_DEPUTADOS, FONTE_INDISPONIVEL, FalhaDeColeta
from monitor_comissoes.transporte import RespostaJson

URL_BASE = "https://dadosabertos.camara.leg.br"


class TransporteDePaginas:
    """Resposta sintética de duas páginas, para testar a paginação por `rel: next`."""

    def __init__(self, paginas, total):
        self.paginas = paginas
        self.total = total
        self.pedidos = []

    def obter_json(self, url):
        self.pedidos.append(url)
        return RespostaJson(
            corpo=json.dumps(self.paginas[url]).encode(), cabecalhos={"x-total-count": self.total}
        )


def test_le_os_deputados_reais_ordenados_por_id(transporte):
    deputados = obter_deputados_novo(transporte, URL_BASE)

    assert [d.id for d in deputados] == [156190, 204365, 204455, 204528, 220633]
    assert {d.nome for d in deputados} == {
        "Marcel van Hattem",
        "Gilson Marques",
        "Luiz Lima",
        "Adriana Ventura",
        "Ricardo Salles",
    }
    assert transporte.pedidos == [f"{URL_BASE}/api/v2/deputados?siglaPartido=NOVO&itens=100"]


def test_segue_a_paginacao_pelo_link_next():
    pagina2 = f"{URL_BASE}/api/v2/deputados?siglaPartido=NOVO&pagina=2&itens=100"
    pagina1 = f"{URL_BASE}/api/v2/deputados?siglaPartido=NOVO&itens=100"
    transporte = TransporteDePaginas(
        {
            pagina1: {
                "dados": [{"id": 2, "nome": "B"}],
                "links": [{"rel": "next", "href": pagina2}],
            },
            pagina2: {
                "dados": [{"id": 1, "nome": "A"}],
                "links": [{"rel": "self", "href": pagina2}],
            },
        },
        total="2",
    )

    deputados = obter_deputados_novo(transporte, URL_BASE)

    assert [d.id for d in deputados] == [1, 2]
    assert transporte.pedidos == [pagina1, pagina2]


def test_total_diferente_de_x_total_count_e_falha(transporte):
    transporte.total_deputados = "9"

    with pytest.raises(FalhaDeColeta) as erro:
        obter_deputados_novo(transporte, URL_BASE)

    assert erro.value.categoria == API_DEPUTADOS
    assert "9" in erro.value.motivo


def test_erro_de_http_vira_api_deputados(transporte):
    transporte.erro["deputados"] = FalhaDeColeta(FONTE_INDISPONIVEL, "deputados: HTTP 503")

    with pytest.raises(FalhaDeColeta) as erro:
        obter_deputados_novo(transporte, URL_BASE)

    assert erro.value.categoria == API_DEPUTADOS
    assert "não foi possível obter os deputados do NOVO" in erro.value.motivo
    assert "503" in erro.value.motivo


@pytest.mark.parametrize(
    "corpo",
    [b"<html>erro</html>", b'{"x": 1}', b'{"dados": [{"nome": "sem id"}]}', b'{"dados": []}'],
)
def test_resposta_invalida_ou_vazia_vira_api_deputados(transporte, corpo):
    transporte.json_deputados = corpo
    transporte.total_deputados = "0"

    with pytest.raises(FalhaDeColeta) as erro:
        obter_deputados_novo(transporte, URL_BASE)

    assert erro.value.categoria == API_DEPUTADOS
