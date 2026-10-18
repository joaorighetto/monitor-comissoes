"""Arquivo de mudanças do dia (MUD): formato, validação e ordem (contracts/mudancas-json.md)."""

import copy
import json
from datetime import date

import pytest

from monitor_comissoes.erros import INTERNA, FalhaDeColeta
from monitor_comissoes.mudancas import (
    CAMPOS_PROPRIOS,
    TIPOS,
    evento,
    montar_arquivo,
    nome_do_arquivo,
    ordenar_eventos,
    validar_arquivo,
)
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
