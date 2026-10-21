"""O index.html (PAG, contracts/pagina-html.md): estrutura, textos, escape e sem JS."""

import re

import pagina_sinteticos as p
from monitor_comissoes.pagina import entradas, html, modelo
from pagina_dom import parse
from pagina_sinteticos import FIXTURES

OFICIAL = "https://www.camara.leg.br/"


def montar(atual, status=None, janela=None):
    status = status or entradas.ler_status_do_dia(FIXTURES / "status-ok.json")
    if janela is None:
        janela = entradas.ler_janela(FIXTURES / "mudancas", atual)
    return html.renderizar(modelo.montar_pagina(atual, status, janela))


def pagina_real():
    return montar(entradas.ler_atual(FIXTURES / "atual-real.json"))


def pagina_com(*itens, **meta):
    """A página de um retrato sintético (CE e CREDN), sem arquivos de mudanças."""
    atual = p.retrato_com(list(itens), **meta)
    status = p.status_ok()
    return montar(atual, status, entradas.ler_janela(FIXTURES / "nao-existe", atual))


def item_de(documento, **filtros):
    return documento.um(tag="li", classe="item", **filtros)


# ---------- regras gerais ----------


def test_documento_html5_em_portugues_com_cabecalho_basico():
    texto = pagina_real()
    doc = parse(texto)

    assert texto.startswith("<!doctype html>")
    assert doc.um(tag="html").attrs["lang"] == "pt-BR"
    assert doc.um(tag="meta", charset="utf-8")
    assert doc.um(tag="meta", name="viewport").attrs["content"] == (
        "width=device-width, initial-scale=1"
    )
    assert doc.um(tag="meta", name="color-scheme").attrs["content"] == "light dark"
    assert doc.um(tag="title").texto == "Monitor de comissões"


def test_um_h1_com_marca_texto():
    doc = parse(pagina_real())

    h1 = doc.um(tag="h1")

    assert h1.texto == "Monitor de comissões"
    assert h1.um(classe="pf-mark").texto == "comissões"


def test_um_css_e_um_unico_script_com_defer():
    doc = parse(pagina_real())

    assert doc.um(tag="link", rel="stylesheet").attrs["href"] == "estilo.css"
    scripts = doc.achar(tag="script")
    assert len(scripts) == 1
    assert scripts[0].attrs["src"] == "pagina.js" and scripts[0].tem_atributo("defer")
    assert scripts[0].filhos == []


def test_sem_estilo_embutido_nem_atributo_de_evento():
    doc = parse(pagina_real())

    assert doc.achar(tag="style") == []
    for no in doc.percorrer():
        assert not [a for a in no.attrs if a.startswith("on")], (no.tag, no.attrs)
        assert "style" not in no.attrs, (no.tag, "style embutido")


def test_nenhum_caminho_proprio_comeca_por_barra_e_nenhuma_url_externa_alem_da_camara():
    doc = parse(pagina_real())

    for no in doc.percorrer():
        for nome in ("href", "src"):
            valor = no.attrs.get(nome)
            if valor is None:
                continue
            assert not valor.startswith("/"), (no.tag, valor)
            if "://" in valor:
                assert valor.startswith(OFICIAL), (no.tag, valor)


def test_todo_href_e_oficial_ancora_ou_arquivo_da_propria_pagina():
    doc = parse(pagina_real())
    permitidos = {"atual.json", "itens.csv"}

    for no in doc.achar(tag="a"):
        href = no.attrs["href"]
        assert href.startswith(OFICIAL) or href.startswith("#") or href in permitidos, href


def test_o_documento_tem_link_para_pular_para_a_lista():
    doc = parse(pagina_real())

    assert doc.um(tag="a", classe="pagina-pular").attrs["href"] == "#lista"
    assert doc.um(tag="ol", id="lista")


# ---------- linha de atualização e números ----------


def test_linha_de_atualizacao():
    doc = parse(pagina_real())

    assert doc.um(tag="p", id="atualizacao").texto == (
        "Dados da Câmara de 20/10 (arquivo gerado às 09h05) · verificado em 20/10 às 09h09"
    )


def test_numeros_em_lista_de_definicoes():
    doc = parse(pagina_real())
    secao = doc.um(tag="section", aria_labelledby="t-numeros")

    pares = {
        dt.texto: dd.texto
        for dt, dd in zip(secao.achar(tag="dt"), secao.achar(tag="dd"), strict=True)
    }

    assert secao.um(tag="h2", id="t-numeros").texto == "Números"
    assert pares == {
        "Itens na lista": "105",
        "CE": "96",
        "CREDN": "9",
        "Mudanças desde o retrato anterior": "6",
    }


def test_mudancas_do_numero_com_linha_de_base_e_sem_arquivo():
    atual = entradas.ler_atual(FIXTURES / "atual-real.json")
    base = p.arquivo_de_mudancas(
        "2026-10-20",
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 105},
        dados_camara_em="2026-10-20T04:31:26+00:00",
    )
    janela = [(modelo_dia, None) for modelo_dia, _ in entradas.ler_janela(FIXTURES / "x", atual)]
    com_base = [(janela[0][0], base)] + janela[1:]

    def valor(janela):
        doc = parse(montar(atual, janela=janela))
        dts = doc.um(tag="section", aria_labelledby="t-numeros").achar(tag="dt")
        dds = doc.um(tag="section", aria_labelledby="t-numeros").achar(tag="dd")
        return dict(zip((d.texto for d in dts), (d.texto for d in dds), strict=True))[
            "Mudanças desde o retrato anterior"
        ]

    assert valor(com_base) == "linha de base: primeiro retrato"
    assert valor(janela) == "sem comparação ainda"


def test_a_ordem_das_secoes():
    doc = parse(pagina_real())
    ids = [h.attrs["id"] for h in doc.achar(tag="h2")]

    assert ids.index("t-numeros") < ids.index("t-lista")
    assert doc.um(tag="header").um(tag="h1")
    assert doc.um(tag="header").um(tag="p", id="atualizacao")


# ---------- lista ----------


def test_a_lista_real_tem_os_105_itens_na_ordem_de_parado_ha():
    doc = parse(pagina_real())
    itens = doc.um(tag="ol", id="lista").achar(tag="li", classe="item")
    real = entradas.ler_atual(FIXTURES / "atual-real.json")
    esperados = [f"item-{i['id']}" for i in modelo.ordenar(real["itens"])]

    assert len(itens) == real["meta"]["total_itens"] == 105
    assert [i.attrs["id"] for i in itens] == esperados


def test_cada_item_do_retrato_real_tem_link_oficial_e_identificacao():
    doc = parse(pagina_real())
    real = {i["id"]: i for i in entradas.ler_atual(FIXTURES / "atual-real.json")["itens"]}

    for item in doc.achar(tag="li", classe="item"):
        titulo = item.um(tag="h3", classe="item-titulo").um(tag="a")
        origem = real[int(item.attrs["data-id"])]
        assert titulo.attrs["href"] == origem["link"]
        assert titulo.texto == origem["identificacao"]


def dados_do_item(item):
    dl = item.um(tag="dl", classe="item-dados")
    return {dt.texto: dd for dt, dd in zip(dl.achar(tag="dt"), dl.achar(tag="dd"), strict=True)}


def test_markup_de_um_item_completo():
    apensado = {
        "id": 2190633,
        "identificacao": "PL 155/2019",
        "link": "https://www.camara.leg.br/propostas-legislativas/2190633",
    }
    relator = {
        "id": 178929,
        "nome": "Diego Garcia",
        "partido_hoje": "UNIÃO",
        "designado_em": "2023-03-15T00:00:00",
        "fonte": "https://www.camara.leg.br/propostas-legislativas/2267727",
    }
    item = p.item_completo(
        id=2267727,
        numero=5594,
        ano=2020,
        etiquetas=("autoria NOVO", "autor hoje no NOVO"),
        relator=relator,
        apensado_a=apensado,
        parado_ha_dias=1302,
    )
    item["autores"] = [
        {"nome": "Adriana Ventura", "id_deputado": 1, "partido_na_data": "NOVO", "ordem": 1},
        {"nome": "Paula Belmonte", "id_deputado": 2, "partido_na_data": "CIDADANIA", "ordem": 2},
    ]
    doc = parse(pagina_com(item))

    li = item_de(doc, id="item-2267727")
    dados = dados_do_item(li)

    assert li.attrs["data-id"] == "2267727"
    assert li.um(tag="p", classe="item-ementa").texto == "Ementa do PL 5594/2020."
    assert [e.texto for e in li.achar(tag="span", classe="etiqueta")] == [
        "autoria NOVO",
        "autor hoje no NOVO",
    ]
    assert dados["Comissão"].texto == "CE"
    assert dados["Situação"].texto == "Aguardando Parecer"
    assert dados["Parado há"].texto == "nesta situação há 1302 dias"
    assert dados["Autores"].texto == "Adriana Ventura (NOVO), Paula Belmonte (CIDADANIA)"
    assert dados["Relator"].texto == "Diego Garcia (UNIÃO)"
    ap = dados["Apensado"].um(tag="a")
    assert dados["Apensado"].texto == "apensado ao PL 155/2019"
    assert ap.attrs["href"] == apensado["link"]
    assert li.achar(classe="item-marca") == []


def test_item_nao_apensado_nao_tem_linha_de_apensado_e_sem_etiqueta_nao_tem_etiquetas():
    doc = parse(pagina_com(p.item_completo(id=7, etiquetas=(), relator=None)))
    li = item_de(doc, id="item-7")

    assert "Apensado" not in dados_do_item(li)
    assert li.achar(tag="p", classe="item-etiquetas") == []
    assert dados_do_item(li)["Relator"].texto == "sem relator atual"


def test_dia_no_singular():
    doc = parse(pagina_com(p.item_completo(id=1, parado_ha_dias=1)))

    assert dados_do_item(item_de(doc, id="item-1"))["Parado há"].texto == (
        "nesta situação há 1 dia"
    )


def test_marcas_de_principal_nao_localizada_e_relator_indeterminado():
    item = p.item_completo(
        id=9,
        principal_nao_localizada=True,
        relator_indeterminado={"motivo": "designação sem relator identificado"},
    )
    doc = parse(pagina_com(item))

    marcas = [m.texto for m in item_de(doc, id="item-9").achar(tag="p", classe="item-marca")]

    assert marcas == ["principal não localizada", "relator indeterminado"]


def test_a_lista_so_traz_o_que_o_retrato_traz():
    doc = parse(pagina_com(p.item_completo(id=1), p.item_completo(id=2, comissao="CREDN")))

    assert len(doc.achar(tag="li", classe="item")) == 2


# ---------- escape (FR-020) ----------


def test_texto_da_camara_com_html_sai_como_texto():
    perigoso = "<script>alert(1)</script> & \"aspas\" 'simples' <b>x</b>"
    item = p.item_completo(id=3, situacao=perigoso)
    item["ementa"] = perigoso
    item["autores"] = [
        {"nome": perigoso, "id_deputado": 1, "partido_na_data": "<i>PL</i>", "ordem": 1}
    ]
    item["relator"] = {
        "id": 1,
        "nome": perigoso,
        "partido_hoje": "<u>X</u>",
        "designado_em": "2025-01-01T00:00:00",
        "fonte": "https://www.camara.leg.br/propostas-legislativas/3",
    }
    texto = pagina_com(item)
    doc = parse(texto)
    li = item_de(doc, id="item-3")

    assert doc.achar(tag="script")[0].attrs["src"] == "pagina.js"
    assert len(doc.achar(tag="script")) == 1
    assert doc.achar(tag="b") == [] and doc.achar(tag="i") == [] and doc.achar(tag="u") == []
    assert li.um(tag="p", classe="item-ementa").texto == perigoso
    assert dados_do_item(li)["Situação"].texto == perigoso
    assert "<script>alert" not in texto and "<b>x" not in texto


def test_texto_dentro_de_atributo_nao_escapa_do_atributo():
    item = p.item_completo(id=4, comissao='CE" onmouseover="alert(1)')
    doc = parse(pagina_com(item))
    li = item_de(doc, id="item-4")

    assert li.attrs["data-comissao"] == 'CE" onmouseover="alert(1)'
    assert not [a for a in li.attrs if a.startswith("on")]


# ---------- determinismo ----------


def test_duas_geracoes_da_mesma_entrada_dao_o_mesmo_texto():
    assert pagina_real() == pagina_real()


def test_a_pagina_nao_traz_hora_de_geracao():
    # o instante da verificação vem do status.json (é dado, não hora de geração)
    texto = re.sub(r'data-verificado-em="[^"]*"', "", pagina_real())

    assert not re.search(r"gerada em|gerado agora|\d{2}:\d{2}:\d{2}", texto)


# ---------- faixas (US2) ----------


def pagina_com_status(nome):
    atual = entradas.ler_atual(FIXTURES / "atual-real.json")
    return parse(montar(atual, entradas.ler_status_do_dia(FIXTURES / nome)))


def test_sem_falha_nao_ha_faixa_de_erro():
    assert parse(pagina_real()).achar(id="faixa-erro") == []


def test_faixa_de_erro_em_texto_com_role_alert_e_lista_do_ultimo_retrato_bom():
    doc = pagina_com_status("status-falha.json")

    faixa = doc.um(tag="p", id="faixa-erro")

    assert faixa.attrs["role"] == "alert"
    assert "faixa" in faixa.classes
    assert not faixa.tem_atributo("hidden")
    assert faixa.texto == (
        "A atualização de 21/10 falhou (a Câmara não atualizou os arquivos). Dados de 20/10."
    )
    assert len(doc.achar(tag="li", classe="item")) == 105
    assert doc.um(tag="p", id="atualizacao").texto.endswith("verificado em 21/10 às 09h00")


def test_faixa_de_atraso_existe_escondida_com_o_instante_e_role_status():
    doc = parse(pagina_real())

    faixa = doc.um(tag="p", id="faixa-atraso")

    assert faixa.tem_atributo("hidden")
    assert faixa.attrs["role"] == "status"
    assert faixa.attrs["data-verificado-em"] == "2026-10-20T09:09:05-03:00"
    assert faixa.texto == (
        "Dados atrasados: a última verificação foi em 20/10 às 09h09, há mais de 30 horas. "
        "A atualização diária pode ter parado."
    )


def test_as_faixas_ficam_no_cabecalho_depois_da_linha_de_atualizacao():
    doc = parse(montar_falha())
    cabecalho = doc.um(tag="header")
    ids = [p_.attrs.get("id") for p_ in cabecalho.achar(tag="p")]

    assert ids == ["atualizacao", "faixa-erro", "faixa-atraso"]


def montar_falha():
    atual = entradas.ler_atual(FIXTURES / "atual-real.json")
    return montar(atual, entradas.ler_status_do_dia(FIXTURES / "status-falha.json"))


def test_motivo_da_falha_com_html_sai_como_texto():
    atual = entradas.ler_atual(FIXTURES / "atual-real.json")
    status = dict(entradas.ler_status_do_dia(FIXTURES / "status-falha.json"))
    status["falha"] = {"categoria": "interna", "motivo": "<script>x</script> & falhou"}

    doc = parse(montar(atual, status))

    assert doc.um(tag="p", id="faixa-erro").texto == (
        "A atualização de 21/10 falhou (<script>x</script> & falhou). Dados de 20/10."
    )
    assert len(doc.achar(tag="script")) == 1
