"""Alterações de pauta (research R6): cinco tipos, só contra a última checagem, uma vez só."""

import copy
from datetime import date

import pytest

from monitor_comissoes.erros import FONTE_INDISPONIVEL, FalhaDeColeta
from monitor_comissoes.pauta.checagem import comparar, recuperar_sumidas
from pauta_sinteticos import detalhe_evento, evento, reuniao_gravada

AGORA = "2026-10-24T15:17:02-03:00"
JANELA = (date(2026, 10, 17), date(2026, 10, 31))
CAMPOS = ["detectada_em", "tipo", "reuniao", "item", "de", "para", "detalhe"]


def nunca_buscar(id_evento):
    raise AssertionError(f"não devia buscar o evento {id_evento}")


def buscar(eventos):
    """`buscar_evento` falso: id → corpo `dados` do detalhe, ou None (404)."""
    return lambda id_evento: eventos[id_evento]


def detalhe(id_evento, inicio, **campos):
    return detalhe_evento(id_evento, inicio, **campos)["dados"]


def _comparar(anteriores, atuais, buscar_evento=nunca_buscar):
    return comparar(anteriores, atuais, buscar_evento, AGORA, JANELA)


def tipos(alteracoes):
    return [(a["tipo"], a["item"]["chave"] if a["item"] else None) for a in alteracoes]


# --- reunião que continua na janela ------------------------------------------------------------


def test_mesma_pauta_nao_da_alteracao():
    reuniao = reuniao_gravada(1, chaves=("p:10", "p:11"))

    assert _comparar([reuniao], [reuniao]) == []


def test_so_a_ordem_mudou_nao_da_alteracao():
    antes = reuniao_gravada(1, chaves=("p:10", "p:11", "t:Item"))
    depois = reuniao_gravada(1, chaves=("t:Item", "p:11", "p:10"))

    assert _comparar([antes], [depois]) == []


def test_item_entrou_e_item_saiu_com_os_campos_do_contrato():
    antes = reuniao_gravada(1, chaves=("p:10", "p:11"))
    depois = reuniao_gravada(1, chaves=("p:11", "p:12", "t:Item sem proposição"))

    alteracoes = _comparar([antes], [depois])

    assert tipos(alteracoes) == [
        ("item_entrou", "p:12"),
        ("item_entrou", "t:Item sem proposição"),
        ("item_saiu", "p:10"),
    ]
    entrou = alteracoes[0]
    assert list(entrou) == CAMPOS
    assert entrou == {
        "detectada_em": AGORA,
        "tipo": "item_entrou",
        "reuniao": {
            "id": 1,
            "comissao": "CE",
            "inicio": "2026-10-28T10:00",
            "link": "https://www.camara.leg.br/evento-legislativo/1",
        },
        "item": {
            "chave": "p:12",
            "titulo": "PL 12/2020",
            "proposicao": {
                "id": 12,
                "identificacao": "PL 12/2020",
                "link": "https://www.camara.leg.br/propostas-legislativas/12",
            },
        },
        "de": None,
        "para": None,
        "detalhe": None,
    }
    assert alteracoes[1]["item"]["proposicao"] is None
    assert alteracoes[2]["item"]["chave"] == "p:10"


def test_proposicao_repetida_conta_duas_vezes():
    antes = reuniao_gravada(1, chaves=("p:10",))
    depois = reuniao_gravada(1, chaves=("p:10", "p:10"))

    assert tipos(_comparar([antes], [depois])) == [("item_entrou", "p:10")]
    assert tipos(_comparar([depois], [antes])) == [("item_saiu", "p:10")]


def test_data_ou_hora_mudou_com_de_e_para_e_o_inicio_anterior():
    antes = reuniao_gravada(1, "2026-10-28T10:00", chaves=("p:10",))
    depois = reuniao_gravada(1, "2026-10-29T14:30", chaves=("p:10", "p:11"))

    alteracoes = _comparar([antes], [depois])

    assert tipos(alteracoes) == [("item_entrou", "p:11"), ("data_hora", None)]
    hora = alteracoes[1]
    assert (hora["de"], hora["para"]) == ("2026-10-28T10:00", "2026-10-29T14:30")
    assert all(a["reuniao"]["inicio"] == "2026-10-28T10:00" for a in alteracoes)


def test_cancelada_da_so_cancelada():
    antes = reuniao_gravada(1, chaves=("p:10",))
    depois = reuniao_gravada(1, "2026-10-29T10:00", "cancelada", chaves=("p:11",))

    alteracoes = _comparar([antes], [depois])

    assert tipos(alteracoes) == [("cancelada", None)]
    assert alteracoes[0]["de"] is None and alteracoes[0]["detalhe"] is None


@pytest.mark.parametrize("situacao", ["realizada", "outra"])
def test_realizada_ou_outra_nao_da_alteracao(situacao):
    antes = reuniao_gravada(1, chaves=("p:10",))
    depois = reuniao_gravada(1, "2026-10-28T10:11", situacao, chaves=("p:10", "p:11"))

    assert _comparar([antes], [depois]) == []


@pytest.mark.parametrize("situacao", ["realizada", "cancelada", "outra"])
def test_so_compara_reuniao_convocada_na_checagem_anterior(situacao):
    antes = reuniao_gravada(1, situacao=situacao, chaves=("p:10",))
    depois = reuniao_gravada(1, "2026-10-29T10:00", "convocada", chaves=("p:11",))

    assert _comparar([antes], [depois]) == []


def test_reuniao_nova_na_janela_nao_da_alteracao():
    assert _comparar([], [reuniao_gravada(1, chaves=("p:10",))]) == []


def test_mesma_reuniao_em_duas_comissoes_compara_cada_uma():
    antes = [
        reuniao_gravada(1, chaves=("p:10",)),
        reuniao_gravada(1, chaves=("p:10",), comissao="CREDN"),
    ]
    depois = [antes[0], reuniao_gravada(1, chaves=("p:10", "p:11"), comissao="CREDN")]

    [alteracao] = _comparar(antes, depois)

    assert alteracao["reuniao"]["comissao"] == "CREDN"
    assert alteracao["tipo"] == "item_entrou"


# --- reunião que sumiu da janela ---------------------------------------------------------------


def test_sumiu_e_mudou_para_fora_da_janela():
    antes = reuniao_gravada(1, chaves=("p:10",))

    [alteracao] = _comparar([antes], [], buscar({1: detalhe(1, "2026-11-05T10:00")}))

    assert alteracao["tipo"] == "data_hora"
    assert (alteracao["de"], alteracao["para"]) == ("2026-10-28T10:00", "2026-11-05T10:00")


@pytest.mark.parametrize("situacao", ["Convocada", "Encerrada (Final)"])
@pytest.mark.parametrize("inicio", ["2026-10-16T10:00", "2026-10-16T10:11"])
def test_sumiu_so_porque_a_data_ficou_para_tras_nao_da_alteracao(situacao, inicio):
    # Reunião de 16/10 que estava convocada na última checagem boa (por exemplo, a Câmara a
    # deixou "Convocada" depois de realizada, ou a pauta ficou dias sem checagem boa): a janela
    # de 24/10 começa em 17/10. A data não mudou; a reunião só envelheceu.
    antes = reuniao_gravada(1, "2026-10-16T10:00", chaves=("p:10",))

    assert _comparar([antes], [], buscar({1: detalhe(1, inicio, situacao=situacao)})) == []


def test_sumiu_cancelada_fora_da_janela_e_cancelada():
    antes = reuniao_gravada(1, "2026-10-16T10:00", chaves=("p:10",))
    cancelada = detalhe(1, "2026-10-16T10:00", situacao="Cancelada")

    assert tipos(_comparar([antes], [], buscar({1: cancelada}))) == [("cancelada", None)]


def test_sumiu_e_foi_cancelada():
    antes = reuniao_gravada(1, chaves=("p:10",))
    cancelada = detalhe(1, "2026-10-28T10:00", situacao="Cancelada")

    assert tipos(_comparar([antes], [], buscar({1: cancelada}))) == [("cancelada", None)]


def test_sumiu_e_nao_existe_mais():
    antes = reuniao_gravada(1, chaves=("p:10",))

    [alteracao] = _comparar([antes], [], buscar({1: None}))

    assert alteracao["tipo"] == "retirada_da_agenda"
    assert alteracao["detalhe"] is None


def test_sumiu_porque_deixou_de_ser_reuniao_deliberativa_da_comissao():
    antes = reuniao_gravada(1, chaves=("p:10",))
    audiencia = detalhe(1, "2026-10-28T10:00", tipo="Audiência Pública")
    outro_orgao = detalhe(1, "2026-10-28T10:00", orgao=2018)

    [por_tipo] = _comparar([antes], [], buscar({1: audiencia}))
    [por_orgao] = _comparar([antes], [], buscar({1: outro_orgao}))

    assert por_tipo["tipo"] == "retirada_da_agenda"
    assert por_tipo["detalhe"] == "agora: Audiência Pública (CE)"
    assert por_orgao["detalhe"] == "agora: Reunião Deliberativa (CREDN)"


def test_sumiu_da_lista_mas_o_detalhe_ainda_e_a_mesma_reuniao():
    # A lista e o detalhe divergem às vezes (R2); sem indício de mudança, não há alteração.
    antes = reuniao_gravada(1, chaves=("p:10",))

    assert _comparar([antes], [], buscar({1: detalhe(1, "2026-10-28T10:00")})) == []


def test_reuniao_realizada_que_sumiu_nao_e_buscada():
    antes = reuniao_gravada(1, situacao="realizada", chaves=("p:10",))

    assert _comparar([antes], []) == []


def test_erro_na_busca_do_evento_propaga():
    def falhar(id_evento):
        raise FalhaDeColeta(FONTE_INDISPONIVEL, "/eventos/1: HTTP 503")

    with pytest.raises(FalhaDeColeta):
        _comparar([reuniao_gravada(1, chaves=("p:10",))], [], falhar)


def test_ordem_das_alteracoes():
    antes = [
        reuniao_gravada(2, "2026-10-28T10:00", chaves=("p:10",)),
        reuniao_gravada(1, "2026-10-28T10:00", chaves=("p:20", "p:21")),
        reuniao_gravada(3, "2026-10-27T09:00", chaves=()),
    ]
    depois = [
        reuniao_gravada(2, "2026-10-28T11:00", chaves=("p:11",)),
        reuniao_gravada(1, "2026-10-28T10:00", chaves=("p:22",)),
    ]

    alteracoes = _comparar(antes, depois, buscar({3: None}))

    assert [
        (a["reuniao"]["id"], a["tipo"], a["item"] and a["item"]["chave"]) for a in alteracoes
    ] == [
        (3, "retirada_da_agenda", None),
        (1, "item_entrou", "p:22"),
        (1, "item_saiu", "p:20"),
        (1, "item_saiu", "p:21"),
        (2, "item_entrou", "p:11"),
        (2, "item_saiu", "p:10"),
        (2, "data_hora", None),
    ]


# --- arquivo do dia: linha de base, acúmulo e "vista desde" -----------------------------------


def _checagem(reunioes, checada_em, hoje):
    from monitor_comissoes.pauta.checagem import janela, montar_checagem

    return montar_checagem(
        checada_em,
        janela(hoje),
        "2026-10-24T04:31:37+00:00",
        "2026-10-24T08:34:13-03:00",
        [{"id": 204455, "nome": "Luiz Lima"}],
        reunioes,
    )


def checar(anterior, reunioes, checada_em, hoje=date(2026, 10, 24), buscar_evento=nunca_buscar):
    """Uma checagem completa sobre `reunioes` (como `montar_reunioes` as devolveria)."""
    from monitor_comissoes.pauta.checagem import janela, montar_arquivo

    reunioes = [{**r, "vista_desde": checada_em} for r in reunioes]
    novas = []
    if anterior is not None:
        anteriores = anterior["checagem"]["reunioes"]
        novas = comparar(anteriores, reunioes, buscar_evento, checada_em, janela(hoje))
    return montar_arquivo(
        hoje, ("CE", "CREDN"), _checagem(reunioes, checada_em, hoje), anterior, novas
    )


MANHA = "2026-10-24T05:49:12-03:00"
TARDE = "2026-10-24T15:17:02-03:00"
NOITE = "2026-10-24T22:47:30-03:00"
AMANHA = "2026-10-25T05:48:00-03:00"


def test_primeira_checagem_e_linha_de_base_sem_alteracoes():
    arquivo = checar(None, [reuniao_gravada(1, chaves=("p:10",))], MANHA)

    assert list(arquivo) == ["meta", "checagem", "alteracoes"]
    assert arquivo["meta"] == {
        "versao_formato": 1,
        "data": "2026-10-24",
        "comissoes": ["CE", "CREDN"],
        "linha_de_base": {"motivo": "primeira checagem", "checada_em": MANHA},
    }
    assert list(arquivo["checagem"]) == [
        "checada_em",
        "janela",
        "lote",
        "inventario",
        "deputados_novo_em_exercicio",
        "reunioes",
    ]
    assert arquivo["checagem"]["janela"] == {"inicio": "2026-10-17", "fim": "2026-10-31"}
    assert arquivo["checagem"]["lote"] == {"dados_camara_em": "2026-10-24T04:31:37+00:00"}
    assert arquivo["checagem"]["inventario"] == {"gerado_em": "2026-10-24T08:34:13-03:00"}
    assert arquivo["alteracoes"] == []
    assert arquivo["checagem"]["reunioes"][0]["vista_desde"] == MANHA


def test_mesmo_dia_acumula_e_herda_a_linha_de_base():
    manha = checar(None, [reuniao_gravada(1, chaves=("p:10",))], MANHA)
    tarde = checar(manha, [reuniao_gravada(1, chaves=("p:10", "p:11"))], TARDE)
    noite = checar(tarde, [reuniao_gravada(1, chaves=("p:11",))], NOITE)

    assert noite["meta"]["linha_de_base"] == {"motivo": "primeira checagem", "checada_em": MANHA}
    assert [(a["detectada_em"], a["tipo"]) for a in noite["alteracoes"]] == [
        (TARDE, "item_entrou"),
        (NOITE, "item_saiu"),
    ]
    assert noite["checagem"]["checada_em"] == NOITE


def test_tres_checagens_com_tres_alteracoes_diferentes():
    ontem = checar(
        None,
        [reuniao_gravada(1, chaves=("p:10",))],
        "2026-10-23T22:47:30-03:00",
        date(2026, 10, 23),
    )
    manha = checar(ontem, [reuniao_gravada(1, chaves=("p:10", "p:11"))], MANHA)
    tarde = checar(manha, [reuniao_gravada(1, "2026-10-28T14:00", chaves=("p:10", "p:11"))], TARDE)
    noite = checar(tarde, [reuniao_gravada(1, "2026-10-28T14:00", "cancelada", chaves=())], NOITE)

    assert noite["meta"]["linha_de_base"] is None
    assert [(a["detectada_em"], a["tipo"]) for a in noite["alteracoes"]] == [
        (MANHA, "item_entrou"),
        (TARDE, "data_hora"),
        (NOITE, "cancelada"),
    ]
    assert noite["checagem"]["checada_em"] == NOITE


def test_dia_seguinte_so_tem_as_alteracoes_novas_no_arquivo_de_hoje():
    manha = checar(None, [reuniao_gravada(1, chaves=("p:10",))], MANHA)
    tarde = checar(manha, [reuniao_gravada(1, chaves=("p:10", "p:11"))], TARDE)

    amanha = checar(
        tarde, [reuniao_gravada(1, chaves=("p:10", "p:11", "p:12"))], AMANHA, date(2026, 10, 25)
    )

    assert amanha["meta"]["data"] == "2026-10-25"
    assert amanha["meta"]["linha_de_base"] is None
    assert [(a["detectada_em"], a["item"]["chave"]) for a in amanha["alteracoes"]] == [
        (AMANHA, "p:12")
    ]


def test_vista_desde_copiado_e_novo_para_reuniao_que_entrou():
    manha = checar(None, [reuniao_gravada(1, chaves=("p:10",))], MANHA)
    reunioes = [
        reuniao_gravada(1, chaves=("p:10",)),
        reuniao_gravada(2, "2026-10-31T10:00", chaves=("p:20",)),
        reuniao_gravada(1, chaves=("p:10",), comissao="CREDN"),
    ]

    tarde = checar(manha, reunioes, TARDE)

    vistas = {(r["id"], r["comissao"]): r["vista_desde"] for r in tarde["checagem"]["reunioes"]}
    assert vistas == {(1, "CE"): MANHA, (2, "CE"): TARDE, (1, "CREDN"): TARDE}
    assert tarde["alteracoes"] == []  # reunião nova na janela não é alteração


def test_reuniao_que_entra_na_janela_porque_o_dia_avancou():
    ontem = checar(
        None,
        [reuniao_gravada(1, chaves=("p:10",))],
        "2026-10-23T22:47:30-03:00",
        date(2026, 10, 23),
    )
    nova = reuniao_gravada(9, "2026-11-01T10:00", chaves=("p:90",))

    hoje = checar(ontem, [reuniao_gravada(1, chaves=("p:10",)), nova], MANHA)

    assert hoje["alteracoes"] == []
    assert hoje["checagem"]["reunioes"][1]["vista_desde"] == MANHA


def test_a_mesma_fonte_checada_de_novo_nao_acrescenta_alteracao():
    reunioes = [reuniao_gravada(1, chaves=("p:10", "p:11"))]
    manha = checar(None, [reuniao_gravada(1, chaves=("p:10",))], MANHA)
    tarde = checar(manha, reunioes, TARDE)

    noite = checar(tarde, reunioes, NOITE)
    amanha = checar(noite, reunioes, AMANHA, date(2026, 10, 25))

    assert len(noite["alteracoes"]) == 1
    assert amanha["alteracoes"] == []


def test_duas_checagens_da_mesma_fonte_diferem_so_no_momento():
    manha = checar(None, [reuniao_gravada(1, chaves=("p:10",))], MANHA)
    reunioes = [reuniao_gravada(1, chaves=("p:10",)), reuniao_gravada(2, chaves=("t:X",))]

    uma = checar(manha, reunioes, TARDE)
    outra = checar(manha, reunioes, NOITE)

    assert uma["checagem"]["checada_em"] != outra["checagem"]["checada_em"]
    outra["checagem"]["checada_em"] = uma["checagem"]["checada_em"]
    # A reunião 2 é nova nas duas: o "vista desde" é o momento de cada uma.
    outra["checagem"]["reunioes"][1]["vista_desde"] = uma["checagem"]["reunioes"][1]["vista_desde"]
    assert uma == outra


def test_montar_arquivo_nao_altera_as_entradas():
    manha = checar(None, [reuniao_gravada(1, chaves=("p:10",))], MANHA)
    copia = copy.deepcopy(manha)

    checar(manha, [reuniao_gravada(1, chaves=("p:11",))], TARDE)

    assert manha == copia


# --- reunião que sumiu só da lista (recuperar_sumidas) -----------------------------------------


def _eventos_da_ce(*eventos):
    return {"CE": (2009, list(eventos)), "CREDN": (2018, [])}


@pytest.mark.parametrize("situacao", ["convocada", "realizada", "cancelada"])
def test_recupera_pelo_detalhe_em_qualquer_situacao_sem_alterar_a_entrada(situacao):
    anterior = [reuniao_gravada(1, situacao=situacao, chaves=("p:10",))]
    entrada = _eventos_da_ce(evento(2, "2026-10-29T10:00"))
    copia = copy.deepcopy(entrada)
    situacao_camara = {"convocada": "Convocada", "realizada": "Encerrada", "cancelada": "Cancelada"}
    encontrado = detalhe(1, "2026-10-28T10:00", situacao=situacao_camara[situacao])

    saida = recuperar_sumidas(anterior, entrada, buscar({1: encontrado}), date(2026, 10, 24))

    assert [e["id"] for e in saida["CE"][1]] == [2, 1]
    assert saida["CREDN"] == (2018, [])
    assert entrada == copia


def test_nao_recupera_404_outra_comissao_nem_fora_da_janela():
    anterior = [
        reuniao_gravada(1, chaves=("p:10",)),
        reuniao_gravada(2, chaves=("p:10",)),
        reuniao_gravada(3, chaves=("p:10",)),
    ]
    eventos = {
        1: None,
        2: detalhe(2, "2026-10-28T10:00", orgao=2018),
        3: detalhe(3, "2026-11-05T10:00"),
    }

    saida = recuperar_sumidas(anterior, _eventos_da_ce(), buscar(eventos), date(2026, 10, 24))

    assert saida["CE"][1] == []


def test_nao_busca_quem_esta_na_lista_nem_a_realizada_que_ficou_para_tras():
    anterior = [
        reuniao_gravada(1, chaves=("p:10",)),
        reuniao_gravada(2, "2026-10-16T10:00", situacao="realizada", chaves=("p:10",)),
        reuniao_gravada(3, chaves=("p:10",), comissao="CDH"),  # comissão fora da configuração
    ]
    entrada = _eventos_da_ce(evento(1, "2026-10-28T10:00"))

    saida = recuperar_sumidas(anterior, entrada, nunca_buscar, date(2026, 10, 24))

    assert [e["id"] for e in saida["CE"][1]] == [1]
