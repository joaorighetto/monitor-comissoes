"""Entradas sintéticas da AVI: arquivo de mudanças, `status.json` e `atual.json` do dia.

Seguem os contratos da MUD, da AGE e da COL; os ids, identificações e links vêm de itens reais do
`data/atual.json` de 20/10/2026. Nada aqui lê a rede nem o disco.
"""

import copy
from datetime import date, datetime

import sinteticos as s
from monitor_comissoes import mudancas as mud
from monitor_comissoes.status import montar_status

DIA = "2026-10-20"
DADOS_CAMARA_EM = "2026-10-20T04:31:26+00:00"
RETRATO_HOJE = {"dia": DIA, "dados_camara_em": DADOS_CAMARA_EM}
RETRATO_ONTEM = {"dia": "2026-10-19", "dados_camara_em": "2026-10-19T04:31:26+00:00"}

# Itens reais do data/atual.json (id, identificação, comissão).
ITENS_REAIS = {
    "ce_a": (2330962, "PL 1831/2022", "CE"),
    "ce_b": (2373671, "PL 3510/2023", "CE"),
    "ce_c": (148585, "PL 2752/2003", "CE"),
    "ce_d": (2380176, "PLP 173/2023", "CE"),
    "ce_e": (2345296, "PL 3075/2022", "CE"),
    "credn_a": (2345297, "PL 3076/2022", "CREDN"),
}


def _base(chave: str) -> dict:
    id, identificacao, comissao = ITENS_REAIS[chave]
    return {
        "id": id,
        "identificacao": identificacao,
        "comissao": comissao,
        "link": f"{s.LINK}{id}",
    }


def evento(tipo: str, chave: str = "ce_a", **proprios) -> dict:
    """Um evento válido de cada tipo, a partir de um item real; `proprios` sobrescreve campos."""
    padroes = {
        "entrou": {
            "motivo": {"codigo": "chegou_a_comissao", "texto": "chegou à comissão"},
            "etiquetas": ["autoria NOVO"],
        },
        "saiu": {
            "motivo": {"codigo": "outro_orgao", "texto": "foi para outro órgão"},
            "destino": {"orgao": "CFT", "situacao": "Aguardando Parecer", "apensado_a": None},
            "outros_fatos": [],
        },
        "situacao": {
            "de": "Aguardando Parecer",
            "para": "Pronta para Pauta",
            "comissao_de": _base(chave)["comissao"],
        },
        "relator": {
            "mudanca": "designado",
            "de": None,
            "para": {"id": 204455, "nome": "Luiz Lima", "partido_hoje": "NOVO"},
        },
        "parecer": {},
        "etiquetas": {"ganhou": ["relatoria NOVO"], "perdeu": []},
    }[tipo]
    campos = {**padroes, **proprios}
    return mud.evento(tipo, **_base(chave), **campos)


def ressalva(chave: str = "ce_b", motivo: str = "relator indeterminado hoje") -> dict:
    return {**_base(chave), "motivo": motivo}


def mudancas(
    eventos=(),
    ressalvas=(),
    *,
    linha_de_base=None,
    retrato=RETRATO_HOJE,
    retrato_anterior=RETRATO_ONTEM,
    dia: str = DIA,
) -> dict:
    """O arquivo de mudanças do dia, validado por `mudancas.validar_arquivo`."""
    documento = mud.montar_arquivo(
        data=date.fromisoformat(dia),
        retrato=copy.deepcopy(retrato),
        retrato_anterior=copy.deepcopy(retrato_anterior),
        linha_de_base=linha_de_base,
        eventos=list(eventos),
        ressalvas=list(ressalvas),
    )
    mud.validar_arquivo(documento)
    return documento


def completo() -> dict:
    """Um evento de cada tipo, em CE e CREDN, e uma ressalva de relator indeterminado."""
    return mudancas(
        [
            evento("entrou", "ce_a"),
            evento("saiu", "ce_b"),
            evento("situacao", "ce_c"),
            evento("relator", "ce_d"),
            evento("parecer", "ce_e"),
            evento("etiquetas", "credn_a"),
        ],
        [ressalva("ce_b")],
    )


def muitos_eventos(n: int, comissoes=("CE", "CREDN"), *, prefixo: str = "") -> dict:
    """`n` eventos de situação distribuídos em rodízio pelas comissões; ids e links únicos."""
    eventos = []
    for i in range(n):
        comissao = comissoes[i % len(comissoes)]
        id = 1_000_000 + i
        eventos.append(
            mud.evento(
                "situacao",
                id=id,
                identificacao=f"{prefixo}PL {i + 1}/2024",
                comissao=comissao,
                link=f"{s.LINK}{id}",
                de="Aguardando Parecer",
                para="Pronta para Pauta",
                comissao_de=comissao,
            )
        )
    return mudancas(eventos)


def status_ok(
    *,
    dia: str = DIA,
    total_itens: int = 105,
    dados_camara_em: str = DADOS_CAMARA_EM,
    verificado_em: str = "2026-10-20T03:45:00-03:00",
) -> dict:
    return montar_status(
        resultado="ok",
        verificado_em=datetime.fromisoformat(verificado_em),
        data_referencia=date.fromisoformat(dia),
        tentativas=1,
        falha=None,
        variacao_aceita=None,
        retrato={
            "gerado_em": f"{dia}T03:40:12-03:00",
            "dados_camara_em": dados_camara_em,
            "total_itens": total_itens,
            "estoque_bruto": 1531,
        },
    )


def status_falha(
    *,
    dia: str = DIA,
    categoria: str = "arquivos_desatualizados",
    motivo: str = "a Câmara não atualizou os arquivos",
    com_retrato_bom: bool = True,
    dados_camara_em: str = "2026-10-19T04:31:26+00:00",
    total_itens: int = 105,
) -> dict:
    retrato = None
    if com_retrato_bom:
        retrato = {
            "gerado_em": "2026-10-19T03:40:12-03:00",
            "dados_camara_em": dados_camara_em,
            "total_itens": total_itens,
            "estoque_bruto": 1531,
        }
    return montar_status(
        resultado="falha",
        verificado_em=datetime.fromisoformat(f"{dia}T03:50:00-03:00"),
        data_referencia=date.fromisoformat(dia),
        tentativas=4,
        falha={"categoria": categoria, "motivo": motivo},
        variacao_aceita=None,
        retrato=retrato,
    )


def atual(itens=None, *, versao: int = 3, dia: str = DIA) -> dict:
    """`atual.json` completo na versão 3 (ou só o `meta` coerente em outra versão)."""
    if itens is None:
        itens = [
            s.item(id=ITENS_REAIS["ce_a"][0], numero=1831, ano=2022),
            s.item(id=ITENS_REAIS["ce_b"][0], numero=3510, ano=2023),
            s.item(
                id=ITENS_REAIS["ce_c"][0],
                numero=2752,
                ano=2003,
                principal_nao_localizada=True,
            ),
            s.item(
                id=ITENS_REAIS["credn_a"][0],
                numero=3076,
                ano=2022,
                comissao="CREDN",
                principal_nao_localizada=True,
            ),
        ]
    return s.retrato(
        itens,
        gerado_em=f"{dia}T03:40:12-03:00",
        dados_camara_em=DADOS_CAMARA_EM,
        versao=versao,
    )


def cenarios() -> dict[str, dict]:
    """Os cenários de `tests/fixtures/aviso/`: nome -> {atual, status, mudancas|None}."""
    base_primeiro = mudancas(
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 105},
        retrato_anterior=None,
    )
    base_formato = mudancas(
        linha_de_base={"motivo": "formato anterior incompatível", "total_itens": 105}
    )
    return {
        "completo": {"atual": atual(), "status": status_ok(), "mudancas": completo()},
        "sem-eventos": {"atual": atual(), "status": status_ok(), "mudancas": mudancas()},
        "linha-base-primeiro": {
            "atual": atual(),
            "status": status_ok(),
            "mudancas": base_primeiro,
        },
        "linha-base-formato": {
            "atual": atual(),
            "status": status_ok(),
            "mudancas": base_formato,
        },
        "intervalo": {
            "atual": atual(),
            "status": status_ok(),
            "mudancas": mudancas(
                [evento("situacao", "ce_c")],
                retrato_anterior={
                    "dia": "2026-10-17",
                    "dados_camara_em": "2026-10-17T04:31:26+00:00",
                },
            ),
        },
        "falha": {"atual": atual(), "status": status_falha(), "mudancas": None},
        "sem-retrato": {
            "atual": atual(),
            "status": status_falha(com_retrato_bom=False),
            "mudancas": None,
        },
    }


__all__ = [
    "DIA",
    "atual",
    "cenarios",
    "completo",
    "evento",
    "muitos_eventos",
    "mudancas",
    "ressalva",
    "status_falha",
    "status_ok",
]
