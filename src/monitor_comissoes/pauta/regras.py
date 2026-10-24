"""Regras puras da pauta: situação da reunião, proposição do item, grupo, chave e identificação.

Nada aqui lê rede ou disco. As regras vêm do PRODUCT.md (§5.8 e §5.9) e do research da PAU
(R3 a R6).
"""

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
