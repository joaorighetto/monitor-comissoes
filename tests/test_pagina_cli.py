"""O comando `gerar` ponta a ponta (PAG, contracts/pagina-cli.md)."""

import json
import shutil

import pytest

import pagina_sinteticos as p
from monitor_comissoes.pagina import cli
from pagina_dom import parse
from pagina_sinteticos import FIXTURES

ATUAL = FIXTURES / "atual-real.json"
STATUS = FIXTURES / "status-ok.json"


def gerar(saida, *extras, atual=ATUAL, status=STATUS):
    return cli.main(
        ["gerar", "--atual", str(atual), "--status", str(status), "--saida", str(saida), *extras]
    )


def arquivos_de(pasta):
    return {
        str(c.relative_to(pasta)).replace("\\", "/"): c.read_bytes()
        for c in pasta.rglob("*")
        if c.is_file()
    }


def test_gerar_imprime_o_resumo_e_grava_o_site(tmp_path, capsys):
    saida = tmp_path / "site"

    codigo = gerar(saida)

    assert codigo == 0
    linha = capsys.readouterr().out.strip()
    assert linha == (
        f"OK: página gerada com 105 itens · dados da Câmara de 20/10 · 4 dias de mudanças · {saida}"
    )
    nomes = set(arquivos_de(saida))
    assert {"index.html", "estilo.css", "pagina.js"} <= nomes
    assert len([n for n in nomes if n.startswith("fontes/")]) == 4


def test_o_numero_de_itens_da_pagina_e_o_total_do_retrato(tmp_path):
    saida = tmp_path / "site"
    gerar(saida)

    doc = parse((saida / "index.html").read_text(encoding="utf-8"))

    assert len(doc.achar(tag="li", classe="item")) == 105


def test_duas_execucoes_dao_arquivos_identicos_byte_a_byte(tmp_path):
    gerar(tmp_path / "a")
    gerar(tmp_path / "b")

    assert arquivos_de(tmp_path / "a") == arquivos_de(tmp_path / "b")


def test_o_index_do_retrato_real_cabe_em_400_mil_bytes(tmp_path):
    gerar(tmp_path / "site")

    assert len((tmp_path / "site" / "index.html").read_bytes()) < 400_000


def test_regerar_na_mesma_pasta_nao_muda_nada(tmp_path):
    saida = tmp_path / "site"
    gerar(saida)
    antes = arquivos_de(saida)

    assert gerar(saida) == 0
    assert arquivos_de(saida) == antes


def test_sem_pasta_de_mudancas_a_pagina_sai_com_zero_dias(tmp_path, capsys):
    entradas = p.gravar_entradas(tmp_path / "entradas", p.retrato_real(), p.status_real())

    codigo = cli.main(["gerar", "--atual", str(entradas.atual), "--saida", str(tmp_path / "site")])

    assert codigo == 0
    assert "0 dias de mudanças" in capsys.readouterr().out


# ---------- falhas: nada é escrito (SC-009) ----------


def copia_das_entradas(tmp_path):
    """O `atual.json`, o `status.json` e as mudanças reais, copiados para uma pasta editável."""
    pasta = tmp_path / "entradas"
    shutil.copytree(FIXTURES / "mudancas", pasta / "mudancas")
    shutil.copy(ATUAL, pasta / "atual.json")
    shutil.copy(STATUS, pasta / "status.json")
    return pasta


def com_atual_alterado(pasta, alterar):
    documento = json.loads((pasta / "atual.json").read_text(encoding="utf-8"))
    alterar(documento)
    (pasta / "atual.json").write_text(json.dumps(documento), encoding="utf-8")


def sem_atual(pasta):
    (pasta / "atual.json").unlink()


def sem_status(pasta):
    (pasta / "status.json").unlink()


def json_invalido(pasta):
    (pasta / "status.json").write_text("{ nada", encoding="utf-8")


def versao_4(pasta):
    shutil.copy(FIXTURES / "atual-formato-4.json", pasta / "atual.json")


def lista_vazia(pasta):
    com_atual_alterado(pasta, lambda d: (d.update(itens=[]), d["meta"].update(total_itens=0)))


def total_diferente(pasta):
    com_atual_alterado(pasta, lambda d: d["meta"].update(total_itens=104))


def status_de_outro_retrato(pasta):
    shutil.copy(FIXTURES / "status-retrato-outro.json", pasta / "status.json")


def falha_sem_retrato_bom(pasta):
    shutil.copy(FIXTURES / "status-falha-sem-retrato.json", pasta / "status.json")


def mudancas_corrompidas(pasta):
    (pasta / "mudancas" / "2026-10-18.json").write_text("{ corrompido", encoding="utf-8")


def link_de_fora(pasta):
    com_atual_alterado(pasta, lambda d: d["itens"][4].update(link="https://exemplo.com/x"))


CASOS_DE_FALHA = [
    (sem_atual, "atual.json"),
    (sem_status, "status.json"),
    (json_invalido, "status.json"),
    (versao_4, "versao_formato"),
    (lista_vazia, "itens"),
    (total_diferente, "total_itens"),
    (status_de_outro_retrato, "ultimo_retrato_bom"),
    (falha_sem_retrato_bom, "ultimo_retrato_bom"),
    (mudancas_corrompidas, "2026-10-18.json"),
    (link_de_fora, "link oficial"),
]


@pytest.mark.parametrize(
    ("estragar", "trecho"), CASOS_DE_FALHA, ids=lambda x: getattr(x, "__name__", x)
)
def test_entrada_ruim_falha_com_codigo_1_e_nao_cria_a_saida(tmp_path, capsys, estragar, trecho):
    pasta = copia_das_entradas(tmp_path)
    estragar(pasta)
    saida = tmp_path / "site"

    codigo = cli.main(["gerar", "--atual", str(pasta / "atual.json"), "--saida", str(saida)])

    assert codigo == 1
    captura = capsys.readouterr()
    assert captura.err.startswith("FALHA [pagina]: ")
    assert trecho in captura.err
    assert captura.out == ""
    assert not saida.exists()


def test_falha_nao_altera_a_pagina_ja_gerada(tmp_path, capsys):
    saida = tmp_path / "site"
    gerar(saida)
    antes = arquivos_de(saida)
    pasta = copia_das_entradas(tmp_path)
    lista_vazia(pasta)

    codigo = cli.main(["gerar", "--atual", str(pasta / "atual.json"), "--saida", str(saida)])

    assert codigo == 1
    assert arquivos_de(saida) == antes


def test_excecao_inesperada_vira_falha_com_o_tipo_e_codigo_1(tmp_path, capsys, monkeypatch):
    def quebra(_pagina):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli.site.html, "renderizar", quebra)
    saida = tmp_path / "site"

    codigo = gerar(saida)

    assert codigo == 1
    assert "FALHA [pagina]: RuntimeError: boom" in capsys.readouterr().err
    assert not saida.exists()


def test_falha_da_coleta_com_retrato_bom_gera_a_pagina_com_a_faixa(tmp_path, capsys):
    saida = tmp_path / "site"

    codigo = gerar(saida, status=FIXTURES / "status-falha.json")

    assert codigo == 0
    doc = parse((saida / "index.html").read_text(encoding="utf-8"))
    assert doc.um(tag="p", id="faixa-erro")
    assert len(doc.achar(tag="li", classe="item")) == 105


def test_argumento_invalido_sai_com_2(capsys):
    with pytest.raises(SystemExit) as saida:
        cli.main(["gerar", "--naoexiste"])

    assert saida.value.code == 2
    with pytest.raises(SystemExit) as sem_comando:
        cli.main([])
    assert sem_comando.value.code == 2
