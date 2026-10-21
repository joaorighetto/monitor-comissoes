"""Formatação pura da mensagem do dia (AVI): dicionários entram, texto sai.

Sem relógio, sem rede e sem disco. Formato: specs/005-resumo-telegram/contracts/mensagem.md.
"""

from datetime import datetime

from .config import Config
from .estoque import BRASILIA

LIMITE = 4096  # unidades UTF-16 de uma mensagem do Telegram
LIMITE_AVISO = 1200  # unidades que a lista de itens de cada aviso pode ocupar


def tamanho(texto: str) -> int:
    """Tamanho em unidades UTF-16: a medida conservadora do limite da Bot API (research R3)."""
    return len(texto.encode("utf-16-le")) // 2


def dia_mes(iso: str) -> str:
    """`DD/MM` de uma data e hora ISO com fuso, no dia de Brasília."""
    return datetime.fromisoformat(iso).astimezone(BRASILIA).strftime("%d/%m")


def destino_da_pagina(config: Config, dia: str) -> tuple[str, str]:
    """Texto e endereço do "veja a página" (FR-011): a página, ou o arquivo do dia sem ela."""
    if config.pagina_url:
        return "veja a página", config.pagina_url
    return (
        "veja o arquivo do dia",
        f"https://github.com/{config.repositorio}/blob/main/data/mudancas/{dia}.json",
    )
