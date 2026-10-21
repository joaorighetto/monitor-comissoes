import pytest

from monitor_comissoes.config import Config, carregar_config
from monitor_comissoes.erros import CONFIGURACAO, FalhaDeColeta


def escrever(tmp_path, texto):
    caminho = tmp_path / "config.toml"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def test_config_valida(tmp_path):
    caminho = escrever(tmp_path, 'comissoes = ["CE", "CREDN"]\nano_minimo = 2003\n')

    assert carregar_config(caminho, 2026) == Config(("CE", "CREDN"), 2003)


def test_config_do_repositorio_e_valida():
    from pathlib import Path

    raiz = Path(__file__).parent.parent
    config = carregar_config(raiz / "config.toml", 2026)

    assert config.comissoes == ("CE", "CREDN")
    assert config.ano_minimo == 2003


def test_arquivo_ausente(tmp_path):
    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(tmp_path / "nao-existe.toml", 2026)

    assert erro.value.categoria == CONFIGURACAO


@pytest.mark.parametrize(
    ("texto", "campo"),
    [
        ("comissoes = []\nano_minimo = 2003\n", "comissoes"),
        ("ano_minimo = 2003\n", "comissoes"),
        ('comissoes = "CE"\nano_minimo = 2003\n', "comissoes"),
        ('comissoes = ["CE", "CE"]\nano_minimo = 2003\n', "comissoes"),
        ('comissoes = ["CE", ""]\nano_minimo = 2003\n', "comissoes"),
        ('comissoes = ["CE", 7]\nano_minimo = 2003\n', "comissoes"),
        ('comissoes = [" CE"]\nano_minimo = 2003\n', "comissoes"),
        ('comissoes = ["CE "]\nano_minimo = 2003\n', "comissoes"),
        ('comissoes = ["CE"]\n', "ano_minimo"),
        ('comissoes = ["CE"]\nano_minimo = "2003"\n', "ano_minimo"),
        ('comissoes = ["CE"]\nano_minimo = 2003.5\n', "ano_minimo"),
        ('comissoes = ["CE"]\nano_minimo = true\n', "ano_minimo"),
        ('comissoes = ["CE"]\nano_minimo = 1989\n', "ano_minimo"),
        ('comissoes = ["CE"]\nano_minimo = 2027\n', "ano_minimo"),
    ],
)
def test_valores_invalidos_nomeiam_o_campo(tmp_path, texto, campo):
    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, texto), 2026)

    assert erro.value.categoria == CONFIGURACAO
    assert campo in erro.value.motivo


def test_toml_malformado(tmp_path):
    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, "comissoes = ["), 2026)

    assert erro.value.categoria == CONFIGURACAO


def test_limites_do_ano_minimo(tmp_path):
    assert carregar_config(escrever(tmp_path, 'comissoes = ["CE"]\nano_minimo = 1990\n'), 2026)
    assert carregar_config(escrever(tmp_path, 'comissoes = ["CE"]\nano_minimo = 2026\n'), 2026)


# --- Tabela [execucao] (AGE) ---------------------------------------------------------------

BASE = 'comissoes = ["CE"]\nano_minimo = 2003\n'


def test_sem_a_tabela_execucao_valem_os_padroes(tmp_path):
    config = carregar_config(escrever(tmp_path, BASE), 2026)

    assert (config.tentativas, config.espera_minutos, config.limite_variacao_percentual) == (
        4,
        30,
        20,
    )


def test_tabela_execucao_completa_e_lida(tmp_path):
    texto = BASE + (
        "[execucao]\ntentativas = 2\nespera_minutos = 5\nlimite_variacao_percentual = 50\n"
    )

    config = carregar_config(escrever(tmp_path, texto), 2026)

    assert (config.tentativas, config.espera_minutos, config.limite_variacao_percentual) == (
        2,
        5,
        50,
    )


@pytest.mark.parametrize(
    ("campo", "valores_validos", "valores_invalidos"),
    [
        ("tentativas", (1, 10), (0, 11)),  # Entre 1 e 10
        ("espera_minutos", (0, 120), (-1, 121)),  # Entre 0 e 120
        ("limite_variacao_percentual", (1, 100), (0, 101)),  # Entre 1 e 100
    ],
)
def test_limites_dos_campos_de_execucao(tmp_path, campo, valores_validos, valores_invalidos):
    for valor in valores_validos:
        texto = BASE + f"[execucao]\n{campo} = {valor}\n"
        assert carregar_config(escrever(tmp_path, texto), 2026)
    for valor in valores_invalidos:
        texto = BASE + f"[execucao]\n{campo} = {valor}\n"
        with pytest.raises(FalhaDeColeta) as erro:
            carregar_config(escrever(tmp_path, texto), 2026)
        assert erro.value.categoria == CONFIGURACAO
        assert f"execucao.{campo}" in erro.value.motivo


@pytest.mark.parametrize("valor", ['"4"', "4.5", "true"])
@pytest.mark.parametrize("campo", ["tentativas", "espera_minutos", "limite_variacao_percentual"])
def test_campo_de_execucao_que_nao_e_inteiro_falha(tmp_path, campo, valor):
    texto = BASE + f"[execucao]\n{campo} = {valor}\n"

    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, texto), 2026)

    assert erro.value.categoria == CONFIGURACAO
    assert f"execucao.{campo}" in erro.value.motivo


def test_chave_desconhecida_em_execucao_falha(tmp_path):
    texto = BASE + "[execucao]\ntentativa = 3\n"

    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, texto), 2026)

    assert erro.value.categoria == CONFIGURACAO
    assert "tentativa" in erro.value.motivo


def test_execucao_que_nao_e_tabela_falha(tmp_path):
    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, 'execucao = "x"\n' + BASE), 2026)

    assert erro.value.categoria == CONFIGURACAO
    assert "execucao" in erro.value.motivo


def test_os_valores_de_execucao_do_config_toml_sao_os_padroes():
    from pathlib import Path

    from monitor_comissoes.config import PADROES

    raiz = Path(__file__).parent.parent
    config = carregar_config(raiz / "config.toml", 2026)

    assert {
        "tentativas": config.tentativas,
        "espera_minutos": config.espera_minutos,
        "limite_variacao_percentual": config.limite_variacao_percentual,
    } == PADROES


# --- AVI: tabela [aviso] ---------------------------------------------------------------------

BASE = 'comissoes = ["CE", "CREDN"]\nano_minimo = 2003\n'


def test_sem_a_tabela_aviso_valem_os_padroes(tmp_path):
    config = carregar_config(escrever(tmp_path, BASE), 2026)

    assert config.pagina_url == ""
    assert config.repositorio == "joaorighetto/monitor-comissoes"


def test_aviso_le_pagina_e_repositorio(tmp_path):
    texto = (
        BASE + '[aviso]\npagina_url = "https://exemplo.github.io/monitor"\nrepositorio = "a/b"\n'
    )

    config = carregar_config(escrever(tmp_path, texto), 2026)

    assert config.pagina_url == "https://exemplo.github.io/monitor"
    assert config.repositorio == "a/b"


@pytest.mark.parametrize(
    "linha",
    [
        'pagina_url = "http://exemplo.com"',
        'pagina_url = " https://exemplo.com"',
        "pagina_url = 3",
        "repositorio = 3",
        'repositorio = ""',
        'repositorio = "semBarra"',
        'repositorio = "a/b/c"',
        'repositorio = "a/"',
        'repositorio = "/b"',
    ],
)
def test_aviso_com_valor_invalido_falha(tmp_path, linha):
    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, BASE + f"[aviso]\n{linha}\n"), 2026)

    assert erro.value.categoria == CONFIGURACAO
    assert "aviso." in erro.value.motivo


def test_chave_desconhecida_em_aviso_falha(tmp_path):
    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, BASE + "[aviso]\nchat = 1\n"), 2026)

    assert "aviso.chat" in erro.value.motivo


def test_aviso_que_nao_e_tabela_falha(tmp_path):
    with pytest.raises(FalhaDeColeta) as erro:
        carregar_config(escrever(tmp_path, "aviso = 3\n" + BASE), 2026)

    assert "aviso" in erro.value.motivo
