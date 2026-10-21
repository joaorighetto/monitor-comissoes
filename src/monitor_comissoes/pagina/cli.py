"""Linha de comando da página pública: `python -m monitor_comissoes.pagina gerar`.

Contrato em specs/006-pagina-publica/contracts/pagina-cli.md. Lê os arquivos que a coleta já
gravou e monta o site inteiro na memória; só depois grava. Qualquer falha termina com código 1 e
sem escrever nada, para o workflow não publicar uma página vazia ou parcial.
"""

import argparse
import sys
from pathlib import Path

from ..erros import FalhaDePagina
from ..resumo import dia_mes
from . import entradas, modelo, site


def gerar(args: argparse.Namespace) -> int:
    atual = entradas.ler_atual(args.atual)
    status = entradas.ler_status_do_dia(args.status or args.atual.parent / "status.json")
    entradas.conferir(atual, status, args.atual)
    janela = entradas.ler_janela(args.mudancas or args.atual.parent / "mudancas", atual)

    pagina = modelo.montar_pagina(atual, status, janela)
    arquivos = site.montar(pagina)
    site.gravar(arquivos, args.saida)

    dias = sum(1 for _, documento in janela if documento is not None)
    print(
        f"OK: página gerada com {atual['meta']['total_itens']} itens · "
        f"dados da Câmara de {dia_mes(atual['meta']['dados_camara_em'])} · "
        f"{dias} dias de mudanças · {args.saida}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="monitor_comissoes.pagina", description=__doc__)
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    comando = subcomandos.add_parser("gerar", help="gera o site estático na pasta de saída")
    comando.add_argument("--atual", type=Path, default=Path("data/atual.json"))
    comando.add_argument("--status", type=Path, default=None, help="padrão: ao lado do --atual")
    comando.add_argument("--mudancas", type=Path, default=None, help="padrão: ao lado do --atual")
    comando.add_argument("--saida", type=Path, default=Path("site"))
    args = parser.parse_args(argv)
    try:
        return gerar(args)
    except FalhaDePagina as falha:
        print(f"FALHA [pagina]: {falha}", file=sys.stderr)
        return 1
    except Exception as erro:  # nenhuma falha pode terminar sem aviso
        print(f"FALHA [pagina]: {type(erro).__name__}: {erro}", file=sys.stderr)
        return 1
