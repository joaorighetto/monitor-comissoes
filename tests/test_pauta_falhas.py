"""Falha visível da checagem da pauta (User Story 6, FR-022 a FR-024).

Em toda falha: saída 1, `FALHA [categoria]: motivo` no stderr, `data/pautas/` intocada, o
`status-pauta.json` com a falha e a última checagem boa, e os arquivos da coleta intocados.
"""

import json

import pytest

from monitor_comissoes.pauta.cli import main
from monitor_comissoes.saida import serializar
from pauta_sinteticos import (
    API,
    PAUTA,
    arquivo_do_dia,
    evento,
    falha_http,
    item_pauta,
    itens_reais,
    lista_eventos,
    pauta,
    reuniao_gravada,
)
from test_pauta_cli import (
    JANELA_CREDN,
    MANHA,
    TARDE,
    foto_da_coleta,
    ler,
    preparar_ambiente,
    transporte_do_dia,
)

JANELA_CE = "eventos/2009-2026-10-17-2026-10-31"


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return preparar_ambiente(tmp_path)


def foto_das_pautas(raiz):
    pasta = raiz / "data" / "pautas"
    if not pasta.exists():
        return None
    return {p.name: p.read_bytes() for p in pasta.iterdir()}


def gravar_pauta(raiz, documento):
    pasta = raiz / "data" / "pautas"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{documento['meta']['data']}.json").write_text(
        serializar(documento), encoding="utf-8"
    )


def checar_com_falha(raiz, capsys, transporte, categoria, trecho, ultima=None, agora=TARDE):
    """Roda a checagem que deve falhar e confere tudo o que uma falha garante."""
    pautas, coleta = foto_das_pautas(raiz), foto_da_coleta(raiz)

    assert main(["checar"], transporte=transporte, agora=agora) == 1

    saida = capsys.readouterr()
    assert saida.out == ""
    [linha] = saida.err.splitlines()
    assert linha.startswith(f"FALHA [{categoria}]: ")
    motivo = linha.removeprefix(f"FALHA [{categoria}]: ")
    assert trecho in motivo
    assert foto_das_pautas(raiz) == pautas
    assert foto_da_coleta(raiz) == coleta
    assert ler(raiz / "data" / "status-pauta.json") == {
        "versao_formato": 1,
        "resultado": "falha",
        "verificado_em": agora.isoformat(),
        "falha": {"categoria": categoria, "motivo": motivo},
        "ultima_checagem_boa": ultima,
    }
    return motivo


# --- a Câmara -------------------------------------------------------------------------------


def test_eventos_indisponiveis(ambiente, capsys):
    transporte = transporte_do_dia()
    transporte.erro[JANELA_CE] = falha_http(f"{API}/orgaos/2009/eventos", 503)

    checar_com_falha(ambiente, capsys, transporte, "fonte_indisponivel", "/orgaos/2009/eventos")


def test_pauta_indisponivel(ambiente, capsys):
    transporte = transporte_do_dia()
    transporte.erro["pautas/83091"] = falha_http(f"{API}/eventos/83091/pauta", 503)

    checar_com_falha(ambiente, capsys, transporte, "fonte_indisponivel", "/eventos/83091/pauta")


def test_json_invalido(ambiente, capsys):
    transporte = transporte_do_dia()
    transporte.respostas["pautas/83091"] = b'{"dados": ['

    motivo = checar_com_falha(ambiente, capsys, transporte, "formato_alterado", "não é JSON")

    assert motivo.startswith("/eventos/83091/pauta: ")


def test_campo_ausente(ambiente, capsys):
    itens = itens_reais(83091)
    del itens[0]["relator"]
    transporte = transporte_do_dia()
    transporte.respostas["pautas/83091"] = {"dados": itens, "links": []}

    checar_com_falha(ambiente, capsys, transporte, "formato_alterado", "campo relator")


def test_paginacao_incompleta(ambiente, capsys):
    janela = json.loads((PAUTA / f"{JANELA_CE}.json").read_text(encoding="utf-8"))
    transporte = transporte_do_dia()
    transporte.respostas[JANELA_CE] = janela
    transporte.cabecalhos[JANELA_CE] = {"x-total-count": "3"}

    checar_com_falha(
        ambiente, capsys, transporte, "formato_alterado", "anunciou 3 eventos e entregou 2"
    )


def test_a_pauta_de_uma_reuniao_falha_e_a_checagem_inteira_falha(ambiente, capsys):
    # A CREDN tem uma reunião com pauta boa; só a da CE falha, e nada é gravado.
    transporte = transporte_do_dia()
    reuniao_credn = evento(99001, "2026-10-28T10:00", orgao=2018)
    transporte.respostas[JANELA_CREDN] = lista_eventos([reuniao_credn], orgao=2018)
    transporte.cabecalhos[JANELA_CREDN] = {"x-total-count": "1"}
    transporte.respostas["pautas/99001"] = pauta([item_pauta(1)])
    transporte.erro["pautas/83091"] = falha_http(f"{API}/eventos/83091/pauta", 503)

    checar_com_falha(ambiente, capsys, transporte, "fonte_indisponivel", "/eventos/83091/pauta")


def test_deputados_indisponiveis(ambiente, capsys):
    transporte = transporte_do_dia()
    transporte.erro["deputados-novo"] = falha_http(f"{API}/deputados", 503)

    checar_com_falha(ambiente, capsys, transporte, "api_deputados", "deputados do NOVO")


def test_erro_na_busca_de_reuniao_sumida_que_nao_e_404(ambiente, capsys):
    # A reunião 99999 estava convocada na checagem anterior e sumiu da lista; a busca pelo id
    # responde 500. Sem saber o que houve com ela, a checagem não registra nada.
    anterior = arquivo_do_dia(
        "2026-10-23",
        [reuniao_gravada(99999)],
        checada_em="2026-10-23T22:47:30-03:00",
        linha_de_base={"motivo": "primeira checagem"},
    )
    gravar_pauta(ambiente, anterior)
    transporte = transporte_do_dia()
    transporte.erro["eventos/99999"] = falha_http(f"{API}/eventos/99999", 500)

    checar_com_falha(
        ambiente,
        capsys,
        transporte,
        "fonte_indisponivel",
        "/eventos/99999",
        ultima="2026-10-23T22:47:30-03:00",
    )


def test_excecao_inesperada_vira_interna(ambiente, capsys):
    transporte = transporte_do_dia()
    transporte.erro["pautas/83091"] = RuntimeError("defeito simulado")

    motivo = checar_com_falha(ambiente, capsys, transporte, "interna", "defeito simulado")

    assert motivo == "RuntimeError: defeito simulado"


# --- as entradas locais ---------------------------------------------------------------------


def test_indice_ausente(ambiente, capsys):
    (ambiente / "cache" / "indice-autoria.json").unlink()

    checar_com_falha(
        ambiente, capsys, transporte_do_dia(), "entrada_invalida", "indice-autoria.json"
    )


def test_indice_invalido(ambiente, capsys):
    (ambiente / "cache" / "indice-autoria.json").write_text("{", encoding="utf-8")

    checar_com_falha(
        ambiente, capsys, transporte_do_dia(), "entrada_invalida", "indice-autoria.json"
    )


def test_inventario_ausente(ambiente, capsys):
    (ambiente / "data" / "atual.json").unlink()

    checar_com_falha(ambiente, capsys, transporte_do_dia(), "entrada_invalida", "atual.json")


def test_inventario_invalido(ambiente, capsys):
    (ambiente / "data" / "atual.json").write_text('{"meta": {}}\n', encoding="utf-8")

    checar_com_falha(ambiente, capsys, transporte_do_dia(), "entrada_invalida", "atual.json")


def test_arquivo_anterior_ilegivel_nao_vira_linha_de_base(ambiente, capsys):
    pasta = ambiente / "data" / "pautas"
    pasta.mkdir(parents=True)
    (pasta / "2026-10-23.json").write_text('{"meta": ', encoding="utf-8")

    checar_com_falha(ambiente, capsys, transporte_do_dia(), "entrada_invalida", "2026-10-23.json")

    assert sorted(p.name for p in pasta.iterdir()) == ["2026-10-23.json"]


def test_arquivo_com_data_futura(ambiente, capsys):
    gravar_pauta(ambiente, arquivo_do_dia("2026-10-25", checada_em="2026-10-25T05:49:12-03:00"))

    checar_com_falha(ambiente, capsys, transporte_do_dia(), "entrada_invalida", "2026-10-25.json")


def test_configuracao_invalida(ambiente, capsys):
    (ambiente / "config.toml").write_text("comissoes = [\n", encoding="utf-8")

    checar_com_falha(ambiente, capsys, transporte_do_dia(), "configuracao", "config.toml")


# --- a última checagem boa ------------------------------------------------------------------


def test_ultima_checagem_boa_vem_do_status_anterior(ambiente, capsys):
    assert main(["checar"], transporte=transporte_do_dia(), agora=MANHA) == 0
    capsys.readouterr()
    transporte = transporte_do_dia()
    transporte.erro["pautas/83091"] = falha_http(f"{API}/eventos/83091/pauta", 503)

    checar_com_falha(
        ambiente,
        capsys,
        transporte,
        "fonte_indisponivel",
        "/eventos/83091/pauta",
        ultima=MANHA.isoformat(),
    )


def test_sem_status_a_ultima_checagem_boa_vem_do_arquivo_mais_recente(ambiente, capsys):
    assert main(["checar"], transporte=transporte_do_dia(), agora=MANHA) == 0
    capsys.readouterr()
    (ambiente / "data" / "status-pauta.json").unlink()
    transporte = transporte_do_dia()
    transporte.erro["pautas/83091"] = falha_http(f"{API}/eventos/83091/pauta", 503)

    checar_com_falha(
        ambiente,
        capsys,
        transporte,
        "fonte_indisponivel",
        "/eventos/83091/pauta",
        ultima=MANHA.isoformat(),
    )


def test_duas_falhas_seguidas_mantem_a_ultima_checagem_boa(ambiente, capsys):
    assert main(["checar"], transporte=transporte_do_dia(), agora=MANHA) == 0
    capsys.readouterr()
    transporte = transporte_do_dia()
    transporte.erro["deputados-novo"] = falha_http(f"{API}/deputados", 503)
    checar_com_falha(
        ambiente, capsys, transporte, "api_deputados", "NOVO", ultima=MANHA.isoformat()
    )

    checar_com_falha(
        ambiente, capsys, transporte, "api_deputados", "NOVO", ultima=MANHA.isoformat()
    )


# --- a coleta -------------------------------------------------------------------------------


def test_falha_da_coleta_nao_impede_a_checagem(ambiente, capsys):
    status_da_coleta = {
        "versao_formato": 1,
        "resultado": "falha",
        "verificado_em": "2026-10-24T08:30:00-03:00",
        "falha": {"categoria": "fonte_indisponivel", "motivo": "simulada"},
    }
    (ambiente / "data" / "status.json").write_text(json.dumps(status_da_coleta), encoding="utf-8")
    coleta = foto_da_coleta(ambiente)

    assert main(["checar"], transporte=transporte_do_dia(), agora=TARDE) == 0

    assert capsys.readouterr().err == ""
    assert (ambiente / "data" / "pautas" / "2026-10-24.json").exists()
    assert foto_da_coleta(ambiente) == coleta
