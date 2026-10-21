"""Linha de comando da página pública: `python -m monitor_comissoes.pagina gerar`."""

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="monitor_comissoes.pagina", description=__doc__)
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    gerar = subcomandos.add_parser("gerar", help="gera o site estático na pasta de saída")
    gerar.add_argument("--atual", type=Path, default=Path("data/atual.json"))
    gerar.add_argument("--status", type=Path, default=None, help="padrão: ao lado do --atual")
    gerar.add_argument("--mudancas", type=Path, default=None, help="padrão: ao lado do --atual")
    gerar.add_argument("--saida", type=Path, default=Path("site"))
    parser.parse_args(argv)
    return 0
