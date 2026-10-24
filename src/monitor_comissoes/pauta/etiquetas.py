"""Ligação do item da pauta com o NOVO (PRODUCT.md §5.8). Puro: sem rede nem disco.

A autoria vem do índice de autoria (o último lote bom); a relatoria, do relator da pauta; o
"leva apensado do NOVO", do inventário (`atual.json`).
"""

from ..estoque import ETIQUETA_AUTOR_HOJE, ETIQUETA_AUTORIA, ETIQUETA_RELATORIA


def etiquetas(
    id_proposicao: int, relator: dict | None, indice: dict, ids_novo: frozenset[int]
) -> tuple[list[str], bool]:
    """As etiquetas do item, na ordem fixa, e se a autoria ficou sem verificar.

    `indice` é o `proposicoes` do índice de autoria. Uma proposição fora dele não está no último
    lote bom: não ganha as etiquetas de autoria e fica com "autoria não verificada"; a de
    relatoria continua valendo, pelo relator da pauta.
    """
    nomes = []
    entrada = indice.get(str(id_proposicao))
    if entrada is not None:
        autoria_novo, deputados = entrada
        if autoria_novo == 1:
            nomes.append(ETIQUETA_AUTORIA)
        if any(deputado in ids_novo for deputado in deputados):
            nomes.append(ETIQUETA_AUTOR_HOJE)
    if relator is not None and relator["id"] in ids_novo:
        nomes.append(ETIQUETA_RELATORIA)
    return nomes, entrada is None


def apensados_do_novo(id_proposicao: int, inventario: list[dict]) -> list[dict]:
    """Os itens do inventário apensados à proposição, com as etiquetas de lá, ordenados por id."""
    apensados = [
        {
            "id": item["id"],
            "identificacao": item["identificacao"],
            "link": item["link"],
            "etiquetas": list(item["etiquetas"]),
        }
        for item in inventario
        if item["id"] != id_proposicao
        and item["apensado_a"] is not None
        and item["apensado_a"]["id"] == id_proposicao
    ]
    return sorted(apensados, key=lambda a: a["id"])
