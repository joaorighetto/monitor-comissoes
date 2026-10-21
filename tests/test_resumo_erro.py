"""Mensagens de erro (AVI, US4): falha da coleta e "a coleta de hoje não rodou"."""

from datetime import date

import pytest

import aviso_sinteticos as a
from monitor_comissoes.erros import CATEGORIAS
from monitor_comissoes.resumo import LIMITE, montar_coleta_nao_rodou, montar_erro_da_coleta, tamanho

HOJE = date(2026, 10, 20)


def test_erro_da_coleta_com_dados_bons_anteriores():
    status = a.status_falha()

    assert montar_erro_da_coleta(status, HOJE) == "\n".join(
        [
            "⚠ ERRO · Monitor de comissões · 20/10",
            "A atualização de 20/10 falhou: a Câmara não atualizou os arquivos"
            " [arquivos_desatualizados]",
            "Nenhuma lista nova foi publicada. Últimos dados bons: dados de 19/10 (105 itens).",
        ]
    )


@pytest.mark.parametrize("categoria", CATEGORIAS)
def test_cada_categoria_aparece_com_o_motivo_sem_reescrever(categoria):
    status = a.status_falha(categoria=categoria, motivo=f"motivo de {categoria} com 'aspas' e *")

    texto = montar_erro_da_coleta(status, HOJE)

    assert f"falhou: motivo de {categoria} com 'aspas' e * [{categoria}]" in texto
    assert texto.startswith("⚠ ERRO")


def test_sem_retrato_bom_diz_que_ainda_nao_ha_dados_bons():
    texto = montar_erro_da_coleta(a.status_falha(com_retrato_bom=False), HOJE)

    assert texto.endswith("Nenhuma lista nova foi publicada. Ainda não há dados bons.")
    assert "Últimos dados bons" not in texto


def test_erro_da_coleta_nao_tem_eventos_nem_totais():
    texto = montar_erro_da_coleta(a.status_falha(), HOJE)

    assert "evento" not in texto and "sem mudanças" not in texto


def test_um_item_so_no_singular():
    texto = montar_erro_da_coleta(a.status_falha(total_itens=1), HOJE)

    assert "(1 item)" in texto


def test_motivo_enorme_e_cortado_com_reticencias_e_cabe_no_teto():
    status = a.status_falha(motivo="erro " * 5000)

    texto = montar_erro_da_coleta(status, HOJE)

    assert tamanho(texto) <= LIMITE
    assert "…" in texto
    assert texto.split("\n")[-1].startswith("Nenhuma lista nova foi publicada")


def test_motivo_enorme_com_caracteres_fora_do_bmp_tambem_cabe():
    texto = montar_erro_da_coleta(a.status_falha(motivo="😀" * 5000), HOJE)

    assert tamanho(texto) <= LIMITE


def test_coleta_que_nao_rodou_com_status_de_ontem():
    status = a.status_ok(dia="2026-10-19", dados_camara_em="2026-10-19T04:31:26+00:00")

    assert montar_coleta_nao_rodou(status, HOJE) == "\n".join(
        [
            "⚠ ERRO · Monitor de comissões · 20/10",
            "A coleta de hoje (20/10) não rodou. Último registro: 19/10, ok.",
            "Nenhuma lista nova foi publicada. Últimos dados bons: dados de 19/10 (105 itens).",
        ]
    )


def test_coleta_que_nao_rodou_depois_de_uma_falha_de_ontem():
    status = a.status_falha(dia="2026-10-19")

    texto = montar_coleta_nao_rodou(status, HOJE)

    assert "Último registro: 19/10, falha." in texto


def test_coleta_que_nao_rodou_sem_nenhum_registro():
    assert montar_coleta_nao_rodou(None, HOJE) == "\n".join(
        [
            "⚠ ERRO · Monitor de comissões · 20/10",
            "A coleta de hoje (20/10) não rodou. Não há registro de coleta.",
            "Nenhuma lista nova foi publicada. Ainda não há dados bons.",
        ]
    )


def test_coleta_que_nao_rodou_com_status_sem_retrato_bom():
    status = a.status_falha(dia="2026-10-19", com_retrato_bom=False)

    assert montar_coleta_nao_rodou(status, HOJE).endswith("Ainda não há dados bons.")
