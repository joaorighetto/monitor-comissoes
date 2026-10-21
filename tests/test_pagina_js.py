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


# ---------- filtros (US3) ----------

ITENS = [
    {"id": 1, "comissao": "CE", "etiquetas": ["autoria", "relatoria"]},
    {"id": 2, "comissao": "CE", "etiquetas": ["relatoria"]},
    {"id": 3, "comissao": "CREDN", "etiquetas": ["autor-hoje"]},
    {"id": 4, "comissao": "CREDN", "etiquetas": ["relatoria"]},
    {"id": 5, "comissao": "CE", "etiquetas": []},
]


def filtrar(comissao, motivo):
    return avaliar(f"m.filtrar({json.dumps(ITENS)}, {json.dumps(comissao)}, {json.dumps(motivo)})")


def test_filtrar_sem_escolha_devolve_todos_na_ordem():
    assert filtrar("", "") == [1, 2, 3, 4, 5]


def test_filtrar_por_comissao():
    assert filtrar("CE", "") == [1, 2, 5]
    assert filtrar("CREDN", "") == [3, 4]


def test_filtrar_por_motivo_um_item_com_duas_etiquetas_aparece_sob_as_duas():
    assert filtrar("", "autoria") == [1]
    assert filtrar("", "relatoria") == [1, 2, 4]
    assert filtrar("", "autor-hoje") == [3]


def test_filtrar_combina_comissao_e_motivo_por_e():
    assert filtrar("CE", "relatoria") == [1, 2]
    assert filtrar("CREDN", "relatoria") == [4]
    assert filtrar("CREDN", "autoria") == []


def test_item_sem_etiqueta_so_aparece_em_todos():
    for motivo in ("autoria", "autor-hoje", "relatoria"):
        assert 5 not in filtrar("", motivo)
    assert 5 in filtrar("", "")


CENARIO_DE_DOM = """
function el(dados) {
  const base = {hidden: false, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }};
  return Object.assign(base, dados);
}
const itens = __ITENS__.map((i) => el({dataset: {id: String(i.id), comissao: i.comissao,
  etiquetas: i.etiquetas.join(" ")}}));
const chips = [
  el({dataset: {grupo: "comissao", valor: ""}}), el({dataset: {grupo: "comissao", valor: "CE"}}),
  el({dataset: {grupo: "motivo", valor: ""}}), el({dataset: {grupo: "motivo", valor: "relatoria"}}),
];
const status = el({textContent: ""});
const filtros = el({hidden: true, ouvintes: {}, addEventListener(t, f) { this.ouvintes[t] = f; }});
const doc = {
  querySelectorAll: (s) => (s === ".item" ? itens : s === ".pf-chip" ? chips : []),
  getElementById: (id) => ({"filtro-status": status, filtros: filtros}[id] || null),
};
""".replace("__ITENS__", json.dumps(ITENS))


def com_dom(corpo):
    return avaliar(f"(() => {{ {CENARIO_DE_DOM} {corpo} }})()")


def test_aplicar_esconde_so_o_que_nao_atende_e_anuncia_o_resultado():
    resultado = com_dom(
        "m.aplicar(doc, 'CE', 'relatoria');return [itens.map((i) => i.hidden), status.textContent];"
    )

    assert resultado == [[False, False, True, True, True], "Mostrando 2 de 5 itens."]


def test_aplicar_marca_o_chip_escolhido_em_cada_grupo():
    resultado = com_dom(
        "m.aplicar(doc, 'CE', 'relatoria'); return chips.map((c) => c.attrs['aria-pressed']);"
    )

    assert resultado == ["false", "true", "false", "true"]


def test_aplicar_com_todos_mostra_tudo():
    resultado = com_dom(
        "m.aplicar(doc, 'CE', ''); m.aplicar(doc, '', '');"
        "return [itens.map((i) => i.hidden), status.textContent];"
    )

    assert resultado == [[False] * 5, "Mostrando 5 de 5 itens."]


def test_aplicar_conta_os_visiveis_inclusive_quando_e_um_ou_nenhum():
    unico = com_dom("m.aplicar(doc, 'CREDN', 'relatoria'); return status.textContent;")
    nenhum = com_dom("m.aplicar(doc, 'CREDN', 'autoria'); return status.textContent;")

    assert unico == "Mostrando 1 de 5 itens."
    assert nenhum == "Mostrando 0 de 5 itens."


def test_com_uma_unica_proposicao_o_texto_fica_no_singular():
    resultado = avaliar(
        "(() => { const un = [{dataset: {id: '9', comissao: 'CE', etiquetas: ''}, hidden: false}];"
        " const st = {textContent: ''};"
        " const d = {querySelectorAll: (s) => (s === '.item' ? un : []),"
        " getElementById: (id) => (id === 'filtro-status' ? st : null)};"
        " m.aplicar(d, '', ''); return st.textContent; })()"
    )

    assert resultado == "Mostrando 1 de 1 item."


def test_iniciar_libera_os_filtros_sem_esconder_nenhum_item():
    resultado = com_dom(
        "m.iniciar(doc); return [filtros.hidden, itens.map((i) => i.hidden), status.textContent];"
    )

    assert resultado == [False, [False] * 5, "Mostrando 5 de 5 itens."]


def test_clique_no_chip_filtra_pelo_grupo_dele_e_mantem_o_outro():
    resultado = com_dom(
        "m.iniciar(doc);"
        "const clicar = (chip) => filtros.ouvintes.click({target: {closest: () => chip}});"
        "clicar(chips[1]); const so_ce = itens.map((i) => i.hidden);"
        "clicar(chips[3]); const ce_e_relatoria = itens.map((i) => i.hidden);"
        "clicar(chips[0]); const so_relatoria = itens.map((i) => i.hidden);"
        "return [so_ce, ce_e_relatoria, so_relatoria, status.textContent];"
    )

    assert resultado == [
        [False, False, True, True, False],
        [False, False, True, True, True],
        [False, False, True, False, True],
        "Mostrando 3 de 5 itens.",
    ]


def test_clique_fora_de_um_chip_nao_faz_nada():
    resultado = com_dom(
        "m.iniciar(doc); filtros.ouvintes.click({target: {closest: () => null}});"
        "return itens.map((i) => i.hidden);"
    )

    assert resultado == [False] * 5
