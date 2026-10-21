"""Aviso diário (AVI): monta a mensagem do dia e a envia ao Telegram.

`python -m monitor_comissoes.aviso enviar|texto` (contrato em
specs/005-resumo-telegram/contracts/aviso-cli.md). Só lê os arquivos que a coleta já gravou; nenhum
deles é alterado por este módulo.
"""

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import Config
from .entradas import ler_itens_do_atual, ler_mudancas, ler_status_do_dia
from .envio import gravar_registro, ja_enviado, ler_registro
from .erros import FalhaDeEnvio
from .estoque import BRASILIA
from .mudancas import nome_do_arquivo
from .resumo import (
    blocos_de_aviso,
    montar_coleta_nao_rodou,
    montar_erro_da_coleta,
    montar_normal,
    tamanho,
)
from .telegram import _sem_segredos

VARIAVEL_TOKEN = "TELEGRAM_BOT_TOKEN"
VARIAVEL_CHAT = "TELEGRAM_CHAT_ID"


@dataclass(frozen=True)
class Caminhos:
    atual: Path
    status: Path
    mudancas: Path  # a pasta; o arquivo do dia é AAAA-MM-DD.json dentro dela
    envio: Path

    @classmethod
    def ao_lado_de(
        cls,
        atual: Path,
        *,
        status: Path | None = None,
        mudancas: Path | None = None,
        envio: Path | None = None,
    ) -> "Caminhos":
        """Os padrões ficam ao lado do `atual.json`, como na MUD (contracts/aviso-cli.md)."""
        atual = Path(atual)
        return cls(
            atual=atual,
            status=Path(status) if status else atual.parent / "status.json",
            mudancas=Path(mudancas) if mudancas else atual.parent / "mudancas",
            envio=Path(envio) if envio else atual.parent / "envio.json",
        )


@dataclass(frozen=True)
class Mensagem:
    tipo: str  # "normal" ou "erro": a chave do registro de envio
    dia: str  # AAAA-MM-DD, o dia da execução em Brasília
    texto: str


def montar_mensagem_do_dia(caminhos: Caminhos, config: Config, hoje: date) -> Mensagem:
    """Decide o tipo e monta o texto (research R6). Entrada incoerente levanta `FalhaDeEnvio`."""
    dia = hoje.isoformat()
    status = ler_status_do_dia(caminhos.status)
    if status is None or status["data_referencia"] != dia:
        return Mensagem("erro", dia, montar_coleta_nao_rodou(status, hoje))
    if status["resultado"] == "falha":
        return Mensagem("erro", dia, montar_erro_da_coleta(status, hoje))
    arquivo = caminhos.mudancas / nome_do_arquivo(date.fromisoformat(status["data_referencia"]))
    mudancas = ler_mudancas(arquivo, status)
    sem_principal = [i for i in ler_itens_do_atual(caminhos.atual) if i["principal_nao_localizada"]]
    avisos = blocos_de_aviso(mudancas["ressalvas"], sem_principal, config)
    return Mensagem("normal", dia, montar_normal(mudancas, status, config, avisos))


def _exigir(ambiente: Mapping[str, str], nome: str) -> str:
    valor = ambiente.get(nome, "")
    if not valor.strip():
        raise FalhaDeEnvio(f"variável {nome} ausente")
    return valor


def executar_envio(
    caminhos: Caminhos,
    config: Config,
    relogio: Callable[[], datetime],
    ambiente: Mapping[str, str],
    criar_cliente: Callable[[str, str], object],
) -> int:
    """Um envio. Devolve o código de saída: 0 em sucesso, 1 em qualquer falha."""
    segredos = [ambiente.get(VARIAVEL_TOKEN, ""), ambiente.get(VARIAVEL_CHAT, "")]

    def limpo(texto: str) -> str:
        return _sem_segredos(texto, segredos[0], segredos[1])

    try:
        hoje = relogio().astimezone(BRASILIA).date()
        mensagem = montar_mensagem_do_dia(caminhos, config, hoje)
        tipo = "normal" if mensagem.tipo == "normal" else "de erro"
        dia = hoje.strftime("%d/%m")
        if ja_enviado(ler_registro(caminhos.envio), mensagem.tipo, mensagem.dia):
            print(f"JÁ ENVIADO: mensagem {tipo} de {dia}")
            return 0
        token = _exigir(ambiente, VARIAVEL_TOKEN)
        chat_id = _exigir(ambiente, VARIAVEL_CHAT)
        criar_cliente(token, chat_id).enviar(mensagem.texto)
        try:
            gravar_registro(caminhos.envio, mensagem.tipo, mensagem.dia)
        except Exception as erro:
            raise FalhaDeEnvio(
                f"a mensagem {tipo} de {dia} FOI enviada ao grupo, mas o registro de envio não "
                f"pôde ser gravado ({type(erro).__name__}: {erro}); não reenvie sem conferir"
            ) from None
    except FalhaDeEnvio as erro:
        print(f"FALHA [envio]: {limpo(str(erro))}", file=sys.stderr)
        return 1
    except Exception as erro:  # nenhuma falha pode terminar sem aviso
        print(f"FALHA [envio]: {type(erro).__name__}: {limpo(str(erro))}", file=sys.stderr)
        return 1
    print(f"OK: mensagem {tipo} de {dia} enviada ({tamanho(mensagem.texto)} caracteres)")
    return 0
