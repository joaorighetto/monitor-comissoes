"""Resultado do item em reunião realizada (PRODUCT.md §5.9, research R5), com textos reais."""

import json
from collections import Counter

import pytest

from monitor_comissoes.pauta.regras import grupo, proposicao_do_item, resultado, situacao
from pauta_sinteticos import PAUTA, item_real, itens_reais

ROTULOS = (
    "retirado de pauta",
    "vista",
    "aprovado",
    "rejeitado",
    "não apreciado",
    "sem registro",
    "outro",
)


def texto_real(evento, ordem):
    return item_real(evento, ordem)["situacaoItem"]


@pytest.mark.parametrize(
    ("evento", "ordem", "rotulo"),
    [
        (81555, 10, "retirado de pauta"),  # "Retirado de pauta, por acordo, a pedido do Relator…"
        (80265, 23, "retirado de pauta"),  # "Prejudicado o Requerimento… Retirado de pauta…"
        (80265, 24, "aprovado"),  # "Prejudicado o Requerimento de Retirada… Aprovado o Parecer…"
        (80375, 17, "vista"),  # "Lido o Parecer pelo Relator. Vista ao Deputado…"
        (81862, 5, "rejeitado"),  # "… Rejeitado o Parecer do Relator…"
        (81862, 12, "rejeitado"),
        (80344, 6, "não apreciado"),  # "Não deliberado."
        # "… Requerimento de Retirado de Pauta … Aprovado o Parecer da Relatora…" (grafia da Câmara)
        (80344, 16, "aprovado"),
        (80344, 5, "outro"),  # votação do Requerimento de Retirada de Pauta, sem quórum
        (81609, 19, "outro"),  # "Iniciada a Discussão. Discutiu a Matéria…"
    ],
)
def test_textos_reais(evento, ordem, rotulo):
    texto = texto_real(evento, ordem)

    assert resultado(texto) == {"rotulo": rotulo, "texto": texto}


@pytest.mark.parametrize(
    ("texto", "rotulo"),
    [
        ("Aprovado o Parecer.", "aprovado"),
        ("Aprovada a Redação Final.", "aprovado"),
        ("Rejeitado o Parecer.", "rejeitado"),
        ("Rejeitada a matéria.", "rejeitado"),
        ("Vista conjunta. Aprovado o Parecer.", "vista"),
        ("Adiada a discussão.", "não apreciado"),
        ("Matéria não apreciada.", "não apreciado"),
        ("Encerrada a reunião antes da apreciação do item.", "não apreciado"),
        ("Item prejudicado pelo encerramento da reunião.", "não apreciado"),
        ("RETIRADO DE PAUTA.", "retirado de pauta"),
        ("Retirada de pauta a matéria.", "retirado de pauta"),
        ("Aprovado o Requerimento de Retirada de Pauta.", "retirado de pauta"),
        (
            "Aprovada a Inversão de Pauta. Aprovado Requerimento de Retirada de Pauta.",
            "retirado de pauta",
        ),
        ("Rejeitado o Requerimento de Retirada de Pauta. Aprovado o Parecer.", "aprovado"),
        (
            "Retirado o Requerimento de Retirada de Pauta pelo Autor. Aprovado o Parecer.",
            "aprovado",
        ),
        ("Revista a redação.", "outro"),  # "vista" só como palavra
        ("Desaprovado o trecho.", "outro"),  # "aprovado" só como palavra
        ("Lido o Parecer.", "outro"),
    ],
)
def test_regras_em_ordem_e_sem_diferenca_de_maiusculas(texto, rotulo):
    assert resultado(texto) == {"rotulo": rotulo, "texto": texto}


@pytest.mark.parametrize("texto", [None, "", "   \n"])
def test_sem_texto_e_sem_registro(texto):
    assert resultado(texto) == {"rotulo": "sem registro", "texto": texto}


def _situacoes_das_janelas():
    situacoes = {}
    for arquivo in (PAUTA / "eventos").glob("*-*.json"):
        for evento in json.loads(arquivo.read_text(encoding="utf-8"))["dados"]:
            situacoes[evento["id"]] = situacao(evento["situacao"])
    return situacoes


def test_cobertura_dos_sete_rotulos_nas_reunioes_realizadas_salvas():
    # As avulsas (80265 e 81862) são reuniões realizadas fora das janelas salvas (README).
    situacoes = {**_situacoes_das_janelas(), 80265: "realizada", 81862: "realizada"}
    contagem = Counter()
    outros = []
    for arquivo in (PAUTA / "pautas").glob("*.json"):
        id_evento = int(arquivo.stem)
        if situacoes[id_evento] != "realizada":
            continue
        for item in itens_reais(id_evento):
            proposicao = proposicao_do_item(item)
            if grupo(proposicao and proposicao["siglaTipo"]) != "listado":
                continue
            classificado = resultado(item["situacaoItem"])
            assert classificado["texto"] == item["situacaoItem"]
            contagem[classificado["rotulo"]] += 1
            if classificado["rotulo"] == "outro":
                outros.append((id_evento, item["ordem"]))

    assert set(contagem) == set(ROTULOS)
    assert sorted(outros) == [(80344, 5), (81609, 19)]
