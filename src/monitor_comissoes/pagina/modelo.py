"""O que a página mostra (PAG, data-model.md): valores imutáveis, puros, sem relógio nem disco.

Recebe os documentos já conferidos por `entradas.py` e decide ordem, números e o texto de cada
campo. Nenhuma regra de domínio é recalculada: "parado há", etiquetas e relator vêm como estão.
"""

from dataclasses import dataclass
from datetime import date, datetime

from ..estoque import BRASILIA
from ..resumo import dia_mes

# Identificador curto de cada etiqueta, usado em `data-etiquetas` e nos chips de motivo.
MOTIVOS = {
    "autoria NOVO": "autoria",
    "autor hoje no NOVO": "autor-hoje",
    "relatoria NOVO": "relatoria",
}

MARCA_SEM_PRINCIPAL = "principal não localizada"
MARCA_RELATOR_INDETERMINADO = "relator indeterminado"
SEM_RELATOR = "sem relator atual"


def hora_minuto(iso: str) -> str:
    """`HHhMM` de uma data e hora ISO com fuso, no horário de Brasília."""
    return datetime.fromisoformat(iso).astimezone(BRASILIA).strftime("%Hh%M")


def linha_de_atualizacao(atual: dict, status: dict) -> str:
    """ "Dados da Câmara de DD/MM (arquivo gerado às HHhMM) · verificado em DD/MM às HHhMM"."""
    meta = atual["meta"]
    verificado = status["verificado_em"]
    return (
        f"Dados da Câmara de {dia_mes(meta['dados_camara_em'])} "
        f"(arquivo gerado às {hora_minuto(meta['gerado_em'])}) · "
        f"verificado em {dia_mes(verificado)} às {hora_minuto(verificado)}"
    )


@dataclass(frozen=True)
class Numeros:
    total_itens: int
    por_comissao: tuple[tuple[str, int], ...]
    # ("eventos", n), ("linha_de_base", motivo) ou ("indisponivel", None): nunca um zero inventado
    mudancas: tuple[str, int | str | None]


def numeros(atual: dict, janela: list[tuple[date, dict | None]]) -> Numeros:
    """Os números do topo. As mudanças vêm do arquivo do dia do retrato, o primeiro da janela."""
    meta = atual["meta"]
    por_comissao = tuple(
        (sigla, meta["total_por_comissao"].get(sigla, 0)) for sigla in meta["comissoes"]
    )
    documento = janela[0][1] if janela else None
    if documento is None:
        mudancas: tuple[str, int | str | None] = ("indisponivel", None)
    elif documento["meta"]["linha_de_base"] is not None:
        mudancas = ("linha_de_base", documento["meta"]["linha_de_base"]["motivo"])
    else:
        mudancas = ("eventos", documento["meta"]["total_eventos"])
    return Numeros(meta["total_itens"], por_comissao, mudancas)


def ordenar(itens: list[dict]) -> list[dict]:
    """Do mais parado para o menos; itens com o mesmo valor ficam em ordem estável de id."""
    return sorted(itens, key=lambda item: (-item["parado_ha_dias"], item["id"]))


@dataclass(frozen=True)
class ItemDaLista:
    id: int
    identificacao: str
    link: str
    ementa: str
    comissao: str
    situacao: str
    parado: str
    autores: tuple[str, ...]
    etiquetas: tuple[str, ...]
    motivos: tuple[str, ...]
    relator: str
    apensado: tuple[str, str] | None
    marcas: tuple[str, ...]


def _com_partido(nome: str, partido: str | None) -> str:
    return f"{nome} ({partido})" if partido else nome


def _parado(dias: int) -> str:
    return f"nesta situação há {dias} dia" if dias == 1 else f"nesta situação há {dias} dias"


def item_da_lista(item: dict) -> ItemDaLista:
    autores = sorted(item["autores"], key=lambda a: a.get("ordem", 0))
    relator = item["relator"]
    apensado = item["apensado_a"]
    marcas = []
    if item["principal_nao_localizada"]:
        marcas.append(MARCA_SEM_PRINCIPAL)
    if item["relator_indeterminado"] is not None:
        marcas.append(MARCA_RELATOR_INDETERMINADO)
    return ItemDaLista(
        id=item["id"],
        identificacao=item["identificacao"],
        link=item["link"],
        ementa=item["ementa"],
        comissao=item["comissao"],
        situacao=item["situacao"],
        parado=_parado(item["parado_ha_dias"]),
        autores=tuple(_com_partido(a["nome"], a["partido_na_data"]) for a in autores),
        etiquetas=tuple(item["etiquetas"]),
        motivos=tuple(MOTIVOS[e] for e in item["etiquetas"] if e in MOTIVOS),
        relator=(
            SEM_RELATOR
            if relator is None
            else _com_partido(relator["nome"], relator["partido_hoje"])
        ),
        apensado=None if apensado is None else (apensado["identificacao"], apensado["link"]),
        marcas=tuple(marcas),
    )


LIMITE_DE_ATRASO_HORAS = 30


def faixa_de_erro(status: dict) -> str | None:
    """O texto da faixa de erro quando a última execução falhou (PRODUCT.md, §6.2)."""
    if status["resultado"] != "falha":
        return None
    dia = date.fromisoformat(status["data_referencia"]).strftime("%d/%m")
    dados = dia_mes(status["ultimo_retrato_bom"]["dados_camara_em"])
    return f"A atualização de {dia} falhou ({status['falha']['motivo']}). Dados de {dados}."


@dataclass(frozen=True)
class FaixaDeAtraso:
    """Sempre emitida e escondida; só o navegador a mostra, com o relógio do leitor."""

    verificado_em: str
    texto: str


def faixa_de_atraso(status: dict) -> FaixaDeAtraso:
    verificado = status["verificado_em"]
    return FaixaDeAtraso(
        verificado_em=verificado,
        texto=(
            f"Dados atrasados: a última verificação foi em {dia_mes(verificado)} às "
            f"{hora_minuto(verificado)}, há mais de {LIMITE_DE_ATRASO_HORAS} horas. "
            "A atualização diária pode ter parado."
        ),
    )


@dataclass(frozen=True)
class Pagina:
    """Tudo o que `html.renderizar` precisa, já decidido."""

    atualizacao: str
    faixa_erro: str | None
    faixa_atraso: FaixaDeAtraso
    numeros: Numeros
    itens: tuple[ItemDaLista, ...]


def montar_pagina(atual: dict, status: dict, janela: list[tuple[date, dict | None]]) -> Pagina:
    """O modelo da página a partir das entradas já conferidas por `entradas.py`."""
    return Pagina(
        atualizacao=linha_de_atualizacao(atual, status),
        faixa_erro=faixa_de_erro(status),
        faixa_atraso=faixa_de_atraso(status),
        numeros=numeros(atual, janela),
        itens=tuple(item_da_lista(i) for i in ordenar(atual["itens"])),
    )
