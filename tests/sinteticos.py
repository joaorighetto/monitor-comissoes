"""Retratos sintéticos da MUD: itens e documentos no formato 3 do `atual.json`.

Os campos seguem um item real do `data/atual.json` (PL 5594/2020), com a ordem do contrato. Cada
teste altera um campo por vez. Nada aqui lê a rede nem o disco.
"""

import copy

from monitor_comissoes.saida import serializar

LINK = "https://www.camara.leg.br/propostas-legislativas/"
DEPUTADOS_NOVO = [
    {"id": 204455, "nome": "Luiz Lima"},
    {"id": 204528, "nome": "Adriana Ventura"},
]


def relator(id=204455, nome="Luiz Lima", partido_hoje="NOVO", referencia=None):
    return {
        "id": id,
        "nome": nome,
        "partido_hoje": partido_hoje,
        "designado_em": "2025-04-09T00:00:00",
        "fonte": f"{LINK}{referencia or 1}",
    }


def item(
    id=1,
    *,
    numero=None,
    ano=2020,
    comissao="CE",
    situacao="Aguardando Parecer",
    etiquetas=("autoria NOVO",),
    relator=None,
    relator_indeterminado=None,
    apensado_a=None,
    sequencia=41,
    ultimo_status_em="2023-03-28T00:00:00",
    principal_nao_localizada=False,
):
    """Um item completo, na ordem dos campos do contrato (versão 3)."""
    numero = numero or id
    return {
        "id": id,
        "tipo": "PL",
        "numero": numero,
        "ano": ano,
        "identificacao": f"PL {numero}/{ano}",
        "ementa": f"Ementa do PL {numero}/{ano}.",
        "data_apresentacao": "2020-12-18T13:51:00",
        "link": f"{LINK}{id}",
        "autores": [
            {
                "nome": "Adriana Ventura",
                "id_deputado": 204528,
                "partido_na_data": "NOVO",
                "ordem": 1,
            }
        ],
        "etiquetas": list(etiquetas),
        "comissao": comissao,
        "situacao": situacao,
        "ultimo_status_em": ultimo_status_em,
        "ultimo_status_sequencia": sequencia,
        "parado_ha_dias": 1300,
        "apensado_a": apensado_a,
        "principal_nao_localizada": principal_nao_localizada,
        "relator": relator,
        "relator_indeterminado": relator_indeterminado,
    }


def apensado(id, identificacao="PL 9/2019"):
    return {"id": id, "identificacao": identificacao, "link": f"{LINK}{id}"}


def retrato(
    itens,
    *,
    gerado_em="2026-10-18T03:40:12-03:00",
    dados_camara_em="2026-10-18T04:31:36+00:00",
    versao=3,
    comissoes=("CE", "CREDN"),
):
    """O documento completo (`meta` e `itens`). Em outra versão, só o `meta` é garantido."""
    por_comissao = {c: sum(1 for i in itens if i["comissao"] == c) for c in comissoes}
    return {
        "meta": {
            "versao_formato": versao,
            "gerado_em": gerado_em,
            "dados_camara_em": dados_camara_em,
            "comissoes": list(comissoes),
            "ano_minimo": 2003,
            "anos_lidos": [2003, 2026],
            "total_itens": len(itens),
            "total_por_comissao": por_comissao,
            "deputados_novo_em_exercicio": copy.deepcopy(DEPUTADOS_NOVO),
        },
        "itens": copy.deepcopy(list(itens)),
    }


def texto(documento):
    """O texto exato que o programa grava (UTF-8, indentação de 2, quebra de linha final)."""
    return serializar(documento)
