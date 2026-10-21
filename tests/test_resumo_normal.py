"""Mensagem normal (AVI, US1 e US2): eventos, sem mudanças, linha de base e intervalo."""

import pytest

import aviso_sinteticos as a
import sinteticos as s
from monitor_comissoes.config import Config
from monitor_comissoes.resumo import montar_normal

CONFIG = Config(("CE", "CREDN"), 2003)
LINK = s.LINK


def texto_normal(documento=None, status=None, config=CONFIG, avisos=()):
    return montar_normal(
        documento if documento is not None else a.completo(),
        status if status is not None else a.status_ok(),
        config,
        avisos,
    )


def esperado_completo():
    return "\n".join(
        [
            "Monitor de comissões · dados de 20/10 · 105 itens",
            "6 eventos: 1 entrou · 1 saiu · 1 situação · 1 relator · 1 parecer · 1 etiquetas",
            "",
            "CE",
            "• Entrou: PL 1831/2022 — chegou à comissão",
            f"  {LINK}2330962",
            "• Saiu: PL 3510/2023 — foi para outro órgão (destino: CFT)",
            f"  {LINK}2373671",
            "• Situação: PL 2752/2003 — Aguardando Parecer → Pronta para Pauta",
            f"  {LINK}148585",
            "• Relator: PLP 173/2023 — designado Luiz Lima (NOVO)",
            f"  {LINK}2380176",
            "• Parecer: PL 3075/2022 — parecer do relator",
            f"  {LINK}2345296",
            "",
            "CREDN",
            "• Etiquetas: PL 3076/2022 — ganhou relatoria NOVO",
            f"  {LINK}2345297",
        ]
    )


# --- US1 ------------------------------------------------------------------------------------


def test_mensagem_com_um_evento_de_cada_tipo_nas_duas_comissoes():
    assert texto_normal() == esperado_completo()


def test_a_mensagem_normal_nao_comeca_com_alerta():
    assert not texto_normal().startswith("⚠")


def test_duas_formatacoes_da_mesma_entrada_dao_o_mesmo_texto():
    assert texto_normal() == texto_normal()


def test_nenhuma_linha_termina_com_espaco():
    assert all(linha == linha.rstrip() for linha in texto_normal().split("\n"))


def test_grupos_seguem_a_ordem_da_configuracao_e_nao_a_do_arquivo():
    eventos = [a.evento("parecer", "credn_a"), a.evento("parecer", "ce_a")]
    config = Config(("CREDN", "CE"), 2003)

    texto = texto_normal(a.mudancas(eventos), config=config)

    assert texto.index("\nCREDN\n") < texto.index("\nCE\n")


def test_comissao_sem_evento_nao_tem_grupo():
    texto = texto_normal(a.mudancas([a.evento("parecer", "ce_a")]))

    assert "\nCE\n" in texto and "CREDN" not in texto


def test_linha_de_totais_so_traz_tipos_com_evento_e_usa_singular_e_plural():
    eventos = [a.evento("parecer", "ce_a"), a.evento("parecer", "ce_b"), a.evento("saiu", "ce_c")]

    texto = texto_normal(a.mudancas(eventos))

    assert texto.split("\n")[1] == "3 eventos: 1 saiu · 2 parecer"
    assert texto_normal(a.mudancas([a.evento("saiu")])).split("\n")[1] == "1 evento: 1 saiu"


def test_total_de_itens_vem_do_status_e_o_dia_e_o_dos_dados_da_camara():
    status = a.status_ok(total_itens=1)

    assert texto_normal(status=status).split("\n")[0] == (
        "Monitor de comissões · dados de 20/10 · 1 item"
    )


def test_item_com_dois_eventos_mostra_os_dois():
    eventos = [a.evento("situacao", "ce_a"), a.evento("relator", "ce_a")]

    texto = texto_normal(a.mudancas(eventos))

    assert texto.count("PL 1831/2022") == 2
    assert "• Situação:" in texto and "• Relator:" in texto


def test_todo_evento_tem_o_link_logo_abaixo():
    linhas = texto_normal().split("\n")

    for i, linha in enumerate(linhas):
        if linha.startswith("• "):
            assert linhas[i + 1].startswith(f"  {LINK}")


PRIMEIRO = {"id": 204455, "nome": "Luiz Lima", "partido_hoje": "NOVO"}
SEGUNDO = {"id": 178929, "nome": "Diego Garcia", "partido_hoje": "UNIÃO"}
SAIDA_BASE = {"orgao": "MESA", "situacao": "Arquivada", "apensado_a": None}

VARIANTES = [
    (
        a.evento(
            "entrou",
            motivo={"codigo": "ganhou_etiqueta", "texto": "ganhou etiqueta: autor hoje no NOVO"},
        ),
        "• Entrou: PL 1831/2022 — ganhou etiqueta: autor hoje no NOVO",
    ),
    (
        a.evento(
            "saiu",
            motivo={"codigo": "apensado_fora_da_lista", "texto": "apensado a uma proposição fora"},
            destino={
                "orgao": "CFT",
                "situacao": "Aguardando Parecer",
                "apensado_a": {"id": 9, "identificacao": "PL 9/2019", "link": f"{LINK}9"},
            },
        ),
        "• Saiu: PL 1831/2022 — apensado a uma proposição fora (apensado a PL 9/2019)",
    ),
    (
        a.evento(
            "saiu",
            motivo={"codigo": "encerrado", "texto": "encerrado"},
            destino={**SAIDA_BASE, "situacao": "Perdeu a Eficácia"},
        ),
        "• Saiu: PL 1831/2022 — encerrado (Perdeu a Eficácia)",
    ),
    (
        a.evento(
            "saiu",
            motivo={"codigo": "arquivado_art_105", "texto": "arquivado, art. 105"},
            destino=SAIDA_BASE,
        ),
        "• Saiu: PL 1831/2022 — arquivado, art. 105",
    ),
    (
        a.evento(
            "saiu",
            motivo={"codigo": "perdeu_etiquetas", "texto": "perdeu as etiquetas: autoria NOVO"},
            destino={**SAIDA_BASE, "orgao": "CE"},
        ),
        "• Saiu: PL 1831/2022 — perdeu as etiquetas: autoria NOVO",
    ),
    (
        a.evento("situacao", comissao_de="CREDN"),
        "• Situação: PL 1831/2022 — Aguardando Parecer → Pronta para Pauta (veio da CREDN)",
    ),
    (
        a.evento("relator", mudanca="devolveu", de=PRIMEIRO, para=None),
        "• Relator: PL 1831/2022 — devolveu Luiz Lima (NOVO)",
    ),
    (
        a.evento("relator", mudanca="substituido", de=PRIMEIRO, para=SEGUNDO),
        "• Relator: PL 1831/2022 — Luiz Lima (NOVO) → Diego Garcia (UNIÃO)",
    ),
    (
        a.evento(
            "etiquetas",
            ganhou=["autoria NOVO", "relatoria NOVO"],
            perdeu=["autor hoje no NOVO"],
        ),
        (
            "• Etiquetas: PL 1831/2022 — "
            "ganhou autoria NOVO, relatoria NOVO; perdeu autor hoje no NOVO"
        ),
    ),
    (
        a.evento("etiquetas", ganhou=[], perdeu=["autor hoje no NOVO"]),
        "• Etiquetas: PL 1831/2022 — perdeu autor hoje no NOVO",
    ),
]


@pytest.mark.parametrize(("evento", "esperado"), VARIANTES)
def test_detalhe_de_cada_variante_de_evento(evento, esperado):
    assert esperado in texto_normal(a.mudancas([evento])).split("\n")


def test_parecer_nao_reproduz_tramitacoes_nem_conteudo():
    evento = a.evento("parecer", "ce_a")
    evento["tramitacoes"] = [
        {
            "sequencia": 42,
            "data_hora": "2026-10-19T10:00",
            "orgao": "CE",
            "codigo": "322",
            "descricao": "TEXTO-DA-TRAMITACAO-QUE-NAO-PODE-APARECER",
        }
    ]

    texto = texto_normal(a.mudancas([evento]))

    assert "TEXTO-DA-TRAMITACAO" not in texto and "322" not in texto


def test_caracteres_especiais_saem_exatamente_como_entraram():
    especial = "_ * [ ] ( ) < > & # ~ ` \" ' \\ | { } = + - . !"
    evento = a.evento("situacao", "ce_a", de=f"de {especial}", para=f"para {especial} 😀")

    texto = texto_normal(a.mudancas([evento]))

    assert f"de {especial} → para {especial} 😀" in texto


# --- US2 ------------------------------------------------------------------------------------


def base(motivo, anterior=None):
    return a.mudancas(
        linha_de_base={"motivo": motivo, "total_itens": 105},
        **({"retrato_anterior": anterior} if anterior is not None else {}),
    )


def test_dia_sem_mudancas():
    assert texto_normal(a.mudancas()) == (
        "Monitor de comissões\nsem mudanças · 105 itens · dados de 20/10"
    )


def test_linha_de_base_do_primeiro_retrato():
    documento = a.mudancas(
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 105}, retrato_anterior=None
    )

    assert texto_normal(documento) == "\n".join(
        [
            "Monitor de comissões",
            "linha de base criada com 105 itens · dados de 20/10",
            "Primeiro retrato: ainda não há com o que comparar.",
        ]
    )


def test_linha_de_base_por_formato_incompativel_diz_o_motivo():
    assert texto_normal(base("formato anterior incompatível")) == "\n".join(
        [
            "Monitor de comissões",
            "linha de base criada com 105 itens · dados de 20/10",
            "O retrato anterior estava num formato incompatível: a comparação recomeça amanhã.",
        ]
    )


def test_linha_de_base_nao_tem_linha_de_intervalo_nem_eventos():
    anterior = {"dia": "2026-10-10", "dados_camara_em": "2026-10-10T04:31:26+00:00"}

    texto = texto_normal(base("formato anterior incompatível", anterior))

    assert "Cobre" not in texto and "evento" not in texto


def test_intervalo_de_varios_dias_com_eventos_vem_depois_do_cabecalho():
    documento = a.mudancas(
        [a.evento("parecer", "ce_a")],
        retrato_anterior={"dia": "2026-10-17", "dados_camara_em": "2026-10-17T04:31:26+00:00"},
    )

    linhas = texto_normal(documento).split("\n")

    assert linhas[1] == "1 evento: 1 parecer"
    assert linhas[2] == "Cobre de 17/10 a 20/10: um dia ficou sem retrato."
    assert linhas[3] == "" and linhas[4] == "CE"


def test_intervalo_de_varios_dias_sem_eventos():
    documento = a.mudancas(
        retrato_anterior={"dia": "2026-10-17", "dados_camara_em": "2026-10-17T04:31:26+00:00"}
    )

    assert texto_normal(documento) == "\n".join(
        [
            "Monitor de comissões",
            "sem mudanças · 105 itens · dados de 20/10",
            "Cobre de 17/10 a 20/10: um dia ficou sem retrato.",
        ]
    )


def test_intervalo_de_um_dia_nao_tem_linha_extra():
    assert "Cobre" not in texto_normal(a.mudancas([a.evento("parecer")]))


def test_nenhuma_dessas_mensagens_comeca_com_alerta():
    primeiro = a.mudancas(
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 105}, retrato_anterior=None
    )

    for documento in (a.mudancas(), primeiro):
        assert not texto_normal(documento).startswith("⚠")
