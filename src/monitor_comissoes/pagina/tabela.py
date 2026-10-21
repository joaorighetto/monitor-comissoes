"""O itens.csv (PAG, FR-017; contracts/site.md): uma linha por item, as colunas que a página mostra.

Separador `;`, fim de linha `\\r\\n` e UTF-8 com BOM, para abrir direto no Excel em português, com
acentos. O conteúdo de cada campo é o do `atual.json`: o texto da Câmara não é alterado (nem
neutralizado contra fórmulas; risco aceito no plan.md).
"""

import csv
import io

from .modelo import MARCA_RELATOR_INDETERMINADO, MARCA_SEM_PRINCIPAL, com_partido

SEPARADOR = ";"
JUNCAO = " | "
BOM = b"\xef\xbb\xbf"
CABECALHO = (
    "identificação",
    "link oficial",
    "ementa",
    "comissão",
    "situação",
    "parado há (dias)",
    "etiquetas",
    "autores",
    "relator atual",
    "apensado a",
    "marcas",
)


def _linha(item: dict) -> list[str]:
    autores = sorted(item["autores"], key=lambda a: a.get("ordem", 0))
    relator = item["relator"]
    apensado = item["apensado_a"]
    marcas = []
    if item["principal_nao_localizada"]:
        marcas.append(MARCA_SEM_PRINCIPAL)
    if item["relator_indeterminado"] is not None:
        marcas.append(MARCA_RELATOR_INDETERMINADO)
    return [
        item["identificacao"],
        item["link"],
        item["ementa"],
        item["comissao"],
        item["situacao"],
        str(item["parado_ha_dias"]),
        JUNCAO.join(item["etiquetas"]),
        JUNCAO.join(com_partido(a["nome"], a["partido_na_data"]) for a in autores),
        "" if relator is None else com_partido(relator["nome"], relator["partido_hoje"]),
        "" if apensado is None else apensado["identificacao"],
        JUNCAO.join(marcas),
    ]


def renderizar(itens: list[dict]) -> bytes:
    """O CSV dos `itens`, que já devem vir na ordem da lista da página."""
    saida = io.StringIO(newline="")
    escritor = csv.writer(saida, delimiter=SEPARADOR, lineterminator="\r\n")
    escritor.writerow(CABECALHO)
    for item in itens:
        escritor.writerow(_linha(item))
    return BOM + saida.getvalue().encode("utf-8")
