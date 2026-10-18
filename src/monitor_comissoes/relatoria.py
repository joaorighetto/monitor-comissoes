"""Regra do relator atual (PRODUCT.md §5.4 e D3; research R2). Sem I/O.

O relator atual é o designado na comissão em que a referência está, na passagem mais recente
dela por essa comissão, que não deixou de sê-lo depois disso. Deixam de ser relator a devolução
sem manifestação, a substituição por nova designação e a saída do relator da comissão.
"""

from collections.abc import Iterable
from typing import NamedTuple

from .tramitacoes import Tramitacao

# Órgãos que apenas movimentam a matéria (Mesa, Coordenação de Comissões Permanentes, Plenário):
# não são comissões e nunca iniciam uma passagem.
ORGAOS_DE_APOIO = frozenset({"MESA", "CCP", "PLEN"})

DESIGNACAO = "320"
# 507 Recebimento - Relator(a) (Sem Manifestação); 1250 e 1255 Saída de Relator(a) da Comissão.
ENCERRAM_A_RELATORIA = frozenset({"507", "1250", "1255"})
# 170 Devolução ao(à) Relator(a); 322 Parecer do(a) Relator(a); 501 Recebimento - Relator(a).
MANTEM_A_RELATORIA = frozenset({"170", "322", "501"})


class RelatorAtual(NamedTuple):
    id: int
    designado_em: str  # dataHora da designação que vale, como a API entrega (AAAA-MM-DDTHH:MM)


class ResultadoRelatoria(NamedTuple):
    """Relator atual, ou nenhum, ou indeterminado (com o motivo). Nunca dois ao mesmo tempo."""

    relator: RelatorAtual | None = None
    indeterminado: str | None = None


def relator_atual(tramitacoes: Iterable[Tramitacao], comissao: str) -> ResultadoRelatoria:
    """Relator atual de uma referência que o lote diz estar na `comissao`."""
    corrente: str | None = None
    relator: RelatorAtual | None = None
    indeterminado: str | None = None

    for t in sorted(tramitacoes, key=lambda t: t.sequencia):
        if t.orgao in ORGAOS_DE_APOIO:
            continue
        if t.orgao != corrente:  # nova passagem: nada da anterior vale
            corrente, relator, indeterminado = t.orgao, None, None
        if t.orgao != comissao:
            continue
        if t.codigo == DESIGNACAO:
            if t.id_relator is None:
                relator = None
                indeterminado = f"designação sem relator identificado (sequência {t.sequencia})"
            else:
                relator = RelatorAtual(t.id_relator, t.data_hora)
                indeterminado = None
        elif t.codigo in ENCERRAM_A_RELATORIA:
            relator, indeterminado = None, None
        elif t.codigo not in MANTEM_A_RELATORIA and "relator" in t.descricao.lower():
            relator = None
            indeterminado = f"tipo de tramitação {t.codigo} ({t.descricao}) não reconhecido"

    if corrente != comissao:
        onde = corrente or "nenhum órgão de comissão"
        return ResultadoRelatoria(
            None, f"as tramitações terminam em {onde}, e o lote diz {comissao}"
        )
    return ResultadoRelatoria(relator, indeterminado)
