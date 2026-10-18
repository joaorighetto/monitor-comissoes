"""Execução diária (AGE): coleta, grava `atual.json` e `status.json`.

`python -m monitor_comissoes.diaria executar|mensagem` (contrato em specs/002-.../contracts/cli.md).
O comando da COL (`python -m monitor_comissoes`) não muda.
"""

import argparse
import os
import signal
import sys
import time
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from .coleta import coletar
from .config import carregar_config
from .erros import INTERNA, REPETIVEIS, FalhaDeColeta
from .estoque import BRASILIA
from .mudancas import nome_do_arquivo, resumo
from .plausibilidade import percentual_texto, verificar
from .retratos import preparar
from .saida import serializar
from .status import (
    base_de_comparacao,
    gravar_status,
    gravar_todos,
    ler_status,
    mensagem_commit,
    montar_status,
    retrato_do_atual,
)
from .transporte import Transporte, TransporteHttp


def _agora() -> datetime:
    return datetime.now(BRASILIA)


class InterrupcaoPorSinal(Exception):
    """O processo recebeu SIGTERM (por exemplo, o `timeout` do workflow estourou)."""


def _ao_receber_sigterm(numero, quadro) -> None:
    raise InterrupcaoPorSinal("recebeu SIGTERM (provavelmente o tempo limite da execução)")


def _aviso(texto: str) -> None:
    """Aviso que não derruba a execução: vai ao log e, no Actions, vira anotação na execução."""
    print(f"AVISO: {texto}", file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning title=Coleta diária::{texto}")


def _registrar_falha(
    categoria: str,
    motivo: str,
    atual: Path,
    status: Path,
    tentativas: int,
    relogio: Callable[[], datetime],
) -> int:
    """Anuncia a falha e grava só o `status.json`: o `atual.json` nunca é tocado aqui."""
    print(f"FALHA [{categoria}]: {motivo}", file=sys.stderr)
    try:
        retrato = retrato_do_atual(atual)
        if retrato is not None:
            retrato = {**retrato, "estoque_bruto": base_de_comparacao(atual, status)}
        documento = montar_status(
            resultado="falha",
            verificado_em=relogio(),
            tentativas=tentativas,
            falha={"categoria": categoria, "motivo": motivo},
            variacao_aceita=None,
            retrato=retrato,
        )
        gravar_status(documento, status)
    except Exception as erro:
        print(
            f"FALHA [{INTERNA}]: não foi possível gravar {status} ({type(erro).__name__}: {erro})",
            file=sys.stderr,
        )
    return 1


def executar_diaria(
    caminho_config: Path,
    atual: Path,
    status: Path,
    anterior: Path,
    mudancas: Path,
    aceitar_variacao: bool,
    transporte: Transporte,
    relogio: Callable[[], datetime],
    dormir: Callable[[float], None],
) -> int:
    """Uma execução diária. Devolve o código de saída: 0 em sucesso, 1 em qualquer falha."""
    tentativas = 0
    try:
        agora = relogio()
        config = carregar_config(caminho_config, agora.astimezone(BRASILIA).year)
        base = base_de_comparacao(atual, status)
        # Há retrato anterior a comparar? Sem ele é o primeiro dia de todos; com ele, a falta de
        # base é falha (decisão do mantenedor, 18/10/2026), liberável com a confirmação manual.
        exige_base = retrato_do_atual(atual) is not None
        if base is None and not exige_base:
            _aviso(
                "sem base para comparar a variação do estoque bruto "
                "(primeiro dia: ainda não há atual.json válido)"
            )
        coletado = None
        for tentativa in range(1, config.tentativas + 1):
            tentativas = tentativa
            agora = relogio()  # cada tentativa lê o relógio de novo
            try:
                # O retrato anterior é decidido por data (MUD, R5); um arquivo ilegível falha aqui.
                comparacao = preparar(atual, anterior, agora.astimezone(BRASILIA).date())
                coletado = coletar(config, transporte, agora, comparacao)
                break
            except FalhaDeColeta as falha:
                if falha.categoria not in REPETIVEIS or tentativa == config.tentativas:
                    raise
                print(
                    f"TENTATIVA {tentativa} de {config.tentativas} falhou "
                    f"[{falha.categoria}]: {falha.motivo}; "
                    f"nova tentativa em {config.espera_minutos} minutos",
                    file=sys.stderr,
                )
                dormir(config.espera_minutos * 60)
        variacao_aceita = verificar(
            coletado.estoque_bruto,
            base,
            config.limite_variacao_percentual,
            aceitar_variacao,
            exige_base=exige_base,
        )
        meta = coletado.documento["meta"]
        retrato = {
            "gerado_em": meta["gerado_em"],
            "dados_camara_em": meta["dados_camara_em"],
            "total_itens": meta["total_itens"],
            "estoque_bruto": coletado.estoque_bruto,
        }
        documento_status = montar_status(
            resultado="ok",
            verificado_em=relogio(),
            tentativas=tentativas,
            falha=None,
            variacao_aceita=variacao_aceita,
            retrato=retrato,
        )
        # Ordem das trocas: a cópia do retrato anterior primeiro. Se o processo morresse entre
        # duas trocas, o `atual.json` ainda de ontem rotacionaria de novo, sem perder nada; o
        # contrário (atual novo e cópia velha) quebraria a comparação do dia.
        escritas = []
        if comparacao.copia_anterior is not None:
            escritas.append((comparacao.copia_anterior, anterior))
        escritas += [
            (
                serializar(coletado.mudancas),
                Path(mudancas)
                / nome_do_arquivo(date.fromisoformat(coletado.mudancas["meta"]["data"])),
            ),
            (serializar(coletado.documento), atual),
            (serializar(documento_status), status),
        ]
        gravar_todos(escritas)
    except FalhaDeColeta as falha:
        return _registrar_falha(falha.categoria, falha.motivo, atual, status, tentativas, relogio)
    except Exception as erro:  # nenhuma falha pode terminar sem aviso nem saída parcial
        motivo = f"{type(erro).__name__}: {erro}"
        return _registrar_falha(INTERNA, motivo, atual, status, tentativas, relogio)

    if variacao_aceita is not None and variacao_aceita["estoque_anterior"] is None:
        _aviso(
            "aceito manualmente sem base de comparação "
            f"(estoque bruto {variacao_aceita['estoque_novo']})"
        )
    elif variacao_aceita is not None:
        _aviso(
            "variação aceita manualmente "
            f"({variacao_aceita['estoque_anterior']} → {variacao_aceita['estoque_novo']}, "
            f"{percentual_texto(variacao_aceita['variacao_percentual'])})"
        )
    dia = coletado.dados_camara_em.astimezone(BRASILIA).strftime("%d/%m/%Y")
    print(
        f"OK: {meta['total_itens']} itens · estoque bruto {coletado.estoque_bruto}"
        f" · tentativas {tentativas} · dados da Câmara de {dia}"
        f" · mudanças: {resumo(coletado.mudancas)}"
    )
    return 0


def _mensagem(caminho_status: Path) -> int:
    try:
        documento = ler_status(caminho_status)
        if documento is None:
            raise ValueError(f"status inválido: {caminho_status} não existe")
        print(mensagem_commit(documento))
    except ValueError as erro:
        print(f"FALHA [interna]: {erro}", file=sys.stderr)
        return 1
    return 0


def main(
    argv: list[str] | None = None,
    transporte: Transporte | None = None,
    relogio: Callable[[], datetime] | None = None,
    dormir: Callable[[float], None] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="monitor_comissoes.diaria", description=__doc__)
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    executar = subcomandos.add_parser("executar", help="coleta e grava atual.json e status.json")
    executar.add_argument("--config", type=Path, default=Path("config.toml"))
    executar.add_argument("--atual", type=Path, default=Path("data/atual.json"))
    executar.add_argument("--status", type=Path, default=Path("data/status.json"))
    executar.add_argument(
        "--anterior", type=Path, default=None, help="padrão: anterior.json ao lado do --atual"
    )
    executar.add_argument(
        "--mudancas", type=Path, default=None, help="padrão: a pasta mudancas ao lado do --atual"
    )
    executar.add_argument("--aceitar-variacao", action="store_true")
    mensagem = subcomandos.add_parser("mensagem", help="mensagem de uma linha do commit")
    mensagem.add_argument("--status", type=Path, default=Path("data/status.json"))
    args = parser.parse_args(argv)

    if args.comando == "mensagem":
        return _mensagem(args.status)
    # SIGTERM vira exceção: o `timeout` do workflow pode estourar no meio da espera ou do
    # download, e mesmo assim o status de falha precisa ser gravado antes de sair.
    try:
        anterior = signal.signal(signal.SIGTERM, _ao_receber_sigterm)
    except ValueError:  # fora da thread principal não é possível instalar o tratador
        anterior = None
    try:
        return executar_diaria(
            args.config,
            args.atual,
            args.status,
            args.anterior or args.atual.parent / "anterior.json",
            args.mudancas or args.atual.parent / "mudancas",
            args.aceitar_variacao,
            transporte or TransporteHttp(),
            relogio or _agora,
            dormir or time.sleep,
        )
    finally:
        if anterior is not None:
            signal.signal(signal.SIGTERM, anterior)


if __name__ == "__main__":
    raise SystemExit(main())
