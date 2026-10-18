import urllib.error
from datetime import UTC, datetime
from http.client import HTTPMessage

import pytest

from conftest import RespostaFalsa
from monitor_comissoes.erros import (
    ARQUIVO_INCOMPLETO,
    FONTE_INDISPONIVEL,
    FORMATO_ALTERADO,
    FalhaDeColeta,
)
from monitor_comissoes.transporte import TransporteHttp

URL = "https://exemplo.invalido/arquivos/x.csv"
LAST_MODIFIED = "Sat, 17 Oct 2026 04:33:58 GMT"


def resposta_ok(corpo=b"abc", **extras):
    cabecalhos = {"Content-Length": str(len(corpo)), "Last-Modified": LAST_MODIFIED}
    cabecalhos.update(extras)
    return RespostaFalsa(corpo, {k: v for k, v in cabecalhos.items() if v is not None})


class Abrir:
    """Devolve, em ordem, respostas ou exceções; registra as chamadas."""

    def __init__(self, *saidas):
        self.saidas = list(saidas)
        self.chamadas = []

    def __call__(self, requisicao, timeout=None):
        self.chamadas.append((requisicao, timeout))
        saida = self.saidas.pop(0) if len(self.saidas) > 1 else self.saidas[0]
        if isinstance(saida, Exception):
            raise saida
        return saida() if callable(saida) else saida


def http_erro(codigo):
    return urllib.error.HTTPError(URL, codigo, "erro", HTTPMessage(), None)


def montar(*saidas):
    abrir = Abrir(*saidas)
    esperas = []
    return TransporteHttp(abrir=abrir, dormir=esperas.append), abrir, esperas


def test_baixa_para_o_destino_e_devolve_metadados(tmp_path):
    transporte, abrir, _ = montar(lambda: resposta_ok(b"conteudo"))

    arquivo = transporte.baixar(URL, tmp_path / "x.csv")

    assert (tmp_path / "x.csv").read_bytes() == b"conteudo"
    assert arquivo.tamanho == 8
    assert arquivo.last_modified == datetime(2026, 10, 17, 4, 33, 58, tzinfo=UTC)
    assert abrir.chamadas[0][1] == 60  # timeout de 60 s


def test_falha_temporaria_e_repetida_com_espera_crescente(tmp_path):
    transporte, abrir, esperas = montar(http_erro(503), http_erro(503), lambda: resposta_ok())

    transporte.baixar(URL, tmp_path / "x.csv")

    assert len(abrir.chamadas) == 3
    assert esperas == [2, 4]


def test_503_persistente_vira_fonte_indisponivel(tmp_path):
    transporte, abrir, esperas = montar(http_erro(503))

    with pytest.raises(FalhaDeColeta) as erro:
        transporte.baixar(URL, tmp_path / "x.csv")

    assert erro.value.categoria == FONTE_INDISPONIVEL
    assert "503" in erro.value.motivo
    assert len(abrir.chamadas) == 3
    assert esperas == [2, 4]


def test_404_nao_e_repetido(tmp_path):
    transporte, abrir, _ = montar(http_erro(404))

    with pytest.raises(FalhaDeColeta) as erro:
        transporte.baixar(URL, tmp_path / "x.csv")

    assert erro.value.categoria == FONTE_INDISPONIVEL
    assert "404" in erro.value.motivo
    assert len(abrir.chamadas) == 1


def test_erro_de_rede_persistente(tmp_path):
    transporte, abrir, _ = montar(urllib.error.URLError("sem rota"))

    with pytest.raises(FalhaDeColeta) as erro:
        transporte.baixar(URL, tmp_path / "x.csv")

    assert erro.value.categoria == FONTE_INDISPONIVEL
    assert len(abrir.chamadas) == 3


def test_corpo_menor_que_content_length_e_arquivo_incompleto(tmp_path):
    cortado = lambda: resposta_ok(b"abc", **{"Content-Length": "10"})  # noqa: E731
    transporte, abrir, _ = montar(cortado)
    destino = tmp_path / "x.csv"

    with pytest.raises(FalhaDeColeta) as erro:
        transporte.baixar(URL, destino)

    assert erro.value.categoria == ARQUIVO_INCOMPLETO
    assert len(abrir.chamadas) == 3
    assert not destino.exists()


def test_corte_temporario_se_recupera_na_nova_tentativa(tmp_path):
    cortado = lambda: resposta_ok(b"abc", **{"Content-Length": "10"})  # noqa: E731
    inteiro = lambda: resposta_ok(b"0123456789")  # noqa: E731
    transporte, abrir, _ = montar(cortado, inteiro)

    transporte.baixar(URL, tmp_path / "x.csv")

    assert (tmp_path / "x.csv").read_bytes() == b"0123456789"


def test_sem_content_length_e_formato_alterado(tmp_path):
    transporte, _, _ = montar(lambda: resposta_ok(**{"Content-Length": None}))

    with pytest.raises(FalhaDeColeta) as erro:
        transporte.baixar(URL, tmp_path / "x.csv")

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "Content-Length" in erro.value.motivo


def test_sem_last_modified_e_formato_alterado(tmp_path):
    transporte, _, _ = montar(lambda: resposta_ok(**{"Last-Modified": None}))

    with pytest.raises(FalhaDeColeta) as erro:
        transporte.baixar(URL, tmp_path / "x.csv")

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "Last-Modified" in erro.value.motivo


def test_obter_json_devolve_corpo_e_cabecalhos_em_minusculas():
    corpo = b'{"dados": []}'
    transporte, abrir, _ = montar(
        lambda: RespostaFalsa(corpo, {"X-Total-Count": "5", "Content-Type": "application/json"})
    )

    resposta = transporte.obter_json(URL)

    assert resposta.corpo == corpo
    assert resposta.cabecalhos["x-total-count"] == "5"
    assert abrir.chamadas[0][0].get_header("Accept") == "application/json"


def test_obter_json_repete_falhas_temporarias():
    transporte, abrir, esperas = montar(http_erro(502), lambda: RespostaFalsa(b"{}", {}))

    assert transporte.obter_json(URL).corpo == b"{}"
    assert esperas == [2]
