import sys

from .cli import main


def _saida_em_utf8() -> None:
    """O resumo tem `·` e acentos: em consoles que não são UTF-8 (Windows) o print falharia."""
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")


_saida_em_utf8()
raise SystemExit(main())
