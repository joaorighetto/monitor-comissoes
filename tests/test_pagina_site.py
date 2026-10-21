"""Gravação tudo-ou-nada do site e cópia dos estáticos (PAG, R9; contracts/site.md)."""

import os

import pytest

from monitor_comissoes.erros import FalhaDePagina
from monitor_comissoes.pagina import site


def arquivos_de(pasta):
    return {str(c.relative_to(pasta)).replace("\\", "/") for c in pasta.rglob("*") if c.is_file()}


def test_gravar_cria_a_pasta_e_as_subpastas(tmp_path):
    saida = tmp_path / "site"

    site.gravar({"index.html": b"<html>", "fontes/a.woff2": b"\x00\x01"}, saida)

    assert (saida / "index.html").read_bytes() == b"<html>"
    assert (saida / "fontes" / "a.woff2").read_bytes() == b"\x00\x01"
    assert arquivos_de(saida) == {"index.html", "fontes/a.woff2"}


def test_gravar_sobrescreve_os_seus_e_nao_apaga_outros(tmp_path):
    saida = tmp_path / "site"
    saida.mkdir()
    (saida / "index.html").write_bytes(b"velho")
    (saida / "outro.txt").write_bytes(b"meu")

    site.gravar({"index.html": b"novo"}, saida)

    assert (saida / "index.html").read_bytes() == b"novo"
    assert (saida / "outro.txt").read_bytes() == b"meu"


def test_gravar_duas_vezes_da_os_mesmos_bytes(tmp_path):
    arquivos = {"index.html": "olá".encode(), "itens.csv": b"a;b\r\n"}

    site.gravar(arquivos, tmp_path / "a")
    site.gravar(arquivos, tmp_path / "b")

    for nome in arquivos:
        assert (tmp_path / "a" / nome).read_bytes() == (tmp_path / "b" / nome).read_bytes()


def test_nao_sobra_arquivo_temporario(tmp_path):
    site.gravar({"index.html": b"x", "fontes/a.woff2": b"y"}, tmp_path / "site")

    assert not [n for n in arquivos_de(tmp_path / "site") if n.endswith(".tmp")]


def test_falha_ao_preparar_um_arquivo_nao_grava_nenhum(tmp_path):
    saida = tmp_path / "site"
    saida.mkdir()
    (saida / "fontes").write_bytes(b"sou um arquivo, nao uma pasta")

    with pytest.raises(FalhaDePagina) as erro:
        site.gravar({"index.html": b"x", "fontes/a.woff2": b"y"}, saida)

    assert "não foi possível gravar" in str(erro.value)
    assert not (saida / "index.html").exists()
    assert arquivos_de(saida) == {"fontes"}


def test_falha_na_troca_vira_falha_de_pagina_e_limpa_temporarios(tmp_path, monkeypatch):
    saida = tmp_path / "site"
    chamadas = []
    troca = os.replace

    def troca_que_falha(origem, destino):
        chamadas.append(destino)
        if len(chamadas) == 2:
            raise OSError("disco cheio")
        return troca(origem, destino)

    monkeypatch.setattr(site.os, "replace", troca_que_falha)

    with pytest.raises(FalhaDePagina) as erro:
        site.gravar({"a.html": b"1", "b.html": b"2", "c.html": b"3"}, saida)

    assert "não foi possível gravar" in str(erro.value) and "disco cheio" in str(erro.value)
    assert not [n for n in arquivos_de(saida) if n.endswith(".tmp")]


@pytest.mark.parametrize("nome", ["../fora.html", "/absoluto.html", "a/../../b.html", ""])
def test_caminho_que_sai_da_pasta_falha(tmp_path, nome):
    with pytest.raises(FalhaDePagina):
        site.gravar({nome: b"x"}, tmp_path / "site")


def test_dicionario_vazio_falha(tmp_path):
    with pytest.raises(FalhaDePagina):
        site.gravar({}, tmp_path / "site")


def test_estaticos_trazem_o_css_e_as_quatro_fontes():
    estaticos = site.copiar_estaticos()

    assert "estilo.css" in estaticos
    fontes = [n for n in estaticos if n.startswith("fontes/")]
    assert len(fontes) == 4 and all(n.endswith(".woff2") for n in fontes)
    assert "LEIAME.md" not in estaticos
    assert all(isinstance(v, bytes) and v for v in estaticos.values())


# ---------- ativos estáticos ausentes (revisão) ----------


def estaticos_em(tmp_path, monkeypatch, *, css=True, js=True, fontes=4):
    pasta = tmp_path / "estatico"
    (pasta / "fontes").mkdir(parents=True)
    if css:
        (pasta / "estilo.css").write_bytes(b"css")
    if js:
        (pasta / "pagina.js").write_bytes(b"js")
    for i in range(fontes):
        (pasta / "fontes" / f"f{i}.woff2").write_bytes(b"fonte")
    monkeypatch.setattr(site, "ESTATICO", pasta)


def test_estaticos_completos_de_uma_pasta_trocada(tmp_path, monkeypatch):
    estaticos_em(tmp_path, monkeypatch)

    assert set(site.copiar_estaticos()) == {
        "estilo.css",
        "pagina.js",
        *(f"fontes/f{i}.woff2" for i in range(4)),
    }


@pytest.mark.parametrize(
    ("faltando", "trecho"),
    [({"css": False}, "estilo.css"), ({"js": False}, "pagina.js"), ({"fontes": 3}, "fontes")],
)
def test_ativo_estatico_ausente_e_falha_nunca_pagina_sem_estilo(
    tmp_path, monkeypatch, faltando, trecho
):
    estaticos_em(tmp_path, monkeypatch, **faltando)

    with pytest.raises(FalhaDePagina) as erro:
        site.copiar_estaticos()

    assert trecho in str(erro.value)


def test_estaticos_trazem_o_javascript_da_pagina():
    assert site.copiar_estaticos()["pagina.js"].startswith(b"/* Monitor de comiss")
