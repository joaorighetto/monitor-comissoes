"""O comportamento do pagina.js (PAG, R4), executado com Node. Sem Node, os testes são pulados."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = (
    Path(__file__).parent.parent / "src" / "monitor_comissoes" / "pagina" / "estatico" / "pagina.js"
)
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node não está instalado")

HORA = 3600 * 1000
VERIFICADO = "2026-10-20T09:09:05-03:00"


def avaliar(expressao: str):
    """Roda `expressao` com `m` = o módulo do pagina.js e devolve o resultado como JSON."""
    programa = (
        f"const m = require({json.dumps(JS.as_posix())});console.log(JSON.stringify({expressao}));"
    )
    resultado = subprocess.run(
        [NODE, "-e", programa], capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


def atrasada(verificado, deslocamento_ms):
    return avaliar(
        f"(() => {{ const t = Date.parse({json.dumps(verificado)});"
        f" return m.atrasada({json.dumps(verificado)}, t + ({deslocamento_ms})); }})()"
    )


def test_atrasada_so_acima_de_30_horas():
    assert atrasada(VERIFICADO, 30 * HORA) is False
    assert atrasada(VERIFICADO, 30 * HORA + 1000) is True
    assert atrasada(VERIFICADO, 30 * HORA - 60 * 1000) is False


def test_atrasada_com_instante_futuro_e_falso():
    assert atrasada(VERIFICADO, -5 * HORA) is False


@pytest.mark.parametrize("valor", ['""', '"x"', "null", "undefined"])
def test_entrada_invalida_nunca_mostra_a_faixa(valor):
    assert avaliar(f"m.atrasada({valor}, Date.now())") is False


def faixa(verificado):
    return f"{{hidden: true, dataset: {{verificadoEm: {json.dumps(verificado)}}}}}"


def test_verificar_atraso_mostra_a_faixa_so_quando_atrasada():
    codigo = (
        "(() => {"
        f" const f = {faixa(VERIFICADO)};"
        " const d = {getElementById: (id) => id === 'faixa-atraso' ? f : null};"
        f" const t = Date.parse({json.dumps(VERIFICADO)});"
        " const antes = m.verificarAtraso(d, t + 29 * 3600000);"
        " const escondida = f.hidden;"
        " const depois = m.verificarAtraso(d, t + 31 * 3600000);"
        " return [antes, escondida, depois, f.hidden]; })()"
    )

    assert avaliar(codigo) == [False, True, True, False]


def test_verificar_atraso_sem_faixa_na_pagina_nao_quebra():
    assert avaliar("m.verificarAtraso({getElementById: () => null}, Date.now())") is False


def test_o_script_nao_usa_rede_nem_avaliacao_dinamica():
    texto = JS.read_text(encoding="utf-8")

    for proibido in ("eval(", "new Function", "fetch(", "XMLHttpRequest", "sendBeacon", "import("):
        assert proibido not in texto, proibido
