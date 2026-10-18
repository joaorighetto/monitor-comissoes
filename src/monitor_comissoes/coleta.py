"""Orquestração da coleta: baixa o lote, filtra o estoque e grava data/atual.json."""

import tempfile
from collections import defaultdict
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
    etiquetar,
    ids_na_comissao,
    resolver_referencia,
    subir_ate_a_raiz,
)
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
from .relatoria import ResultadoRelatoria, relator_atual
from .saida import gravar_atomico, montar_documento
from .tramitacoes import obter_tramitacoes
from .transporte import Transporte

URL_BASE = "https://dadosabertos.camara.leg.br"
VERSAO_FORMATO = 2


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
) -> dict[int, str]:
    """Referências cujas tramitações são lidas: id da referência -> comissão do lote.

    Todo item com etiqueta de autoria (para informar o relator) e todo candidato à relatoria
    NOVO. A referência compartilhada por vários itens entra uma vez.
    """
    referencias: dict[int, str] = {}
    for candidata in candidatas.values():
        if candidata.id not in na_comissao:
            continue
        referencia = resolver_referencia(candidata, mapa_principal, linhas).proposicao
        com_autoria = bool(etiquetar(autores_por_id.get(candidata.id, []), ids_deputados))
        if com_autoria or referencia.id_relator in ids_deputados:
            referencias[referencia.id] = referencia.orgao
    return referencias


def _ler_relatorias(
    transporte: Transporte, referencias: dict[int, str]
) -> dict[int, ResultadoRelatoria]:
    return {
        id_referencia: relator_atual(
            obter_tramitacoes(transporte, URL_BASE, id_referencia), referencias[id_referencia]
        )
        for id_referencia in sorted(referencias)
    }


def _deputados_relator(
    transporte: Transporte,
    relatorias: dict[int, ResultadoRelatoria],
    deputados_novo: list[Deputado],
) -> dict[int, DeputadoHoje]:
    """Nome e partido de hoje dos relatores: o NOVO em exercício dispensa a consulta."""
    do_novo = {d.id: DeputadoHoje(d.id, d.nome, PARTIDO) for d in deputados_novo}
    ids = sorted({r.relator.id for r in relatorias.values() if r.relator})
    return {i: do_novo[i] if i in do_novo else obter_deputado(transporte, URL_BASE, i) for i in ids}


def coletar(config: Config, transporte: Transporte, agora: datetime) -> Coletado:
    """Baixa, valida e filtra o lote; devolve o documento sem gravar nada."""
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

        # Linhas necessárias: as proposições a examinar e as raízes de suas cadeias.
        necessarias = set(examinar)
        for id_proposicao in examinar:
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
    referencias = _referencias_a_ler(
        candidatas, na_comissao, autores_por_id, ids_deputados, mapa_principal, linhas
    )
    relatorias = _ler_relatorias(transporte, referencias)
    deputados_relator = _deputados_relator(transporte, relatorias, deputados)

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
    return Coletado(montar_documento(itens, meta), estoque_bruto, lote.last_modified_min)


def executar(config: Config, transporte: Transporte, agora: datetime, saida: Path) -> Resultado:
    """Gera `saida` ou levanta FalhaDeColeta sem tocar no arquivo existente."""
    coletado = coletar(config, transporte, agora)
    gravar_atomico(coletado.documento, saida)
    meta = coletado.documento["meta"]
    return Resultado(meta["total_itens"], meta["total_por_comissao"], coletado.dados_camara_em)
