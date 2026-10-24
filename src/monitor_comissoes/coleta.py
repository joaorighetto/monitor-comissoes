"""Orquestração da coleta: baixa o lote, filtra o estoque e grava data/atual.json."""

import tempfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Config
from .deputados import Deputado, DeputadoHoje, obter_deputado, obter_deputados_novo
from .erros import ESTOQUE_VAZIO, FalhaDeColeta
from .estoque import (
    BRASILIA,
    PARTIDO,
    TIPOS,
    construir_itens,
    deve_ler_tramitacoes,
    estado_de_saida,
    etiquetar,
    ids_na_comissao,
    resolver_referencia,
    subir_ate_a_raiz,
)
from .indice import construir_indice
from .lote import (
    Lote,
    Proposicao,
    baixar_lote,
    contar_estoque_bruto,
    ler_apensacao,
    ler_autores,
    ler_ids_com_autor_novo,
    ler_ids_relator_novo,
    ler_proposicoes,
    verificar_frescor,
)
from .mudancas import comparar, validar_arquivo
from .relatoria import ResultadoRelatoria, relator_atual
from .retratos import Comparacao
from .saida import gravar_atomico, montar_documento
from .tramitacoes import Tramitacao, obter_tramitacoes
from .transporte import Transporte

URL_BASE = "https://dadosabertos.camara.leg.br"
VERSAO_FORMATO = 3


@dataclass(frozen=True)
class Resultado:
    total_itens: int
    por_comissao: dict[str, int]
    dados_camara_em: datetime  # UTC


@dataclass(frozen=True)
class Coletado:
    """Resultado de uma coleta ainda não gravada: o documento e o que a AGE confere."""

    documento: dict
    estoque_bruto: int  # PL/PLP nas comissões, pelo órgão do próprio status (AGE, FR-015a)
    dados_camara_em: datetime  # UTC
    mudancas: dict | None = None  # o arquivo de mudanças do dia (MUD); None sem comparação
    indice: dict | None = None  # o índice de autoria do lote (PAU); só a execução diária o grava


def _candidatos_a_relatoria(
    lote: Lote, ids_deputados: set[int], comissoes: tuple[str, ...], mapa_principal: dict[int, int]
) -> set[int]:
    """Linhas cujo último relator é do NOVO e os apensados dessas raízes (research R3).

    É só o conjunto de proposições a examinar: a etiqueta depende da confirmação pelas
    tramitações.
    """
    com_relator_novo: set[int] = set()
    for ano in lote.anos:
        com_relator_novo |= ler_ids_relator_novo(lote.proposicoes(ano), ids_deputados, comissoes)
    candidatos = set(com_relator_novo)
    for id_proposicao in mapa_principal:
        if subir_ate_a_raiz(id_proposicao, mapa_principal) in com_relator_novo:
            candidatos.add(id_proposicao)
    return candidatos


def _referencias_a_ler(
    candidatas: dict[int, Proposicao],
    na_comissao: set[int],
    autores_por_id: dict[int, list],
    ids_deputados: set[int],
    mapa_principal: dict[int, int],
    linhas: dict[int, Proposicao],
) -> tuple[dict[int, str], set[int]]:
    """Referências cujas tramitações são lidas: (id da referência -> comissão do lote, ids das
    que têm item com etiqueta de autoria).

    Todo item com etiqueta de autoria (para informar o relator) e todo candidato à relatoria
    NOVO (`deve_ler_tramitacoes`). A referência compartilhada por vários itens entra uma vez.
    """
    referencias: dict[int, str] = {}
    com_autoria: set[int] = set()
    for candidata in candidatas.values():
        if candidata.id not in na_comissao:
            continue
        autores = autores_por_id.get(candidata.id, [])
        referencia = resolver_referencia(candidata, mapa_principal, linhas).proposicao
        if deve_ler_tramitacoes(autores, ids_deputados, referencia):
            referencias[referencia.id] = referencia.orgao
            if etiquetar(autores, ids_deputados):
                com_autoria.add(referencia.id)
    return referencias, com_autoria


def _tramitacoes_da_execucao(transporte: Transporte) -> Callable[[int], list[Tramitacao]]:
    """Lê as tramitações de cada referência uma só vez por coleta.

    A relatoria (REL) e as tramitações dos eventos (MUD) usam a mesma resposta: duas leituras ao
    vivo, em instantes diferentes, poderiam divergir dentro da mesma execução.
    """
    lidas: dict[int, list[Tramitacao]] = {}

    def ler(id_referencia: int) -> list[Tramitacao]:
        if id_referencia not in lidas:
            lidas[id_referencia] = obter_tramitacoes(transporte, URL_BASE, id_referencia)
        return lidas[id_referencia]

    return ler


def _ler_relatorias(
    tramitacoes_de: Callable[[int], list[Tramitacao]],
    referencias: dict[int, str],
    linhas: dict[int, Proposicao],
) -> dict[int, ResultadoRelatoria]:
    """O relator de cada referência no instante do lote.

    Como a situação, o relator vale até a sequência do último status do lote: uma designação
    lançada depois entra no dia seguinte. Sem esse corte, reexecutar o dia com o mesmo lote daria
    outro arquivo, e o evento de relator sairia sem a tramitação que o causou.
    """
    return {
        id_referencia: relator_atual(
            [
                t
                for t in tramitacoes_de(id_referencia)
                if t.sequencia <= linhas[id_referencia].ultimo_status_sequencia
            ],
            referencias[id_referencia],
        )
        for id_referencia in sorted(referencias)
    }


def _deputados_relator(
    transporte: Transporte,
    relatorias: dict[int, ResultadoRelatoria],
    deputados_novo: list[Deputado],
    com_autoria: set[int],
) -> dict[int, DeputadoHoje]:
    """Nome e partido de hoje dos relatores que aparecem na lista.

    O NOVO em exercício dispensa a consulta. Um relator só é consultado se a referência dele
    tem item com etiqueta de autoria: o de um candidato refutado pelas tramitações não entra na
    lista, e uma falha ao consultá-lo derrubaria o dia por alguém que nem aparece.
    """
    do_novo = {d.id: DeputadoHoje(d.id, d.nome, PARTIDO) for d in deputados_novo}
    ids = sorted(
        {
            r.relator.id
            for id_referencia, r in relatorias.items()
            if r.relator and (r.relator.id in do_novo or id_referencia in com_autoria)
        }
    )
    return {i: do_novo[i] if i in do_novo else obter_deputado(transporte, URL_BASE, i) for i in ids}


def coletar(
    config: Config,
    transporte: Transporte,
    agora: datetime,
    comparacao: Comparacao | None = None,
) -> Coletado:
    """Baixa, valida e filtra o lote; devolve o documento sem gravar nada.

    Com `comparacao` (a execução diária), devolve também o arquivo de mudanças do dia. A
    comparação roda aqui dentro para que uma falha de rede dela entre no mesmo laço de novas
    tentativas da coleta.
    """
    ano_corrente = agora.astimezone(BRASILIA).year
    deputados = obter_deputados_novo(transporte, URL_BASE)
    ids_deputados = {d.id for d in deputados}

    with tempfile.TemporaryDirectory(prefix="monitor-comissoes-") as pasta:
        lote = baixar_lote(transporte, URL_BASE, config.ano_minimo, ano_corrente, Path(pasta))
        verificar_frescor(lote, agora)
        estoque_bruto = sum(
            contar_estoque_bruto(lote.proposicoes(ano), TIPOS, config.comissoes)
            for ano in lote.anos
        )
        indice = construir_indice(lote, agora)

        # Quais proposições têm autor do NOVO (na data) ou autor deputado do NOVO hoje.
        ligadas_ao_novo: set[int] = set()
        for ano in lote.anos:
            ligadas_ao_novo |= ler_ids_com_autor_novo(lote.autores(ano), PARTIDO, ids_deputados)

        # Cadeias de apensação: id -> id da principal, só das proposições apensadas.
        mapa_principal: dict[int, int] = {}
        for ano in lote.anos:
            mapa_principal.update(ler_apensacao(lote.proposicoes(ano)))

        # Candidatos à relatoria NOVO (REL): examinados junto com os de autoria.
        examinar = ligadas_ao_novo | _candidatos_a_relatoria(
            lote, ids_deputados, config.comissoes, mapa_principal
        )

        # Itens do retrato anterior (MUD): suas linhas do lote dizem para onde foram os que saíram.
        ids_anteriores: set[int] = set()
        if comparacao is not None and comparacao.anterior is not None:
            ids_anteriores = {i["id"] for i in comparacao.anterior.documento["itens"]}

        # Linhas necessárias: as proposições a examinar e as raízes de suas cadeias.
        necessarias = set(examinar) | ids_anteriores
        for id_proposicao in necessarias.copy():
            raiz = subir_ate_a_raiz(id_proposicao, mapa_principal)
            if raiz is not None:
                necessarias.add(raiz)
        linhas = {}
        for ano in lote.anos:
            for p in ler_proposicoes(lote.proposicoes(ano), ids=necessarias):
                linhas[p.id] = p
        candidatas = {i: p for i, p in linhas.items() if i in examinar and p.tipo in TIPOS}

        # Autores completos só das que estão na comissão (a referência é que decide).
        na_comissao = ids_na_comissao(candidatas, config.comissoes, mapa_principal, linhas)
        autores_por_id = defaultdict(list)
        for ano in lote.anos:
            for autor in ler_autores(lote.autores(ano), ids=na_comissao):
                autores_por_id[autor.id_proposicao].append(autor)

    # Tramitações (API ao vivo): relator atual de cada referência e partido de hoje dos relatores.
    referencias, com_autoria = _referencias_a_ler(
        candidatas, na_comissao, autores_por_id, ids_deputados, mapa_principal, linhas
    )
    tramitacoes_de = _tramitacoes_da_execucao(transporte)
    relatorias = _ler_relatorias(tramitacoes_de, referencias, linhas)
    deputados_relator = _deputados_relator(transporte, relatorias, deputados, com_autoria)

    itens = construir_itens(
        candidatas,
        autores_por_id,
        ids_deputados,
        config.comissoes,
        agora,
        mapa_principal=mapa_principal,
        proposicoes=linhas,
        relatorias=relatorias,
        deputados_relator=deputados_relator,
    )
    if not itens:
        raise FalhaDeColeta(ESTOQUE_VAZIO, "nenhum item após os filtros; a lista não é gravada")
    por_comissao = {c: sum(1 for i in itens if i["comissao"] == c) for c in config.comissoes}
    meta = {
        "versao_formato": VERSAO_FORMATO,
        "gerado_em": agora.astimezone(BRASILIA).isoformat(timespec="seconds"),
        "dados_camara_em": lote.last_modified_min.isoformat(timespec="seconds"),
        "comissoes": list(config.comissoes),
        "ano_minimo": config.ano_minimo,
        "anos_lidos": [lote.anos[0], lote.anos[-1]],
        "total_itens": len(itens),
        "total_por_comissao": por_comissao,
        "deputados_novo_em_exercicio": [{"id": d.id, "nome": d.nome} for d in deputados],
    }
    documento = montar_documento(itens, meta)
    mudancas = None
    if comparacao is not None:
        ids_de_hoje = {i["id"] for i in itens}
        estados_de_saida = {
            id_proposicao: estado_de_saida(id_proposicao, linhas, mapa_principal, config.comissoes)
            for id_proposicao in ids_anteriores - ids_de_hoje
        }
        mudancas = comparar(
            comparacao,
            documento,
            estados_de_saida,
            tramitacoes_de,
            config.comissoes,
            agora.astimezone(BRASILIA).date(),
        )
        validar_arquivo(mudancas)
    return Coletado(documento, estoque_bruto, lote.last_modified_min, mudancas, indice)


def executar(config: Config, transporte: Transporte, agora: datetime, saida: Path) -> Resultado:
    """Gera `saida` ou levanta FalhaDeColeta sem tocar no arquivo existente."""
    coletado = coletar(config, transporte, agora)
    gravar_atomico(coletado.documento, saida)
    meta = coletado.documento["meta"]
    return Resultado(meta["total_itens"], meta["total_por_comissao"], coletado.dados_camara_em)
