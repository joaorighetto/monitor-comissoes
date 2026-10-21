"""Registro de envio `data/envio.json` (contracts/envio-json.md)."""

import json
import os

import pytest

from monitor_comissoes.envio import gravar_registro, ja_enviado, ler_registro
from monitor_comissoes.erros import FalhaDeEnvio


def escrever(tmp_path, conteudo):
    caminho = tmp_path / "envio.json"
    caminho.write_text(
        conteudo if isinstance(conteudo, str) else json.dumps(conteudo), encoding="utf-8"
    )
    return caminho


def documento(normal=None, erro=None, versao=1):
    return {"versao_formato": versao, "ultimo_envio": {"normal": normal, "erro": erro}}


def test_arquivo_ausente_equivale_a_nada_enviado(tmp_path):
    assert ler_registro(tmp_path / "envio.json") == {"normal": None, "erro": None}


def test_le_o_arquivo_valido(tmp_path):
    caminho = escrever(tmp_path, documento(normal="2026-10-20", erro="2026-10-19"))

    assert ler_registro(caminho) == {"normal": "2026-10-20", "erro": "2026-10-19"}


@pytest.mark.parametrize(
    "conteudo",
    [
        "{ nao e json",
        "[1]",
        documento(versao=2),
        documento(normal="20/10/2026"),
        documento(normal="2026-13-40"),
        documento(erro=7),
        {"versao_formato": 1},
        {"versao_formato": 1, "ultimo_envio": {"normal": None}},
        {"versao_formato": 1, "ultimo_envio": {"normal": None, "erro": None, "extra": None}},
        {"versao_formato": 1, "ultimo_envio": {"normal": None, "erro": None}, "extra": 1},
        {"versao_formato": True, "ultimo_envio": {"normal": None, "erro": None}},
    ],
)
def test_arquivo_invalido_falha_com_o_nome(tmp_path, conteudo):
    caminho = escrever(tmp_path, conteudo)

    with pytest.raises(FalhaDeEnvio, match="envio.json"):
        ler_registro(caminho)


def test_ja_enviado_so_quando_o_dia_do_tipo_e_o_de_hoje():
    registro = {"normal": "2026-10-20", "erro": "2026-10-19"}

    assert ja_enviado(registro, "normal", "2026-10-20")
    assert not ja_enviado(registro, "erro", "2026-10-20")
    assert not ja_enviado({"normal": None, "erro": None}, "normal", "2026-10-20")
    assert not ja_enviado(registro, "normal", "2026-10-21")


def test_gravar_cria_pasta_e_arquivo_com_ordem_fixa(tmp_path):
    caminho = tmp_path / "data" / "envio.json"

    gravar_registro(caminho, "normal", "2026-10-20")

    assert caminho.read_text(encoding="utf-8") == (
        '{\n  "versao_formato": 1,\n  "ultimo_envio": {\n    "normal": "2026-10-20",\n'
        '    "erro": null\n  }\n}\n'
    )


def test_gravar_um_tipo_preserva_o_outro(tmp_path):
    caminho = escrever(tmp_path, documento(normal="2026-10-19", erro=None))

    gravar_registro(caminho, "erro", "2026-10-20")

    assert ler_registro(caminho) == {"normal": "2026-10-19", "erro": "2026-10-20"}


def test_gravar_com_registro_invalido_nao_sobrescreve(tmp_path):
    caminho = escrever(tmp_path, "{ nao e json")

    with pytest.raises(FalhaDeEnvio):
        gravar_registro(caminho, "normal", "2026-10-20")

    assert caminho.read_text(encoding="utf-8") == "{ nao e json"


def test_falha_ao_gravar_deixa_o_arquivo_anterior_como_estava(tmp_path, monkeypatch):
    caminho = escrever(tmp_path, documento(normal="2026-10-19"))
    antes = caminho.read_bytes()

    def falha(origem, destino):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", falha)

    with pytest.raises(OSError):
        gravar_registro(caminho, "normal", "2026-10-20")

    assert caminho.read_bytes() == antes
    assert [p.name for p in tmp_path.iterdir()] == ["envio.json"]


def test_tipo_desconhecido_e_erro_de_programacao(tmp_path):
    with pytest.raises(ValueError, match="tipo"):
        gravar_registro(tmp_path / "envio.json", "outro", "2026-10-20")
