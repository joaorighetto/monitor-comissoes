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
