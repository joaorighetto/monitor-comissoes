"""Acesso HTTP à Câmara, com novas tentativas. As dependências de rede e de tempo são injetáveis."""

import http.client
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Protocol

from .erros import ARQUIVO_INCOMPLETO, FONTE_INDISPONIVEL, FORMATO_ALTERADO, FalhaDeColeta

TENTATIVAS = 3
ESPERAS = (2, 4)  # segundos antes da 2ª e da 3ª tentativa
TIMEOUT = 60
BLOCO = 1 << 20
USER_AGENT = "monitor-comissoes (github.com/joaorighetto/monitor-comissoes)"


@dataclass(frozen=True)
class RespostaJson:
    corpo: bytes
    cabecalhos: dict[str, str]  # nomes em minúsculas


@dataclass(frozen=True)
class ArquivoBaixado:
    caminho: Path
    tamanho: int
    last_modified: datetime  # UTC


class Transporte(Protocol):
    def obter_json(self, url: str) -> RespostaJson: ...

    def baixar(self, url: str, destino: Path) -> ArquivoBaixado: ...


class RecursoInexistente(FalhaDeColeta):
    """HTTP 404: o recurso pedido não existe na API. Não é repetido.

    Mesma categoria de qualquer erro HTTP (`fonte_indisponivel`); quem precisa distinguir o "não
    existe" de uma falha da fonte (a busca de uma reunião que sumiu da agenda) captura esta classe.
    """


class _Repetivel(Exception):
    """Falha que vale uma nova tentativa; leva a falha final caso as tentativas acabem."""

    def __init__(self, falha: FalhaDeColeta) -> None:
        super().__init__(str(falha))
        self.falha = falha


def _nome(url: str) -> str:
    return url.rsplit("/", 1)[-1]


class TransporteHttp:
    def __init__(
        self,
        abrir=urllib.request.urlopen,
        dormir=time.sleep,
        tentativas: int = TENTATIVAS,
        esperas: tuple[int, ...] = ESPERAS,
        timeout: int = TIMEOUT,
    ) -> None:
        self.abrir = abrir
        self.dormir = dormir
        self.tentativas = tentativas
        self.esperas = esperas
        self.timeout = timeout

    def obter_json(self, url: str) -> RespostaJson:
        def tentar() -> RespostaJson:
            with self._requisitar(url, {"Accept": "application/json"}) as resposta:
                corpo = self._ler(resposta, url)
                cabecalhos = {k.lower(): v for k, v in resposta.headers.items()}
            return RespostaJson(corpo=corpo, cabecalhos=cabecalhos)

        return self._com_tentativas(tentar)

    def baixar(self, url: str, destino: Path) -> ArquivoBaixado:
        nome = _nome(url)

        def tentar() -> ArquivoBaixado:
            with self._requisitar(url, {}) as resposta:
                tamanho = resposta.headers.get("Content-Length")
                modificado = resposta.headers.get("Last-Modified")
                if tamanho is None:
                    raise FalhaDeColeta(FORMATO_ALTERADO, f"{nome}: resposta sem Content-Length")
                if modificado is None:
                    raise FalhaDeColeta(FORMATO_ALTERADO, f"{nome}: resposta sem Last-Modified")
                try:
                    esperado = int(tamanho)
                    data = parsedate_to_datetime(modificado).astimezone(UTC)
                except (TypeError, ValueError) as erro:
                    raise FalhaDeColeta(
                        FORMATO_ALTERADO, f"{nome}: Content-Length ou Last-Modified inválido"
                    ) from erro

                recebido = 0
                try:
                    with open(destino, "wb") as saida:
                        while bloco := self._ler(resposta, url, BLOCO):
                            saida.write(bloco)
                            recebido += len(bloco)
                except BaseException:
                    destino.unlink(missing_ok=True)
                    raise

            if recebido != esperado:
                destino.unlink(missing_ok=True)
                raise _Repetivel(
                    FalhaDeColeta(
                        ARQUIVO_INCOMPLETO, f"{nome}: recebidos {recebido} de {esperado} bytes"
                    )
                )
            return ArquivoBaixado(caminho=destino, tamanho=recebido, last_modified=data)

        return self._com_tentativas(tentar)

    def _requisitar(self, url: str, cabecalhos: dict[str, str]):
        requisicao = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **cabecalhos})
        try:
            return self.abrir(requisicao, timeout=self.timeout)
        except urllib.error.HTTPError as erro:
            classe = RecursoInexistente if erro.code == 404 else FalhaDeColeta
            falha = classe(FONTE_INDISPONIVEL, f"{_nome(url)}: HTTP {erro.code}")
            if erro.code >= 500 or erro.code == 429:
                raise _Repetivel(falha) from erro
            raise falha from erro
        except (urllib.error.URLError, OSError) as erro:
            raise _Repetivel(FalhaDeColeta(FONTE_INDISPONIVEL, f"{_nome(url)}: {erro}")) from erro

    def _ler(self, resposta, url: str, tamanho: int = -1) -> bytes:
        try:
            return resposta.read(tamanho)
        except (http.client.IncompleteRead, OSError) as erro:
            raise _Repetivel(
                FalhaDeColeta(FONTE_INDISPONIVEL, f"{_nome(url)}: leitura interrompida ({erro})")
            ) from erro

    def _com_tentativas(self, tentar):
        for numero in range(self.tentativas):
            try:
                return tentar()
            except _Repetivel as repetivel:
                if numero == self.tentativas - 1:
                    raise repetivel.falha from None
                self.dormir(self.esperas[numero])
        raise AssertionError("tentativas deve ser maior que zero")  # pragma: no cover
