"""Teto de 4.096 unidades, seleção alternada e "e mais N" (AVI, US3)."""

import random

import pytest

import aviso_sinteticos as a
from monitor_comissoes.config import Config
from monitor_comissoes.resumo import LIMITE, montar_normal, tamanho

CONFIG = Config(("CE", "CREDN"), 2003)
REPO = "https://github.com/joaorighetto/monitor-comissoes/blob/main/data/mudancas/2026-10-20.json"


def texto(documento, config=CONFIG, avisos=()):
    return montar_normal(documento, a.status_ok(), config, avisos)


def exibidos(saida: str) -> list[str]:
    return [linha for linha in saida.split("\n") if linha.startswith("• ")]


def omitidos(saida: str) -> int:
    for linha in saida.split("\n"):
        if linha.startswith("e mais "):
            return int(linha.split()[2].rstrip(","))
    return 0


def test_trezentos_eventos_cabem_no_teto_e_as_duas_comissoes_aparecem():
    saida = texto(a.muitos_eventos(300))

    assert tamanho(saida) <= LIMITE
    assert "\nCE\n" in saida and "\nCREDN\n" in saida


def test_n_do_e_mais_n_e_exatamente_o_numero_de_omitidos():
    saida = texto(a.muitos_eventos(300))

    assert len(exibidos(saida)) + omitidos(saida) == 300
    assert omitidos(saida) > 0


def test_a_selecao_alterna_entre_comissoes_na_ordem_do_arquivo():
    saida = texto(a.muitos_eventos(300))
    mostrados = len(exibidos(saida))

    for i in range(1, mostrados + 1):
        assert f"PL {i}/2024 " in saida
    assert f"PL {mostrados + 1}/2024 " not in saida
    assert f"PL {mostrados + 2}/2024 " not in saida


def test_comissao_com_poucos_eventos_aparece_mesmo_com_a_outra_cheia():
    saida = texto(a.muitos_eventos(300, ("CE",) * 20 + ("CREDN",)))

    assert "\nCREDN\n" in saida
    assert tamanho(saida) <= LIMITE


def test_cada_grupo_mostra_na_ordem_da_configuracao():
    saida = texto(a.muitos_eventos(300), Config(("CREDN", "CE"), 2003))

    assert saida.index("\nCREDN\n") < saida.index("\nCE\n")


def test_a_selecao_para_no_primeiro_evento_que_nao_cabe():
    grande = a.evento("situacao", "credn_a", de="x" * 5000)
    pequeno = a.evento("parecer", "ce_a")
    outro = a.evento("parecer", "ce_b")

    saida = texto(a.mudancas([pequeno, grande, outro]))

    assert tamanho(saida) <= LIMITE
    assert len(exibidos(saida)) == 1 and "PL 1831/2022" in saida
    assert "PL 3510/2023" not in saida  # caberia, mas a seleção não pula o que não coube
    assert omitidos(saida) == 2
    assert "x" * 100 not in saida


def test_um_evento_sozinho_maior_que_o_teto_nunca_aparece_cortado():
    grande = a.evento("situacao", "ce_a", de="x" * 5000)

    saida = texto(a.mudancas([grande]))

    assert tamanho(saida) <= LIMITE
    assert exibidos(saida) == []
    assert "e mais 1, veja o arquivo do dia" in saida
    assert "x" * 100 not in saida


def test_a_linha_de_totais_conta_tambem_os_omitidos():
    saida = texto(a.muitos_eventos(300))

    assert saida.split("\n")[1] == "300 eventos: 300 situação"


def test_rodape_sem_pagina_aponta_para_o_arquivo_do_dia():
    linhas = texto(a.muitos_eventos(300)).split("\n")

    assert linhas[-2].endswith(", veja o arquivo do dia")
    assert linhas[-1] == REPO


def test_rodape_com_pagina_configurada():
    config = Config(("CE", "CREDN"), 2003, pagina_url="https://exemplo.github.io/monitor")

    linhas = texto(a.muitos_eventos(300), config).split("\n")

    assert linhas[-2].endswith(", veja a página")
    assert linhas[-1] == "https://exemplo.github.io/monitor"


def test_sem_excedente_nao_ha_rodape():
    saida = texto(a.muitos_eventos(10))

    assert "e mais" not in saida and len(exibidos(saida)) == 10


def test_todo_evento_exibido_tem_o_link_logo_abaixo():
    linhas = texto(a.muitos_eventos(300)).split("\n")

    for i, linha in enumerate(linhas):
        if linha.startswith("• "):
            assert linhas[i + 1].startswith("  https://www.camara.leg.br/propostas-legislativas/")


def test_caracteres_fora_do_bmp_sao_medidos_em_utf16():
    saida = texto(a.muitos_eventos(200, prefixo="😀😀😀😀😀😀😀😀😀😀"))

    assert tamanho(saida) <= LIMITE
    assert len(saida) < tamanho(saida)  # há pares substitutos: len() contaria a menos


def test_com_uma_unica_comissao_tambem_respeita_o_teto():
    saida = texto(a.muitos_eventos(300, ("CE",)))

    assert tamanho(saida) <= LIMITE and "\nCREDN\n" not in saida


def test_avisos_sao_reservados_antes_dos_eventos_e_ficam_inteiros():
    aviso = "⚠ 1 item com relator indeterminado:\n• PL 3510/2023 (CE)\n  " + REPO

    saida = texto(a.muitos_eventos(300), avisos=(aviso,))
    linhas = saida.split("\n")

    assert tamanho(saida) <= LIMITE
    assert aviso in saida
    assert saida.index(aviso) < saida.index("e mais ")
    assert linhas.index("⚠ 1 item com relator indeterminado:") > linhas.index("CREDN")


def test_aviso_grande_demais_e_recusado():
    with pytest.raises(ValueError, match="aviso"):
        texto(a.muitos_eventos(10), avisos=("x" * 5000,))


def test_aviso_sem_excedente_vem_depois_dos_grupos():
    aviso = "⚠ 1 item com principal não localizada:\n• PL 1/2024 (CE)\n  link"

    saida = texto(a.muitos_eventos(2), avisos=(aviso,))

    assert saida.endswith(aviso)


def test_propriedade_o_teto_vale_em_combinacoes_fixas():
    gerador = random.Random(2026)
    for _ in range(40):
        n = gerador.randint(0, 400)
        proporcao = gerador.randint(1, 15)
        prefixo = "A" * gerador.choice([0, 3, 40, 200])
        saida = texto(a.muitos_eventos(n, ("CE",) * proporcao + ("CREDN",), prefixo=prefixo))

        assert tamanho(saida) <= LIMITE, (n, proporcao, len(prefixo))
        assert len(exibidos(saida)) + omitidos(saida) == n
        links = [linha for linha in saida.split("\n") if linha.startswith("  https://www.camara")]
        assert len(links) == len(set(links)) == len(exibidos(saida))
