"""Infraestrutura de teste: sem rede, com as fixtures reais de tests/fixtures/camara/."""

import io
import json
import re
import socket
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPMessage
from pathlib import Path

import pytest

from monitor_comissoes.config import Config
from monitor_comissoes.erros import FalhaDeColeta
from monitor_comissoes.transporte import ArquivoBaixado, RespostaJson

FIXTURES = Path(__file__).parent / "fixtures" / "camara"
BRASILIA = timezone(timedelta(hours=-3))
LOCAIS = {"localhost", "127.0.0.1", "::1"}


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Falha qualquer conexão de rede, inclusive para localhost (que pode ser um proxy de saída).

    Os testes usam funções e transportes falsos; nenhum precisa de socket.
    """
    conectar = socket.socket.connect
    resolver = socket.getaddrinfo

    def conectar_local(self, endereco, *args, **kwargs):
        if isinstance(endereco, tuple):
            raise RuntimeError(f"teste tentou usar a rede: {endereco[0]}")
        return conectar(self, endereco, *args, **kwargs)

    def resolver_local(host, *args, **kwargs):
        if host not in LOCAIS:
            raise RuntimeError(f"teste tentou resolver nome na rede: {host}")
        return resolver(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", conectar_local)
    monkeypatch.setattr(socket, "getaddrinfo", resolver_local)


@pytest.fixture(autouse=True)
def sem_ambiente_do_actions(monkeypatch):
    """O CI define GITHUB_ACTIONS=true, o que faria o `_aviso` imprimir anotações do Actions e
    mudaria a saída que os testes conferem. Os testes da anotação definem a variável por conta
    própria."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


@pytest.fixture
def agora():
    return datetime(2026, 10, 18, 9, 0, tzinfo=BRASILIA)


@pytest.fixture
def config():
    return Config(comissoes=("CE", "CREDN"), ano_minimo=2003)


class RespostaFalsa:
    def __init__(self, corpo: bytes, cabecalhos: dict[str, str]):
        self._corpo = io.BytesIO(corpo)
        self.headers = HTTPMessage()
        for nome, valor in cabecalhos.items():
            self.headers[nome] = valor

    def read(self, n=-1):
        return self._corpo.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TransporteFalso:
    """Serve as fixtures como a Câmara serviria, recalculando o tamanho pelo corpo servido.

    transformar[nome]: função bytes -> bytes aplicada ao corpo (variantes derivadas, cortes).
    erro[nome]: FalhaDeColeta levantada ao pedir o arquivo (use "deputados" para a API).
    last_modified[nome]: sobrescreve o Last-Modified do manifesto.
    transformar_json[chave] / erro_json[chave]: o mesmo para as respostas da API por proposição
    ("tramitacoes/{id}") e por deputado ("deputados/{id}"), servidas de fixtures/<chave>.json.
    """

    def __init__(self):
        manifesto = json.loads((FIXTURES / "manifesto.json").read_text(encoding="utf-8"))
        self._last_modified = {
            nome: parsedate_to_datetime(dados["last_modified"]).astimezone(UTC)
            for nome, dados in manifesto["arquivos"].items()
        }
        self.pedidos: list[str] = []
        self.transformar: dict[str, Callable[[bytes], bytes]] = {}
        self.erro: dict[str, FalhaDeColeta] = {}
        self.last_modified: dict[str, datetime] = {}
        self.json_deputados = (FIXTURES / "deputados-novo.json").read_bytes()
        self.total_deputados = "5"
        self.transformar_json: dict[str, Callable[[bytes], bytes]] = {}
        self.erro_json: dict[str, FalhaDeColeta] = {}

    def obter_json(self, url: str) -> RespostaJson:
        self.pedidos.append(url)
        por_id = re.search(r"/api/v2/(proposicoes|deputados)/(\d+)(/tramitacoes)?$", url)
        if por_id:
            return self._json_por_id(por_id)
        if "deputados" in self.erro:
            raise self.erro["deputados"]
        cabecalhos = {} if self.total_deputados is None else {"x-total-count": self.total_deputados}
        return RespostaJson(corpo=self.json_deputados, cabecalhos=cabecalhos)

    def _json_por_id(self, achado) -> RespostaJson:
        recurso, numero, tramitacoes = achado.groups()
        chave = f"{'tramitacoes' if tramitacoes else 'deputados'}/{numero}"
        if chave in self.erro_json:
            raise self.erro_json[chave]
        arquivo = FIXTURES / f"{chave}.json"
        assert arquivo.exists(), f"fixture ausente: {arquivo.relative_to(FIXTURES)} ({recurso})"
        corpo = arquivo.read_bytes()
        if chave in self.transformar_json:
            corpo = self.transformar_json[chave](corpo)
        return RespostaJson(corpo=corpo, cabecalhos={})

    def baixar(self, url: str, destino: Path) -> ArquivoBaixado:
        nome = url.rsplit("/", 1)[1]
        self.pedidos.append(url)
        if nome in self.erro:
            raise self.erro[nome]
        corpo = (FIXTURES / nome).read_bytes()
        if nome in self.transformar:
            corpo = self.transformar[nome](corpo)
        destino.write_bytes(corpo)
        return ArquivoBaixado(
            caminho=destino,
            tamanho=len(corpo),
            last_modified=self.last_modified.get(nome, self._last_modified[nome]),
        )

    def arquivos_pedidos(self) -> list[str]:
        return [url.rsplit("/", 1)[1] for url in self.pedidos if url.endswith(".csv")]


@pytest.fixture
def transporte():
    return TransporteFalso()
