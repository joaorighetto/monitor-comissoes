"""CLI da checagem da pauta, ponta a ponta com o transporte falso (contracts/pauta-cli.md)."""

import json
import shutil
from datetime import UTC, datetime, timedelta, timezone

import pytest

from monitor_comissoes.pauta.cli import main
from monitor_comissoes.pauta.regras import proposicao_do_item
from monitor_comissoes.saida import serializar
from pauta_sinteticos import (
    API,
    PAUTA,
    TransportePauta,
    falha_http,
    indice,
    itens_reais,
    lista_eventos,
)

BRASILIA = timezone(timedelta(hours=-3))
MANHA = datetime(2026, 10, 24, 5, 49, 12, tzinfo=BRASILIA)
TARDE = datetime(2026, 10, 24, 15, 17, 2, tzinfo=BRASILIA)
JANELA_CREDN = "eventos/2018-2026-10-17-2026-10-31"
ARQUIVOS_DA_COLETA = ("atual.json", "anterior.json", "status.json", "envio.json")


def indice_das_pautas(*eventos, autorias=None):
    """Índice com todas as proposições das pautas em `[0, []]`, salvo `autorias`."""
    proposicoes = {}
    for id_evento in eventos:
        for item in itens_reais(id_evento):
            proposicao = proposicao_do_item(item)
            if proposicao is not None:
                proposicoes[proposicao["id"]] = (0, [])
    proposicoes.update(autorias or {})
    return indice(proposicoes)


def preparar_ambiente(raiz):
    """Um repositório de mentira: config, dados da coleta e o índice no cache."""
    (raiz / "config.toml").write_text(
        'comissoes = ["CE", "CREDN"]\nano_minimo = 2003\n', encoding="utf-8"
    )
    dados = raiz / "data"
    (dados / "mudancas").mkdir(parents=True)
    shutil.copyfile(PAUTA / "atual.json", dados / "atual.json")
    for nome in ("anterior.json", "status.json", "envio.json"):
        (dados / nome).write_text(f'{{"sentinela": "{nome}"}}\n', encoding="utf-8")
    (dados / "mudancas" / "2026-10-24.json").write_text("{}\n", encoding="utf-8")
    (raiz / "cache").mkdir()
    gravar_indice(raiz, indice_das_pautas(83091))
    return raiz


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return preparar_ambiente(tmp_path)


def gravar_indice(raiz, documento):
    (raiz / "cache" / "indice-autoria.json").write_text(json.dumps(documento), encoding="utf-8")


def transporte_do_dia():
    """A CE com a janela salva de 24/10/2026 (83091) e a CREDN sem eventos."""
    transporte = TransportePauta()
    transporte.respostas[JANELA_CREDN] = lista_eventos([], orgao=2018)
    transporte.cabecalhos[JANELA_CREDN] = {"x-total-count": "0"}
    return transporte


def foto_da_coleta(raiz):
    dados = raiz / "data"
    foto = {
        nome: (dados / nome).read_bytes() if (dados / nome).exists() else None
        for nome in ARQUIVOS_DA_COLETA
    }
    foto["mudancas"] = {p.name: p.read_bytes() for p in (dados / "mudancas").iterdir()}
    return foto


def ler(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


def checar(agora, transporte=None):
    return main(["checar"], transporte=transporte or transporte_do_dia(), agora=agora)


def test_checar_grava_o_arquivo_do_dia_e_o_status(ambiente, capsys):
    antes = foto_da_coleta(ambiente)

    assert checar(MANHA) == 0

    saida = capsys.readouterr()
    assert saida.out == (
        "OK: 1 reunião (CE: 1, CREDN: 0) · linha de base · pauta checada em 24/10 às 05h49\n"
    )
    assert saida.err == ""
    arquivo = ler(ambiente / "data" / "pautas" / "2026-10-24.json")
    assert arquivo["meta"]["linha_de_base"] == {"motivo": "primeira checagem"}
    assert arquivo["checagem"]["checada_em"] == "2026-10-24T05:49:12-03:00"
    [reuniao] = arquivo["checagem"]["reunioes"]
    assert reuniao["id"] == 83091 and len(reuniao["itens"]) == 19
    assert arquivo["checagem"]["lote"] == {"dados_camara_em": "2026-10-24T04:31:37+00:00"}
    assert arquivo["checagem"]["inventario"] == {"gerado_em": "2026-10-24T08:34:13-03:00"}
    assert [d["id"] for d in arquivo["checagem"]["deputados_novo_em_exercicio"]] == [
        156190,
        204365,
        204455,
        204528,
        220633,
    ]
    status = ler(ambiente / "data" / "status-pauta.json")
    assert status == {
        "versao_formato": 1,
        "resultado": "ok",
        "verificado_em": "2026-10-24T05:49:12-03:00",
        "falha": None,
        "ultima_checagem_boa": "2026-10-24T05:49:12-03:00",
    }
    assert (ambiente / "data" / "pautas" / "2026-10-24.json").read_text(
        encoding="utf-8"
    ) == serializar(arquivo)
    assert foto_da_coleta(ambiente) == antes


def test_segunda_checagem_da_mesma_fonte_nao_tem_alteracao_nova(ambiente, capsys):
    assert checar(MANHA) == 0
    capsys.readouterr()

    assert checar(TARDE) == 0

    assert capsys.readouterr().out == (
        "OK: 1 reunião (CE: 1, CREDN: 0) · 0 alterações novas · pauta checada em 24/10 às 15h17\n"
    )
    arquivo = ler(ambiente / "data" / "pautas" / "2026-10-24.json")
    assert arquivo["alteracoes"] == []
    assert arquivo["checagem"]["reunioes"][0]["vista_desde"] == "2026-10-24T05:49:12-03:00"


def _sem_o_item(transporte, ordem):
    itens = [i for i in itens_reais(83091) if i["ordem"] != ordem]
    transporte.respostas["pautas/83091"] = {"dados": itens, "links": []}
    return transporte


def test_alteracao_detectada_e_a_mensagem_do_commit(ambiente, capsys):
    assert checar(MANHA) == 0
    assert main(["mensagem"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        "pauta: 2026-10-24 05:49 · ok · 1 reunião · linha de base"
    )

    assert checar(TARDE, _sem_o_item(transporte_do_dia(), 3)) == 0
    assert capsys.readouterr().out == (
        "OK: 1 reunião (CE: 1, CREDN: 0) · 1 alteração nova · pauta checada em 24/10 às 15h17\n"
    )
    assert main(["mensagem"]) == 0
    assert capsys.readouterr().out == "pauta: 2026-10-24 15:17 · ok · 1 reunião · 1 alteração\n"
    [alteracao] = ler(ambiente / "data" / "pautas" / "2026-10-24.json")["alteracoes"]
    assert alteracao["tipo"] == "item_saiu"


def test_mensagem_de_falha(ambiente, capsys):
    transporte = transporte_do_dia()
    transporte.erro["pautas/83091"] = falha_http(f"{API}/eventos/83091/pauta", 503)
    assert checar(TARDE, transporte) == 1
    capsys.readouterr()

    assert main(["mensagem"]) == 0

    assert capsys.readouterr().out == "pauta: 2026-10-24 15:17 · falha · fonte_indisponivel\n"


def test_mensagem_sem_status_sai_com_1(ambiente, capsys):
    assert main(["mensagem"]) == 1
    assert capsys.readouterr().err.startswith("FALHA [interna]: ")


def test_opcoes_de_caminho(ambiente, capsys):
    outro = ambiente / "outro"
    (outro / "cache").mkdir(parents=True)
    shutil.copyfile(ambiente / "cache" / "indice-autoria.json", outro / "cache" / "i.json")
    shutil.copyfile(ambiente / "data" / "atual.json", outro / "a.json")
    argumentos = [
        "checar",
        "--config",
        str(ambiente / "config.toml"),
        "--pautas",
        str(outro / "pautas"),
        "--status",
        str(outro / "s.json"),
        "--atual",
        str(outro / "a.json"),
        "--indice",
        str(outro / "cache" / "i.json"),
    ]

    assert main(argumentos, transporte=transporte_do_dia(), agora=MANHA) == 0

    assert (outro / "pautas" / "2026-10-24.json").exists()
    assert (outro / "s.json").exists()
    assert not (ambiente / "data" / "pautas").exists()
    mensagem = ["mensagem", "--status", str(outro / "s.json"), "--pautas", str(outro / "pautas")]
    assert main(mensagem) == 0


def test_dia_do_arquivo_e_o_de_brasilia(ambiente):
    # 01:47 UTC do dia 25 ainda é 24/10 em Brasília (checagem da noite, R9).
    noite = datetime(2026, 10, 25, 1, 47, tzinfo=UTC)

    assert checar(noite) == 0

    assert [p.name for p in (ambiente / "data" / "pautas").iterdir()] == ["2026-10-24.json"]
