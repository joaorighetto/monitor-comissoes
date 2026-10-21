"""Aviso diário (AVI): monta a mensagem do dia e a envia ao Telegram.

`python -m monitor_comissoes.aviso enviar|texto` (contrato em
specs/005-resumo-telegram/contracts/aviso-cli.md). Só lê os arquivos que a coleta já gravou; nenhum
deles é alterado por este módulo.
"""

import argparse
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import Config, carregar_config
from .entradas import ler_itens_do_atual, ler_mudancas, ler_status_do_dia
from .envio import gravar_registro, ja_enviado, ler_registro, mensagem_do_commit
from .erros import FalhaDeColeta, FalhaDeEnvio
from .estoque import BRASILIA
from .mudancas import nome_do_arquivo
from .resumo import (
    blocos_de_aviso,
    montar_coleta_nao_rodou,
    montar_erro_da_coleta,
    montar_normal,
    tamanho,
)
from .telegram import ClienteTelegram, _sem_segredos

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


def _texto(caminhos: Caminhos, config: Config, hoje: date) -> int:
    """Mostra a mensagem do dia sem enviar, sem credencial e sem gravar nada."""
    try:
        mensagem = montar_mensagem_do_dia(caminhos, config, hoje)
    except FalhaDeEnvio as erro:
        print(f"FALHA [envio]: {erro}", file=sys.stderr)
        return 1
    print(f"TIPO: {mensagem.tipo}")
    print(mensagem.texto)
    return 0


def _mensagem_do_commit(envio: Path, antes: Path | None) -> int:
    try:
        anterior = ler_registro(antes) if antes else {"normal": None, "erro": None}
        print(mensagem_do_commit(anterior, ler_registro(envio)))
    except FalhaDeEnvio as erro:
        print(f"FALHA [envio]: {erro}", file=sys.stderr)
        return 1
    return 0


def main(
    argv: list[str] | None = None,
    relogio: Callable[[], datetime] | None = None,
    ambiente: Mapping[str, str] | None = None,
    criar_cliente: Callable[[str, str], object] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="monitor_comissoes.aviso", description=__doc__)
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    def comum(p: argparse.ArgumentParser) -> None:
        p.add_argument("--config", type=Path, default=Path("config.toml"))
        p.add_argument("--atual", type=Path, default=Path("data/atual.json"))
        p.add_argument("--status", type=Path, default=None, help="padrão: ao lado do --atual")
        p.add_argument("--mudancas", type=Path, default=None, help="padrão: ao lado do --atual")

    texto = subcomandos.add_parser("texto", help="mostra a mensagem do dia, sem enviar")
    comum(texto)
    texto.add_argument(
        "--hoje",
        type=date.fromisoformat,
        default=None,
        help="AAAA-MM-DD: vê a mensagem de um dia salvo (padrão: hoje em Brasília)",
    )
    enviar = subcomandos.add_parser("enviar", help="envia a mensagem do dia ao Telegram")
    comum(enviar)
    enviar.add_argument("--envio", type=Path, default=None, help="padrão: ao lado do --atual")
    mensagem = subcomandos.add_parser(
        "mensagem", help="mensagem de uma linha do commit do registro"
    )
    mensagem.add_argument("--envio", type=Path, default=Path("data/envio.json"))
    mensagem.add_argument(
        "--antes", type=Path, default=None, help="o registro de antes do envio (ausente = vazio)"
    )
    args = parser.parse_args(argv)
    if args.comando == "mensagem":
        return _mensagem_do_commit(args.envio, args.antes)

    relogio = relogio or _agora
    ambiente = os.environ if ambiente is None else ambiente
    criar_cliente = criar_cliente or ClienteTelegram
    caminhos = Caminhos.ao_lado_de(
        args.atual,
        status=args.status,
        mudancas=args.mudancas,
        envio=getattr(args, "envio", None),
    )
    try:
        agora = relogio().astimezone(BRASILIA)
        config = carregar_config(args.config, agora.year)
    except FalhaDeColeta as falha:
        print(f"FALHA [envio]: {falha.motivo}", file=sys.stderr)
        return 1
    if args.comando == "texto":
        return _texto(caminhos, config, args.hoje or agora.date())
    return executar_envio(caminhos, config, relogio, ambiente, criar_cliente)


def _agora() -> datetime:
    return datetime.now(BRASILIA)


def _saida_em_utf8() -> None:
    """A mensagem tem `→`, `•` e `⚠`: em consoles que não são UTF-8 (Windows) o print falharia."""
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    _saida_em_utf8()
    raise SystemExit(main())
