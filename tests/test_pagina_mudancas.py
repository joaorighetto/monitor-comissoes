"""A seção "Mudou nos últimos 7 dias" (PAG, contracts/pagina-html.md, seção 4)."""

from datetime import date

import aviso_sinteticos as a
import pagina_sinteticos as p
from monitor_comissoes.pagina import entradas, html, modelo
from pagina_dom import parse
from pagina_sinteticos import FIXTURES


def pagina(pasta="mudancas", janela=None):
    atual = entradas.ler_atual(FIXTURES / "atual-real.json")
    status = entradas.ler_status_do_dia(FIXTURES / "status-ok.json")
    if janela is None:
        janela = entradas.ler_janela(FIXTURES / pasta, atual)
    return parse(html.renderizar(modelo.montar_pagina(atual, status, janela)))


def secao(doc):
    return doc.um(tag="section", aria_labelledby="t-mudancas")


def dia_de(doc, dia):
    return doc.um(tag="article", id=f"dia-{dia}")


def janela_com(arquivo_do_dia_20, *outros):
    """Uma janela de 7 dias com `arquivo_do_dia_20` e, nos dias dados, os outros arquivos."""
    por_dia = {date(2026, 10, 20): arquivo_do_dia_20, **dict(outros)}
    return [(date(2026, 10, 20 - i), por_dia.get(date(2026, 10, 20 - i))) for i in range(7)]


def test_titulo_e_um_artigo_por_dia_do_mais_recente_ao_mais_antigo():
    doc = pagina()

    assert secao(doc).um(tag="h2", id="t-mudancas").texto == "Mudou nos últimos 7 dias"
    dias = secao(doc).achar(tag="article", classe="dia")
    assert [d.attrs["id"] for d in dias] == [
        f"dia-2026-10-{n}" for n in (20, 19, 18, 17, 16, 15, 14)
    ]
    assert [d.um(tag="h3").texto for d in dias] == [
        "20/10",
        "19/10",
        "18/10",
        "17/10",
        "16/10",
        "15/10",
        "14/10",
    ]


def test_a_secao_fica_entre_os_numeros_e_a_lista():
    doc = pagina()
    ids = [h.attrs["id"] for h in doc.achar(tag="h2")]

    assert ids.index("t-numeros") < ids.index("t-mudancas") < ids.index("t-lista")


def test_textos_de_dia_sem_mudancas_linha_de_base_sem_arquivo_e_intervalo():
    doc = pagina()

    assert dia_de(doc, "2026-10-19").um(tag="p").texto == "Sem mudanças."
    assert dia_de(doc, "2026-10-18").um(tag="p").texto == (
        "Linha de base criada com 105 itens (primeiro retrato)."
    )
    assert dia_de(doc, "2026-10-17").um(tag="p").texto == "Sem arquivo de mudanças neste dia."
    assert "Cobre de 14/10 a 16/10." in [
        p_.texto for p_ in dia_de(doc, "2026-10-16").achar(tag="p")
    ]
    assert dia_de(doc, "2026-10-19").achar(classe="evento") == []


def test_sem_nenhum_arquivo_so_a_frase_de_que_nao_ha_mudancas_registradas():
    doc = pagina("nao-existe")

    assert secao(doc).achar(tag="article") == []
    assert [p_.texto for p_ in secao(doc).achar(tag="p")] == ["Ainda não há mudanças registradas."]


def test_os_seis_tipos_de_evento_do_dia_20_com_link_oficial_e_comissao():
    eventos = dia_de(pagina(), "2026-10-20").achar(tag="li", classe="evento")

    assert [e.attrs["data-tipo"] for e in eventos] == [
        "entrou",
        "saiu",
        "situacao",
        "relator",
        "parecer",
        "etiquetas",
    ]
    for evento in eventos:
        link = evento.um(tag="a")
        assert link.attrs["href"].startswith("https://www.camara.leg.br/propostas-legislativas/")
        assert evento.um(tag="span", classe="evento-comissao").texto in {"CE", "CREDN"}


def test_texto_de_cada_tipo():
    eventos = dia_de(pagina(), "2026-10-20").achar(tag="li", classe="evento")
    por_tipo = {e.attrs["data-tipo"]: e for e in eventos}

    assert por_tipo["entrou"].um(tag="span", classe="evento-tipo").texto == "Entrou"
    assert por_tipo["entrou"].um(tag="a").texto == "PL 1831/2022"
    assert por_tipo["entrou"].um(tag="p", classe="evento-detalhe").texto == (
        "chegou à comissão · etiquetas: autoria NOVO"
    )
    assert por_tipo["saiu"].um(tag="p", classe="evento-detalhe").texto == (
        "foi para outro órgão · destino: CFT (Aguardando Parecer)"
    )
    assert por_tipo["situacao"].um(tag="p", classe="evento-detalhe").texto == (
        "Aguardando Parecer → Pronta para Pauta"
    )
    assert por_tipo["relator"].um(tag="p", classe="evento-detalhe").texto == (
        "designado Luiz Lima (NOVO)"
    )
    assert por_tipo["etiquetas"].um(tag="p", classe="evento-detalhe").texto == (
        "ganhou: relatoria NOVO"
    )
    assert por_tipo["etiquetas"].um(tag="span", classe="evento-comissao").texto == "CREDN"


def test_parecer_so_informa_que_houve_e_nao_reproduz_o_conteudo():
    parecer = dia_de(pagina(), "2026-10-20").um(tag="li", classe="evento", data_tipo="parecer")

    assert parecer.um(tag="p", classe="evento-detalhe").texto == "parecer do relator"
    # a descrição da tramitação só aparece dentro do bloco recolhido de tramitações
    fora = [n.texto for n in parecer.percorrer() if n.tag == "p" and "evento-detalhe" in n.classes]
    assert fora == ["parecer do relator"]


def test_tramitacoes_vao_num_bloco_recolhido_com_data_orgao_e_descricao():
    parecer = dia_de(pagina(), "2026-10-20").um(tag="li", classe="evento", data_tipo="parecer")

    bloco = parecer.um(tag="details", classe="tramitacoes")

    assert bloco.um(tag="summary").texto == "Tramitações (2)"
    assert [li.texto for li in bloco.achar(tag="li")] == [
        "19/10 10:15 · CE · Designado Relator, Dep. Luiz Lima",
        "20/10 08:00 · CE · Parecer do Relator, Dep. Luiz Lima",
    ]
    entrou = dia_de(pagina(), "2026-10-20").um(tag="li", classe="evento", data_tipo="entrou")
    assert entrou.achar(tag="details") == []


def test_saiu_apensado_mostra_o_link_da_principal():
    saiu = dia_de(pagina(), "2026-10-16").um(tag="li", classe="evento", data_tipo="saiu")

    apensado = saiu.um(tag="p", classe="evento-apensado")

    assert apensado.texto == "apensado a PL 155/2019"
    assert apensado.um(tag="a").attrs["href"] == (
        "https://www.camara.leg.br/propostas-legislativas/2190633"
    )


def test_teto_por_dia_abre_20_e_recolhe_o_resto_com_todos_os_eventos_na_pagina():
    doc = pagina("mudancas-teto")
    dia = dia_de(doc, "2026-10-20")

    mais = dia.um(tag="details", classe="mais")
    recolhidos = mais.achar(tag="li", classe="evento")
    abertos = [e for e in dia.achar(tag="li", classe="evento") if e not in recolhidos]

    assert len(abertos) == 20 and len(recolhidos) == 5
    assert mais.um(tag="summary").texto == "e mais 5 eventos de 20/10"
    assert len(dia.achar(tag="li", classe="evento")) == 25
    ids = {e.um(tag="a").attrs["href"] for e in dia.achar(tag="li", classe="evento")}
    assert len(ids) == 25


def test_um_evento_no_excedente_usa_o_singular():
    doc = pagina(janela=janela_com(p.muitos_eventos(21)))

    mais = dia_de(doc, "2026-10-20").um(tag="details", classe="mais")

    assert mais.um(tag="summary").texto == "e mais 1 evento de 20/10"


def test_ate_20_eventos_nao_tem_bloco_recolhido():
    doc = pagina(janela=janela_com(p.muitos_eventos(20)))

    assert dia_de(doc, "2026-10-20").achar(tag="details", classe="mais") == []


def test_as_ressalvas_do_arquivo_nao_aparecem_na_pagina():
    arquivo = a.mudancas([a.evento("entrou")], [a.ressalva("ce_b")])
    assert arquivo["ressalvas"], "a fixture deveria ter uma ressalva"

    texto = html.renderizar(
        modelo.montar_pagina(
            entradas.ler_atual(FIXTURES / "atual-real.json"),
            entradas.ler_status_do_dia(FIXTURES / "status-ok.json"),
            janela_com(arquivo),
        )
    )

    assert "relator indeterminado hoje" not in texto


def test_texto_da_camara_nos_eventos_sai_escapado():
    perigoso = '<script>alert(1)</script> & "x"'
    evento = p.evento(
        "entrou",
        motivo={"codigo": "chegou_a_comissao", "texto": perigoso},
        etiquetas=["<b>autoria NOVO</b>"],
    )
    doc = pagina(
        janela=janela_com(p.arquivo_de_mudancas("2026-10-20", [evento], dia_anterior="2026-10-19"))
    )

    detalhe = dia_de(doc, "2026-10-20").um(tag="p", classe="evento-detalhe")

    assert detalhe.texto == f"{perigoso} · etiquetas: <b>autoria NOVO</b>"
    assert len(doc.achar(tag="script")) == 1 and doc.achar(tag="b") == []


def test_dia_do_meio_de_um_arquivo_de_varios_dias_diz_onde_estao_as_mudancas():
    doc = pagina()

    assert dia_de(doc, "2026-10-15").um(tag="p").texto == (
        "Sem arquivo próprio: as mudanças deste dia estão no arquivo de 16/10."
    )
    assert dia_de(doc, "2026-10-14").um(tag="p").texto == "Sem arquivo de mudanças neste dia."
    assert dia_de(doc, "2026-10-17").um(tag="p").texto == "Sem arquivo de mudanças neste dia."
