from datetime import datetime

import pytest

from conftest import BRASILIA
from monitor_comissoes.deputados import DeputadoHoje
from monitor_comissoes.erros import INTERNA, FalhaDeColeta
from monitor_comissoes.estoque import (
    EstadoDeSaida,
    construir_itens,
    deve_ler_tramitacoes,
    estado_de_saida,
    etiquetar,
    resolver_referencia,
)
from monitor_comissoes.lote import Autor, Proposicao
from monitor_comissoes.relatoria import RelatorAtual, ResultadoRelatoria

AGORA = datetime(2026, 10, 18, 9, 0, tzinfo=BRASILIA)
COMISSOES = ("CE", "CREDN")
DEPUTADOS_NOVO = {204455, 220633}


def prop(id=1, tipo="PL", numero=10, ano=2020, orgao="CE", status=datetime(2026, 10, 8, 14, 30),
         situacao="Aguardando Parecer", principal=None, relator=None, sequencia=7):  # fmt: skip
    return Proposicao(
        id=id,
        tipo=tipo,
        numero=numero,
        ano=ano,
        ementa=f"Ementa {id}",
        data_apresentacao=datetime(ano, 3, 2, 10, 0),
        id_principal=principal,
        ultimo_status_em=status,
        orgao=orgao,
        situacao=situacao,
        id_relator=relator,
        ultimo_status_sequencia=sequencia,
    )


def autor(pid=1, dep=None, partido="PL", nome="Fulano", ordem=1):
    return Autor(
        id_proposicao=pid, id_deputado=dep, nome=nome, partido_na_data=partido, ordem=ordem
    )


def itens(candidatas, autores, comissoes=COMISSOES):
    return construir_itens({p.id: p for p in candidatas}, autores, DEPUTADOS_NOVO, comissoes, AGORA)


# --- etiquetar ----------------------------------------------------------------------------


def test_autoria_novo_pelo_partido_na_data():
    assert etiquetar([autor(partido="NOVO", dep=999)], DEPUTADOS_NOVO) == ["autoria NOVO"]


def test_autor_hoje_no_novo_pelo_id_do_deputado():
    assert etiquetar([autor(partido="PL", dep=204455)], DEPUTADOS_NOVO) == ["autor hoje no NOVO"]


def test_as_duas_etiquetas_em_ordem_fixa():
    autores = [autor(partido="NOVO", dep=204455)]

    assert etiquetar(autores, DEPUTADOS_NOVO) == ["autoria NOVO", "autor hoje no NOVO"]


def test_etiquetas_sem_repeticao_com_varios_autores():
    autores = [autor(partido="NOVO", dep=1, ordem=1), autor(partido="NOVO", dep=2, ordem=2)]

    assert etiquetar(autores, DEPUTADOS_NOVO) == ["autoria NOVO"]


def test_sem_ligacao_com_o_novo_nao_ha_etiqueta():
    assert etiquetar([autor(partido="PL", dep=5), autor(partido="PT", dep=6)], DEPUTADOS_NOVO) == []


def test_autor_que_nao_e_deputado_com_partido_novo_recebe_so_autoria():
    # Senado ou Executivo: idDeputadoAutor vazio, mas o partido registrado é NOVO.
    assert etiquetar([autor(partido="NOVO", dep=None)], DEPUTADOS_NOVO) == ["autoria NOVO"]


def test_autor_sem_id_e_de_outro_partido_nao_recebe_etiqueta():
    assert etiquetar([autor(partido="PT", dep=None)], DEPUTADOS_NOVO) == []


# --- construir_itens ----------------------------------------------------------------------


def test_item_completo_conforme_o_contrato():
    p = prop(id=7, numero=1843, ano=2022, status=datetime(2026, 10, 8, 14, 30))
    autores = {7: [autor(pid=7, dep=204455, partido="PL", nome="Luiz Lima")]}

    [item] = itens([p], autores)

    assert list(item) == [
        "id", "tipo", "numero", "ano", "identificacao", "ementa", "data_apresentacao", "link",
        "autores", "etiquetas", "comissao", "situacao", "ultimo_status_em",
        "ultimo_status_sequencia", "parado_ha_dias",
        "apensado_a", "principal_nao_localizada", "relator", "relator_indeterminado",
    ]  # fmt: skip
    assert item["identificacao"] == "PL 1843/2022"
    assert item["link"] == "https://www.camara.leg.br/propostas-legislativas/7"
    assert item["data_apresentacao"] == "2022-03-02T10:00:00"
    assert item["ultimo_status_em"] == "2026-10-08T14:30:00"
    assert item["ultimo_status_sequencia"] == 7
    assert item["parado_ha_dias"] == 10
    assert item["comissao"] == "CE"
    assert item["situacao"] == "Aguardando Parecer"
    assert item["etiquetas"] == ["autor hoje no NOVO"]
    assert item["autores"] == [
        {"nome": "Luiz Lima", "id_deputado": 204455, "partido_na_data": "PL", "ordem": 1}
    ]
    assert item["apensado_a"] is None
    assert item["principal_nao_localizada"] is False
    assert item["relator"] is None
    assert item["relator_indeterminado"] is None


def test_so_pl_e_plp_sao_candidatas():
    candidatas = [prop(id=1, tipo="PL"), prop(id=2, tipo="PLP"), prop(id=3, tipo="REQ"),
                  prop(id=4, tipo="PDL"), prop(id=5, tipo="PEC")]  # fmt: skip
    autores = {i: [autor(pid=i, partido="NOVO")] for i in range(1, 6)}

    assert [i["id"] for i in itens(candidatas, autores)] == [1, 2]


def test_orgao_fora_da_lista_fica_de_fora():
    candidatas = [prop(id=1, orgao="CE"), prop(id=2, orgao="CFT"), prop(id=3, orgao="")]
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (1, 2, 3)}

    assert [i["id"] for i in itens(candidatas, autores)] == [1]


def test_candidata_sem_etiqueta_ou_sem_autores_fica_de_fora():
    candidatas = [prop(id=1), prop(id=2)]
    autores = {1: [autor(pid=1, partido="PT", dep=9)]}

    assert itens(candidatas, autores) == []


def test_comissao_vem_da_configuracao():
    candidatas = [prop(id=1, orgao="CE"), prop(id=2, orgao="CREDN")]
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (1, 2)}

    assert [i["comissao"] for i in itens(candidatas, autores, comissoes=("CREDN",))] == ["CREDN"]


def test_autores_ordenados_por_ordem_de_assinatura():
    autores = {
        1: [autor(partido="NOVO", nome="B", ordem=2), autor(partido="PL", nome="A", ordem=1)]
    }

    [item] = itens([prop(id=1)], autores)

    assert [a["nome"] for a in item["autores"]] == ["A", "B"]


def test_ordem_dos_itens_parado_ha_mais_tempo_primeiro_e_id_no_empate():
    antigo = datetime(2020, 1, 1)
    recente = datetime(2026, 10, 1)
    candidatas = [prop(id=5, status=recente), prop(id=9, status=antigo), prop(id=3, status=antigo)]
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (3, 5, 9)}

    assert [i["id"] for i in itens(candidatas, autores)] == [3, 9, 5]


def test_parado_ha_conta_dias_inteiros_pela_data_de_brasilia():
    # 18/10/2026 09:00 em Brasília; último status no começo e no fim do dia 17.
    candidatas = [prop(id=1, status=datetime(2026, 10, 17, 0, 0)),
                  prop(id=2, status=datetime(2026, 10, 17, 23, 59)),
                  prop(id=3, status=datetime(2026, 10, 18, 8, 0))]  # fmt: skip
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (1, 2, 3)}

    assert {i["id"]: i["parado_ha_dias"] for i in itens(candidatas, autores)} == {1: 1, 2: 1, 3: 0}


# --- apensados e proposição de referência (dados SINTÉTICOS em memória) ---------------------


def com_referencia(candidatas, autores, mapa, linhas=None, comissoes=COMISSOES):
    todas = {p.id: p for p in candidatas}
    todas.update({p.id: p for p in (linhas or [])})
    return construir_itens(
        {p.id: p for p in candidatas}, autores, DEPUTADOS_NOVO, comissoes, AGORA,
        mapa_principal=mapa, proposicoes=todas,
    )  # fmt: skip


def test_item_traz_a_sequencia_do_ultimo_status_da_referencia():
    raiz = prop(id=2, status=datetime(2026, 9, 1), situacao="Pronta para Pauta", sequencia=43)
    apensado = prop(id=1, status=datetime(2013, 5, 5), principal=2, sequencia=3)
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([apensado], autores, {1: 2}, linhas=[raiz])

    # A sequência é a da raiz (de onde vêm situação e data), não a do apensado.
    assert item["ultimo_status_sequencia"] == 43
    assert item["situacao"] == "Pronta para Pauta"


def test_principal_nao_localizada_usa_a_sequencia_do_proprio_item():
    apensado = prop(id=1, principal=999, sequencia=5)
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([apensado], autores, {1: 999})

    assert item["principal_nao_localizada"] is True
    assert item["ultimo_status_sequencia"] == 5


@pytest.mark.parametrize("sequencia", [0, -1])
def test_sequencia_menor_que_1_e_falha_interna(sequencia):
    p = prop(id=1, sequencia=sequencia)
    autores = {1: [autor(pid=1, partido="NOVO")]}

    with pytest.raises(FalhaDeColeta) as erro:
        itens([p], autores)

    assert erro.value.categoria == INTERNA
    assert "ultimo_status_sequencia" in erro.value.motivo


def test_sem_principal_a_referencia_e_a_propria():
    p = prop(id=1)

    referencia = resolver_referencia(p, {}, {1: p})

    assert referencia.estado == "propria"
    assert referencia.proposicao is p and referencia.raiz is None


def test_apensado_usa_comissao_situacao_e_data_da_raiz():
    raiz = prop(id=2, orgao="CREDN", status=datetime(2026, 9, 1), situacao="Pronta para Pauta")
    apensado = prop(
        id=1,
        orgao="CE",
        status=datetime(2013, 5, 5),
        situacao="Tramitando em Conjunto",
        principal=2,
    )
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([apensado], autores, {1: 2}, linhas=[raiz])

    assert item["comissao"] == "CREDN"
    assert item["situacao"] == "Pronta para Pauta"
    assert item["ultimo_status_em"] == "2026-09-01T00:00:00"
    assert item["parado_ha_dias"] == 47
    assert item["apensado_a"] == {
        "id": 2,
        "identificacao": "PL 10/2020",
        "link": "https://www.camara.leg.br/propostas-legislativas/2",
    }
    assert item["principal_nao_localizada"] is False


def test_cadeia_de_dois_niveis_sobe_ate_a_raiz_e_nao_para_no_meio():
    a = prop(id=1, orgao="CE", principal=2)
    b = prop(id=2, orgao="CE", principal=3, situacao="Tramitando em Conjunto")
    c = prop(id=3, orgao="CREDN", situacao="Aguardando Parecer")
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([a], autores, {1: 2, 2: 3}, linhas=[b, c])

    assert item["apensado_a"]["id"] == 3
    assert item["comissao"] == "CREDN"
    assert item["situacao"] == "Aguardando Parecer"


def test_raiz_em_outra_comissao_deixa_o_apensado_de_fora_mesmo_com_status_proprio_na_lista():
    raiz = prop(id=2, orgao="CFT")
    apensado = prop(id=1, orgao="CE", principal=2)
    autores = {1: [autor(pid=1, partido="NOVO")]}

    assert com_referencia([apensado], autores, {1: 2}, linhas=[raiz]) == []


def test_raiz_na_lista_inclui_o_apensado_mesmo_com_status_proprio_em_outro_orgao():
    raiz = prop(id=2, orgao="CE")
    apensado = prop(id=1, orgao="MESA", principal=2)
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([apensado], autores, {1: 2}, linhas=[raiz])

    assert item["comissao"] == "CE"


def test_raiz_ausente_usa_o_proprio_status_com_a_marca():
    apensado = prop(id=1, orgao="CE", principal=99, situacao="Tramitando em Conjunto")
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([apensado], autores, {1: 99})

    assert item["principal_nao_localizada"] is True
    assert item["apensado_a"] is None
    assert item["comissao"] == "CE"
    assert item["situacao"] == "Tramitando em Conjunto"


def test_raiz_ausente_com_o_proprio_orgao_fora_da_lista_nao_entra():
    apensado = prop(id=1, orgao="CFT", principal=99)
    autores = {1: [autor(pid=1, partido="NOVO")]}

    assert com_referencia([apensado], autores, {1: 99}) == []


def test_elo_intermediario_ausente_tambem_e_nao_localizada():
    a = prop(id=1, orgao="CE", principal=2)  # o id 2 não existe nas linhas lidas
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([a], autores, {1: 2, 2: 3})

    assert item["principal_nao_localizada"] is True


@pytest.mark.parametrize("mapa", [{1: 2, 2: 1}, {1: 1}, {1: 2, 2: 3, 3: 2}])
def test_ciclo_e_tratado_como_principal_nao_localizada(mapa):
    a = prop(id=1, orgao="CE", principal=mapa[1])
    outras = [prop(id=i, orgao="CE", principal=mapa.get(i)) for i in mapa if i != 1]
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([a], autores, mapa, linhas=outras)

    assert item["principal_nao_localizada"] is True
    assert item["apensado_a"] is None
    assert item["comissao"] == "CE"


def test_etiquetas_vem_dos_autores_do_proprio_apensado_nunca_da_raiz():
    raiz = prop(id=2, orgao="CE")
    apensado = prop(id=1, orgao="CE", principal=2)
    autores = {1: [autor(pid=1, partido="PT", dep=7)], 2: [autor(pid=2, partido="NOVO")]}

    assert com_referencia([apensado], autores, {1: 2}, linhas=[raiz]) == []


def test_raiz_pode_ser_de_qualquer_tipo():
    raiz = prop(id=2, tipo="PEC", orgao="CE")
    apensado = prop(id=1, tipo="PL", orgao="CE", principal=2)
    autores = {1: [autor(pid=1, partido="NOVO")]}

    [item] = com_referencia([apensado], autores, {1: 2}, linhas=[raiz])

    assert item["apensado_a"]["identificacao"] == "PEC 10/2020"


# --- REL: relatoria NOVO -------------------------------------------------------------------

LUIZ_LIMA = DeputadoHoje(204455, "Luiz Lima", "NOVO")
THIAGO = DeputadoHoje(220560, "Thiago de Joaldo", "REPUBLICANOS")
COM_LUIZ_LIMA = ResultadoRelatoria(RelatorAtual(204455, "2025-04-09T00:00"))
COM_THIAGO = ResultadoRelatoria(RelatorAtual(220560, "2026-04-27T17:13"))
SEM_RELATOR = ResultadoRelatoria()


def itens_rel(candidatas, autores, relatorias, deputados=(LUIZ_LIMA, THIAGO), **extra):
    return construir_itens(
        {p.id: p for p in candidatas},
        autores,
        DEPUTADOS_NOVO,
        COMISSOES,
        AGORA,
        relatorias=relatorias,
        deputados_relator={d.id: d for d in deputados},
        **extra,
    )


def test_relatoria_novo_pelo_id_do_relator_atual():
    assert etiquetar([], DEPUTADOS_NOVO, id_relator=204455) == ["relatoria NOVO"]


def test_relator_de_outro_partido_nao_recebe_etiqueta_de_relatoria():
    assert etiquetar([], DEPUTADOS_NOVO, id_relator=220560) == []
    assert etiquetar([], DEPUTADOS_NOVO, id_relator=None) == []


def test_as_tres_etiquetas_em_ordem_fixa():
    autores = [autor(partido="NOVO", dep=204455)]

    assert etiquetar(autores, DEPUTADOS_NOVO, id_relator=220633) == [
        "autoria NOVO",
        "autor hoje no NOVO",
        "relatoria NOVO",
    ]


def test_item_so_de_relatoria_entra_com_o_relator_e_a_fonte():
    # PL 4501/2023: autoria de outro partido, relator atual na CE é Luiz Lima.
    p = prop(id=4501, relator=204455)
    autores = {4501: [autor(pid=4501, dep=9, partido="PSB", nome="Duarte Jr.")]}

    [item] = itens_rel([p], autores, {4501: COM_LUIZ_LIMA})

    assert item["etiquetas"] == ["relatoria NOVO"]
    assert item["relator"] == {
        "id": 204455,
        "nome": "Luiz Lima",
        "partido_hoje": "NOVO",
        "designado_em": "2025-04-09T00:00:00",
        "fonte": "https://www.camara.leg.br/propostas-legislativas/4501",
    }
    assert item["relator_indeterminado"] is None


def test_candidato_sem_relator_atual_confirmado_fica_de_fora():
    # PL 937/2022: o lote ainda aponta o relator do NOVO, mas as tramitações dizem que devolveu.
    p = prop(id=937, relator=204455)

    assert itens_rel([p], {}, {937: SEM_RELATOR}) == []


def test_item_com_autoria_e_relator_de_outro_partido_mantem_so_a_autoria():
    p = prop(id=3871, relator=220560)
    autores = {3871: [autor(pid=3871, partido="NOVO", dep=1)]}

    [item] = itens_rel([p], autores, {3871: COM_THIAGO})

    assert item["etiquetas"] == ["autoria NOVO"]
    assert item["relator"]["nome"] == "Thiago de Joaldo"
    assert item["relator"]["partido_hoje"] == "REPUBLICANOS"


def test_item_so_de_autoria_sem_relator_traz_relator_nulo():
    p = prop(id=5594)
    autores = {5594: [autor(pid=5594, partido="NOVO", dep=1)]}

    [item] = itens_rel([p], autores, {5594: SEM_RELATOR})

    assert item["relator"] is None
    assert item["relator_indeterminado"] is None


def test_autoria_e_relatoria_no_mesmo_item():
    p = prop(id=1843, relator=204455)
    autores = {1843: [autor(pid=1843, partido="NOVO", dep=1)]}

    [item] = itens_rel([p], autores, {1843: COM_LUIZ_LIMA})

    assert item["etiquetas"] == ["autoria NOVO", "relatoria NOVO"]


def test_relatoria_nao_inclui_fora_da_comissao_da_lista():
    p = prop(id=1, orgao="CFT", relator=204455)

    assert itens_rel([p], {}, {1: COM_LUIZ_LIMA}) == []


# --- REL US2: apensados herdam o relator da principal --------------------------------------


def itens_apensados(candidatas, autores, relatorias, mapa, linhas=None):
    return itens_rel(
        candidatas,
        autores,
        relatorias,
        mapa_principal=mapa,
        proposicoes=linhas or {p.id: p for p in candidatas},
    )


def test_apensado_herda_o_relator_da_principal():
    raiz = prop(id=1, relator=204455)
    apensado = prop(id=2, orgao="CFT", principal=1, status=datetime(2013, 5, 6))
    autores = {2: [autor(pid=2, partido="PT", dep=9)]}

    [item] = itens_apensados(
        [apensado], autores, {1: COM_LUIZ_LIMA}, {2: 1}, {1: raiz, 2: apensado}
    )

    assert item["id"] == 2
    assert item["etiquetas"] == ["relatoria NOVO"]
    assert item["apensado_a"]["id"] == 1
    assert item["relator"]["nome"] == "Luiz Lima"
    assert item["relator"]["fonte"].endswith("/1")  # a ficha de onde o relator foi lido: a raiz


def test_cadeia_de_dois_niveis_usa_o_relator_da_raiz():
    c = prop(id=3, relator=204455)
    b = prop(id=2, principal=3)
    a = prop(id=1, principal=2)

    [item] = itens_apensados(
        [a], {}, {3: COM_LUIZ_LIMA, 2: SEM_RELATOR}, {1: 2, 2: 3}, {1: a, 2: b, 3: c}
    )

    assert item["apensado_a"]["id"] == 3
    assert item["etiquetas"] == ["relatoria NOVO"]
    assert item["relator"]["id"] == 204455


def test_relator_do_proprio_apensado_nao_vale_se_a_raiz_nao_tem_relator_do_novo():
    # O apensado foi relatado pelo NOVO no passado; hoje quem vale é o relator da principal.
    raiz = prop(id=1, relator=220560)
    apensado = prop(id=2, principal=1, relator=204455)
    autores = {2: [autor(pid=2, partido="PT", dep=9)]}

    resultado = itens_apensados(
        [apensado], autores, {1: COM_THIAGO}, {2: 1}, {1: raiz, 2: apensado}
    )

    assert resultado == []


def test_raiz_fora_da_lista_de_comissoes_deixa_o_apensado_de_fora_mesmo_com_relator():
    raiz = prop(id=1, orgao="CFT", relator=204455)
    apensado = prop(id=2, principal=1, orgao="CE")

    assert itens_apensados([apensado], {}, {1: COM_LUIZ_LIMA}, {2: 1}, {1: raiz, 2: apensado}) == []


def test_principal_nao_localizada_usa_o_relator_do_proprio_item():
    # A raiz (id 99) não está nas linhas lidas: vale o status e a relatoria do próprio apensado.
    apensado = prop(id=2, principal=99, relator=204455)

    [item] = itens_apensados([apensado], {}, {2: COM_LUIZ_LIMA}, {2: 99})

    assert item["principal_nao_localizada"] is True
    assert item["apensado_a"] is None
    assert item["etiquetas"] == ["relatoria NOVO"]
    assert item["relator"]["fonte"].endswith("/2")


def test_dois_apensados_da_mesma_raiz_compartilham_o_relator():
    raiz = prop(id=1, relator=204455)
    a, b = prop(id=2, principal=1), prop(id=3, principal=1)

    resultado = itens_apensados([a, b], {}, {1: COM_LUIZ_LIMA}, {2: 1, 3: 1}, {1: raiz, 2: a, 3: b})

    assert [i["id"] for i in resultado] == [2, 3]
    assert {i["relator"]["id"] for i in resultado} == {204455}


# --- REL US4: relator indeterminado --------------------------------------------------------

INDETERMINADO = ResultadoRelatoria(indeterminado="tipo de tramitação 9999 não reconhecido")


def test_candidato_indeterminado_sem_outra_etiqueta_entra_com_a_marca():
    p = prop(id=1, relator=204455)  # o lote aponta relator do NOVO, as tramitações não decidem

    [item] = itens_rel([p], {}, {1: INDETERMINADO})

    assert item["etiquetas"] == []
    assert item["relator"] is None
    assert item["relator_indeterminado"] == {"motivo": INDETERMINADO.indeterminado}


def test_item_de_autoria_indeterminado_mantem_a_etiqueta_de_autoria_e_leva_a_marca():
    p = prop(id=1, relator=220560)
    autores = {1: [autor(pid=1, partido="NOVO", dep=1)]}

    [item] = itens_rel([p], autores, {1: INDETERMINADO})

    assert item["etiquetas"] == ["autoria NOVO"]
    assert item["relator_indeterminado"] is not None


def test_indeterminado_sem_candidatura_e_sem_etiqueta_fica_de_fora():
    p = prop(id=1, relator=220560)  # relator do lote é de outro partido: não é candidato

    assert itens_rel([p], {}, {1: INDETERMINADO}) == []


def test_indeterminado_nao_da_nem_nega_a_relatoria_novo():
    p = prop(id=1, relator=204455)
    autores = {1: [autor(pid=1, partido="NOVO", dep=1)]}

    [item] = itens_rel([p], autores, {1: INDETERMINADO})

    assert "relatoria NOVO" not in item["etiquetas"]


def test_indeterminado_de_uma_referencia_nao_afeta_os_outros_itens():
    a, b = prop(id=1, relator=204455), prop(id=2, relator=204455)

    resultado = itens_rel([a, b], {}, {1: INDETERMINADO, 2: COM_LUIZ_LIMA})

    por_id = {i["id"]: i for i in resultado}
    assert por_id[1]["relator_indeterminado"] is not None and por_id[1]["relator"] is None
    assert (
        por_id[2]["etiquetas"] == ["relatoria NOVO"] and por_id[2]["relator_indeterminado"] is None
    )


def test_apensado_de_raiz_indeterminada_tambem_leva_a_marca():
    raiz = prop(id=1, relator=204455)
    apensado = prop(id=2, principal=1)

    [item] = itens_apensados([apensado], {}, {1: INDETERMINADO}, {2: 1}, {1: raiz, 2: apensado})

    assert item["etiquetas"] == []
    assert item["apensado_a"]["id"] == 1
    assert item["relator_indeterminado"] is not None


# --- revisão independente: nada de "sem relator" por referência não lida (I1) ---------------


def test_referencia_que_deveria_ter_sido_lida_e_erro_interno_e_nao_sem_relator():
    p = prop(id=1, relator=204455)
    autores = {1: [autor(pid=1, partido="NOVO", dep=1)]}

    with pytest.raises(FalhaDeColeta) as erro:
        itens_rel([p], autores, {})  # a coleta deveria ter lido a referência 1

    assert erro.value.categoria == INTERNA
    assert "referência 1" in erro.value.motivo


def test_candidato_que_nao_precisa_ser_lido_nao_exige_relatoria():
    # O relator do lote é de outro partido e não há autoria do NOVO: nada a ler, nada a listar.
    p = prop(id=1, relator=220560)

    assert itens_rel([p], {}, {}) == []


def test_apensado_com_relator_proprio_do_novo_mas_raiz_de_outro_nao_exige_leitura():
    raiz = prop(id=1, relator=220560)
    apensado = prop(id=2, principal=1, relator=204455)

    assert itens_apensados([apensado], {}, {}, {2: 1}, {1: raiz, 2: apensado}) == []


def test_deve_ler_tramitacoes_decide_pela_autoria_ou_pelo_relator_do_lote():
    com_autoria = [autor(partido="NOVO")]

    assert deve_ler_tramitacoes(com_autoria, DEPUTADOS_NOVO, prop(relator=None))
    assert deve_ler_tramitacoes([], DEPUTADOS_NOVO, prop(relator=204455))
    assert not deve_ler_tramitacoes([], DEPUTADOS_NOVO, prop(relator=220560))
    assert not deve_ler_tramitacoes([], DEPUTADOS_NOVO, prop(relator=None))


def test_designado_em_com_segundos_nao_ganha_segundos_a_mais():
    p = prop(id=1, relator=204455)
    comsegundos = ResultadoRelatoria(RelatorAtual(204455, "2025-04-09T10:11:12"))

    [item] = itens_rel([p], {1: [autor(pid=1, partido="NOVO", dep=1)]}, {1: comsegundos})

    assert item["relator"]["designado_em"] == "2025-04-09T10:11:12"


# --- estado de quem saiu da lista (MUD, research R1) --------------------------------------------

from conftest import FIXTURES  # noqa: E402
from monitor_comissoes.lote import ler_apensacao, ler_proposicoes  # noqa: E402

PL_4047_2019 = 2211957  # apensado, via cadeia, ao PL 3047/2015 (id 1734799), que está na CFT
PL_3047_2015 = 1734799
PL_7843_2017 = 2141142  # Transformado em Norma Jurídica, na MESA
PL_30_2015 = 267841  # Aguardando Apreciação pelo Senado Federal, na MESA
PL_1843_2022 = 2331032  # CE, Aguardando Parecer


def lote_real():
    linhas, mapa = {}, {}
    for arquivo in sorted(FIXTURES.glob("proposicoes-20*.csv")):
        for p in ler_proposicoes(arquivo):
            linhas[p.id] = p
        mapa.update(ler_apensacao(arquivo))
    return linhas, mapa


def test_apensado_a_principal_fora_das_comissoes_traz_a_raiz_e_o_orgao_dela():
    linhas, mapa = lote_real()

    estado = estado_de_saida(PL_4047_2019, linhas, mapa, COMISSOES)

    assert estado == EstadoDeSaida(
        existe=True,
        referencia_id=PL_3047_2015,
        orgao="CFT",
        situacao="Aguardando Designação de Relator(a)",
        sequencia=87,
        apensado_a={
            "id": PL_3047_2015,
            "identificacao": "PL 3047/2015",
            "link": f"https://www.camara.leg.br/propostas-legislativas/{PL_3047_2015}",
        },
        na_comissao=False,
    )


def test_transformado_em_norma_traz_a_situacao_e_a_mesa_como_orgao():
    linhas, mapa = lote_real()

    estado = estado_de_saida(PL_7843_2017, linhas, mapa, COMISSOES)

    assert (estado.existe, estado.referencia_id, estado.orgao) == (True, PL_7843_2017, "MESA")
    assert estado.situacao == "Transformado em Norma Jurídica"
    assert estado.sequencia == 134
    assert estado.apensado_a is None and estado.na_comissao is False


def test_aguardando_o_senado_traz_a_situacao_e_a_sequencia_reais():
    linhas, mapa = lote_real()

    estado = estado_de_saida(PL_30_2015, linhas, mapa, COMISSOES)

    assert estado.situacao == "Aguardando Apreciação pelo Senado Federal"
    assert (estado.sequencia, estado.na_comissao) == (259, False)


def test_referencia_que_continua_na_comissao_tem_na_comissao_verdadeiro():
    linhas, mapa = lote_real()

    estado = estado_de_saida(PL_1843_2022, linhas, mapa, COMISSOES)

    assert (estado.orgao, estado.situacao, estado.sequencia) == ("CE", "Aguardando Parecer", 42)
    assert estado.na_comissao is True


def test_a_lista_de_comissoes_decide_na_comissao():
    linhas, mapa = lote_real()

    assert estado_de_saida(PL_1843_2022, linhas, mapa, ("CREDN",)).na_comissao is False
    assert estado_de_saida(PL_7843_2017, linhas, mapa, ("MESA",)).na_comissao is True


def test_id_ausente_do_lote_nao_existe_e_nao_inventa_campos():
    linhas, mapa = lote_real()

    estado = estado_de_saida(987_654_321, linhas, mapa, COMISSOES)

    assert estado == EstadoDeSaida(False, None, None, None, None, None, False)


def test_principal_nao_localizada_usa_o_proprio_item():
    # Derivado: o apensado aponta para uma principal que não está no lote.
    apensado = prop(id=1, orgao="CE", situacao="Tramitando em Conjunto", principal=999, sequencia=5)

    estado = estado_de_saida(1, {1: apensado}, {1: 999}, COMISSOES)

    assert (estado.existe, estado.referencia_id, estado.orgao) == (True, 1, "CE")
    assert estado.apensado_a is None  # sem raiz localizada, não há "apensado a"
    assert (estado.sequencia, estado.na_comissao) == (5, True)


def test_apensado_a_raiz_na_comissao_herda_orgao_situacao_e_sequencia_da_raiz():
    raiz = prop(id=2, orgao="CREDN", situacao="Pronta para Pauta", sequencia=43)
    apensado = prop(id=1, orgao="CE", situacao="Tramitando em Conjunto", principal=2, sequencia=3)

    estado = estado_de_saida(1, {1: apensado, 2: raiz}, {1: 2}, COMISSOES)

    assert (estado.referencia_id, estado.orgao, estado.situacao) == (
        2,
        "CREDN",
        "Pronta para Pauta",
    )
    assert estado.sequencia == 43
    assert estado.apensado_a["id"] == 2 and estado.na_comissao is True
