"""Avisos de relator indeterminado e de principal não localizada (AVI, US6)."""

import json

import pytest

import aviso_sinteticos as a
import sinteticos as s
from monitor_comissoes.aviso import montar_mensagem_do_dia
from monitor_comissoes.erros import FalhaDeEnvio
from monitor_comissoes.resumo import LIMITE, LIMITE_AVISO, blocos_de_aviso, montar_normal, tamanho
from test_aviso import AGORA, CONFIG, preparar

LINK = s.LINK


def item(id, identificacao, comissao):
    return {"id": id, "identificacao": identificacao, "comissao": comissao, "link": f"{LINK}{id}"}


def test_sem_ressalvas_e_sem_itens_nao_ha_bloco():
    assert blocos_de_aviso([], [], CONFIG) == ()


def test_bloco_de_relator_indeterminado():
    ressalvas = [item(2373671, "PL 3510/2023", "CE")]

    assert blocos_de_aviso(ressalvas, [], CONFIG) == (
        "\n".join(
            [
                "⚠ 1 item com relator indeterminado:",
                "• PL 3510/2023 (CE)",
                f"  {LINK}2373671",
            ]
        ),
    )


def test_bloco_de_principal_nao_localizada_no_plural():
    itens = [item(148585, "PL 2752/2003", "CE"), item(2345297, "PL 3076/2022", "CREDN")]

    assert blocos_de_aviso([], itens, CONFIG) == (
        "\n".join(
            [
                "⚠ 2 itens com principal não localizada:",
                "• PL 2752/2003 (CE)",
                f"  {LINK}148585",
                "• PL 3076/2022 (CREDN)",
                f"  {LINK}2345297",
            ]
        ),
    )


def test_relator_indeterminado_vem_antes_de_principal_nao_localizada():
    blocos = blocos_de_aviso([item(1, "PL 1/2024", "CE")], [item(2, "PL 2/2024", "CE")], CONFIG)

    assert blocos[0].startswith("⚠ 1 item com relator") and blocos[1].startswith(
        "⚠ 1 item com prin"
    )


def test_itens_seguem_a_comissao_da_configuracao_e_depois_o_id():
    itens = [
        item(30, "PL 30/2024", "CREDN"),
        item(20, "PL 20/2024", "CE"),
        item(10, "PL 10/2024", "CE"),
    ]

    bloco = blocos_de_aviso(itens, [], CONFIG)[0]

    assert [linha for linha in bloco.split("\n") if linha.startswith("• ")] == [
        "• PL 10/2024 (CE)",
        "• PL 20/2024 (CE)",
        "• PL 30/2024 (CREDN)",
    ]


def test_contagem_inteira_e_lista_limitada_a_1200_unidades_com_e_mais_m():
    ressalvas = [item(1000 + i, f"PL {i}/2024", "CE") for i in range(100)]

    bloco = blocos_de_aviso(ressalvas, [], CONFIG)[0]
    linhas = bloco.split("\n")
    mostrados = sum(1 for linha in linhas if linha.startswith("• PL "))

    assert linhas[0] == "⚠ 100 itens com relator indeterminado:"
    assert tamanho(bloco) <= LIMITE_AVISO
    assert 0 < mostrados < 100
    assert linhas[-1] == f"• e mais {100 - mostrados} itens"
    assert tamanho(bloco) > LIMITE_AVISO - 200  # aproveita o espaço


def test_e_mais_m_no_singular():
    finais = set()
    for total in range(1, 40):
        ressalvas = [item(1000 + i, f"PL {i}/2024", "CE") for i in range(total)]
        finais.add(blocos_de_aviso(ressalvas, [], CONFIG)[0].splitlines()[-1])

    assert "• e mais 1 item" in finais
    assert "• e mais 1 itens" not in finais


def test_aviso_aparece_na_mensagem_sem_mudancas_e_na_linha_de_base():
    blocos = blocos_de_aviso([], [item(148585, "PL 2752/2003", "CE")], CONFIG)
    base = a.mudancas(
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 105}, retrato_anterior=None
    )

    sem_mudancas = montar_normal(a.mudancas(), a.status_ok(), CONFIG, blocos)
    com_base = montar_normal(base, a.status_ok(), CONFIG, blocos)

    assert sem_mudancas.endswith("sem mudanças · 105 itens · dados de 20/10\n\n" + blocos[0])
    assert com_base.endswith("Primeiro retrato: ainda não há com o que comparar.\n\n" + blocos[0])


def test_dois_avisos_cheios_ainda_cabem_com_eventos_sob_o_teto():
    ressalvas = [item(1000 + i, f"PL {i}/2024", "CE") for i in range(300)]
    principais = [item(5000 + i, f"PL {i}/2025", "CREDN") for i in range(300)]
    blocos = blocos_de_aviso(ressalvas, principais, CONFIG)

    texto = montar_normal(a.muitos_eventos(300), a.status_ok(), CONFIG, blocos)

    assert tamanho(texto) <= LIMITE
    assert all(bloco in texto for bloco in blocos)
    assert "e mais" in texto.split("\n\n")[-1]


# --- ponta a ponta (T018) ----------------------------------------------------------------------


def test_mensagem_do_dia_traz_os_dois_avisos(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    texto = montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date()).texto

    assert "⚠ 1 item com relator indeterminado:\n• PL 3510/2023 (CE)" in texto
    assert "⚠ 2 itens com principal não localizada:" in texto
    assert "• PL 2752/2003 (CE)" in texto and "• PL 3076/2022 (CREDN)" in texto
    assert texto.index("relator indeterminado") > texto.index("CREDN\n• Etiquetas")


def test_dia_sem_eventos_mantem_o_aviso_de_principal_nao_localizada(tmp_path):
    caminhos = preparar(tmp_path, "sem-eventos")

    texto = montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date()).texto

    assert texto.startswith("Monitor de comissões\nsem mudanças · 105 itens · dados de 20/10")
    assert "⚠ 2 itens com principal não localizada:" in texto
    assert "relator indeterminado" not in texto


def test_a_mensagem_de_erro_nao_precisa_do_atual(tmp_path):
    caminhos = preparar(tmp_path, "falha")
    caminhos.atual.unlink()

    assert montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date()).tipo == "erro"


def estragar(caminhos, mexer):
    documento = json.loads(caminhos.atual.read_text(encoding="utf-8"))
    mexer(documento)
    caminhos.atual.write_text(json.dumps(documento), encoding="utf-8")


@pytest.mark.parametrize(
    ("mexer", "trecho"),
    [
        (lambda d: d["meta"].update(versao_formato=1), "versao_formato"),
        (lambda d: d["meta"].update(versao_formato=4), "versao_formato"),
        (lambda d: d["itens"][0].pop("principal_nao_localizada"), "principal_nao_localizada"),
        (lambda d: d["itens"][0].update(link=""), "link"),
    ],
)
def test_atual_fora_do_contrato_falha_em_vez_de_omitir_o_aviso(tmp_path, mexer, trecho):
    caminhos = preparar(tmp_path, "completo")
    estragar(caminhos, mexer)

    with pytest.raises(FalhaDeEnvio, match=trecho):
        montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date())


def test_atual_ausente_num_dia_normal_falha(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    caminhos.atual.unlink()

    with pytest.raises(FalhaDeEnvio, match="atual.json"):
        montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date())
