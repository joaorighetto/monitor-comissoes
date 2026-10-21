"""Registro de envio `data/envio.json`: o último dia de cada tipo de mensagem aceita pelo Telegram.

Contrato em specs/005-resumo-telegram/contracts/envio-json.md. Existe para a reexecução no mesmo
dia não repetir a mensagem (constituição, V).
"""

import json
from datetime import date
from pathlib import Path

from .erros import FalhaDeEnvio
from .saida import gravar_atomico

VERSAO_FORMATO = 1
TIPOS = ("normal", "erro")


def _invalido(caminho: Path, motivo: str) -> FalhaDeEnvio:
    return FalhaDeEnvio(f"registro de envio inválido ({caminho}): {motivo}")


def _dia_valido(valor) -> bool:
    if valor is None:
        return True
    if not isinstance(valor, str):
        return False
    try:
        return date.fromisoformat(valor).isoformat() == valor
    except ValueError:
        return False


def ler_registro(caminho: Path) -> dict[str, str | None]:
    """`{"normal": dia|None, "erro": dia|None}`. Arquivo ausente = nada enviado ainda."""
    caminho = Path(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"normal": None, "erro": None}
    except (OSError, UnicodeDecodeError) as erro:
        raise _invalido(caminho, f"não foi possível ler ({erro})") from erro
    try:
        documento = json.loads(texto)
    except ValueError as erro:
        raise _invalido(caminho, f"não é um JSON válido ({erro})") from erro
    if not isinstance(documento, dict):
        raise _invalido(caminho, "o arquivo deve conter um objeto")
    if list(documento) != ["versao_formato", "ultimo_envio"]:
        raise _invalido(caminho, "campos esperados ['versao_formato', 'ultimo_envio']")
    versao = documento["versao_formato"]
    if isinstance(versao, bool) or versao != VERSAO_FORMATO:
        raise _invalido(caminho, f"versao_formato {versao!r} não suportada")
    ultimo = documento["ultimo_envio"]
    if not isinstance(ultimo, dict) or list(ultimo) != list(TIPOS):
        raise _invalido(caminho, f"ultimo_envio deve ter os campos {list(TIPOS)}")
    for tipo in TIPOS:
        if not _dia_valido(ultimo[tipo]):
            raise _invalido(caminho, f"ultimo_envio.{tipo} deve ser null ou AAAA-MM-DD")
    return {tipo: ultimo[tipo] for tipo in TIPOS}


def ja_enviado(registro: dict[str, str | None], tipo: str, dia: str) -> bool:
    return registro[tipo] == dia


def gravar_registro(caminho: Path, tipo: str, dia: str) -> None:
    """Grava o `dia` no `tipo` e preserva o outro tipo. Atômico; registro inválido não é tocado."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo desconhecido: {tipo!r}")
    registro = ler_registro(caminho)
    registro[tipo] = dia
    gravar_atomico(
        {
            "versao_formato": VERSAO_FORMATO,
            "ultimo_envio": {t: registro[t] for t in TIPOS},
        },
        Path(caminho),
    )


def mensagem_do_commit(antes: dict[str, str | None], depois: dict[str, str | None]) -> str:
    """Mensagem de uma linha do commit do registro: `aviso: DIA · tipo` do tipo que mudou."""
    mudou = [tipo for tipo in TIPOS if depois[tipo] != antes[tipo]]
    if len(mudou) != 1:
        raise FalhaDeEnvio(
            f"o registro de envio deveria ter mudado um único tipo, mudou {len(mudou)}"
        )
    return f"aviso: {depois[mudou[0]]} · {mudou[0]}"
