"""Renderização do index.html (PAG, contracts/pagina-html.md).

Funções puras: o modelo entra, o texto sai. Todo texto vindo dos dados passa por `esc()`, o único
caminho de texto para o HTML (FR-020). Nada aqui lê o relógio, então a mesma entrada dá o mesmo
documento. Todo caminho próprio é relativo: a página fica em `/monitor-comissoes/`.
"""

from html import escape

from .modelo import (
    LIMITES,
    DiaDeMudancas,
    EventoDaPagina,
    GrupoDeChips,
    ItemDaLista,
    Numeros,
    Pagina,
    sem_mudancas_registradas,
)

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


def _tramitacoes(evento: EventoDaPagina) -> str:
    if not evento.tramitacoes:
        return ""
    itens = "\n".join(
        f"<li>{esc(t.quando)} · {esc(t.orgao)} · {esc(t.descricao)}</li>"
        for t in evento.tramitacoes
    )
    return (
        f'<details class="tramitacoes"><summary>Tramitações ({len(evento.tramitacoes)})</summary>\n'
        f"<ul>\n{itens}\n</ul>\n</details>"
    )


def _evento(evento: EventoDaPagina) -> str:
    linhas = [
        f'<li class="evento" data-tipo="{esc(evento.tipo)}">',
        f'<p class="evento-titulo"><span class="evento-tipo">{esc(evento.rotulo)}</span> '
        f"{_link(evento.identificacao, evento.link)} "
        f'<span class="evento-comissao pf-muted">{esc(evento.comissao)}</span></p>',
        f'<p class="evento-detalhe">{esc(evento.detalhe)}</p>',
    ]
    if evento.apensado is not None:
        identificacao, href = evento.apensado
        linhas.append(f'<p class="evento-apensado">apensado a {_link(identificacao, href)}</p>')
    detalhe = _tramitacoes(evento)
    if detalhe:
        linhas.append(detalhe)
    linhas.append("</li>")
    return "\n".join(linhas)


def _lista_de_eventos(eventos: tuple[EventoDaPagina, ...]) -> str:
    corpo = "\n".join(_evento(e) for e in eventos)
    return f'<ul class="eventos">\n{corpo}\n</ul>'


def _dia_de_mudancas(dia: DiaDeMudancas) -> str:
    rotulo = dia.data.strftime("%d/%m")
    linhas = [f'<article class="dia" id="dia-{dia.data.isoformat()}">', f"<h3>{rotulo}</h3>"]
    if dia.estado == "sem_arquivo":
        linhas.append("<p>Sem arquivo de mudanças neste dia.</p>")
    elif dia.estado == "coberto":
        linhas.append(
            "<p>Sem arquivo próprio: as mudanças deste dia estão no arquivo de "
            f"{esc(dia.coberto_por)}.</p>"
        )
    elif dia.estado == "sem_mudancas":
        linhas.append("<p>Sem mudanças.</p>")
    elif dia.estado == "linha_de_base":
        motivo, total = dia.linha_de_base
        linhas.append(f"<p>Linha de base criada com {total} itens ({esc(motivo)}).</p>")
    if dia.intervalo is not None:
        inicio, fim = dia.intervalo
        linhas.append(f'<p class="pf-muted">Cobre de {inicio} a {fim}.</p>')
    if dia.abertos:
        linhas.append(_lista_de_eventos(dia.abertos))
    if dia.recolhidos:
        n = len(dia.recolhidos)
        titulo = f"e mais {n} evento de {rotulo}" if n == 1 else f"e mais {n} eventos de {rotulo}"
        linhas.append(
            f'<details class="mais"><summary>{titulo}</summary>\n'
            f"{_lista_de_eventos(dia.recolhidos)}\n</details>"
        )
    linhas.append("</article>")
    return "\n".join(linhas)


def _secao_mudancas(dias: tuple[DiaDeMudancas, ...]) -> str:
    if sem_mudancas_registradas(dias):
        corpo = "<p>Ainda não há mudanças registradas.</p>"
    else:
        corpo = "\n".join(_dia_de_mudancas(d) for d in dias)
    return (
        '<section aria-labelledby="t-mudancas">\n'
        '<h2 id="t-mudancas" class="pf-h2">Mudou nos últimos 7 dias</h2>\n'
        f"{corpo}\n</section>"
    )


def _grupo_de_chips(grupo: GrupoDeChips) -> str:
    botoes = "\n".join(
        f'<button class="pf-chip" type="button" aria-pressed="{str(c.ativo).lower()}" '
        f'data-grupo="{grupo.nome}" data-valor="{esc(c.valor)}">{esc(c.rotulo)}</button>'
        for c in grupo.chips
    )
    return f'<div class="pf-chips" role="group" aria-label="{esc(grupo.rotulo)}">\n{botoes}\n</div>'


def _filtros(grupos: tuple[GrupoDeChips, GrupoDeChips]) -> str:
    """Nascem escondidos: sem JavaScript os chips não funcionariam, então nem aparecem."""
    corpo = "\n".join(_grupo_de_chips(g) for g in grupos)
    return (
        f'<div id="filtros" class="filtros" hidden>\n{corpo}\n'
        '<p id="filtro-status" class="pf-muted" aria-live="polite"></p>\n</div>'
    )


def _secao_lista(pagina: Pagina) -> str:
    corpo = "\n".join(_item(i) for i in pagina.itens)
    return (
        '<section aria-labelledby="t-lista">\n'
        '<h2 id="t-lista" class="pf-h2">Lista</h2>\n'
        f"{_filtros(pagina.filtros)}\n"
        f'<ol id="lista" class="lista">\n{corpo}\n</ol>\n'
        "</section>"
    )


def _secao_limites() -> str:
    itens = "\n".join(f"<li>{esc(limite)}</li>" for limite in LIMITES)
    return (
        '<section aria-labelledby="t-limites">\n'
        '<h2 id="t-limites" class="pf-h2">Limites</h2>\n'
        f'<ul class="limites">\n{itens}\n</ul>\n</section>'
    )


def _secao_baixar(pagina: Pagina) -> str:
    return (
        '<section aria-labelledby="t-baixar">\n'
        '<h2 id="t-baixar" class="pf-h2">Baixar dados</h2>\n'
        '<p class="acoes">'
        '<a class="pf-btn pf-btn--link" href="atual.json" download>Baixar atual.json</a> '
        '<a class="pf-btn pf-btn--link" href="itens.csv" download>Baixar itens.csv</a></p>\n'
        '<p class="fonte pf-muted">'
        f"Fonte: Câmara dos Deputados · dados de {esc(pagina.dados_de)}</p>\n"
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
            _secao_mudancas(pagina.mudancas),
            _secao_lista(pagina),
            _secao_limites(),
            _secao_baixar(pagina),
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )
