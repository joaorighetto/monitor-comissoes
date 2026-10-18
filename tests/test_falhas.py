"""Cada categoria de falha termina com erro, motivo e o atual.json anterior intacto."""

import csv
import io
import json
import os
import tempfile
from datetime import UTC, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import pytest

from conftest import FIXTURES, RespostaFalsa
from monitor_comissoes import coleta
from monitor_comissoes.cli import main
from monitor_comissoes.erros import FONTE_INDISPONIVEL, FalhaDeColeta
from monitor_comissoes.transporte import TransporteHttp

CONFIG_REPO = Path(__file__).parent.parent / "config.toml"
SENTINELA = '{"sentinela": true}\n'


def rodar(tmp_path, transporte, agora, config=CONFIG_REPO, com_anterior=True):
    saida = tmp_path / "data" / "atual.json"
    if com_anterior:
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(SENTINELA, encoding="utf-8")
    codigo = main(
        ["--config", str(config), "--saida", str(saida)], transporte=transporte, agora=agora
    )
    return codigo, saida


def verificar_falha(capsys, codigo, saida, categoria, *trechos, com_anterior=True):
    erro = capsys.readouterr().err
    assert codigo == 1
    assert erro.startswith(f"FALHA [{categoria}]: "), erro
    for trecho in trechos:
        assert trecho in erro, erro
    if com_anterior:
        assert saida.read_bytes() == SENTINELA.encode()  # idêntico byte a byte
    else:
        assert not saida.exists()
    assert [p.name for p in saida.parent.glob("*")] in ([saida.name], [])  # sem .tmp


def reescrever_csv(corpo: bytes, alterar) -> bytes:
    leitor = csv.reader(io.StringIO(corpo.decode("utf-8-sig"), newline=""), delimiter=";")
    linhas = alterar([linha for linha in leitor])
    saida = io.StringIO(newline="")
    csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n").writerows(linhas)
    return saida.getvalue().encode("utf-8-sig")


def sem_coluna(nome):
    def alterar(linhas):
        i = linhas[0].index(nome)
        return [[v for k, v in enumerate(linha) if k != i] for linha in linhas]

    return lambda corpo: reescrever_csv(corpo, alterar)


# --- uma falha por categoria --------------------------------------------------------------


def test_fonte_indisponivel(tmp_path, transporte, agora, capsys):
    transporte.erro["proposicoes-2010.csv"] = FalhaDeColeta(
        FONTE_INDISPONIVEL, "proposicoes-2010.csv: HTTP 503"
    )

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "fonte_indisponivel", "proposicoes-2010.csv", "503")


def test_arquivo_ausente_404(tmp_path, transporte, agora, capsys):
    transporte.erro["proposicoesAutores-2012.csv"] = FalhaDeColeta(
        FONTE_INDISPONIVEL, "proposicoesAutores-2012.csv: HTTP 404"
    )

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "fonte_indisponivel", "404")


@pytest.mark.parametrize("arquivo", ["proposicoes-2020.csv", "proposicoesAutores-2020.csv"])
def test_formato_alterado_por_coluna_ausente(tmp_path, transporte, agora, capsys, arquivo):
    coluna = "ultimoStatus_dataHora" if arquivo.startswith("proposicoes-") else "siglaPartidoAutor"
    transporte.transformar[arquivo] = sem_coluna(coluna)

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "formato_alterado", f"coluna {coluna}", arquivo)


def test_arquivos_desatualizados(tmp_path, transporte, agora, capsys):
    transporte.last_modified["proposicoes-2021.csv"] = agora - timedelta(hours=36, minutes=1)

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(
        capsys, codigo, saida, "arquivos_desatualizados", "a Câmara não atualizou os arquivos"
    )


def test_exatamente_36_horas_ainda_e_aceito(tmp_path, transporte, capsys):
    # O arquivo mais antigo passa a ter 1 hora a menos que o mais antigo do manifesto, e o
    # relógio é fixado em exatamente 36 horas depois dele (a dispersão fica abaixo de 6 horas).
    manifesto = json.loads((FIXTURES / "manifesto.json").read_text(encoding="utf-8"))["arquivos"]
    mais_antigo = min(
        parsedate_to_datetime(a["last_modified"]).astimezone(UTC) for a in manifesto.values()
    )
    transporte.last_modified["proposicoes-2021.csv"] = mais_antigo - timedelta(hours=1)
    agora = mais_antigo - timedelta(hours=1) + timedelta(hours=36)

    codigo, saida = rodar(tmp_path, transporte, agora)

    assert codigo == 0
    assert saida.read_bytes() != SENTINELA.encode()


def test_arquivo_so_com_cabecalho(tmp_path, transporte, agora, capsys):
    transporte.transformar["proposicoes-2018.csv"] = lambda corpo: reescrever_csv(
        corpo, lambda linhas: linhas[:1]
    )

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "arquivo_incompleto", "proposicoes-2018.csv")


def test_ultima_linha_incompleta(tmp_path, transporte, agora, capsys):
    transporte.transformar["proposicoes-2022.csv"] = lambda corpo: corpo.rstrip(b"\r\n")[:-60]

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "arquivo_incompleto", "proposicoes-2022.csv")


def test_api_de_deputados_fora_do_ar_nao_baixa_nenhum_arquivo(tmp_path, transporte, agora, capsys):
    transporte.erro["deputados"] = FalhaDeColeta(FONTE_INDISPONIVEL, "deputados: HTTP 503")

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "api_deputados", "deputados do NOVO")
    assert transporte.arquivos_pedidos() == []


def test_estoque_vazio(tmp_path, transporte, agora, capsys):
    config = tmp_path / "config-sem-itens.toml"
    config.write_text(
        'comissoes = ["COMISSAO-QUE-NAO-EXISTE"]\nano_minimo = 2003\n', encoding="utf-8"
    )

    codigo, saida = rodar(tmp_path, transporte, agora, config=config)

    verificar_falha(capsys, codigo, saida, "estoque_vazio", "nenhum item")


def test_configuracao_invalida_falha_antes_de_qualquer_pedido(tmp_path, transporte, agora, capsys):
    config = tmp_path / "config-invalida.toml"
    config.write_text("comissoes = []\nano_minimo = 2003\n", encoding="utf-8")

    codigo, saida = rodar(tmp_path, transporte, agora, config=config)

    verificar_falha(capsys, codigo, saida, "configuracao", "comissoes")
    assert transporte.pedidos == []


# --- integridade --------------------------------------------------------------------------


def test_excecao_inesperada_vira_falha_interna_e_preserva_o_arquivo(
    tmp_path, transporte, agora, capsys, monkeypatch
):
    def explode(*args, **kwargs):
        raise ValueError("falha de programação")

    monkeypatch.setattr(coleta, "baixar_lote", explode)

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "interna", "ValueError", "falha de programação")


def test_falha_na_troca_do_arquivo_preserva_o_anterior_e_nao_deixa_tmp(
    tmp_path, transporte, agora, capsys, monkeypatch
):
    def falha(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", falha)

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "interna", "disco cheio")


def test_primeira_execucao_com_falha_nao_cria_o_arquivo(tmp_path, transporte, agora, capsys):
    transporte.erro["deputados"] = FalhaDeColeta(FONTE_INDISPONIVEL, "deputados: HTTP 503")

    codigo, saida = rodar(tmp_path, transporte, agora, com_anterior=False)

    verificar_falha(capsys, codigo, saida, "api_deputados", com_anterior=False)


def test_diretorio_temporario_e_apagado_em_sucesso_e_em_falha(
    tmp_path, transporte, agora, monkeypatch
):
    temporarios = tmp_path / "temporarios"
    temporarios.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporarios))

    codigo, _ = rodar(tmp_path, transporte, agora)
    assert codigo == 0
    assert list(temporarios.iterdir()) == []

    transporte.transformar["proposicoes-2018.csv"] = lambda corpo: b""
    codigo, _ = rodar(tmp_path, transporte, agora)
    assert codigo == 1
    assert list(temporarios.iterdir()) == []


def test_ordem_de_verificacao_deputados_antes_do_lote_e_frescor_antes_do_calculo(
    tmp_path, transporte, agora
):
    transporte.last_modified["proposicoes-2021.csv"] = agora - timedelta(hours=40)

    rodar(tmp_path, transporte, agora)

    # Os pedidos da API vêm antes de qualquer arquivo em lote.
    assert transporte.pedidos[0].endswith("siglaPartido=NOVO&itens=100")
    assert all(url.endswith(".csv") for url in transporte.pedidos[1:])


# --- ponta a ponta com o TransporteHttp real (apenas `abrir` é falso) ----------------------


def abrir_da_camara(arquivo_cortado=None):
    """Serve as fixtures por HTTP falso; `arquivo_cortado` é anunciado maior do que o corpo."""
    manifesto = json.loads((FIXTURES / "manifesto.json").read_text(encoding="utf-8"))["arquivos"]

    def abrir(requisicao, timeout=None):
        url = requisicao.full_url
        if "/deputados" in url:
            corpo = (FIXTURES / "deputados-novo.json").read_bytes()
            return RespostaFalsa(corpo, {"X-Total-Count": "5"})
        nome = url.rsplit("/", 1)[1]
        corpo = (FIXTURES / nome).read_bytes()
        anunciado = len(corpo) + 500 if nome == arquivo_cortado else len(corpo)
        cabecalhos = {
            "Content-Length": str(anunciado),
            "Last-Modified": manifesto[nome]["last_modified"],
        }
        return RespostaFalsa(corpo, cabecalhos)

    return abrir


def test_download_cortado_pelo_transporte_real_falha_e_preserva_o_arquivo(tmp_path, agora, capsys):
    transporte = TransporteHttp(
        abrir=abrir_da_camara("proposicoes-2020.csv"), dormir=lambda s: None
    )

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "arquivo_incompleto", "proposicoes-2020.csv")


def test_mesmo_transporte_sem_o_corte_gera_o_arquivo(tmp_path, agora, capsys):
    transporte = TransporteHttp(abrir=abrir_da_camara(), dormir=lambda s: None)

    codigo, saida = rodar(tmp_path, transporte, agora)

    assert codigo == 0
    assert json.loads(saida.read_text(encoding="utf-8"))["meta"]["total_itens"] > 0


# --- consistência entre os arquivos (regra de 6 horas) -------------------------------------


def last_modified_mais_antigo():
    manifesto = json.loads((FIXTURES / "manifesto.json").read_text(encoding="utf-8"))["arquivos"]
    return min(
        parsedate_to_datetime(a["last_modified"]).astimezone(UTC) for a in manifesto.values()
    )


def test_arquivos_gerados_em_momentos_diferentes(tmp_path, transporte, agora, capsys):
    # Um arquivo de ontem e o resto de hoje: nenhum passa de 36 horas, mas a lista seria mista.
    transporte.last_modified["proposicoes-2021.csv"] = last_modified_mais_antigo() + timedelta(
        hours=6, minutes=1
    )

    codigo, saida = rodar(tmp_path, transporte, agora)

    verificar_falha(capsys, codigo, saida, "arquivos_desatualizados", "momentos diferentes")


def test_diferenca_de_6_horas_entre_os_arquivos_ainda_e_aceita(tmp_path, transporte, agora):
    transporte.last_modified["proposicoes-2021.csv"] = last_modified_mais_antigo() + timedelta(
        hours=6
    )

    codigo, _ = rodar(tmp_path, transporte, agora)

    assert codigo == 0
