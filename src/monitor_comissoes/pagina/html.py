"""Renderização do index.html (PAG, contracts/pagina-html.md).

Funções puras: o modelo entra, o texto sai. Todo texto vindo dos dados passa por `esc()`, o único
caminho de texto para o HTML (FR-020). Nada aqui lê o relógio, então a mesma entrada dá o mesmo
documento. Todo caminho próprio é relativo: a página fica em `/monitor-comissoes/`.
"""

from html import escape

from .modelo import ItemDaLista, Numeros, Pagina

TITULO = "Monitor de comissões"


def esc(texto: object) -> str:
    """Texto seguro para o corpo e para atributos entre aspas duplas."""
    return escape(str(texto), quote=True)


def _link(texto: str, href: str) -> str:
    return f'<a href="{esc(href)}">{esc(texto)}</a>'


def _cabecalho(pagina: Pagina) -> str:
    linhas = [
        '<header class="pf-wrap cabecalho">',
        '<h1>Monitor de <span class="pf-mark">comissões</span></h1>',
        f'<p id="atualizacao" class="pf-muted">{esc(pagina.atualizacao)}</p>',
    ]
    if pagina.faixa_erro is not None:
        linhas.append(f'<p id="faixa-erro" class="faixa" role="alert">{esc(pagina.faixa_erro)}</p>')
    atraso = pagina.faixa_atraso
    linhas.append(
        f'<p id="faixa-atraso" class="faixa" role="status" hidden '
        f'data-verificado-em="{esc(atraso.verificado_em)}">{esc(atraso.texto)}</p>'
    )
    linhas.append("</header>")
    return "\n".join(linhas)


def _mudancas_do_numero(numeros: Numeros) -> str:
    tipo, valor = numeros.mudancas
    if tipo == "eventos":
        return str(valor)
    if tipo == "linha_de_base":
        return f"linha de base: {valor}"
    return "sem comparação ainda"


def _secao_numeros(numeros: Numeros) -> str:
    linhas = [("Itens na lista", str(numeros.total_itens))]
    linhas += [(sigla, str(total)) for sigla, total in numeros.por_comissao]
    linhas.append(("Mudanças desde o retrato anterior", _mudancas_do_numero(numeros)))
    definicoes = "\n".join(f"<div><dt>{esc(t)}</dt><dd>{esc(v)}</dd></div>" for t, v in linhas)
    return (
        '<section aria-labelledby="t-numeros">\n'
        '<h2 id="t-numeros" class="pf-h2">Números</h2>\n'
        f'<dl class="numeros">\n{definicoes}\n</dl>\n'
        "</section>"
    )


def _item(item: ItemDaLista) -> str:
    linhas = [
        f'<li class="item" id="item-{item.id}" data-id="{item.id}" '
        f'data-comissao="{esc(item.comissao)}" data-etiquetas="{esc(" ".join(item.motivos))}">',
        f'<h3 class="item-titulo">{_link(item.identificacao, item.link)}</h3>',
        f'<p class="item-ementa">{esc(item.ementa)}</p>',
    ]
    if item.etiquetas:
        rotulos = " ".join(f'<span class="etiqueta">{esc(e)}</span>' for e in item.etiquetas)
        linhas.append(f'<p class="item-etiquetas">{rotulos}</p>')
    dados = [
        ("Comissão", esc(item.comissao)),
        ("Situação", esc(item.situacao)),
        ("Parado há", esc(item.parado)),
        ("Autores", esc(", ".join(item.autores))),
        ("Relator", esc(item.relator)),
    ]
    if item.apensado is not None:
        identificacao, href = item.apensado
        dados.append(("Apensado", f"apensado ao {_link(identificacao, href)}"))
    pares = "\n".join(f"<dt>{t}</dt><dd>{d}</dd>" for t, d in dados)
    linhas.append(f'<dl class="item-dados">\n{pares}\n</dl>')
    linhas += [f'<p class="item-marca">{esc(m)}</p>' for m in item.marcas]
    linhas.append("</li>")
    return "\n".join(linhas)


def _secao_lista(itens: tuple[ItemDaLista, ...]) -> str:
    corpo = "\n".join(_item(i) for i in itens)
    return (
        '<section aria-labelledby="t-lista">\n'
        '<h2 id="t-lista" class="pf-h2">Lista</h2>\n'
        f'<ol id="lista" class="lista">\n{corpo}\n</ol>\n'
        "</section>"
    )


def renderizar(pagina: Pagina) -> str:
    """O `index.html` completo."""
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="pt-BR">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<meta name="color-scheme" content="light dark">',
            f"<title>{esc(TITULO)}</title>",
            '<link rel="stylesheet" href="estilo.css">',
            '<script src="pagina.js" defer></script>',
            "</head>",
            "<body>",
            '<a class="pagina-pular" href="#lista">Ir para a lista</a>',
            _cabecalho(pagina),
            '<main class="pf-wrap">',
            _secao_numeros(pagina.numeros),
            _secao_lista(pagina.itens),
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )
