"""O que a página mostra (PAG, data-model.md): linha de atualização, números, ordem e itens."""

import copy
from datetime import date

import pagina_sinteticos as p
from monitor_comissoes.pagina import entradas, modelo
from pagina_sinteticos import FIXTURES


def real():
    return entradas.ler_atual(FIXTURES / "atual-real.json")


def status_real():
    return entradas.ler_status_do_dia(FIXTURES / "status-ok.json")


def janela_real():
    return entradas.ler_janela(FIXTURES / "mudancas", real())


# ---------- datas e horas em Brasília ----------


def test_dia_e_hora_em_brasilia():
    assert modelo.dia_mes("2026-10-20T04:31:26+00:00") == "20/10"
    assert modelo.dia_mes("2026-10-20T01:30:00+00:00") == "19/10"
    assert modelo.hora_minuto("2026-10-20T09:05:07-03:00") == "09h05"
    assert modelo.hora_minuto("2026-10-20T12:09:00+00:00") == "09h09"


# ---------- linha de atualização ----------


def test_linha_de_atualizacao_do_retrato_real():
    texto = modelo.linha_de_atualizacao(real(), status_real())

    assert texto == (
        "Dados da Câmara de 20/10 (arquivo gerado às 09h05) · verificado em 20/10 às 09h09"
    )


def test_linha_de_atualizacao_no_dia_da_falha_diz_de_quando_sao_os_dados():
    status = entradas.ler_status_do_dia(FIXTURES / "status-falha.json")

    texto = modelo.linha_de_atualizacao(real(), status)

    assert texto == (
        "Dados da Câmara de 20/10 (arquivo gerado às 09h05) · verificado em 21/10 às 09h00"
    )


def test_linha_de_atualizacao_converte_para_brasilia_na_virada_de_dia():
    atual = copy.deepcopy(real())
    atual["meta"]["dados_camara_em"] = "2026-10-20T01:30:00+00:00"

    assert modelo.linha_de_atualizacao(atual, status_real()).startswith("Dados da Câmara de 19/10 ")


# ---------- números ----------


def test_numeros_do_retrato_real_com_o_arquivo_do_dia():
    numeros = modelo.numeros(real(), janela_real())

    assert numeros.total_itens == 105
    assert numeros.por_comissao == (("CE", 96), ("CREDN", 9))
    assert numeros.mudancas == ("eventos", 6)


def test_numeros_na_ordem_das_comissoes_do_meta():
    atual = copy.deepcopy(real())
    atual["meta"]["comissoes"] = ["CREDN", "CE"]

    assert modelo.numeros(atual, janela_real()).por_comissao == (("CREDN", 9), ("CE", 96))


def test_numeros_com_linha_de_base():
    janela = [
        (
            date(2026, 10, 20),
            p.arquivo_de_mudancas(
                "2026-10-20",
                linha_de_base={"motivo": "primeiro retrato", "total_itens": 105},
                dados_camara_em="2026-10-20T04:31:26+00:00",
            ),
        )
    ] + [(date(2026, 10, 19 - i), None) for i in range(6)]

    assert modelo.numeros(real(), janela).mudancas == ("linha_de_base", "primeiro retrato")


def test_numeros_sem_arquivo_do_dia_nunca_viram_zero():
    janela = [(date(2026, 10, 20 - i), None) for i in range(7)]

    numeros = modelo.numeros(real(), janela)

    assert numeros.mudancas == ("indisponivel", None)


def test_numeros_com_arquivo_do_dia_sem_eventos_mostram_zero():
    janela = [
        (
            date(2026, 10, 20),
            p.arquivo_de_mudancas(
                "2026-10-20",
                dia_anterior="2026-10-19",
                dados_camara_em="2026-10-20T04:31:26+00:00",
            ),
        )
    ] + [(date(2026, 10, 19 - i), None) for i in range(6)]

    assert modelo.numeros(real(), janela).mudancas == ("eventos", 0)


# ---------- ordem ----------


def test_ordem_do_mais_parado_para_o_menos_com_desempate_por_id():
    itens = [
        p.item_completo(id=30, parado_ha_dias=10),
        p.item_completo(id=20, parado_ha_dias=500),
        p.item_completo(id=10, parado_ha_dias=10),
        p.item_completo(id=5, parado_ha_dias=500),
    ]

    ordenados = modelo.ordenar(itens)

    assert [i["id"] for i in ordenados] == [5, 20, 10, 30]


def test_ordem_nao_depende_da_ordem_de_entrada():
    itens = [p.item_completo(id=i, parado_ha_dias=i % 3) for i in range(1, 20)]

    assert modelo.ordenar(itens) == modelo.ordenar(list(reversed(itens)))


def test_o_retrato_real_sai_ordenado_por_parado_ha():
    ordenados = modelo.ordenar(real()["itens"])
    parados = [i["parado_ha_dias"] for i in ordenados]

    assert parados == sorted(parados, reverse=True)
    assert len(ordenados) == 105


# ---------- item da lista ----------


def relator(nome="Luiz Lima", partido="NOVO"):
    return {
        "id": 204455,
        "nome": nome,
        "partido_hoje": partido,
        "designado_em": "2025-04-09T00:00:00",
        "fonte": "https://www.camara.leg.br/propostas-legislativas/1",
    }


def test_item_com_todos_os_campos():
    item = p.item_completo(
        id=2267727,
        numero=5594,
        ano=2020,
        etiquetas=("autoria NOVO", "autor hoje no NOVO"),
        relator=relator(),
        apensado_a={
            "id": 2190633,
            "identificacao": "PL 155/2019",
            "link": "https://www.camara.leg.br/propostas-legislativas/2190633",
        },
        parado_ha_dias=1302,
    )
    item["autores"] = [
        {"nome": "Paula Belmonte", "id_deputado": 2, "partido_na_data": "CIDADANIA", "ordem": 2},
        {"nome": "Adriana Ventura", "id_deputado": 1, "partido_na_data": "NOVO", "ordem": 1},
    ]

    v = modelo.item_da_lista(item)

    assert v.id == 2267727
    assert v.identificacao == "PL 5594/2020"
    assert v.link == "https://www.camara.leg.br/propostas-legislativas/2267727"
    assert v.ementa == "Ementa do PL 5594/2020."
    assert v.comissao == "CE" and v.situacao == "Aguardando Parecer"
    assert v.autores == ("Adriana Ventura (NOVO)", "Paula Belmonte (CIDADANIA)")
    assert v.etiquetas == ("autoria NOVO", "autor hoje no NOVO")
    assert v.motivos == ("autoria", "autor-hoje")
    assert v.parado == "nesta situação há 1302 dias"
    assert v.relator == "Luiz Lima (NOVO)"
    assert v.apensado == ("PL 155/2019", "https://www.camara.leg.br/propostas-legislativas/2190633")
    assert v.marcas == ()


def test_parado_ha_no_singular_e_no_plural():
    um = modelo.item_da_lista(p.item_completo(parado_ha_dias=1))
    zero = modelo.item_da_lista(p.item_completo(parado_ha_dias=0))
    dois = modelo.item_da_lista(p.item_completo(parado_ha_dias=2))

    assert um.parado == "nesta situação há 1 dia"
    assert zero.parado == "nesta situação há 0 dias"
    assert dois.parado == "nesta situação há 2 dias"


def test_sem_relator_atual():
    v = modelo.item_da_lista(p.item_completo(relator=None))

    assert v.relator == "sem relator atual"
    assert v.marcas == ()


def test_relator_sem_partido_mostra_so_o_nome():
    v = modelo.item_da_lista(p.item_completo(relator=relator(partido=None)))

    assert v.relator == "Luiz Lima"


def test_autor_que_nao_e_deputado_aparece_sem_parenteses():
    item = p.item_completo()
    item["autores"] = [
        {"nome": "Comissão Especial", "id_deputado": None, "partido_na_data": "", "ordem": 1}
    ]

    assert modelo.item_da_lista(item).autores == ("Comissão Especial",)


def test_marcas_de_principal_nao_localizada_e_relator_indeterminado():
    v = modelo.item_da_lista(
        p.item_completo(
            principal_nao_localizada=True,
            relator_indeterminado={"motivo": "designação sem relator identificado"},
            etiquetas=(),
        )
    )

    assert v.marcas == ("principal não localizada", "relator indeterminado")
    assert v.etiquetas == () and v.motivos == ()
    assert v.apensado is None


def test_item_sem_etiqueta_nao_tem_motivo():
    assert modelo.item_da_lista(p.item_completo(etiquetas=())).motivos == ()


def test_as_tres_etiquetas_mapeiam_para_os_identificadores_curtos():
    v = modelo.item_da_lista(
        p.item_completo(etiquetas=("autoria NOVO", "autor hoje no NOVO", "relatoria NOVO"))
    )

    assert v.motivos == ("autoria", "autor-hoje", "relatoria")


def test_todos_os_itens_reais_viram_item_da_lista():
    itens = [modelo.item_da_lista(i) for i in real()["itens"]]

    assert len(itens) == 105
    assert all(i.link.startswith("https://www.camara.leg.br/") for i in itens)


# ---------- faixas ----------


def test_sem_falha_nao_ha_faixa_de_erro():
    pagina = modelo.montar_pagina(real(), status_real(), janela_real())

    assert pagina.faixa_erro is None


def test_faixa_de_erro_diz_o_dia_que_falhou_o_motivo_e_os_dados_bons():
    status = entradas.ler_status_do_dia(FIXTURES / "status-falha.json")

    pagina = modelo.montar_pagina(real(), status, janela_real())

    assert pagina.faixa_erro == (
        "A atualização de 21/10 falhou (a Câmara não atualizou os arquivos). Dados de 20/10."
    )


def test_faixa_de_erro_usa_o_dia_de_brasilia_dos_dados_bons():
    status = copy.deepcopy(entradas.ler_status_do_dia(FIXTURES / "status-falha.json"))
    status["ultimo_retrato_bom"]["dados_camara_em"] = "2026-10-20T01:30:00+00:00"
    atual = copy.deepcopy(real())
    atual["meta"]["dados_camara_em"] = "2026-10-20T01:30:00+00:00"

    assert modelo.montar_pagina(atual, status, janela_real()).faixa_erro.endswith("Dados de 19/10.")


def test_faixa_de_atraso_sempre_existe_com_o_instante_e_o_texto():
    pagina = modelo.montar_pagina(real(), status_real(), janela_real())

    assert pagina.faixa_atraso.verificado_em == "2026-10-20T09:09:05-03:00"
    assert pagina.faixa_atraso.texto == (
        "Dados atrasados: a última verificação foi em 20/10 às 09h09, há mais de 30 horas. "
        "A atualização diária pode ter parado."
    )


def test_faixa_de_atraso_tambem_existe_quando_a_ultima_execucao_falhou():
    status = entradas.ler_status_do_dia(FIXTURES / "status-falha.json")

    pagina = modelo.montar_pagina(real(), status, janela_real())

    assert pagina.faixa_atraso.verificado_em == "2026-10-21T09:00:00-03:00"
    assert "21/10 às 09h00" in pagina.faixa_atraso.texto
