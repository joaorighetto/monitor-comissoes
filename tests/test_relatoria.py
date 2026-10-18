"""Regra do relator atual (research R2), sobre tramitações reais e variantes derivadas."""

import random

import pytest

from conftest import TransporteFalso
from monitor_comissoes.relatoria import relator_atual
from monitor_comissoes.tramitacoes import Tramitacao, obter_tramitacoes

URL_BASE = "https://dadosabertos.camara.leg.br"

PL_937_2022 = 2319917  # CE: o relator do NOVO devolveu sem manifestação (507)
PL_3514_2023 = 2373721  # CREDN: o relator do NOVO foi designado na CESPO
PL_4501_2023 = 2388105  # CE: Luiz Lima, relator atual
PL_1843_2022 = (
    2331032  # CE: Adriana Ventura, com "500 Mantido o parecer" e "170 Devolução ao relator"
)
PL_3871_2024 = 2461936  # CE: Thiago de Joaldo (REPUBLICANOS)
PL_648_2024 = 2319916  # CE: termina em 507
PL_4781_2025 = 2564786  # CE: termina em 507
PL_330_2025 = 2483186  # CREDN: recebida, nunca designada

LUIZ_LIMA = 204455
ADRIANA_VENTURA = 204528
THIAGO_DE_JOALDO = 220560
OUTRO = 999001


def real(id_proposicao: int) -> list[Tramitacao]:
    return obter_tramitacoes(TransporteFalso(), URL_BASE, id_proposicao)


def depois(base: list[Tramitacao], orgao: str, codigo: str, relator: int | None = None):
    """Acrescenta ao fim das tramitações REAIS uma tramitação derivada (só existe no teste)."""
    proxima = max(t.sequencia for t in base) + 1
    nova = Tramitacao(
        sequencia=proxima,
        data_hora="2026-10-18T10:00",
        orgao=orgao,
        codigo=codigo,
        descricao="derivada",
        id_relator=relator,
    )
    return [*base, nova]


# --- casos reais da sondagem ---------------------------------------------------------------


def test_pl_937_2022_relator_do_novo_devolveu_a_materia():
    resultado = relator_atual(real(PL_937_2022), "CE")

    assert resultado.relator is None
    assert resultado.indeterminado is None


def test_pl_3514_2023_relator_era_de_outra_comissao():
    resultado = relator_atual(real(PL_3514_2023), "CREDN")

    assert resultado.relator is None
    assert resultado.indeterminado is None


def test_pl_4501_2023_luiz_lima_e_o_relator_atual():
    resultado = relator_atual(real(PL_4501_2023), "CE")

    assert resultado.relator.id == LUIZ_LIMA
    assert resultado.relator.designado_em == "2025-04-09T00:00"
    assert resultado.indeterminado is None


def test_pl_1843_2022_parecer_mantido_e_devolucao_ao_relator_nao_zeram():
    resultado = relator_atual(real(PL_1843_2022), "CE")

    assert resultado.relator.id == ADRIANA_VENTURA
    assert resultado.relator.designado_em == "2025-04-09T00:00"


def test_relator_de_outro_partido_tambem_e_devolvido_com_a_data_da_designacao():
    resultado = relator_atual(real(PL_3871_2024), "CE")

    assert resultado.relator.id == THIAGO_DE_JOALDO
    assert resultado.relator.designado_em == "2026-04-27T17:13"


@pytest.mark.parametrize("id_proposicao", [PL_648_2024, PL_4781_2025])
def test_materia_devolvida_no_fim_fica_sem_relator(id_proposicao):
    assert relator_atual(real(id_proposicao), "CE").relator is None


def test_materia_recebida_e_nunca_designada_fica_sem_relator():
    resultado = relator_atual(real(PL_330_2025), "CREDN")

    assert resultado.relator is None
    assert resultado.indeterminado is None


# --- ordem -------------------------------------------------------------------------------


@pytest.mark.parametrize("id_proposicao", [PL_937_2022, PL_4501_2023, PL_1843_2022])
def test_a_ordem_da_lista_nao_importa_so_a_sequencia(id_proposicao):
    comissao = "CE"
    esperado = relator_atual(real(id_proposicao), comissao)
    embaralhada = real(id_proposicao)
    random.Random(7).shuffle(embaralhada)

    assert relator_atual(embaralhada, comissao) == esperado


def test_devolucao_e_designacao_no_mesmo_instante_vale_a_sequencia():
    # As duas tramitações derivadas têm a mesma data e hora; só a sequência as ordena.
    tramitacoes = depois(depois(real(PL_4501_2023), "CE", "507"), "CE", "320", OUTRO)
    random.Random(3).shuffle(tramitacoes)

    assert relator_atual(tramitacoes, "CE").relator.id == OUTRO


# --- devolução, substituição e saída (derivadas das tramitações reais) -------------------


def test_devolucao_sem_manifestacao_apos_a_designacao_zera_o_relator():
    resultado = relator_atual(depois(real(PL_4501_2023), "CE", "507"), "CE")

    assert resultado.relator is None


def test_substituicao_do_novo_por_outro_partido():
    base = real(PL_4501_2023)
    assert relator_atual(base, "CE").relator.id == LUIZ_LIMA

    resultado = relator_atual(depois(base, "CE", "320", THIAGO_DE_JOALDO), "CE")

    assert resultado.relator.id == THIAGO_DE_JOALDO


def test_substituicao_de_outro_partido_pelo_novo():
    base = real(PL_3871_2024)
    assert relator_atual(base, "CE").relator.id == THIAGO_DE_JOALDO

    resultado = relator_atual(depois(base, "CE", "320", LUIZ_LIMA), "CE")

    assert resultado.relator.id == LUIZ_LIMA
    assert resultado.relator.designado_em == "2026-10-18T10:00"


@pytest.mark.parametrize("codigo", ["1250", "1255"])
def test_saida_do_relator_da_comissao_encerra_a_relatoria(codigo):
    resultado = relator_atual(depois(real(PL_4501_2023), "CE", codigo), "CE")

    assert resultado.relator is None
    assert resultado.indeterminado is None


@pytest.mark.parametrize("codigo", ["1250", "1255"])
def test_redesignacao_depois_da_saida_restaura_o_relator_com_a_nova_data(codigo):
    saiu = depois(real(PL_4501_2023), "CE", codigo)

    resultado = relator_atual(depois(saiu, "CE", "320", LUIZ_LIMA), "CE")

    assert resultado.relator.id == LUIZ_LIMA
    assert resultado.relator.designado_em == "2026-10-18T10:00"


@pytest.mark.parametrize("codigo", ["170", "322", "501"])
def test_devolucao_ao_relator_parecer_e_recebimento_de_parecer_mantem_o_relator(codigo):
    resultado = relator_atual(depois(real(PL_4501_2023), "CE", codigo), "CE")

    assert resultado.relator.id == LUIZ_LIMA


# --- passagens e órgãos de apoio -----------------------------------------------------------


@pytest.mark.parametrize("apoio", ["MESA", "CCP", "PLEN"])
def test_tramitacao_de_orgao_de_apoio_nao_zera_o_relator(apoio):
    resultado = relator_atual(depois(real(PL_4501_2023), apoio, "604"), "CE")

    assert resultado.relator.id == LUIZ_LIMA


def test_materia_que_saiu_e_voltou_a_comissao_perde_a_designacao_da_passagem_anterior():
    base = real(PL_4501_2023)
    voltou = depois(depois(base, "CFT", "500"), "CE", "500")

    resultado = relator_atual(voltou, "CE")

    assert resultado.relator is None
    assert resultado.indeterminado is None


def test_na_nova_passagem_vale_a_nova_designacao():
    base = real(PL_4501_2023)
    voltou = depois(depois(base, "CFT", "500"), "CE", "500")

    resultado = relator_atual(depois(voltou, "CE", "320", THIAGO_DE_JOALDO), "CE")

    assert resultado.relator.id == THIAGO_DE_JOALDO


def test_designacao_numa_comissao_que_nao_e_a_atual_nao_vale():
    base = real(PL_330_2025)  # recebida pela CREDN, sem relator

    resultado = relator_atual(depois(base, "CREDN", "320", LUIZ_LIMA), "CREDN")
    assert resultado.relator.id == LUIZ_LIMA

    # A mesma designação feita na CE não conta para quem está na CREDN.
    resultado = relator_atual(depois(base, "CE", "320", LUIZ_LIMA), "CREDN")
    assert resultado.relator is None
