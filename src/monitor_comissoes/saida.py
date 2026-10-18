"""Gravação do data/atual.json: tudo ou nada."""

import json
import os
from pathlib import Path


def montar_documento(itens: list[dict], meta: dict) -> dict:
    return {"meta": meta, "itens": itens}


def serializar(documento: dict) -> str:
    return json.dumps(documento, ensure_ascii=False, indent=2) + "\n"


def gravar_atomico(documento: dict, destino: Path) -> None:
    """Grava `documento` em `destino` sem nunca deixar o arquivo pela metade.

    Escreve num temporário na mesma pasta e troca com `os.replace`, que é atômico no mesmo
    sistema de arquivos. Em qualquer falha o arquivo anterior fica como estava.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = serializar(documento)
    temporario = destino.with_name(destino.name + ".tmp")
    try:
        with open(temporario, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, destino)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
