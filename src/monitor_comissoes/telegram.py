"""Cliente da Bot API do Telegram: só `sendMessage`, com `urllib` (sem dependência nova).

Contrato em specs/005-resumo-telegram/contracts/aviso-cli.md. O token vai na URL da Bot API; por
isso nenhuma mensagem de erro é montada a partir da URL, e todo texto que vem de fora (descrição
do Telegram, exceção do `urllib`) passa por `sem_segredos` antes de entrar em uma `FalhaDeEnvio`.
"""

import http.client
import json
import time
import urllib.error
import urllib.request

from .erros import FalhaDeEnvio

LIMITE_TENTATIVAS = 3
ESPERAS = (5, 15)  # segundos antes da 2ª e da 3ª tentativa
RETRY_AFTER_MAXIMO = 60
TIMEOUT = 30
USER_AGENT = "monitor-comissoes (github.com/joaorighetto/monitor-comissoes)"
API = "https://api.telegram.org"


def sem_segredos(texto: str, token: str, chat_id: str) -> str:
    """Troca o token e o chat_id, onde aparecerem, por `***`.

    Troca também a forma escapada (`repr`) de cada um: as exceções do `http.client` citam a
    URL entre aspas, e um segredo com caractere de controle sairia escapado.
    """
    for segredo in (token, chat_id):
        if segredo:
            for forma in (segredo, repr(segredo)[1:-1]):
                texto = texto.replace(forma, "***")
    return texto


class _Repetir(Exception):
    """Falha passageira: vale outra tentativa depois de `espera` segundos."""

    def __init__(self, motivo: str, espera: float | None = None) -> None:
        super().__init__(motivo)
        self.motivo = motivo
        self.espera = espera


class ClienteTelegram:
    def __init__(
        self,
        token: str,
        chat_id: str,
        abrir=urllib.request.urlopen,
        dormir=time.sleep,
        timeout: int = TIMEOUT,
    ) -> None:
        if not token.strip() or not chat_id.strip():
            raise ValueError("credencial do Telegram vazia (token e chat_id são obrigatórios)")
        if any(c.isspace() or not c.isprintable() for c in token + chat_id):
            # Sem mostrar o valor: ele é o segredo.
            raise ValueError("credencial do Telegram com espaço ou caractere de controle")
        self._token = token
        self._chat_id = chat_id
        self._abrir = abrir
        self._dormir = dormir
        self._timeout = timeout

    def __repr__(self) -> str:
        return "ClienteTelegram(...)"

    def _limpo(self, texto: str) -> str:
        return sem_segredos(texto, self._token, self._chat_id)

    def enviar(self, texto: str) -> None:
        """Envia `texto` ao grupo. Levanta `FalhaDeEnvio` (sem segredo) se não for aceito."""
        ultimo = ""
        for numero in range(LIMITE_TENTATIVAS):
            try:
                self._tentar(texto)
                return
            except _Repetir as repetir:
                ultimo = repetir.motivo
                if numero == LIMITE_TENTATIVAS - 1:
                    break
                espera = repetir.espera if repetir.espera is not None else ESPERAS[numero]
                self._dormir(espera)
        raise FalhaDeEnvio(
            f"a Bot API não aceitou a mensagem depois de {LIMITE_TENTATIVAS} tentativas: {ultimo}"
        )

    def _tentar(self, texto: str) -> None:
        corpo = json.dumps(
            {
                "chat_id": self._chat_id,
                "text": texto,
                "link_preview_options": {"is_disabled": True},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        requisicao = urllib.request.Request(
            f"{API}/bot{self._token}/sendMessage",
            data=corpo,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with self._abrir(requisicao, timeout=self._timeout) as resposta:
                dados = resposta.read()
        except urllib.error.HTTPError as erro:
            self._falha_http(erro)
        except (http.client.InvalidURL, ValueError) as erro:
            # Pedido que nem chega a ser feito: repetir não adianta. Só o nome do tipo: o texto
            # dessas exceções cita a URL, e com ela o token.
            raise FalhaDeEnvio(
                f"não foi possível montar o pedido à Bot API ({type(erro).__name__})"
            ) from None
        except http.client.HTTPException as erro:
            # RemoteDisconnected, BadStatusLine, IncompleteRead...: a conexão caiu; vale outra
            # tentativa. Também só o nome do tipo.
            raise _Repetir(f"conexão interrompida ({type(erro).__name__})") from None
        except (urllib.error.URLError, OSError) as erro:
            # `from None`: a exceção original pode repetir a URL, e com ela o token.
            raise _Repetir(self._limpo(f"erro de rede ({type(erro).__name__}: {erro})")) from None
        self._conferir(dados)

    def _falha_http(self, erro: urllib.error.HTTPError) -> None:
        codigo = erro.code
        try:
            corpo = json.loads(erro.read().decode("utf-8"))
        except (ValueError, OSError, http.client.HTTPException):
            corpo = {}
        if not isinstance(corpo, dict):
            corpo = {}
        descricao = self._limpo(str(corpo.get("description") or "sem descrição"))
        motivo = f"HTTP {codigo}: {descricao}"
        if codigo == 429:
            parametros = corpo.get("parameters")
            espera = parametros.get("retry_after") if isinstance(parametros, dict) else None
            if not isinstance(espera, int | float) or isinstance(espera, bool):
                raise _Repetir(motivo) from None
            if espera > RETRY_AFTER_MAXIMO:
                raise FalhaDeEnvio(
                    f"a Bot API pediu {espera:g} s de espera (limite {RETRY_AFTER_MAXIMO} s): "
                    f"{motivo}"
                ) from None
            raise _Repetir(motivo, espera) from None
        if codigo >= 500:
            raise _Repetir(motivo) from None
        raise FalhaDeEnvio(f"a Bot API recusou a mensagem ({motivo})") from None

    def _conferir(self, dados: bytes) -> None:
        try:
            corpo = json.loads(dados.decode("utf-8"))
        except ValueError:
            corpo = None
        if not isinstance(corpo, dict) or not isinstance(corpo.get("ok"), bool):
            raise FalhaDeEnvio("resposta da Bot API fora do formato esperado (sem o campo ok)")
        if not corpo["ok"]:
            descricao = self._limpo(str(corpo.get("description") or "sem descrição"))
            raise FalhaDeEnvio(f"a Bot API recusou a mensagem (ok: false): {descricao}")
