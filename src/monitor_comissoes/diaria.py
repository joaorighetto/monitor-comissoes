"""Execução diária (AGE): coleta, grava `atual.json` e `status.json`.

`python -m monitor_comissoes.diaria executar|mensagem` (contrato em specs/002-.../contracts/cli.md).
O comando da COL (`python -m monitor_comissoes`) não muda.
"""

import argparse
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .coleta import coletar
from .config import carregar_config
from .erros import INTERNA, FalhaDeColeta
from .estoque import BRASILIA
from .plausibilidade import percentual_texto, verificar
from .status import (
    base_de_comparacao,
    gravar_par,
    gravar_status,
    ler_status,
    mensagem_commit,
    montar_status,
    retrato_do_atual,
)
from .transporte import Transporte, TransporteHttp


def _agora() -> datetime:
    return datetime.now(BRASILIA)


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
        if base is None:
            print(
                "AVISO: sem base para comparar a variação do estoque bruto "
                "(primeiro dia ou status que não descreve o atual.json)",
                file=sys.stderr,
            )
        tentativas = 1
        coletado = coletar(config, transporte, agora)
        variacao_aceita = verificar(
            coletado.estoque_bruto, base, config.limite_variacao_percentual, aceitar_variacao
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
        gravar_par(coletado.documento, atual, documento_status, status)
    except FalhaDeColeta as falha:
        return _registrar_falha(falha.categoria, falha.motivo, atual, status, tentativas, relogio)
    except Exception as erro:  # nenhuma falha pode terminar sem aviso nem saída parcial
        motivo = f"{type(erro).__name__}: {erro}"
        return _registrar_falha(INTERNA, motivo, atual, status, tentativas, relogio)

    if variacao_aceita is not None:
        print(
            "AVISO: variação aceita manualmente "
            f"({variacao_aceita['estoque_anterior']} → {variacao_aceita['estoque_novo']}, "
            f"{percentual_texto(variacao_aceita['variacao_percentual'])})",
            file=sys.stderr,
        )
    dia = coletado.dados_camara_em.astimezone(BRASILIA).strftime("%d/%m/%Y")
    print(
        f"OK: {meta['total_itens']} itens · estoque bruto {coletado.estoque_bruto}"
        f" · tentativas {tentativas} · dados da Câmara de {dia}"
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
    executar.add_argument("--aceitar-variacao", action="store_true")
    mensagem = subcomandos.add_parser("mensagem", help="mensagem de uma linha do commit")
    mensagem.add_argument("--status", type=Path, default=Path("data/status.json"))
    args = parser.parse_args(argv)

    if args.comando == "mensagem":
        return _mensagem(args.status)
    return executar_diaria(
        args.config,
        args.atual,
        args.status,
        args.aceitar_variacao,
        transporte or TransporteHttp(),
        relogio or _agora,
        dormir or time.sleep,
    )


if __name__ == "__main__":
    raise SystemExit(main())
