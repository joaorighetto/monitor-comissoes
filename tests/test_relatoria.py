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


# --- indeterminado (FR-011) -------------------------------------------------------------------


def test_designacao_sem_relator_identificado_e_indeterminada():
    base = real(PL_330_2025)

    resultado = relator_atual(depois(base, "CREDN", "320", None), "CREDN")

    assert resultado.relator is None
    assert "designação sem relator" in resultado.indeterminado


def test_tipo_de_relatoria_desconhecido_e_indeterminado():
    nova = Tramitacao(99, "2026-10-18T10:00", "CE", "9999", "Relator(a) Substituído", None)

    resultado = relator_atual([*real(PL_4501_2023), nova], "CE")

    assert resultado.relator is None
    assert "9999" in resultado.indeterminado


def test_tipo_desconhecido_sem_a_palavra_relator_e_ignorado():
    nova = Tramitacao(99, "2026-10-18T10:00", "CE", "9998", "Pedido de Vista", None)

    resultado = relator_atual([*real(PL_4501_2023), nova], "CE")

    assert resultado.relator.id == LUIZ_LIMA
    assert resultado.indeterminado is None


@pytest.mark.parametrize("codigo", ["320", "507", "1250", "1255"])
def test_nova_designacao_ou_saida_resolve_a_indeterminacao_por_tipo_desconhecido(codigo):
    nova = Tramitacao(99, "2026-10-18T10:00", "CE", "9999", "Relator(a) Substituído", None)
    indeterminada = [*real(PL_4501_2023), nova]
    assert relator_atual(indeterminada, "CE").indeterminado

    resultado = relator_atual(depois(indeterminada, "CE", codigo, OUTRO), "CE")

    assert resultado.indeterminado is None
    assert (resultado.relator is not None) == (codigo == "320")


def test_materia_em_outra_comissao_na_api_e_indeterminada():
    # O lote diz CE, mas as tramitações já terminam na CFT (a matéria andou desde ontem).
    resultado = relator_atual(depois(real(PL_4501_2023), "CFT", "500"), "CE")

    assert resultado.relator is None
    assert "CFT" in resultado.indeterminado
    assert "CE" in resultado.indeterminado


def test_so_orgaos_de_apoio_e_indeterminado():
    so_apoio = [t for t in real(PL_4501_2023) if t.orgao in ("MESA", "CCP", "PLEN")]

    resultado = relator_atual(so_apoio, "CE")

    assert resultado.relator is None
    assert "nenhum órgão de comissão" in resultado.indeterminado


def test_relator_e_indeterminado_nunca_aparecem_juntos():
    ids = [PL_937_2022, PL_4501_2023, PL_1843_2022, PL_3871_2024, PL_330_2025, PL_648_2024]
    variantes = [real(i) for i in ids]
    variantes += [depois(real(i), "CE", "9999") for i in ids]
    for tramitacoes in variantes:
        resultado = relator_atual(tramitacoes, "CE")
        assert not (resultado.relator and resultado.indeterminado)


# --- revisão independente: órgãos de serviço (C1) ----------------------------------------------

PL_2459367 = 2459367  # história real com um órgão de serviço (SGM) entre tramitações da CE


def test_notificacao_de_orgao_de_servico_nao_apaga_o_relator():
    # SGM só notifica; nunca recebe a matéria. A CE continua com ela e o relator segue valendo.
    base = depois(real(PL_4501_2023), "SGM", "1005")

    resultado = relator_atual(depois(base, "CE", "501"), "CE")

    assert resultado.relator.id == LUIZ_LIMA
    assert resultado.indeterminado is None


def test_historia_real_com_sgm_entre_tramitacoes_da_ce():
    orgaos = {t.orgao for t in real(PL_2459367)}
    assert "SGM" in orgaos  # o caso real que o revisor apontou

    resultado = relator_atual(real(PL_2459367), "CE")

    assert resultado.relator.id == LUIZ_LIMA
    assert resultado.relator.designado_em == "2026-03-20T14:18"


def test_orgao_de_servico_depois_da_designacao_e_antes_de_uma_nova_nao_muda_o_resultado():
    sem_servico = depois(real(PL_4501_2023), "CE", "501")
    com_servico = depois(depois(real(PL_4501_2023), "SGM", "1005"), "CE", "501")

    assert relator_atual(com_servico, "CE") == relator_atual(sem_servico, "CE")


def test_orgao_que_recebe_a_materia_continua_iniciando_uma_nova_passagem():
    # CFT recebe a matéria (500): é comissão, e a designação da passagem anterior na CE não vale.
    voltou = depois(depois(depois(real(PL_4501_2023), "CFT", "500"), "CFT", "322"), "CE", "500")

    assert relator_atual(voltou, "CE").relator is None
