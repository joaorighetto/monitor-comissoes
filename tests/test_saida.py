import os

import pytest

from monitor_comissoes.saida import gravar_atomico

ANTERIOR = '{"sentinela": true}\n'


def sobras(pasta):
    return [p.name for p in pasta.iterdir() if p.name != "atual.json"]


def test_cria_a_pasta_e_grava_com_quebra_de_linha_final(tmp_path):
    destino = tmp_path / "data" / "atual.json"

    gravar_atomico({"a": "ação"}, destino)

    texto = destino.read_text(encoding="utf-8")
    assert texto == '{\n  "a": "ação"\n}\n'  # UTF-8 sem escape, 2 espaços, newline final


def test_substitui_o_arquivo_existente(tmp_path):
    destino = tmp_path / "atual.json"
    destino.write_text(ANTERIOR, encoding="utf-8")

    gravar_atomico({"novo": 1}, destino)

    assert '"novo": 1' in destino.read_text(encoding="utf-8")
    assert sobras(tmp_path) == []


def test_erro_na_serializacao_preserva_o_anterior(tmp_path):
    destino = tmp_path / "atual.json"
    destino.write_text(ANTERIOR, encoding="utf-8")

    with pytest.raises(TypeError):
        gravar_atomico({"invalido": {1, 2}}, destino)

    assert destino.read_bytes() == ANTERIOR.encode()
    assert sobras(tmp_path) == []


def test_erro_na_troca_preserva_o_anterior_e_nao_deixa_tmp(tmp_path, monkeypatch):
    destino = tmp_path / "atual.json"
    destino.write_text(ANTERIOR, encoding="utf-8")

    def falha(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", falha)

    with pytest.raises(OSError, match="disco cheio"):
        gravar_atomico({"novo": 1}, destino)

    assert destino.read_bytes() == ANTERIOR.encode()
    assert sobras(tmp_path) == []


def test_primeira_execucao_com_falha_nao_cria_o_arquivo(tmp_path):
    destino = tmp_path / "data" / "atual.json"

    with pytest.raises(TypeError):
        gravar_atomico({"invalido": object()}, destino)

    assert not destino.exists()
    assert sobras(destino.parent) == []
