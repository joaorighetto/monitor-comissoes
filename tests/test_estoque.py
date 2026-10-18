from datetime import datetime

import pytest

from conftest import BRASILIA
from monitor_comissoes.deputados import DeputadoHoje
from monitor_comissoes.estoque import construir_itens, etiquetar, resolver_referencia
from monitor_comissoes.lote import Autor, Proposicao
from monitor_comissoes.relatoria import RelatorAtual, ResultadoRelatoria

AGORA = datetime(2026, 10, 18, 9, 0, tzinfo=BRASILIA)
COMISSOES = ("CE", "CREDN")
DEPUTADOS_NOVO = {204455, 220633}


def prop(id=1, tipo="PL", numero=10, ano=2020, orgao="CE", status=datetime(2026, 10, 8, 14, 30),
         situacao="Aguardando Parecer", principal=None, relator=None):  # fmt: skip
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
        "autores", "etiquetas", "comissao", "situacao", "ultimo_status_em", "parado_ha_dias",
        "apensado_a", "principal_nao_localizada", "relator", "relator_indeterminado",
    ]  # fmt: skip
    assert item["identificacao"] == "PL 1843/2022"
    assert item["link"] == "https://www.camara.leg.br/propostas-legislativas/7"
    assert item["data_apresentacao"] == "2022-03-02T10:00:00"
    assert item["ultimo_status_em"] == "2026-10-08T14:30:00"
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
