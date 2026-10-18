"""Plausibilidade do estoque bruto: um lote truncado nunca vira lista publicada (AGE).

Aritmética de inteiros, para que "exatamente 20%" passe sem erro de ponto flutuante.
"""

from .erros import ESTOQUE_IMPLAUSIVEL, ESTOQUE_VAZIO, SEM_BASE_DE_COMPARACAO, FalhaDeColeta


def percentual_texto(percentual: float, casas: int = 1) -> str:
    """`-28,2%`, `+25,0%`: sinal explícito e vírgula decimal, como nas mensagens do produto."""
    return f"{percentual:+.{casas}f}".replace(".", ",") + "%"


def verificar(
    estoque_bruto: int,
    base: int | None,
    limite_percentual: int,
    aceitar: bool,
    exige_base: bool = False,
) -> dict | None:
    """Falha se o estoque bruto é vazio ou variou mais que o limite em relação à `base`.

    - Estoque bruto zero falha sempre, com ou sem base, e a confirmação não o libera.
    - Sem base (`None` ou 0) e sem `exige_base` (primeiro dia, sem retrato anterior), a variação
      não se aplica.
    - Sem base mas com `exige_base` (há retrato anterior que ninguém consegue comparar), falha com
      `sem_base_de_comparacao`; com `aceitar`, passa e devolve o registro sem número anterior.
    - Variação acima do limite falha com `estoque_implausivel`; com `aceitar` não falha e
      devolve o registro da variação aceita. Só "mais de" o limite é implausível.
    """
    if estoque_bruto == 0:
        raise FalhaDeColeta(ESTOQUE_VAZIO, "nenhum PL/PLP nas comissões acompanhadas")
    if not base:
        if not exige_base:
            return None
        if aceitar:
            return {
                "estoque_anterior": None,
                "estoque_novo": estoque_bruto,
                "variacao_percentual": None,
            }
        raise FalhaDeColeta(
            SEM_BASE_DE_COMPARACAO,
            "há atual.json, mas não há base para comparar a variação (status ausente, inválido "
            f"ou que não o descreve); estoque bruto de hoje: {estoque_bruto}",
        )
    diferenca = estoque_bruto - base
    if abs(diferenca) * 100 <= limite_percentual * base:
        return None
    percentual = round(diferenca * 100 / base, 1)
    if aceitar:
        return {
            "estoque_anterior": base,
            "estoque_novo": estoque_bruto,
            "variacao_percentual": percentual,
        }
    raise FalhaDeColeta(
        ESTOQUE_IMPLAUSIVEL,
        f"estoque bruto variou {percentual_texto(diferenca * 100 / base, 2)} "
        f"({base} → {estoque_bruto}); o limite é de {limite_percentual}%",
    )
