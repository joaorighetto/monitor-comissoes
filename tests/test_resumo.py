"""Formatação pura da mensagem do dia (AVI): contracts/mensagem.md."""

import pytest

from monitor_comissoes.config import Config
from monitor_comissoes.resumo import LIMITE, LIMITE_AVISO, destino_da_pagina, dia_mes, tamanho

# --- auxiliares (T008) -------------------------------------------------------------------------


def test_constantes_do_contrato():
    assert LIMITE == 4096
    assert LIMITE_AVISO == 1200


def test_tamanho_conta_unidades_utf16():
    assert tamanho("a") == 1
    assert tamanho("⚠") == 1
    assert tamanho("😀") == 2
    assert tamanho("") == 0
    assert tamanho("ação") == 4


def test_dia_mes_usa_o_fuso_de_brasilia():
    assert dia_mes("2026-10-20T04:31:26+00:00") == "20/10"
    assert dia_mes("2026-10-20T01:30:00+00:00") == "19/10"
    assert dia_mes("2026-01-05T09:00:00-03:00") == "05/01"


def test_destino_com_pagina_configurada():
    config = Config(("CE",), 2003, pagina_url="https://exemplo.github.io/monitor")

    assert destino_da_pagina(config, "2026-10-20") == (
        "veja a página",
        "https://exemplo.github.io/monitor",
    )


def test_destino_sem_pagina_e_o_arquivo_do_dia_no_repositorio():
    config = Config(("CE",), 2003, repositorio="a/b")

    assert destino_da_pagina(config, "2026-10-20") == (
        "veja o arquivo do dia",
        "https://github.com/a/b/blob/main/data/mudancas/2026-10-20.json",
    )


@pytest.mark.parametrize("dia", ["2026-10-20", "2027-02-01"])
def test_destino_padrao_aponta_para_o_repositorio_do_projeto(dia):
    texto, url = destino_da_pagina(Config(("CE",), 2003), dia)

    assert texto == "veja o arquivo do dia"
    assert url == (
        f"https://github.com/joaorighetto/monitor-comissoes/blob/main/data/mudancas/{dia}.json"
    )
