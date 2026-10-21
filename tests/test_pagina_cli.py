"""O comando `gerar` ponta a ponta (PAG, contracts/pagina-cli.md)."""

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
