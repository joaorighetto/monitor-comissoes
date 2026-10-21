"""Gera `tests/fixtures/aviso/<cenário>/` a partir de `aviso_sinteticos.cenarios()`.

Uso (só quando o contrato mudar): `uv run python tests/aviso_gerar_fixtures.py`. Os arquivos são
versionados; `test_aviso_sinteticos.py` confere que eles continuam iguais ao que este script grava.
"""

from pathlib import Path

import aviso_sinteticos as a
from monitor_comissoes.saida import serializar

RAIZ = Path(__file__).parent / "fixtures" / "aviso"


def arquivos() -> dict[Path, str]:
    """Caminho -> texto de cada arquivo dos cenários."""
    saida = {}
    for nome, cenario in a.cenarios().items():
        pasta = RAIZ / nome
        saida[pasta / "atual.json"] = serializar(cenario["atual"])
        saida[pasta / "status.json"] = serializar(cenario["status"])
        if cenario["mudancas"] is not None:
            dia = cenario["status"]["data_referencia"]
            saida[pasta / "mudancas" / f"{dia}.json"] = serializar(cenario["mudancas"])
    return saida


if __name__ == "__main__":
    for caminho, texto in arquivos().items():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8", newline="\n")
        print(caminho.relative_to(RAIZ.parent.parent.parent))
