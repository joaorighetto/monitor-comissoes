"""Arquivo de mudanças do dia (MUD): formato, validação e ordem (contracts/mudancas-json.md)."""

import copy
import json
from datetime import date

import pytest

import sinteticos as s
from monitor_comissoes.erros import INTERNA, FalhaDeColeta
from monitor_comissoes.mudancas import (
    CAMPOS_PROPRIOS,
    TIPOS,
    comparar,
    evento,
    montar_arquivo,
    nome_do_arquivo,
    ordenar_eventos,
    validar_arquivo,
)
from monitor_comissoes.retratos import Comparacao
from monitor_comissoes.saida import serializar
from monitor_comissoes.tramitacoes import Tramitacao

LINK = "https://www.camara.leg.br/propostas-legislativas/"
RETRATO = {"dia": "2026-10-19", "dados_camara_em": "2026-10-19T04:31:36+00:00"}
ANTERIOR = {"dia": "2026-10-18", "dados_camara_em": "2026-10-18T04:31:36+00:00"}
TRAMITACAO = Tramitacao(42, "2026-10-17T10:00", "CE", "322", "Parecer do(a) Relator(a)", None)
RELATOR = {"id": 204455, "nome": "Luiz Lima", "partido_hoje": "NOVO"}
OUTRO = {"id": 204528, "nome": "Adriana Ventura", "partido_hoje": "NOVO"}


def um(tipo, id=1, comissao="CE", **proprios):
    padrao = {
        "entrou": {
            "motivo": {"codigo": "chegou_a_comissao", "texto": "chegou à comissão"},
            "etiquetas": ["autoria NOVO"],
        },
        "saiu": {
            "motivo": {"codigo": "outro_orgao", "texto": "foi para outro órgão"},
            "destino": {"orgao": "CFT", "situacao": "Aguardando Parecer", "apensado_a": None},
            "outros_fatos": [],
        },
        "situacao": {"de": "Aguardando Parecer", "para": "Pronta para Pauta"},
        "relator": {"mudanca": "designado", "de": None, "para": RELATOR},
        "parecer": {},
        "etiquetas": {"ganhou": ["relatoria NOVO"], "perdeu": []},
    }[tipo]
    padrao.update(proprios)
    return evento(
        tipo,
        id=id,
        identificacao=f"PL {id}/2020",
        comissao=comissao,
        link=f"{LINK}{id}",
        tramitacoes=[TRAMITACAO],
        **padrao,
    )


def arquivo(eventos=None, **argumentos):
    padrao = {
        "data": date(2026, 10, 19),
        "retrato": RETRATO,
        "retrato_anterior": ANTERIOR,
        "linha_de_base": None,
        "eventos": eventos
        if eventos is not None
        else [um(t, id=i) for i, t in enumerate(TIPOS, 1)],
        "ressalvas": [],
    }
    padrao.update(argumentos)
    return montar_arquivo(**padrao)


def invalido(documento, trecho):
    with pytest.raises(FalhaDeColeta) as erro:
        validar_arquivo(documento)
    assert erro.value.categoria == INTERNA
    assert trecho in erro.value.motivo


# --- montar_arquivo -------------------------------------------------------------------------


def test_nome_do_arquivo_e_a_data_da_execucao():
    assert nome_do_arquivo(date(2026, 10, 19)) == "2026-10-19.json"


def test_o_arquivo_tem_meta_eventos_e_ressalvas_na_ordem_fixa():
    documento = arquivo()

    assert list(documento) == ["meta", "eventos", "ressalvas"]
    assert list(documento["meta"]) == [
        "versao_formato",
        "data",
        "retrato",
        "retrato_anterior",
        "linha_de_base",
        "total_eventos",
        "total_por_tipo",
    ]
    assert documento["meta"]["versao_formato"] == 1
    assert documento["meta"]["data"] == "2026-10-19"
    assert documento["meta"]["retrato"] == RETRATO
    assert documento["meta"]["retrato_anterior"] == ANTERIOR
    assert documento["meta"]["linha_de_base"] is None
    validar_arquivo(documento)


def test_total_por_tipo_sempre_tem_as_seis_chaves_na_ordem():
    vazio = arquivo(eventos=[])
    com_dois = arquivo(eventos=[um("saiu", 1), um("saiu", 2), um("parecer", 3)])

    assert list(vazio["meta"]["total_por_tipo"]) == list(TIPOS)
    assert TIPOS == ("entrou", "saiu", "situacao", "relator", "parecer", "etiquetas")
    assert all(v == 0 for v in vazio["meta"]["total_por_tipo"].values())
    assert vazio["meta"]["total_eventos"] == 0
    assert com_dois["meta"]["total_por_tipo"] == {
        "entrou": 0,
        "saiu": 2,
        "situacao": 0,
        "relator": 0,
        "parecer": 1,
        "etiquetas": 0,
    }
    assert com_dois["meta"]["total_eventos"] == 3


def test_cada_tipo_de_evento_tem_os_campos_comuns_e_os_proprios_na_ordem_do_contrato():
    for tipo in TIPOS:
        campos = list(um(tipo))
        assert campos == [
            "tipo",
            "id",
            "identificacao",
            "comissao",
            "link",
            *CAMPOS_PROPRIOS[tipo],
            "tramitacoes",
        ]
    assert CAMPOS_PROPRIOS == {
        "entrou": ("motivo", "etiquetas"),
        "saiu": ("motivo", "destino", "outros_fatos"),
        "situacao": ("de", "para"),
        "relator": ("mudanca", "de", "para"),
        "parecer": (),
        "etiquetas": ("ganhou", "perdeu"),
    }


def test_a_tramitacao_sai_com_cinco_campos_e_sem_despacho_nem_relator():
    com_despacho = Tramitacao(
        43, "2026-10-17T11:00", "CE", "502", "Arquivamento", 204455, "Arquivado nos termos do 105"
    )

    [saida] = evento(
        "parecer", id=1, identificacao="PL 1/2020", comissao="CE", link=f"{LINK}1",
        tramitacoes=[com_despacho],
    )["tramitacoes"]  # fmt: skip

    assert saida == {
        "sequencia": 43,
        "data_hora": "2026-10-17T11:00",
        "orgao": "CE",
        "codigo": "502",
        "descricao": "Arquivamento",
    }
    assert list(saida) == ["sequencia", "data_hora", "orgao", "codigo", "descricao"]


def test_evento_exige_exatamente_os_campos_proprios_do_tipo():
    with pytest.raises(ValueError, match="motivo"):
        evento("entrou", id=1, identificacao="x", comissao="CE", link="x", etiquetas=[])
    with pytest.raises(ValueError, match="extra"):
        evento("parecer", id=1, identificacao="x", comissao="CE", link="x", extra=1)
    with pytest.raises(ValueError, match="tipo"):
        evento("movimentacao", id=1, identificacao="x", comissao="CE", link="x")


def test_linha_de_base_nao_tem_eventos_nem_ressalvas():
    documento = arquivo(
        eventos=[],
        retrato_anterior=None,
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 23},
    )

    assert documento["meta"]["linha_de_base"] == {"motivo": "primeiro retrato", "total_itens": 23}
    assert documento["meta"]["retrato_anterior"] is None
    assert documento["eventos"] == [] and documento["ressalvas"] == []
    validar_arquivo(documento)


def test_serializacao_igual_a_dos_outros_arquivos_de_dados():
    documento = arquivo()
    texto = serializar(documento)

    assert texto.endswith("}\n") and not texto.endswith("\n\n")
    assert json.loads(texto) == documento
    assert '"identificacao": "PL 1/2020"' in texto
    assert "\\u" not in texto  # ensure_ascii desligado: "chegou à comissão" sai legível
    assert "chegou à comissão" in texto
    assert texto.startswith('{\n  "meta": {\n    "versao_formato": 1,')


# --- validar_arquivo: o que passa -------------------------------------------------------------


def test_arquivo_valido_com_um_evento_de_cada_tipo_passa():
    validar_arquivo(arquivo())


def test_mesmo_item_pode_ter_um_evento_de_cada_tipo():
    eventos = [um(tipo, id=7) for tipo in TIPOS]

    validar_arquivo(arquivo(eventos=eventos))


# --- validar_arquivo: regra 1, totais ----------------------------------------------------------


def test_total_de_eventos_que_nao_bate_falha():
    documento = arquivo()
    documento["meta"]["total_eventos"] += 1

    invalido(documento, "total_eventos")


def test_total_por_tipo_que_nao_bate_ou_sem_as_seis_chaves_falha():
    documento = arquivo()
    documento["meta"]["total_por_tipo"]["saiu"] += 1
    invalido(documento, "total_por_tipo")

    documento = arquivo()
    del documento["meta"]["total_por_tipo"]["parecer"]
    invalido(documento, "total_por_tipo")


def test_campos_do_meta_fora_da_ordem_ou_a_mais_falham():
    documento = arquivo()
    documento["meta"]["extra"] = 1
    invalido(documento, "meta")

    documento = arquivo()
    meta = documento["meta"]
    documento["meta"] = {"data": meta.pop("data"), **meta}
    invalido(documento, "meta")


# --- validar_arquivo: regra 2, linha de base ----------------------------------------------------


def test_linha_de_base_com_evento_falha():
    documento = arquivo(linha_de_base={"motivo": "primeiro retrato", "total_itens": 1})

    invalido(documento, "linha de base")


def test_linha_de_base_com_ressalva_falha():
    documento = arquivo(
        eventos=[],
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 1},
        ressalvas=[
            {
                "id": 1,
                "identificacao": "PL 1/2020",
                "comissao": "CE",
                "link": f"{LINK}1",
                "motivo": "relator indeterminado hoje",
            }
        ],
    )

    invalido(documento, "linha de base")


@pytest.mark.parametrize("motivo", ["", "outro", None, 3])
def test_motivo_de_linha_de_base_desconhecido_falha(motivo):
    documento = arquivo(eventos=[], linha_de_base={"motivo": motivo, "total_itens": 1})

    invalido(documento, "linha de base")


def test_sem_linha_de_base_o_retrato_anterior_e_obrigatorio():
    documento = arquivo(retrato_anterior=None)

    invalido(documento, "retrato_anterior")


def test_linha_de_base_por_formato_incompativel_pode_trazer_o_retrato_anterior():
    documento = arquivo(
        eventos=[],
        linha_de_base={"motivo": "formato anterior incompatível", "total_itens": 5},
    )

    validar_arquivo(documento)
    assert documento["meta"]["retrato_anterior"] == ANTERIOR


# --- validar_arquivo: regra 3, link e motivo ----------------------------------------------------


@pytest.mark.parametrize("link", ["", "https://exemplo.com/1", None, 5])
def test_evento_sem_link_oficial_falha(link):
    documento = arquivo()
    documento["eventos"][0]["link"] = link

    invalido(documento, "link")


@pytest.mark.parametrize("tipo", ["entrou", "saiu"])
@pytest.mark.parametrize(
    "motivo", [None, {}, {"codigo": "", "texto": "x"}, {"codigo": "x", "texto": ""}]
)
def test_motivo_vazio_em_entrou_ou_saiu_falha(tipo, motivo):
    documento = arquivo(eventos=[um(tipo)])
    documento["eventos"][0]["motivo"] = motivo

    invalido(documento, "motivo")


def test_codigo_de_motivo_desconhecido_falha():
    documento = arquivo(eventos=[um("saiu")])
    documento["eventos"][0]["motivo"]["codigo"] = "inventado"

    invalido(documento, "motivo")


def test_tipo_de_evento_desconhecido_falha():
    documento = arquivo()
    documento["eventos"][0]["tipo"] = "movimentacao"

    invalido(documento, "tipo")


def test_relator_com_mudanca_incoerente_falha():
    for proprios in (
        {"mudanca": "designado", "de": RELATOR, "para": OUTRO},
        {"mudanca": "devolveu", "de": None, "para": None},
        {"mudanca": "substituido", "de": None, "para": OUTRO},
        {"mudanca": "inventado", "de": None, "para": OUTRO},
    ):
        documento = arquivo(eventos=[um("relator", **proprios)])
        invalido(documento, "relator")


def test_etiquetas_sem_ganho_nem_perda_falha():
    documento = arquivo(eventos=[um("etiquetas", ganhou=[], perdeu=[])])

    invalido(documento, "etiquetas")


# --- validar_arquivo: regras 4 e 6, repetição e tramitações --------------------------------------


def test_o_mesmo_item_com_dois_eventos_do_mesmo_tipo_falha():
    documento = arquivo(eventos=[um("situacao", 1), um("situacao", 1)])

    invalido(documento, "repetido")


def test_tramitacoes_fora_de_ordem_ou_repetidas_falham():
    for sequencias in ([43, 42], [42, 42]):
        documento = arquivo(eventos=[um("parecer")])
        documento["eventos"][0]["tramitacoes"] = [
            {"sequencia": s, "data_hora": "2026-10-17T10:00", "orgao": "CE", "codigo": "322",
             "descricao": "x"}
            for s in sequencias
        ]  # fmt: skip

        invalido(documento, "tramitacoes")


def test_tramitacao_com_campo_faltando_ou_de_tipo_errado_falha():
    for ruim in (
        {"sequencia": 1, "data_hora": "x", "orgao": "CE", "codigo": "1"},
        {"sequencia": "1", "data_hora": "x", "orgao": "CE", "codigo": "1", "descricao": "x"},
        {"sequencia": True, "data_hora": "x", "orgao": "CE", "codigo": "1", "descricao": "x"},
    ):
        documento = arquivo(eventos=[um("parecer")])
        documento["eventos"][0]["tramitacoes"] = [ruim]

        invalido(documento, "tramitacoes")


def test_evento_sem_a_lista_de_tramitacoes_falha():
    documento = arquivo(eventos=[um("parecer")])
    del documento["eventos"][0]["tramitacoes"]

    invalido(documento, "campos")


# --- ressalvas ------------------------------------------------------------------------------


def test_ressalva_valida_passa_e_invalida_falha():
    ressalva = {
        "id": 1,
        "identificacao": "PL 1/2020",
        "comissao": "CE",
        "link": f"{LINK}1",
        "motivo": "relator indeterminado nos dois retratos",
    }
    validar_arquivo(arquivo(eventos=[], ressalvas=[ressalva]))

    for mudanca in ({"motivo": ""}, {"link": "https://exemplo.com"}, {"id": "1"}):
        documento = arquivo(eventos=[], ressalvas=[{**ressalva, **mudanca}])
        invalido(documento, "ressalva")


# --- ordenar_eventos --------------------------------------------------------------------------


def test_ordem_por_comissao_da_configuracao_depois_tipo_depois_id():
    eventos = [
        um("situacao", 5, "CREDN"),
        um("saiu", 9, "CE"),
        um("entrou", 8, "CE"),
        um("saiu", 3, "CE"),
        um("etiquetas", 1, "CREDN"),
        um("entrou", 2, "CREDN"),
    ]

    ordenados = ordenar_eventos(eventos, ("CE", "CREDN"))

    assert [(e["comissao"], e["tipo"], e["id"]) for e in ordenados] == [
        ("CE", "entrou", 8),
        ("CE", "saiu", 3),
        ("CE", "saiu", 9),
        ("CREDN", "entrou", 2),
        ("CREDN", "situacao", 5),
        ("CREDN", "etiquetas", 1),
    ]


def test_comissao_fora_da_configuracao_vem_depois_por_sigla():
    eventos = [um("saiu", 1, "CFT"), um("saiu", 2, "CE"), um("saiu", 3, "CCJC")]

    ordenados = ordenar_eventos(eventos, ("CE", "CREDN"))

    assert [e["comissao"] for e in ordenados] == ["CE", "CCJC", "CFT"]


def test_ordenar_nao_altera_a_lista_de_entrada_e_independe_da_ordem_dela():
    eventos = [um("saiu", 3), um("entrou", 1), um("saiu", 2, "CREDN")]
    copia = copy.deepcopy(eventos)

    a = ordenar_eventos(eventos, ("CE", "CREDN"))
    b = ordenar_eventos(list(reversed(eventos)), ("CE", "CREDN"))

    assert eventos == copia
    assert a == b


# --- comparar: linha de base (User Story 3) -----------------------------------------------------

HOJE = date(2026, 10, 19)


def sem_tramitacoes(id_referencia):
    raise AssertionError("a linha de base não consulta tramitações")


def hoje_sintetico():
    return s.retrato(
        [s.item(1), s.item(2), s.item(3, comissao="CREDN")],
        gerado_em="2026-10-19T03:40:12-03:00",
        dados_camara_em="2026-10-19T04:31:36+00:00",
    )


def preparado(motivo, retrato_anterior=None):
    return Comparacao(
        anterior=None,
        motivo_linha_de_base=motivo,
        retrato_anterior=retrato_anterior,
        copia_anterior=None,
    )


def test_primeiro_retrato_vira_linha_de_base_sem_eventos_e_sem_consultar_tramitacoes():
    documento = comparar(
        preparado("primeiro retrato"),
        hoje_sintetico(),
        {},
        sem_tramitacoes,
        ("CE", "CREDN"),
        HOJE,
    )

    validar_arquivo(documento)
    meta = documento["meta"]
    assert meta["data"] == "2026-10-19"
    assert meta["retrato"] == {"dia": "2026-10-19", "dados_camara_em": "2026-10-19T04:31:36+00:00"}
    assert meta["retrato_anterior"] is None
    assert meta["linha_de_base"] == {"motivo": "primeiro retrato", "total_itens": 3}
    assert meta["total_eventos"] == 0
    assert documento["eventos"] == [] and documento["ressalvas"] == []


def test_formato_incompativel_vira_linha_de_base_e_traz_o_retrato_anterior_informativo():
    anterior = {"dia": "2026-10-18", "dados_camara_em": "2026-10-18T04:31:36+00:00"}

    documento = comparar(
        preparado("formato anterior incompatível", anterior),
        hoje_sintetico(),
        {},
        sem_tramitacoes,
        ("CE", "CREDN"),
        HOJE,
    )

    validar_arquivo(documento)
    assert documento["meta"]["retrato_anterior"] == anterior
    assert documento["meta"]["linha_de_base"] == {
        "motivo": "formato anterior incompatível",
        "total_itens": 3,
    }
    assert documento["eventos"] == []


def test_o_arquivo_nao_tem_horario_de_execucao():
    a = comparar(
        preparado("primeiro retrato"), hoje_sintetico(), {}, sem_tramitacoes, ("CE",), HOJE
    )
    outro = hoje_sintetico()
    outro["meta"]["gerado_em"] = "2026-10-19T03:59:59-03:00"  # só a hora da execução muda

    b = comparar(preparado("primeiro retrato"), outro, {}, sem_tramitacoes, ("CE",), HOJE)

    assert serializar(a) == serializar(b)
    assert "gerado_em" not in serializar(a)


def test_retrato_do_dia_usa_a_data_de_gerado_em_em_brasilia():
    hoje = hoje_sintetico()
    hoje["meta"]["gerado_em"] = "2026-10-20T01:30:00+00:00"  # 22:30 de 19/10 em Brasília

    documento = comparar(preparado("primeiro retrato"), hoje, {}, sem_tramitacoes, ("CE",), HOJE)

    assert documento["meta"]["retrato"]["dia"] == "2026-10-19"


# --- comparar: entrou e saiu (User Story 1) -----------------------------------------------------

from conftest import TransporteFalso  # noqa: E402
from monitor_comissoes.erros import FORMATO_ALTERADO  # noqa: E402
from monitor_comissoes.estoque import EstadoDeSaida  # noqa: E402
from monitor_comissoes.retratos import ler  # noqa: E402
from monitor_comissoes.tramitacoes import obter_tramitacoes  # noqa: E402

URL_BASE = "https://dadosabertos.camara.leg.br"
COMISSOES = ("CE", "CREDN")
PL_3514_2023 = 2373721  # CREDN: recebida em 08/07/2025, sequência 29 (real)
PL_4501_2023 = 2388105  # CE: recebida em 25/09/2023, última sequência 26 (real)
PL_COM_MESA = 1212477  # CE desde 2015, com dezenas de idas e voltas pela MESA (real)
PL_ARQUIVADO = 2086175  # parecer na sequência 37; arquivado (art. 105) na 42 (real)


def real(id_proposicao):
    return obter_tramitacoes(TransporteFalso(), URL_BASE, id_proposicao)


def t(sequencia, data_hora="2026-10-17T10:00", orgao="CE", codigo="9999", descricao="derivada",
      despacho=""):  # fmt: skip
    return Tramitacao(sequencia, data_hora, orgao, codigo, descricao, None, despacho)


class Fonte:
    """`obter_tramitacoes` injetado: devolve listas prontas e registra quem foi consultado."""

    def __init__(self, listas=None):
        self.listas = listas or {}
        self.consultas = []

    def __call__(self, id_referencia):
        self.consultas.append(id_referencia)
        if id_referencia not in self.listas:
            raise AssertionError(f"consulta inesperada às tramitações de {id_referencia}")
        return sorted(self.listas[id_referencia], key=lambda x: x.sequencia)


def preparado_com(documento):
    anterior = ler(json.dumps(documento), "anterior")
    informativo = {
        "dia": anterior.dia.isoformat(),
        "dados_camara_em": documento["meta"]["dados_camara_em"],
    }
    return Comparacao(anterior, None, informativo, None)


def hoje_com(itens, **argumentos):
    return s.retrato(
        itens,
        gerado_em="2026-10-19T03:40:12-03:00",
        dados_camara_em="2026-10-19T04:31:36+00:00",
        **argumentos,
    )


def anterior_com(itens, dados_camara_em):
    return s.retrato(itens, dados_camara_em=dados_camara_em)


def rodar(anterior, hoje, fonte, estados=None):
    documento = comparar(
        preparado_com(anterior), hoje, estados or {}, fonte, COMISSOES, date(2026, 10, 19)
    )
    validar_arquivo(documento)
    return documento


def so(documento, tipo):
    return [e for e in documento["eventos"] if e["tipo"] == tipo]


def sequencias(evento_):
    return [x["sequencia"] for x in evento_["tramitacoes"]]


# ---- entrou ----


def chegada_real(dados_camara_em_anterior, etiquetas=("autoria NOVO",), **item_extra):
    item = s.item(PL_3514_2023, comissao="CREDN", sequencia=29, etiquetas=etiquetas, **item_extra)
    fonte = Fonte({PL_3514_2023: real(PL_3514_2023)})
    documento = rodar(anterior_com([], dados_camara_em_anterior), hoje_com([item]), fonte)
    return documento, fonte


def test_entrou_porque_chegou_a_comissao_depois_do_retrato_anterior():
    documento, fonte = chegada_real("2025-07-07T04:30:00+00:00")  # lote de 07/07; chegou em 08/07

    [entrada] = so(documento, "entrou")
    assert entrada["motivo"] == {"codigo": "chegou_a_comissao", "texto": "chegou à comissão"}
    assert (entrada["id"], entrada["comissao"], entrada["etiquetas"]) == (
        PL_3514_2023,
        "CREDN",
        ["autoria NOVO"],
    )
    assert entrada["link"].endswith(f"/{PL_3514_2023}")
    assert 29 in sequencias(entrada) and max(sequencias(entrada)) == 29
    assert all(x["data_hora"][:10] >= "2025-07-07" for x in entrada["tramitacoes"])
    assert fonte.consultas == [PL_3514_2023]


def test_a_chegada_no_mesmo_dia_do_lote_anterior_conta_como_posterior():
    # Janela de um dia (plan.md, D5): o lote anterior é de 08/07 em Brasília e a chegada é de 08/07.
    documento, _ = chegada_real("2025-07-08T04:31:36+00:00")

    [entrada] = so(documento, "entrou")
    assert entrada["motivo"]["codigo"] == "chegou_a_comissao"


def test_entrou_porque_ganhou_etiqueta_e_o_texto_diz_qual():
    documento, _ = chegada_real("2025-07-09T04:30:00+00:00", etiquetas=("autor hoje no NOVO",))

    [entrada] = so(documento, "entrou")
    assert entrada["motivo"] == {
        "codigo": "ganhou_etiqueta",
        "texto": "ganhou etiqueta: autor hoje no NOVO",
    }
    assert entrada["tramitacoes"] == []  # nada lançado depois de 09/07 até a sequência 29


def test_entrou_sem_etiqueta_e_sem_chegada_recente_e_nao_determinado():
    documento, _ = chegada_real(
        "2025-07-09T04:30:00+00:00",
        etiquetas=(),
        relator_indeterminado={"motivo": "designação sem relator identificado"},
    )

    [entrada] = so(documento, "entrou")
    assert entrada["motivo"] == {"codigo": "nao_determinado", "texto": "não determinado"}
    assert entrada["etiquetas"] == []


def test_entrou_ignora_tramitacoes_lancadas_depois_do_lote_de_hoje():
    lista = [*real(PL_3514_2023), t(30, "2025-07-09T10:00", "CREDN", "500", "Recebimento")]
    item = s.item(PL_3514_2023, comissao="CREDN", sequencia=29)

    documento = rodar(
        anterior_com([], "2025-07-07T04:30:00+00:00"),
        hoje_com([item]),
        Fonte({PL_3514_2023: lista}),
    )

    [entrada] = so(documento, "entrou")
    assert max(sequencias(entrada)) == 29  # a 30 aparece amanhã


def test_materia_que_saiu_e_voltou_conta_a_volta_como_chegada():
    base = real(PL_4501_2023)
    lista = [
        *base,
        t(27, "2026-02-01T10:00", "CFT", "500", "Recebimento"),
        t(28, "2026-03-01T10:00", "CE", "500", "Recebimento"),
    ]
    item = s.item(PL_4501_2023, sequencia=28)

    antes_da_volta = rodar(
        anterior_com([], "2026-02-15T04:30:00+00:00"),
        hoje_com([item]),
        Fonte({PL_4501_2023: lista}),
    )
    depois_da_volta = rodar(
        anterior_com([], "2026-03-02T04:30:00+00:00"),
        hoje_com([item]),
        Fonte({PL_4501_2023: lista}),
    )

    assert so(antes_da_volta, "entrou")[0]["motivo"]["codigo"] == "chegou_a_comissao"
    assert so(depois_da_volta, "entrou")[0]["motivo"]["codigo"] == "ganhou_etiqueta"


def test_ida_e_volta_pela_mesa_nao_e_chegada_nova():
    item = s.item(PL_COM_MESA, sequencia=63)  # CE desde 2015; a última tramitação é da MESA
    fonte = Fonte({PL_COM_MESA: real(PL_COM_MESA)})

    documento = rodar(anterior_com([], "2026-06-01T04:30:00+00:00"), hoje_com([item]), fonte)

    [entrada] = so(documento, "entrou")
    assert entrada["motivo"]["codigo"] == "ganhou_etiqueta"  # a chegada à CE é de 2015
    assert sequencias(entrada) == [63]  # só o lançado desde 01/06/2026


def test_apensado_que_entrou_consulta_a_referencia_e_uma_vez_so_por_referencia():
    principal = s.apensado(PL_3514_2023, "PL 3514/2023")
    a = s.item(101, comissao="CREDN", sequencia=29, apensado_a=principal)
    b = s.item(102, comissao="CREDN", sequencia=29, apensado_a=principal)
    fonte = Fonte({PL_3514_2023: real(PL_3514_2023)})

    documento = rodar(anterior_com([], "2025-07-07T04:30:00+00:00"), hoje_com([a, b]), fonte)

    assert [e["id"] for e in so(documento, "entrou")] == [101, 102]
    assert fonte.consultas.count(PL_3514_2023) == 1


def test_resposta_sem_a_sequencia_do_lote_de_hoje_e_formato_alterado():
    item = s.item(PL_3514_2023, comissao="CREDN", sequencia=999)

    with pytest.raises(FalhaDeColeta) as erro:
        rodar(
            anterior_com([], "2025-07-07T04:30:00+00:00"),
            hoje_com([item]),
            Fonte({PL_3514_2023: real(PL_3514_2023)}),
        )

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "999" in erro.value.motivo and str(PL_3514_2023) in erro.value.motivo


# ---- saiu ----


def previsto(id=1, **extra):
    return s.item(id, sequencia=41, etiquetas=("autoria NOVO",), **extra)


def estado(**campos):
    padrao = {
        "existe": True,
        "referencia_id": 1,
        "orgao": "CFT",
        "situacao": "Aguardando Parecer",
        "sequencia": 45,
        "apensado_a": None,
        "na_comissao": False,
    }
    padrao.update(campos)
    return EstadoDeSaida(**padrao)


def saiu(item_a, estado_, listas=None, itens_hoje=()):
    fonte = Fonte(listas or {})
    documento = rodar(
        anterior_com([item_a], "2026-10-18T04:31:36+00:00"),
        hoje_com(list(itens_hoje)),
        fonte,
        {item_a["id"]: estado_},
    )
    [evento_] = so(documento, "saiu")
    return evento_, fonte


SEGUE_AO_SENADO = "aprovado, segue ao Senado"
VIROU_NORMA = "transformado em norma jurídica"


def lista_do_intervalo(referencia=1, de=41, ate=45):
    return {referencia: [t(n) for n in range(de - 1, ate + 3)]}  # com sobra antes e depois


def test_saiu_arquivado_pelo_art_105_com_a_tramitacao_real():
    item_a = s.item(PL_ARQUIVADO, sequencia=37, situacao="Pronta para Pauta")
    situacao = estado(referencia_id=PL_ARQUIVADO, orgao="MESA", situacao="Arquivada", sequencia=43)

    saida, _ = saiu(item_a, situacao, {PL_ARQUIVADO: real(PL_ARQUIVADO)})

    assert saida["motivo"] == {"codigo": "arquivado_art_105", "texto": "arquivado, art. 105"}
    assert saida["destino"] == {"orgao": "MESA", "situacao": "Arquivada", "apensado_a": None}
    assert saida["outros_fatos"] == ["outro_orgao"]
    assert saida["comissao"] == "CE" and saida["id"] == PL_ARQUIVADO
    assert sequencias(saida) == [42, 43]  # (37, 43] na ordem; 38 a 41 são de outro tipo ou ausentes


def test_saiu_arquivado_sem_a_mencao_ao_art_105():
    item_a = s.item(PL_ARQUIVADO, sequencia=37)
    lista = [
        x if x.sequencia != 42 else x._replace(despacho="Arquivado por decisão da Presidência.")
        for x in real(PL_ARQUIVADO)
    ]
    situacao = estado(referencia_id=PL_ARQUIVADO, orgao="MESA", situacao="Arquivada", sequencia=43)

    saida, _ = saiu(item_a, situacao, {PL_ARQUIVADO: lista})

    assert saida["motivo"] == {"codigo": "arquivado", "texto": "arquivado"}


def test_o_art_105_so_vale_na_tramitacao_de_arquivamento_do_intervalo():
    item_a = s.item(PL_ARQUIVADO, sequencia=37)
    situacao = estado(referencia_id=PL_ARQUIVADO, orgao="MESA", situacao="Arquivada", sequencia=39)
    base = [t(n) for n in range(30, 37)]
    cita = "Arquivado nos termos do Artigo 105 do RICD"

    def motivo(*extras):
        saida, _ = saiu(item_a, situacao, {PL_ARQUIVADO: [*base, *extras]})
        return saida["motivo"]["codigo"]

    # 502 que cita o artigo, dentro do intervalo (37, 39]: vale.
    assert motivo(t(38, codigo="502", despacho=cita), t(39)) == "arquivado_art_105"
    # 640 (desarquivamento) que cita o artigo, no intervalo: não é arquivamento.
    assert (
        motivo(t(38, codigo="640", despacho=cita), t(39, codigo="502", despacho="x")) == "arquivado"
    )
    # 502 que cita o artigo, mas anterior ao intervalo (é de um arquivamento antigo): não vale.
    assert motivo(t(33, codigo="502", despacho=cita), t(38), t(39)) == "arquivado"
    # Escrita em maiúsculas e com ponto: o padrão reconhece "ART. 105".
    assert motivo(t(38, codigo="502", despacho="ARQUIVADO - ART. 105 DO RICD"), t(39)) == (
        "arquivado_art_105"
    )


@pytest.mark.parametrize(
    ("situacao", "codigo", "texto"),
    [
        ("Transformado em Norma Jurídica", "transformado_em_norma", VIROU_NORMA),
        ("Aguardando Apreciação pelo Senado Federal", "aprovado_segue_ao_senado", SEGUE_AO_SENADO),
        ("Enviada ao Senado Federal", "aprovado_segue_ao_senado", SEGUE_AO_SENADO),
        ("Recusado", "encerrado", "encerrado"),
        ("Retirado pelo(a) Autor(a)", "encerrado", "encerrado"),
        ("Tramitação Finalizada", "encerrado", "encerrado"),
    ],
)  # fmt: skip
def test_saiu_por_situacao_final(situacao, codigo, texto):
    saida, _ = saiu(
        previsto(),
        estado(orgao="MESA", situacao=situacao),
        lista_do_intervalo(),
    )

    assert saida["motivo"] == {"codigo": codigo, "texto": texto}
    assert saida["destino"]["situacao"] == situacao
    assert saida["outros_fatos"] == ["outro_orgao"]


def test_saiu_apensado_a_proposicao_fora_da_lista():
    raiz = s.apensado(99, "PL 3047/2015")
    situacao = estado(referencia_id=99, orgao="CFT", sequencia=87, apensado_a=raiz)

    saida, fonte = saiu(
        previsto(), situacao, {99: [t(n, "2026-10-18T10:00") for n in range(80, 90)]}
    )

    assert saida["motivo"] == {
        "codigo": "apensado_fora_da_lista",
        "texto": "apensado a uma proposição fora da lista",
    }
    assert saida["destino"]["apensado_a"] == raiz
    assert saida["outros_fatos"] == ["outro_orgao"]
    # A referência mudou: vale a data (desde o lote anterior, de 18/10) e a sequência de hoje (87).
    assert fonte.consultas == [99] and max(sequencias(saida)) == 87


def test_apensado_a_raiz_que_e_item_de_hoje_nao_e_fora_da_lista():
    raiz = s.apensado(99, "PL 3047/2015")
    situacao = estado(referencia_id=99, orgao="CE", sequencia=87, apensado_a=raiz, na_comissao=True)
    lista = {99: [t(n, "2026-10-18T10:00") for n in range(80, 90)]}

    saida, _ = saiu(previsto(), situacao, lista, itens_hoje=[s.item(99, sequencia=87)])

    assert saida["motivo"]["codigo"] == "perdeu_etiquetas"


def test_saiu_para_outro_orgao():
    saida, fonte = saiu(previsto(), estado(orgao="CFT", sequencia=45), lista_do_intervalo(ate=45))

    assert saida["motivo"] == {"codigo": "outro_orgao", "texto": "foi para outro órgão"}
    assert saida["destino"] == {
        "orgao": "CFT",
        "situacao": "Aguardando Parecer",
        "apensado_a": None,
    }
    assert saida["outros_fatos"] == []
    assert sequencias(saida) == [42, 43, 44, 45]  # (41, 45] na mesma referência
    assert fonte.consultas == [1]


def test_saiu_por_perder_as_etiquetas_sem_consultar_tramitacoes_se_a_sequencia_nao_mudou():
    item_a = s.item(1, sequencia=41, etiquetas=("autor hoje no NOVO", "relatoria NOVO"))
    situacao = estado(orgao="CE", sequencia=41, na_comissao=True)

    saida, fonte = saiu(item_a, situacao)

    assert saida["motivo"] == {
        "codigo": "perdeu_etiquetas",
        "texto": "perdeu as etiquetas: autor hoje no NOVO, relatoria NOVO",
    }
    assert saida["tramitacoes"] == []
    assert fonte.consultas == []  # nada mudou na tramitação: nenhuma consulta


def test_saiu_de_proposicao_ausente_do_lote_e_nao_determinado():
    saida, fonte = saiu(previsto(), EstadoDeSaida(False, None, None, None, None, None, False))

    assert saida["motivo"] == {"codigo": "nao_determinado", "texto": "não determinado"}
    assert saida["destino"] == {"orgao": None, "situacao": None, "apensado_a": None}
    assert saida["tramitacoes"] == [] and fonte.consultas == []


def test_precedencia_situacao_final_depois_apensado_depois_outro_orgao():
    raiz = s.apensado(99, "PL 3047/2015")
    situacao = estado(
        referencia_id=99,
        orgao="MESA",
        situacao="Transformado em Norma Jurídica",
        sequencia=87,
        apensado_a=raiz,
    )

    saida, _ = saiu(previsto(), situacao, {99: [t(n, "2026-10-18T10:00") for n in range(80, 90)]})

    assert saida["motivo"]["codigo"] == "transformado_em_norma"
    assert saida["outros_fatos"] == ["apensado_fora_da_lista", "outro_orgao"]


def test_situacao_fora_da_tabela_cai_em_outro_orgao_sem_erro():
    saida, _ = saiu(
        previsto(),
        estado(orgao="CFT", situacao="Aguardando Designação de Relator(a)"),
        lista_do_intervalo(),
    )

    assert saida["motivo"]["codigo"] == "outro_orgao"
    assert saida["destino"]["situacao"] == "Aguardando Designação de Relator(a)"


def test_quando_a_principal_sai_cada_apensado_sai_com_o_mesmo_motivo_e_destino():
    principal = s.item(10, sequencia=41)
    apensado_ = s.item(11, sequencia=41, apensado_a=s.apensado(10, "PL 10/2020"))
    destino = estado(referencia_id=10, orgao="CFT", sequencia=45)
    documento = rodar(
        anterior_com([principal, apensado_], "2026-10-18T04:31:36+00:00"),
        hoje_com([]),
        Fonte({10: [t(n) for n in range(40, 48)]}),
        {10: destino, 11: destino},
    )

    saidas = so(documento, "saiu")
    assert [e["id"] for e in saidas] == [10, 11]
    assert {(e["motivo"]["codigo"], e["destino"]["orgao"]) for e in saidas} == {
        ("outro_orgao", "CFT")
    }
    assert sequencias(saidas[0]) == sequencias(saidas[1]) == [42, 43, 44, 45]


def test_a_sequencia_de_hoje_menor_que_a_anterior_e_formato_alterado():
    with pytest.raises(FalhaDeColeta) as erro:
        saiu(previsto(), estado(sequencia=30), lista_do_intervalo())

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "30" in erro.value.motivo and "41" in erro.value.motivo


def test_o_evento_de_saida_usa_a_comissao_e_o_link_do_retrato_anterior():
    item_a = s.item(7, comissao="CREDN", sequencia=41, numero=77)

    saida, _ = saiu(item_a, estado(referencia_id=7, orgao="CFT", sequencia=41), None)

    assert (saida["comissao"], saida["identificacao"], saida["id"]) == ("CREDN", "PL 77/2020", 7)
    assert saida["link"] == item_a["link"]


def test_entrou_e_saiu_no_mesmo_dia_saem_ordenados_por_comissao_tipo_e_id():
    novo = s.item(50, comissao="CREDN", sequencia=29)
    velho = s.item(60, comissao="CE", sequencia=41)
    documento = rodar(
        anterior_com([velho], "2025-07-07T04:30:00+00:00"),
        hoje_com([novo]),
        Fonte({PL_3514_2023: real(PL_3514_2023)} | {50: real(PL_3514_2023)}),
        {60: estado(referencia_id=60, orgao="CFT", sequencia=41)},
    )

    assert [(e["comissao"], e["tipo"], e["id"]) for e in documento["eventos"]] == [
        ("CE", "saiu", 60),
        ("CREDN", "entrou", 50),
    ]


def test_candidato_so_indeterminado_que_sai_nao_tem_etiqueta_a_perder_e_fica_nao_determinado():
    item_a = s.item(1, sequencia=41, etiquetas=(), relator_indeterminado={"motivo": "x"})

    saida, _ = saiu(item_a, estado(orgao="CE", sequencia=41, na_comissao=True))

    assert saida["motivo"] == {"codigo": "nao_determinado", "texto": "não determinado"}


# --- comparar: itens que continuam na lista (User Story 2) ---------------------------------------

PL_COM_PARECERES = 2330962  # CCTI: pareceres do relator nas sequências 22 e 28 (reais)
LUIZ = {"id": 204455, "nome": "Luiz Lima", "partido_hoje": "NOVO"}
ADRIANA = {"id": 204528, "nome": "Adriana Ventura", "partido_hoje": "NOVO"}


def com_relator(dados, referencia=1):
    return s.relator(dados["id"], dados["nome"], dados["partido_hoje"], referencia)


def mantidos(a, h, listas=None):
    """Compara o mesmo item em dois dias e devolve (documento, fonte)."""
    fonte = Fonte(listas or {})
    documento = rodar(anterior_com([a], "2026-10-18T04:31:36+00:00"), hoje_com([h]), fonte)
    return documento, fonte


def dos_tipos(documento):
    return [e["tipo"] for e in documento["eventos"]]


def test_item_sem_nenhuma_diferenca_nao_aparece_e_nao_consulta_tramitacoes():
    item = s.item(1, sequencia=41)

    documento, fonte = mantidos(item, item)

    assert documento["eventos"] == [] and documento["ressalvas"] == []
    assert fonte.consultas == []
    assert documento["meta"]["linha_de_base"] is None


def test_situacao_de_para_com_o_texto_exato_e_sem_consulta_se_a_sequencia_nao_mudou():
    a = s.item(1, sequencia=41, situacao="Aguardando Parecer")
    h = s.item(1, sequencia=41, situacao="Pronta para Pauta")

    documento, fonte = mantidos(a, h)

    [mudanca] = so(documento, "situacao")
    assert (mudanca["de"], mudanca["para"]) == ("Aguardando Parecer", "Pronta para Pauta")
    assert mudanca["tramitacoes"] == [] and fonte.consultas == []
    assert dos_tipos(documento) == ["situacao"]


def test_situacao_com_sequencia_nova_traz_todas_as_tramitacoes_do_intervalo():
    a = s.item(1, sequencia=41, situacao="Aguardando Parecer")
    h = s.item(1, sequencia=43, situacao="Pronta para Pauta")
    lista = {1: [t(n) for n in range(40, 46)]}

    documento, fonte = mantidos(a, h, lista)

    [mudanca] = so(documento, "situacao")
    assert sequencias(mudanca) == [42, 43]  # (41, 43]: nem a 41 nem as lançadas depois do lote
    assert fonte.consultas == [1]


@pytest.mark.parametrize(
    ("antes", "depois", "mudanca", "de", "para"),
    [
        (None, LUIZ, "designado", None, LUIZ),
        (LUIZ, None, "devolveu", LUIZ, None),
        (LUIZ, ADRIANA, "substituido", LUIZ, ADRIANA),
    ],
)
def test_evento_de_relator(antes, depois, mudanca, de, para):
    a = s.item(1, relator=com_relator(antes) if antes else None)
    h = s.item(1, relator=com_relator(depois) if depois else None)

    documento, _ = mantidos(a, h)

    [evento_] = so(documento, "relator")
    assert (evento_["mudanca"], evento_["de"], evento_["para"]) == (mudanca, de, para)
    assert list(evento_["para"] or evento_["de"]) == ["id", "nome", "partido_hoje"]


def test_mesmo_relator_nao_e_evento_mesmo_que_o_partido_de_hoje_tenha_mudado():
    a = s.item(1, relator=com_relator(LUIZ))
    h = s.item(1, relator=com_relator({**LUIZ, "partido_hoje": "PL"}))

    documento, _ = mantidos(a, h)

    assert documento["eventos"] == [] and documento["ressalvas"] == []


def test_etiquetas_ganhou_perdeu_e_as_duas_coisas_em_ordem_fixa():
    ganhou, _ = mantidos(
        s.item(1, etiquetas=("autoria NOVO",)),
        s.item(1, etiquetas=("autoria NOVO", "autor hoje no NOVO", "relatoria NOVO")),
    )
    perdeu, _ = mantidos(
        s.item(1, etiquetas=("autoria NOVO", "autor hoje no NOVO")),
        s.item(1, etiquetas=("autoria NOVO",)),
    )
    troca, _ = mantidos(
        s.item(1, etiquetas=("autoria NOVO",)), s.item(1, etiquetas=("relatoria NOVO",))
    )

    assert (so(ganhou, "etiquetas")[0]["ganhou"], so(ganhou, "etiquetas")[0]["perdeu"]) == (
        ["autor hoje no NOVO", "relatoria NOVO"],
        [],
    )
    assert (so(perdeu, "etiquetas")[0]["ganhou"], so(perdeu, "etiquetas")[0]["perdeu"]) == (
        [],
        ["autor hoje no NOVO"],
    )
    assert (so(troca, "etiquetas")[0]["ganhou"], so(troca, "etiquetas")[0]["perdeu"]) == (
        ["relatoria NOVO"],
        ["autoria NOVO"],
    )


def test_item_com_varias_mudancas_tem_um_evento_por_tipo_na_ordem_dos_tipos():
    a = s.item(1, sequencia=41, situacao="Aguardando Parecer", etiquetas=("autoria NOVO",))
    h = s.item(
        1,
        sequencia=43,
        situacao="Pronta para Pauta",
        etiquetas=("autoria NOVO", "relatoria NOVO"),
        relator=com_relator(LUIZ),
    )

    documento, fonte = mantidos(a, h, {1: [t(n) for n in range(40, 46)]})

    assert dos_tipos(documento) == ["situacao", "relator", "etiquetas"]
    assert all(
        sequencias(e) == [42, 43] for e in documento["eventos"]
    )  # cada evento traz o intervalo
    assert fonte.consultas == [1]  # uma consulta só


def test_etiquetas_sem_mudanca_de_sequencia_nao_consultam_tramitacoes():
    a = s.item(1, sequencia=41, etiquetas=("autoria NOVO",))
    h = s.item(1, sequencia=41, etiquetas=("autoria NOVO", "autor hoje no NOVO"))

    documento, fonte = mantidos(a, h)

    [mudanca] = so(documento, "etiquetas")
    assert mudanca["ganhou"] == ["autor hoje no NOVO"] and mudanca["tramitacoes"] == []
    assert fonte.consultas == []


# ---- parecer ----


def parecer(sequencia_anterior, sequencia_de_hoje, comissao="CCTI", lista=None):
    a = s.item(PL_COM_PARECERES, comissao=comissao, sequencia=sequencia_anterior)
    h = s.item(PL_COM_PARECERES, comissao=comissao, sequencia=sequencia_de_hoje)
    return mantidos(a, h, {PL_COM_PARECERES: lista or real(PL_COM_PARECERES)})[0]


def test_dois_pareceres_reais_no_intervalo_geram_um_evento_com_todas_as_tramitacoes():
    documento = parecer(20, 30)

    [evento_] = so(documento, "parecer")
    assert sequencias(evento_) == list(range(21, 31))  # o intervalo todo, não só os pareceres
    assert evento_["link"].endswith(f"/{PL_COM_PARECERES}")
    assert dos_tipos(documento) == ["parecer"]  # o resto não é um dos seis tipos: sem mais eventos


def test_so_a_leitura_e_a_aprovacao_do_parecer_nao_geram_evento():
    documento = parecer(28, 30)

    assert documento["eventos"] == []


def test_parecer_exige_o_orgao_da_comissao_do_item():
    outro_orgao = [
        x._replace(orgao="CFT") if x.codigo == "322" else x for x in real(PL_COM_PARECERES)
    ]

    assert parecer(20, 30, lista=outro_orgao)["eventos"] == []
    assert parecer(20, 30, comissao="CE")["eventos"] == []  # item de outra comissão


def test_parecer_fora_do_intervalo_nao_conta():
    # Pareceres 22 e 28 são anteriores a 28 < s <= 30 e posteriores a s <= 21.
    assert parecer(28, 30)["eventos"] == []
    assert parecer(1, 21)["eventos"] == []  # (1, 21] não alcança a 22


def test_apenas_a_tramitacao_322_e_parecer_nao_a_501_do_mesmo_instante():
    so_501 = [x for x in real(PL_COM_PARECERES) if x.codigo != "322"]

    assert parecer(20, 30, lista=so_501)["eventos"] == []


# ---- ressalvas ----


@pytest.mark.parametrize(
    ("indeterminado_ontem", "indeterminado_hoje", "texto"),
    [
        (True, False, "relator indeterminado ontem"),
        (False, True, "relator indeterminado hoje"),
        (True, True, "relator indeterminado nos dois retratos"),
    ],
)
def test_relator_indeterminado_em_um_dos_retratos_vira_ressalva_e_nao_evento_de_relator(
    indeterminado_ontem, indeterminado_hoje, texto
):
    marca = {"motivo": "tipo de tramitação 9999 não reconhecido"}
    a = s.item(
        1,
        relator=None if indeterminado_ontem else com_relator(LUIZ),
        relator_indeterminado=marca if indeterminado_ontem else None,
    )
    h = s.item(
        1,
        relator=None if indeterminado_hoje else com_relator(ADRIANA),
        relator_indeterminado=marca if indeterminado_hoje else None,
    )

    documento, _ = mantidos(a, h)

    assert so(documento, "relator") == []
    [ressalva] = documento["ressalvas"]
    assert ressalva == {
        "id": 1,
        "identificacao": "PL 1/2020",
        "comissao": "CE",
        "link": a["link"],
        "motivo": texto,
    }


def test_a_ressalva_nao_impede_os_outros_eventos_do_item():
    marca = {"motivo": "x"}
    a = s.item(1, situacao="Aguardando Parecer", relator_indeterminado=marca)
    h = s.item(1, situacao="Pronta para Pauta", relator_indeterminado=marca)

    documento, _ = mantidos(a, h)

    assert dos_tipos(documento) == ["situacao"]
    assert len(documento["ressalvas"]) == 1


def test_ressalvas_saem_ordenadas_por_id():
    marca = {"motivo": "x"}
    itens_a = [s.item(i, relator_indeterminado=marca) for i in (30, 5, 12)]
    itens_h = [s.item(i, relator_indeterminado=marca) for i in (12, 30, 5)]

    documento = rodar(
        anterior_com(itens_a, "2026-10-18T04:31:36+00:00"), hoje_com(itens_h), Fonte()
    )

    assert [r["id"] for r in documento["ressalvas"]] == [5, 12, 30]


# ---- intervalo e referência (FR-014, FR-017) ----


def test_a_resposta_com_tramitacoes_posteriores_ao_lote_nao_entra_no_intervalo():
    a = s.item(1, sequencia=41, situacao="Aguardando Parecer")
    h = s.item(1, sequencia=43, situacao="Pronta para Pauta")
    lista = {1: [t(n) for n in range(40, 50)]}  # a API já tem até a 49

    documento, _ = mantidos(a, h, lista)

    assert max(sequencias(so(documento, "situacao")[0])) == 43


def test_tramitacoes_embaralhadas_saem_em_ordem_de_sequencia():
    a = s.item(1, sequencia=41, situacao="Aguardando Parecer")
    h = s.item(1, sequencia=44, situacao="Pronta para Pauta")
    embaralhada = [t(n) for n in (44, 42, 45, 43, 41)]

    documento, _ = mantidos(a, h, {1: embaralhada})

    assert sequencias(so(documento, "situacao")[0]) == [42, 43, 44]


def test_apensado_e_principal_compartilham_uma_so_consulta():
    principal = s.apensado(50, "PL 50/2020")
    a = [
        s.item(50, sequencia=41, situacao="Aguardando Parecer"),
        s.item(51, sequencia=41, situacao="Aguardando Parecer", apensado_a=principal),
    ]
    h = [
        s.item(50, sequencia=43, situacao="Pronta para Pauta"),
        s.item(51, sequencia=43, situacao="Pronta para Pauta", apensado_a=principal),
    ]
    fonte = Fonte({50: [t(n) for n in range(40, 46)]})

    documento = rodar(anterior_com(a, "2026-10-18T04:31:36+00:00"), hoje_com(h), fonte)

    assert [(e["id"], e["tipo"]) for e in documento["eventos"]] == [
        (50, "situacao"),
        (51, "situacao"),
    ]
    assert fonte.consultas == [50]  # o apensado e a principal dividem uma só leitura


def test_item_que_passou_a_ser_apensado_a_outra_principal_usa_a_regra_de_data():
    a = s.item(1, sequencia=41, situacao="Aguardando Parecer")
    h = s.item(
        1,
        sequencia=87,
        situacao="Pronta para Pauta",
        apensado_a=s.apensado(99, "PL 99/2019"),
    )
    lista = {99: [t(80, "2026-10-17T10:00"), t(85, "2026-10-18T10:00"), t(87, "2026-10-18T15:00")]}

    documento, fonte = mantidos(a, h, lista)

    # O lote anterior é de 18/10: entram as tramitações da NOVA referência a partir dessa data.
    assert sequencias(so(documento, "situacao")[0]) == [85, 87]
    assert fonte.consultas == [99]


def test_sequencia_que_regride_na_mesma_referencia_e_formato_alterado():
    a = s.item(1, sequencia=41, situacao="Aguardando Parecer")
    h = s.item(1, sequencia=30, situacao="Pronta para Pauta")

    with pytest.raises(FalhaDeColeta) as erro:
        mantidos(a, h, {1: [t(n) for n in range(25, 45)]})

    assert erro.value.categoria == FORMATO_ALTERADO
