"""Execução diária (AGE): caminho feliz, falhas, plausibilidade, tentativas e reexecução."""

import json
from datetime import datetime, timedelta

import pytest

from monitor_comissoes.coleta import coletar, executar
from monitor_comissoes.config import Config
from monitor_comissoes.diaria import main
from monitor_comissoes.estoque import BRASILIA as FUSO
from monitor_comissoes.saida import serializar

CONFIG_BASE = 'comissoes = ["CE", "CREDN"]\nano_minimo = 2003\n'


class Relogio:
    """Relógio de teste: devolve sempre o mesmo instante, ou avança `passo` a cada leitura."""

    def __init__(self, inicio: datetime, passo: timedelta = timedelta(0)):
        self.momento = inicio
        self.passo = passo
        self.leituras = 0

    def __call__(self) -> datetime:
        atual = self.momento
        self.momento += self.passo
        self.leituras += 1
        return atual


class Dormidas:
    """`dormir` falso: só registra os segundos pedidos."""

    def __init__(self):
        self.pedidos: list[float] = []

    def __call__(self, segundos: float) -> None:
        self.pedidos.append(segundos)


@pytest.fixture
def caminhos(tmp_path):
    (tmp_path / "config.toml").write_text(CONFIG_BASE, encoding="utf-8")
    return {
        "config": tmp_path / "config.toml",
        "atual": tmp_path / "data" / "atual.json",
        "status": tmp_path / "data" / "status.json",
    }


def executar_main(caminhos, transporte, relogio, dormir=None, *, aceitar=False):
    argumentos = [
        "executar",
        "--config",
        str(caminhos["config"]),
        "--atual",
        str(caminhos["atual"]),
        "--status",
        str(caminhos["status"]),
    ]
    if aceitar:
        argumentos.append("--aceitar-variacao")
    return main(argumentos, transporte=transporte, relogio=relogio, dormir=dormir or Dormidas())


def ler(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


# --- US1: caminho feliz ------------------------------------------------------------------------


def test_sucesso_grava_atual_identico_ao_da_coleta_e_status_ok(
    caminhos, transporte, agora, tmp_path
):
    esperado = tmp_path / "esperado" / "atual.json"
    executar(Config(("CE", "CREDN"), 2003), transporte, agora, esperado)
    coletado = coletar(Config(("CE", "CREDN"), 2003), transporte, agora)

    codigo = executar_main(caminhos, transporte, Relogio(agora))

    assert codigo == 0
    assert caminhos["atual"].read_text(encoding="utf-8") == esperado.read_text(encoding="utf-8")
    status = ler(caminhos["status"])
    meta = ler(caminhos["atual"])["meta"]
    assert status["resultado"] == "ok"
    assert status["tentativas"] == 1
    assert status["falha"] is None
    assert status["variacao_aceita"] is None
    assert status["ultimo_retrato_bom"] == {
        "gerado_em": meta["gerado_em"],
        "dados_camara_em": meta["dados_camara_em"],
        "total_itens": meta["total_itens"],
        "estoque_bruto": coletado.estoque_bruto,
    }
    assert status["verificado_em"] == agora.isoformat(timespec="seconds")
    assert status["data_referencia"] == "2026-10-18"


def test_sucesso_imprime_a_linha_de_resumo(caminhos, transporte, agora, capsys):
    coletado = coletar(Config(("CE", "CREDN"), 2003), transporte, agora)
    dia = coletado.dados_camara_em.astimezone(FUSO).strftime("%d/%m/%Y")

    codigo = executar_main(caminhos, transporte, Relogio(agora))

    assert codigo == 0
    saida = capsys.readouterr().out
    total = len(coletado.documento["itens"])
    assert saida == (
        f"OK: {total} itens · estoque bruto {coletado.estoque_bruto} · tentativas 1"
        f" · dados da Câmara de {dia}\n"
    )


def test_primeiro_dia_cria_a_pasta_data_e_os_dois_arquivos(caminhos, transporte, agora):
    assert not caminhos["atual"].parent.exists()

    assert executar_main(caminhos, transporte, Relogio(agora)) == 0

    assert caminhos["atual"].exists()
    assert caminhos["status"].exists()
    assert sorted(p.name for p in caminhos["atual"].parent.iterdir()) == [
        "atual.json",
        "status.json",
    ]


def test_lista_identica_a_anterior_ainda_grava_os_dois_arquivos(caminhos, transporte, agora):
    executar_main(caminhos, transporte, Relogio(agora))
    antes_atual = ler(caminhos["atual"])
    antes_status = ler(caminhos["status"])

    assert executar_main(caminhos, transporte, Relogio(agora + timedelta(hours=2))) == 0

    depois_atual = ler(caminhos["atual"])
    depois_status = ler(caminhos["status"])
    assert [i["id"] for i in depois_atual["itens"]] == [i["id"] for i in antes_atual["itens"]]
    assert depois_atual["meta"]["gerado_em"] != antes_atual["meta"]["gerado_em"]
    assert depois_status["verificado_em"] != antes_status["verificado_em"]


def test_mesmo_relogio_gera_arquivos_identicos_byte_a_byte(tmp_path, transporte, agora):
    resultados = []
    for nome in ("a", "b"):
        pasta = tmp_path / nome
        pasta.mkdir()
        (pasta / "config.toml").write_text(CONFIG_BASE, encoding="utf-8")
        caminhos = {
            "config": pasta / "config.toml",
            "atual": pasta / "data" / "atual.json",
            "status": pasta / "data" / "status.json",
        }
        assert executar_main(caminhos, transporte, Relogio(agora)) == 0
        resultados.append((caminhos["atual"].read_bytes(), caminhos["status"].read_bytes()))

    assert resultados[0] == resultados[1]


def test_mensagem_de_sucesso(caminhos, transporte, agora, capsys):
    executar_main(caminhos, transporte, Relogio(agora))
    capsys.readouterr()
    coletado = coletar(Config(("CE", "CREDN"), 2003), transporte, agora)

    codigo = main(["mensagem", "--status", str(caminhos["status"])])

    assert codigo == 0
    total = len(coletado.documento["itens"])
    assert capsys.readouterr().out == (
        f"dados: 2026-10-18 · ok · {total} itens · estoque bruto {coletado.estoque_bruto}\n"
    )


def test_mensagem_sem_status_ou_com_status_invalido_sai_com_1(caminhos, capsys):
    assert main(["mensagem", "--status", str(caminhos["status"])]) == 1
    assert "status" in capsys.readouterr().err

    caminhos["status"].parent.mkdir(parents=True)
    caminhos["status"].write_text("{ não é json", encoding="utf-8")
    assert main(["mensagem", "--status", str(caminhos["status"])]) == 1
    assert "status" in capsys.readouterr().err


def test_serializacao_do_status_e_do_atual_usa_o_mesmo_formato(caminhos, transporte, agora):
    executar_main(caminhos, transporte, Relogio(agora))

    for arquivo in ("atual", "status"):
        assert caminhos[arquivo].read_text(encoding="utf-8") == serializar(ler(caminhos[arquivo]))
