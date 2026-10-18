"""Linha de comando: `python -m monitor_comissoes` (contrato em specs/.../contracts/cli.md)."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .coleta import executar
from .config import carregar_config
from .erros import FalhaDeColeta
from .estoque import BRASILIA
from .transporte import Transporte, TransporteHttp


def main(
    argv: list[str] | None = None,
    transporte: Transporte | None = None,
    agora: datetime | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="monitor_comissoes", description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--saida", type=Path, default=Path("data/atual.json"))
    args = parser.parse_args(argv)

    agora = agora or datetime.now(BRASILIA)
    transporte = transporte or TransporteHttp()
    try:
        config = carregar_config(args.config, agora.astimezone(BRASILIA).year)
        resultado = executar(config, transporte, agora, args.saida)
    except FalhaDeColeta as falha:
        print(f"FALHA [{falha.categoria}]: {falha.motivo}", file=sys.stderr)
        return 1

    por_comissao = ", ".join(f"{c}: {n}" for c, n in resultado.por_comissao.items())
    dia = resultado.dados_camara_em.astimezone(BRASILIA).strftime("%d/%m/%Y")
    print(f"OK: {resultado.total_itens} itens ({por_comissao}) · dados da Câmara de {dia}")
    return 0
