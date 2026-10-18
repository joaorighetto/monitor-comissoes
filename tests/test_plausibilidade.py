"""Plausibilidade do estoque bruto (AGE, FR-014 a FR-018b), em aritmética de inteiros."""

import pytest

from monitor_comissoes.erros import (
    ESTOQUE_IMPLAUSIVEL,
    ESTOQUE_VAZIO,
    SEM_BASE_DE_COMPARACAO,
    FalhaDeColeta,
)
from monitor_comissoes.plausibilidade import verificar


def falha_de(estoque, base, limite=20, aceitar=False):
    with pytest.raises(FalhaDeColeta) as erro:
        verificar(estoque, base, limite, aceitar)
    return erro.value


def test_queda_de_28_por_cento_falha_e_o_motivo_traz_os_totais_e_a_variacao():
    falha = falha_de(1100, 1531)

    assert falha.categoria == ESTOQUE_IMPLAUSIVEL
    for trecho in ("1531", "1100", "-28,15%", "20%"):
        assert trecho in falha.motivo


def test_alta_de_mais_de_20_por_cento_tambem_falha():
    falha = falha_de(1250, 1000)

    assert falha.categoria == ESTOQUE_IMPLAUSIVEL
    assert "+25,00%" in falha.motivo


@pytest.mark.parametrize("estoque", [800, 1200])
def test_exatamente_20_por_cento_passa(estoque):
    assert verificar(estoque, 1000, 20, False) is None


@pytest.mark.parametrize("estoque", [799, 1201])
def test_so_mais_de_20_por_cento_e_implausivel(estoque):
    assert falha_de(estoque, 1000).categoria == ESTOQUE_IMPLAUSIVEL


def test_variacao_dentro_do_limite_passa():
    assert verificar(1500, 1531, 20, False) is None


def test_sem_base_a_variacao_nao_se_aplica():
    assert verificar(10, None, 20, False) is None


def test_base_zero_e_tratada_como_sem_base():
    assert verificar(10, 0, 20, False) is None


@pytest.mark.parametrize("base", [None, 1531])
@pytest.mark.parametrize("aceitar", [False, True])
def test_estoque_bruto_zero_sempre_falha_inclusive_com_a_confirmacao(base, aceitar):
    falha = falha_de(0, base, aceitar=aceitar)

    assert falha.categoria == ESTOQUE_VAZIO


def test_com_a_confirmacao_a_variacao_acima_do_limite_passa_e_e_registrada():
    aceita = verificar(1100, 1531, 20, True)

    assert aceita == {
        "estoque_anterior": 1531,
        "estoque_novo": 1100,
        "variacao_percentual": -28.2,
    }
    assert list(aceita) == ["estoque_anterior", "estoque_novo", "variacao_percentual"]


def test_com_a_confirmacao_e_variacao_dentro_do_limite_nada_e_registrado():
    assert verificar(1500, 1531, 20, True) is None


def test_o_limite_vem_do_parametro():
    assert falha_de(600, 1000, limite=20).categoria == ESTOQUE_IMPLAUSIVEL  # -40%
    assert verificar(600, 1000, 50, False) is None  # o mesmo -40% passa com limite de 50%
    assert verificar(500, 1000, 50, False) is None  # exatamente 50%
    assert falha_de(499, 1000, limite=50).categoria == ESTOQUE_IMPLAUSIVEL


def test_o_motivo_mostra_duas_casas_para_nao_contradizer_o_limite_por_arredondamento():
    falha = falha_de(12001, 10000)  # +20,01%: acima de 20%, mas arredondado a 1 casa daria 20,0

    assert "+20,01%" in falha.motivo
    assert "o limite é de 20%" in falha.motivo


# --- Base ausente com retrato anterior (decisão do mantenedor, 18/10/2026) -------------------


def test_sem_base_mas_com_retrato_anterior_falha_e_o_motivo_traz_o_estoque_de_hoje():
    with pytest.raises(FalhaDeColeta) as erro:
        verificar(1531, None, 20, False, exige_base=True)

    assert erro.value.categoria == SEM_BASE_DE_COMPARACAO
    assert "1531" in erro.value.motivo


def test_base_zero_tambem_conta_como_sem_base_quando_a_base_e_exigida():
    with pytest.raises(FalhaDeColeta) as erro:
        verificar(1531, 0, 20, False, exige_base=True)

    assert erro.value.categoria == SEM_BASE_DE_COMPARACAO


def test_com_a_confirmacao_a_falta_de_base_e_aceita_e_registrada_sem_numero_anterior():
    aceita = verificar(1531, None, 20, True, exige_base=True)

    assert aceita == {
        "estoque_anterior": None,
        "estoque_novo": 1531,
        "variacao_percentual": None,
    }
    assert list(aceita) == ["estoque_anterior", "estoque_novo", "variacao_percentual"]


@pytest.mark.parametrize("base", [None, 1531])
def test_estoque_zero_falha_mesmo_com_a_confirmacao_e_a_base_exigida(base):
    assert falha_de(0, base, aceitar=True).categoria == ESTOQUE_VAZIO
    with pytest.raises(FalhaDeColeta) as erro:
        verificar(0, base, 20, True, exige_base=True)
    assert erro.value.categoria == ESTOQUE_VAZIO


def test_com_base_presente_a_exigencia_de_base_nao_muda_nada():
    assert verificar(1500, 1531, 20, False, exige_base=True) is None
    with pytest.raises(FalhaDeColeta) as erro:
        verificar(1100, 1531, 20, False, exige_base=True)
    assert erro.value.categoria == ESTOQUE_IMPLAUSIVEL


def test_sem_exigir_base_o_primeiro_dia_continua_passando():
    assert verificar(1531, None, 20, False, exige_base=False) is None
    assert verificar(1531, None, 20, False) is None  # exige_base é falso por padrão
