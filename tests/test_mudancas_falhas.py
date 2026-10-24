"""Falhas da MUD (User Story 5): a execução inteira falha, com o motivo, e nada fica pela metade.

Cada cenário confere, byte a byte, `atual.json`, `anterior.json` e a pasta `data/mudancas/` antes e
depois. Só o `status.json` muda, e registra a falha (PRODUCT.md, §7 e D10; constituição, III).
"""

import json
import os
from datetime import timedelta
from pathlib import Path

import pytest

import sinteticos as s
from conftest import TransporteFalso
from monitor_comissoes import status
from monitor_comissoes.erros import (
    FONTE_INDISPONIVEL,
    FORMATO_ALTERADO,
    INTERNA,
    FalhaDeColeta,
)
from monitor_comissoes.mudancas import comparar
from monitor_comissoes.retratos import Comparacao
from monitor_comissoes.retratos import ler as ler_retrato
from test_diaria import (
    Dormidas,
    Relogio,
    executar_main,
    ler,
    novo_ambiente,
    ontem_com_os_seis_tipos,
)

# No lote como "Transformado em Norma Jurídica", sequência 134; sem fixture de tramitações.
PL_SAIU = 2141142
ORDEM_DAS_TROCAS = [
    "anterior.json",
    "2026-10-19.json",
    "indice-autoria.json",
    "atual.json",
    "status.json",
]


@pytest.fixture
def caminhos(tmp_path):
    return novo_ambiente(tmp_path, "falhas")


def foto(caminhos) -> dict[str, bytes | None]:
    """Os arquivos de dados, byte a byte (e quais existem); o status fica de fora de propósito."""
    arquivos = {
        "atual": caminhos["atual"],
        "anterior": caminhos["anterior"],
        "indice": caminhos["indice"],
    }
    resultado = {nome: c.read_bytes() if c.exists() else None for nome, c in arquivos.items()}
    pasta = caminhos["mudancas"]
    for arquivo in sorted(pasta.glob("*")) if pasta.exists() else []:
        resultado[f"mudancas/{arquivo.name}"] = arquivo.read_bytes()
    resultado["pasta-de-dados"] = sorted(p.name for p in caminhos["atual"].parent.iterdir())
    return resultado


def ontem_pronto(caminhos, transporte, agora, *, consulta_tramitacoes_de_quem_saiu=False):
    """Dia 1 verdadeiro e um retrato de ontem sintético no disco (a execução do dia 2 é a testada).

    O PL 7843/2017 (id 2141142) está no retrato de ontem; hoje o lote diz sequência 134. Com
    `consulta_tramitacoes_de_quem_saiu`, ontem ele tinha a 130, e a comparação precisa das
    tramitações dele (que a REL nunca lê e que não existem nas fixtures: o teste as controla).
    """
    ontem = ontem_com_os_seis_tipos(caminhos, transporte, agora)
    if consulta_tramitacoes_de_quem_saiu:
        for item in ontem["itens"]:
            if item["id"] == PL_SAIU:
                item["ultimo_status_sequencia"] = 130
    caminhos["atual"].write_text(json.dumps(ontem, ensure_ascii=False, indent=2), encoding="utf-8")
    return ontem


def falhou(caminhos, antes, capsys, codigo, categoria, trecho):
    erro = capsys.readouterr().err
    assert codigo == 1
    assert f"FALHA [{categoria}]: " in erro, erro
    assert trecho in erro, erro
    assert foto(caminhos) == antes  # nada mudou, byte a byte
    situacao = ler(caminhos["status"])
    assert situacao["resultado"] == "falha"
    assert situacao["falha"]["categoria"] == categoria
    assert trecho in situacao["falha"]["motivo"]
    assert not list(caminhos["atual"].parent.rglob("*.tmp"))  # nenhum temporário sobra
    return situacao


# --- rede e formato das tramitações da comparação ---


def test_erro_de_rede_nas_tramitacoes_da_comparacao_falha_e_repete_como_a_coleta(
    caminhos, agora, capsys
):
    transporte = TransporteFalso()
    ontem_pronto(caminhos, transporte, agora, consulta_tramitacoes_de_quem_saiu=True)
    antes = foto(caminhos)
    transporte.erro_json[f"tramitacoes/{PL_SAIU}"] = FalhaDeColeta(FONTE_INDISPONIVEL, "HTTP 503")
    dormidas = Dormidas()
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)), dormidas)

    situacao = falhou(caminhos, antes, capsys, codigo, FONTE_INDISPONIVEL, str(PL_SAIU))
    assert situacao["tentativas"] == 4  # padrão da configuração: a falha é repetível
    assert len(dormidas.pedidos) == 3  # três esperas entre as quatro tentativas


def test_resposta_sem_a_sequencia_de_hoje_do_lote_e_formato_alterado_e_nao_repete(
    caminhos, agora, capsys
):
    transporte = TransporteFalso()
    ontem_pronto(caminhos, transporte, agora, consulta_tramitacoes_de_quem_saiu=True)
    antes = foto(caminhos)
    transporte.tramitacoes_sinteticas = True  # lista neutra com a sequência 1 apenas
    dormidas = Dormidas()
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)), dormidas)

    situacao = falhou(caminhos, antes, capsys, codigo, FORMATO_ALTERADO, "a sequência 134")
    assert str(PL_SAIU) in situacao["falha"]["motivo"]
    assert situacao["tentativas"] == 1 and dormidas.pedidos == []


def test_sequencia_de_hoje_menor_que_a_anterior_e_formato_alterado(caminhos, agora, capsys):
    transporte = TransporteFalso()
    ontem = ontem_pronto(caminhos, transporte, agora, consulta_tramitacoes_de_quem_saiu=True)
    for item in ontem["itens"]:
        if item["id"] == PL_SAIU:
            item["ultimo_status_sequencia"] = 200  # o lote de hoje diz 134
    caminhos["atual"].write_text(json.dumps(ontem, ensure_ascii=False, indent=2), encoding="utf-8")
    antes = foto(caminhos)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)))

    falhou(caminhos, antes, capsys, codigo, FORMATO_ALTERADO, "regrediu de 200 para 134")


def test_a_comparacao_repassa_a_falha_da_fonte_sem_trocar_a_categoria():
    for categoria in (FONTE_INDISPONIVEL, FORMATO_ALTERADO):

        def quebrada(id_referencia, categoria=categoria):
            raise FalhaDeColeta(categoria, f"tramitações da proposição {id_referencia}: falhou")

        a = s.item(1, sequencia=41, situacao="Aguardando Parecer")
        h = s.item(1, sequencia=43, situacao="Pronta para Pauta")
        anterior = ler_retrato(json.dumps(s.retrato([a])), "anterior")
        comparacao = Comparacao(anterior, None, {"dia": "2026-10-18", "dados_camara_em": "x"}, None)

        with pytest.raises(FalhaDeColeta) as erro:
            comparar(comparacao, s.retrato([h]), {}, quebrada, ("CE",), anterior.dia)

        assert erro.value.categoria == categoria


# --- retrato anterior inválido (nunca vira linha de base em silêncio) ---


def corrompido(caminhos, transporte, agora, *, mexer):
    ontem_pronto(caminhos, transporte, agora)
    mexer(caminhos)
    return foto(caminhos)


def test_atual_de_dia_anterior_corrompido_falha_como_interna_e_nao_repete(caminhos, agora, capsys):
    transporte = TransporteFalso()
    antes = corrompido(
        caminhos,
        transporte,
        agora,
        mexer=lambda c: c["atual"].write_text('{"meta": {"versao_formato": 3', encoding="utf-8"),
    )
    dormidas = Dormidas()
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)), dormidas)

    situacao = falhou(caminhos, antes, capsys, codigo, INTERNA, "retrato anterior inválido")
    assert str(caminhos["atual"]) in situacao["falha"]["motivo"]
    assert situacao["tentativas"] == 1 and dormidas.pedidos == []  # falha na 1ª, sem repetir
    assert not (caminhos["mudancas"] / "2026-10-19.json").exists()  # não virou linha de base


def test_atual_de_dia_anterior_com_itens_estragados_falha_como_interna(caminhos, agora, capsys):
    def estragar(c):
        documento = ler(c["atual"])
        documento["itens"][0]["ultimo_status_sequencia"] = "x"
        c["atual"].write_text(json.dumps(documento), encoding="utf-8")

    transporte = TransporteFalso()
    antes = corrompido(caminhos, transporte, agora, mexer=estragar)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)))

    falhou(caminhos, antes, capsys, codigo, INTERNA, "ultimo_status_sequencia")


def test_anterior_json_corrompido_na_reexecucao_do_dia_falha_como_interna(caminhos, agora, capsys):
    transporte = TransporteFalso()
    ontem_pronto(caminhos, transporte, agora)
    dia2 = agora + timedelta(days=1)
    assert executar_main(caminhos, transporte, Relogio(dia2)) == 0
    caminhos["anterior"].write_text("não é json", encoding="utf-8")
    antes = foto(caminhos)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia2 + timedelta(hours=1)))

    situacao = falhou(caminhos, antes, capsys, codigo, INTERNA, "retrato anterior inválido")
    assert str(caminhos["anterior"]) in situacao["falha"]["motivo"]


def test_atual_de_data_futura_falha_como_interna(caminhos, agora, capsys):
    transporte = TransporteFalso()
    antes = corrompido(
        caminhos,
        transporte,
        agora,
        mexer=lambda c: c["atual"].write_text(
            c["atual"]
            .read_text(encoding="utf-8")
            .replace(
                '"gerado_em": "2026-10-18T09:00:00-03:00"',
                '"gerado_em": "2026-10-30T09:00:00-03:00"',
            ),
            encoding="utf-8",
        ),
    )
    assert b"2026-10-30" in antes["atual"]
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)))

    falhou(caminhos, antes, capsys, codigo, INTERNA, "data futura")


def test_atual_de_dia_anterior_em_formato_antigo_nao_falha_vira_linha_de_base(
    caminhos, agora, capsys
):
    """O contraste com os casos acima: formato antigo é decisão registrada, não falha."""
    transporte = TransporteFalso()
    ontem = ontem_pronto(caminhos, transporte, agora)
    ontem["meta"]["versao_formato"] = 2
    caminhos["atual"].write_text(json.dumps(ontem, ensure_ascii=False, indent=2), encoding="utf-8")

    assert executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1))) == 0

    dados = ler(caminhos["mudancas"] / "2026-10-19.json")
    assert dados["meta"]["linha_de_base"]["motivo"] == "formato anterior incompatível"


# --- gravação: tudo ou nada nos quatro arquivos ---


@pytest.mark.parametrize("k", [1, 2, 3, 4, 5])
def test_falha_ao_preparar_o_k_esimo_arquivo_nao_troca_nenhum(
    caminhos, agora, capsys, monkeypatch, k
):
    transporte = TransporteFalso()
    ontem_pronto(caminhos, transporte, agora)
    antes = foto(caminhos)
    original = status.escrever_temporario
    chamadas = []

    def falso(texto, destino):
        chamadas.append(Path(destino).name)
        if len(chamadas) == k:
            raise OSError("disco cheio (simulado)")
        return original(texto, destino)

    monkeypatch.setattr(status, "escrever_temporario", falso)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)))

    # Com rotação são cinco arquivos: anterior, mudanças, índice de autoria (PAU), atual e
    # status (nessa ordem).
    assert chamadas[:5] == ORDEM_DAS_TROCAS[:k]
    erro = capsys.readouterr().err
    assert codigo == 1 and "disco cheio" in erro
    assert foto(caminhos) == antes  # nenhum dos cinco mudou, e nenhum temporário sobrou
    assert not list(caminhos["atual"].parent.rglob("*.tmp"))
    assert ler(caminhos["status"])["resultado"] == "falha"


@pytest.mark.parametrize("quem", ORDEM_DAS_TROCAS)
def test_falha_na_troca_de_um_dos_cinco_restaura_os_ja_trocados(
    caminhos, agora, capsys, monkeypatch, quem
):
    transporte = TransporteFalso()
    ontem_pronto(caminhos, transporte, agora)
    antes = foto(caminhos)
    trocar = os.replace

    def falso(origem, destino):
        if Path(destino).name == quem:
            raise OSError("troca falhou (simulada)")
        return trocar(origem, destino)

    monkeypatch.setattr(os, "replace", falso)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)))

    # As trocas vão na ordem anterior, mudanças, índice, atual e status: o que já tinha sido
    # trocado volta ao que era, e o que ainda não tinha sido trocado nunca foi tocado.
    assert codigo == 1
    assert foto(caminhos) == antes
    assert not list(caminhos["atual"].parent.rglob("*.tmp"))


def test_falha_da_coleta_no_dia_2_nao_cria_anterior_nem_arquivo_de_mudancas(
    caminhos, agora, capsys
):
    transporte = TransporteFalso()
    ontem_pronto(caminhos, transporte, agora)
    antes = foto(caminhos)
    transporte.erro["proposicoes-2010.csv"] = FalhaDeColeta(
        FONTE_INDISPONIVEL, "proposicoes-2010.csv: HTTP 503"
    )
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1)), Dormidas())

    falhou(caminhos, antes, capsys, codigo, FONTE_INDISPONIVEL, "proposicoes-2010.csv")
    assert antes["anterior"] is None and not caminhos["anterior"].exists()


def test_o_status_de_falha_traz_categoria_e_motivo_para_a_pagina_e_o_telegram(
    caminhos, agora, capsys
):
    transporte = TransporteFalso()
    ontem_pronto(caminhos, transporte, agora)
    caminhos["atual"].write_text("lixo", encoding="utf-8")
    capsys.readouterr()

    assert executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1))) == 1

    situacao = ler(caminhos["status"])
    assert situacao["resultado"] == "falha"
    assert set(situacao["falha"]) == {"categoria", "motivo"}
    assert situacao["falha"]["categoria"] == INTERNA
    assert "retrato anterior inválido" in situacao["falha"]["motivo"]
