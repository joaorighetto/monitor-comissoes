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
from .estoque import BRASILIA
from .status import gravar_par, ler_status, mensagem_commit, montar_status
from .transporte import Transporte, TransporteHttp


def _agora() -> datetime:
    return datetime.now(BRASILIA)


def executar_diaria(
    caminho_config: Path,
    atual: Path,
    status: Path,
    aceitar_variacao: bool,
    transporte: Transporte,
    relogio: Callable[[], datetime],
    dormir: Callable[[float], None],
) -> int:
    """Uma execução diária. Devolve o código de saída: 0 em sucesso."""
    agora = relogio()
    config = carregar_config(caminho_config, agora.astimezone(BRASILIA).year)
    coletado = coletar(config, transporte, agora)
    retrato = {
        "gerado_em": coletado.documento["meta"]["gerado_em"],
        "dados_camara_em": coletado.documento["meta"]["dados_camara_em"],
        "total_itens": coletado.documento["meta"]["total_itens"],
        "estoque_bruto": coletado.estoque_bruto,
    }
    documento_status = montar_status(
        resultado="ok",
        verificado_em=relogio(),
        tentativas=1,
        falha=None,
        variacao_aceita=None,
        retrato=retrato,
    )
    gravar_par(coletado.documento, atual, documento_status, status)
    meta = coletado.documento["meta"]
    dia = coletado.dados_camara_em.astimezone(BRASILIA).strftime("%d/%m/%Y")
    print(
        f"OK: {meta['total_itens']} itens · estoque bruto {coletado.estoque_bruto}"
        f" · tentativas 1 · dados da Câmara de {dia}"
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
