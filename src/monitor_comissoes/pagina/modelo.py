"""O que a página mostra (PAG, data-model.md): valores imutáveis, puros, sem relógio nem disco.

Recebe os documentos já conferidos por `entradas.py` e decide ordem, números e o texto de cada
campo. Nenhuma regra de domínio é recalculada: "parado há", etiquetas e relator vêm como estão.
"""

from dataclasses import dataclass
from datetime import date, datetime

from ..estoque import BRASILIA
from ..resumo import ROTULOS, dia_mes

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


# Os chips de motivo: rótulo e identificador curto de cada etiqueta, na ordem do PRODUCT.md, §6.2.
CHIPS_DE_MOTIVO = (
    ("Autoria NOVO", "autoria"),
    ("Autor hoje no NOVO", "autor-hoje"),
    ("Relatoria NOVO", "relatoria"),
)


@dataclass(frozen=True)
class Chip:
    rotulo: str
    valor: str  # sigla da comissão ou identificador curto do motivo; "" para Todas/Todos
    ativo: bool


@dataclass(frozen=True)
class GrupoDeChips:
    nome: str  # "comissao" ou "motivo": vai em `data-grupo`
    rotulo: str  # o `aria-label` do grupo
    chips: tuple[Chip, ...]


def filtros(atual: dict, itens: list[ItemDaLista]) -> tuple[GrupoDeChips, GrupoDeChips]:
    """Os dois grupos de chips. Categoria sem item não gera chip; Todas e Todos sempre existem."""
    comissoes = [
        Chip(sigla, sigla, False)
        for sigla in atual["meta"]["comissoes"]
        if any(i.comissao == sigla for i in itens)
    ]
    motivos = [
        Chip(rotulo, valor, False)
        for rotulo, valor in CHIPS_DE_MOTIVO
        if any(valor in i.motivos for i in itens)
    ]
    return (
        GrupoDeChips("comissao", "Filtrar por comissão", (Chip("Todas", "", True), *comissoes)),
        GrupoDeChips("motivo", "Filtrar por motivo", (Chip("Todos", "", True), *motivos)),
    )


TETO_EVENTOS_POR_DIA = 20  # os primeiros ficam abertos; o excedente é recolhido, nunca removido


@dataclass(frozen=True)
class TramitacaoDaPagina:
    quando: str  # "DD/MM HH:MM", como a API entrega (sem fuso)
    orgao: str
    descricao: str


@dataclass(frozen=True)
class EventoDaPagina:
    tipo: str
    rotulo: str
    identificacao: str
    link: str
    comissao: str
    detalhe: str
    apensado: tuple[str, str] | None  # só em `saiu`: (identificação, link) da principal
    tramitacoes: tuple[TramitacaoDaPagina, ...]


@dataclass(frozen=True)
class DiaDeMudancas:
    data: date
    estado: str  # "eventos", "sem_mudancas", "linha_de_base" ou "sem_arquivo"
    intervalo: tuple[str, str] | None  # ("DD/MM", "DD/MM") quando o arquivo cobre mais de um dia
    linha_de_base: tuple[str, int] | None  # (motivo, total de itens)
    abertos: tuple[EventoDaPagina, ...]
    recolhidos: tuple[EventoDaPagina, ...]


def _relator_do_evento(relator: dict) -> str:
    return _com_partido(relator["nome"], relator["partido_hoje"])


def _detalhe_do_evento(evento: dict) -> str:
    tipo = evento["tipo"]
    if tipo == "entrou":
        partes = [evento["motivo"]["texto"]]
        if evento["etiquetas"]:
            partes.append("etiquetas: " + ", ".join(evento["etiquetas"]))
        return " · ".join(partes)
    if tipo == "saiu":
        partes = [evento["motivo"]["texto"]]
        destino = evento["destino"]
        if destino["orgao"] and destino["situacao"]:
            partes.append(f"destino: {destino['orgao']} ({destino['situacao']})")
        elif destino["orgao"] or destino["situacao"]:
            partes.append(f"destino: {destino['orgao'] or destino['situacao']}")
        return " · ".join(partes)
    if tipo == "situacao":
        texto = f"{evento['de']} → {evento['para']}"
        if evento["comissao_de"] != evento["comissao"]:
            texto += f" · veio da {evento['comissao_de']}"
        return texto
    if tipo == "relator":
        mudanca = evento["mudanca"]
        if mudanca == "designado":
            return f"designado {_relator_do_evento(evento['para'])}"
        if mudanca == "devolveu":
            return f"devolveu {_relator_do_evento(evento['de'])}"
        return (
            f"substituído: {_relator_do_evento(evento['de'])} → "
            f"{_relator_do_evento(evento['para'])}"
        )
    if tipo == "parecer":
        return "parecer do relator"
    partes = []
    if evento["ganhou"]:
        partes.append("ganhou: " + ", ".join(evento["ganhou"]))
    if evento["perdeu"]:
        partes.append("perdeu: " + ", ".join(evento["perdeu"]))
    return " · ".join(partes)


def _quando(data_hora: str) -> str:
    momento = datetime.fromisoformat(data_hora)
    return momento.strftime("%d/%m %H:%M")


def evento_da_pagina(evento: dict) -> EventoDaPagina:
    apensado = None
    if evento["tipo"] == "saiu" and evento["destino"]["apensado_a"] is not None:
        raiz = evento["destino"]["apensado_a"]
        apensado = (raiz["identificacao"], raiz["link"])
    return EventoDaPagina(
        tipo=evento["tipo"],
        rotulo=ROTULOS[evento["tipo"]],
        identificacao=evento["identificacao"],
        link=evento["link"],
        comissao=evento["comissao"],
        detalhe=_detalhe_do_evento(evento),
        apensado=apensado,
        tramitacoes=tuple(
            TramitacaoDaPagina(_quando(t["data_hora"]), t["orgao"], t["descricao"])
            for t in evento["tramitacoes"]
        ),
    )


def _dia_de_mudancas(dia: date, documento: dict | None) -> DiaDeMudancas:
    if documento is None:
        return DiaDeMudancas(dia, "sem_arquivo", None, None, (), ())
    meta = documento["meta"]
    anterior = meta["retrato_anterior"]
    intervalo = None
    if anterior is not None:
        inicio = date.fromisoformat(anterior["dia"])
        fim = date.fromisoformat(meta["retrato"]["dia"])
        if (fim - inicio).days > 1:
            intervalo = (inicio.strftime("%d/%m"), fim.strftime("%d/%m"))
    base = meta["linha_de_base"]
    if base is not None:
        return DiaDeMudancas(
            dia, "linha_de_base", intervalo, (base["motivo"], base["total_itens"]), (), ()
        )
    eventos = [evento_da_pagina(e) for e in documento["eventos"]]
    if not eventos:
        return DiaDeMudancas(dia, "sem_mudancas", intervalo, None, (), ())
    return DiaDeMudancas(
        dia,
        "eventos",
        intervalo,
        None,
        tuple(eventos[:TETO_EVENTOS_POR_DIA]),
        tuple(eventos[TETO_EVENTOS_POR_DIA:]),
    )


def dias_de_mudancas(janela: list[tuple[date, dict | None]]) -> tuple[DiaDeMudancas, ...]:
    """Os dias da janela, do mais recente ao mais antigo, já decididos para a página."""
    return tuple(_dia_de_mudancas(dia, documento) for dia, documento in janela)


def sem_mudancas_registradas(dias: tuple[DiaDeMudancas, ...]) -> bool:
    """Verdadeiro se nenhum dos dias tem arquivo (antes da primeira execução com a MUD)."""
    return all(d.estado == "sem_arquivo" for d in dias)


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
    mudancas: tuple[DiaDeMudancas, ...]
    filtros: tuple[GrupoDeChips, GrupoDeChips]
    itens: tuple[ItemDaLista, ...]


def montar_pagina(atual: dict, status: dict, janela: list[tuple[date, dict | None]]) -> Pagina:
    """O modelo da página a partir das entradas já conferidas por `entradas.py`."""
    itens = tuple(item_da_lista(i) for i in ordenar(atual["itens"]))
    return Pagina(
        atualizacao=linha_de_atualizacao(atual, status),
        faixa_erro=faixa_de_erro(status),
        faixa_atraso=faixa_de_atraso(status),
        numeros=numeros(atual, janela),
        mudancas=dias_de_mudancas(janela),
        filtros=filtros(atual, list(itens)),
        itens=itens,
    )
