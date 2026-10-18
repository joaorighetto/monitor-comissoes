"""Orquestração da coleta: baixa o lote, filtra o estoque e grava data/atual.json."""

import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Config
from .deputados import obter_deputados_novo
from .erros import ESTOQUE_VAZIO, FalhaDeColeta
from .estoque import BRASILIA, PARTIDO, TIPOS, construir_itens, ids_na_comissao, subir_ate_a_raiz
from .lote import (
    baixar_lote,
    ler_apensacao,
    ler_autores,
    ler_ids_com_autor_novo,
    ler_proposicoes,
    verificar_frescor,
)
from .saida import gravar_atomico, montar_documento
from .transporte import Transporte

URL_BASE = "https://dadosabertos.camara.leg.br"
VERSAO_FORMATO = 1


@dataclass(frozen=True)
class Resultado:
    total_itens: int
    por_comissao: dict[str, int]
    dados_camara_em: datetime  # UTC


def executar(config: Config, transporte: Transporte, agora: datetime, saida: Path) -> Resultado:
    """Gera `saida` ou levanta FalhaDeColeta sem tocar no arquivo existente."""
    ano_corrente = agora.astimezone(BRASILIA).year
    deputados = obter_deputados_novo(transporte, URL_BASE)
    ids_deputados = {d.id for d in deputados}

    with tempfile.TemporaryDirectory(prefix="monitor-comissoes-") as pasta:
        lote = baixar_lote(transporte, URL_BASE, config.ano_minimo, ano_corrente, Path(pasta))
        verificar_frescor(lote, agora)

        # Quais proposições têm autor do NOVO (na data) ou autor deputado do NOVO hoje.
        ligadas_ao_novo: set[int] = set()
        for ano in lote.anos:
            ligadas_ao_novo |= ler_ids_com_autor_novo(lote.autores(ano), PARTIDO, ids_deputados)

        # Cadeias de apensação: id -> id da principal, só das proposições apensadas.
        mapa_principal: dict[int, int] = {}
        for ano in lote.anos:
            mapa_principal.update(ler_apensacao(lote.proposicoes(ano)))

        # Linhas necessárias: as proposições ligadas ao NOVO e as raízes de suas cadeias.
        necessarias = set(ligadas_ao_novo)
        for id_proposicao in ligadas_ao_novo:
            raiz = subir_ate_a_raiz(id_proposicao, mapa_principal)
            if raiz is not None:
                necessarias.add(raiz)
        linhas = {}
        for ano in lote.anos:
            for p in ler_proposicoes(lote.proposicoes(ano), ids=necessarias):
                linhas[p.id] = p
        candidatas = {i: p for i, p in linhas.items() if i in ligadas_ao_novo and p.tipo in TIPOS}

        # Autores completos só das que estão na comissão (a referência é que decide).
        na_comissao = ids_na_comissao(candidatas, config.comissoes, mapa_principal, linhas)
        autores_por_id = defaultdict(list)
        for ano in lote.anos:
            for autor in ler_autores(lote.autores(ano), ids=na_comissao):
                autores_por_id[autor.id_proposicao].append(autor)

    itens = construir_itens(
        candidatas,
        autores_por_id,
        ids_deputados,
        config.comissoes,
        agora,
        mapa_principal=mapa_principal,
        proposicoes=linhas,
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
    gravar_atomico(montar_documento(itens, meta), saida)
    return Resultado(len(itens), por_comissao, lote.last_modified_min)
