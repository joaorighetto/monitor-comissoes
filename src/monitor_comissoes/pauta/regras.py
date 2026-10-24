"""Regras puras da pauta: situação da reunião, proposição do item, grupo, chave e identificação.

Nada aqui lê rede ou disco. As regras vêm do PRODUCT.md (§5.8 e §5.9) e do research da PAU
(R3 a R6).
"""

import re

REUNIAO_DELIBERATIVA = "Reunião Deliberativa"
TIPOS_LISTADOS = ("PL", "PLP", "PEC", "MSC", "PDL")
REQUERIMENTO = "REQ"

SITUACOES = {
    "Convocada": "convocada",
    "Encerrada": "realizada",
    "Encerrada (Final)": "realizada",
    "Encerrada (Termo)": "realizada",
    "Cancelada": "cancelada",
}


def situacao(texto: str) -> str:
    """A situação normalizada (R3). Uma situação nova da Câmara é `outra`, não formato alterado."""
    return SITUACOES.get(texto, "outra")


def proposicao_do_item(item: dict) -> dict | None:
    """A proposição do item, no formato da API (§5.8, R4).

    Item de REQ é o próprio REQ, qualquer que seja a relacionada. Nos demais, a relacionada quando
    existe (o parecer `PRL` se refere ao PL que está sendo votado); senão, a `proposicao_`.
    """
    principal, relacionada = item["proposicao_"], item["proposicaoRelacionada_"]
    if principal is not None and principal["siglaTipo"] == REQUERIMENTO:
        return principal
    return relacionada if relacionada is not None else principal


def grupo(tipo: str | None) -> str:
    """`listado` (PL, PLP, PEC, MSC, PDL), `req` ou `outro` (inclusive item sem proposição)."""
    if tipo in TIPOS_LISTADOS:
        return "listado"
    if tipo == REQUERIMENTO:
        return "req"
    return "outro"


def chave(item: dict) -> str:
    """A identidade do item na pauta (R6): `p:{id}` da proposição do item, ou `t:{título}`."""
    proposicao = proposicao_do_item(item)
    return f"p:{proposicao['id']}" if proposicao is not None else f"t:{item['titulo']}"


def identificacao(proposicao: dict) -> str:
    """`Tipo número/ano`. A relacionada traz número e ano como texto (R4)."""
    return f"{proposicao['siglaTipo']} {int(proposicao['numero'])}/{int(proposicao['ano'])}"


# Com a variação "Requerimento de Retirado de Pauta", que aparece em texto real (80344, ordem 16).
EXPRESSAO_EXCLUIDA = re.compile(r"requerimento de retirad[oa] de pauta")
REGRAS_DO_RESULTADO = (
    ("vista", re.compile(r"\bvista\b")),
    ("aprovado", re.compile(r"\baprovad[oa]\b")),
    ("rejeitado", re.compile(r"\brejeitad[oa]\b")),
    (
        "não apreciado",
        re.compile(r"adiad|não apreciad|não deliberad|encerrada a reunião|encerramento da reunião"),
    ),
)
RETIRADO = re.compile(r"retirad[oa] de pauta")
# O requerimento de retirada aprovado tira o item da pauta (emenda ao §5.9).
REQUERIMENTO_APROVADO = re.compile(r"aprovad[oa] (?:o )?requerimento de retirad[oa] de pauta")


def resultado(texto: str | None) -> dict:
    """O rótulo do §5.9 e o texto original (R5). As regras valem na ordem; a primeira decide.

    "Retirado de pauta" não conta dentro de "Requerimento de Retirada de Pauta": só essas
    ocorrências saem da busca, e não o texto inteiro. Mas o requerimento aprovado tira o item.
    """
    if texto is None or not texto.strip():
        return {"rotulo": "sem registro", "texto": texto}
    minusculo = texto.lower()
    if REQUERIMENTO_APROVADO.search(minusculo) or RETIRADO.search(
        EXPRESSAO_EXCLUIDA.sub("", minusculo)
    ):
        return {"rotulo": "retirado de pauta", "texto": texto}
    for rotulo, padrao in REGRAS_DO_RESULTADO:
        if padrao.search(minusculo):
            return {"rotulo": rotulo, "texto": texto}
    return {"rotulo": "outro", "texto": texto}
