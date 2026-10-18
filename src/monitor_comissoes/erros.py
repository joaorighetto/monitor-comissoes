"""Falhas de coleta: toda interrupção visível da execução usa FalhaDeColeta."""

CONFIGURACAO = "configuracao"
FONTE_INDISPONIVEL = "fonte_indisponivel"
FORMATO_ALTERADO = "formato_alterado"
ARQUIVOS_DESATUALIZADOS = "arquivos_desatualizados"
ARQUIVO_INCOMPLETO = "arquivo_incompleto"
API_DEPUTADOS = "api_deputados"
ESTOQUE_VAZIO = "estoque_vazio"
ESTOQUE_IMPLAUSIVEL = "estoque_implausivel"
INTERNA = "interna"

CATEGORIAS = (
    CONFIGURACAO,
    FONTE_INDISPONIVEL,
    FORMATO_ALTERADO,
    ARQUIVOS_DESATUALIZADOS,
    ARQUIVO_INCOMPLETO,
    API_DEPUTADOS,
    ESTOQUE_VAZIO,
    ESTOQUE_IMPLAUSIVEL,
    INTERNA,
)

# Falhas que podem ser passageiras: a execução diária espera e tenta de novo (AGE, FR-019).
# As demais (configuração, formato, estoque vazio ou implausível, interna) repetir não resolve.
REPETIVEIS = (
    FONTE_INDISPONIVEL,
    ARQUIVOS_DESATUALIZADOS,
    ARQUIVO_INCOMPLETO,
    API_DEPUTADOS,
)


class FalhaDeColeta(Exception):
    """Falha que interrompe a execução sem gravar nada."""

    def __init__(self, categoria: str, motivo: str) -> None:
        super().__init__(f"{categoria}: {motivo}")
        self.categoria = categoria
        self.motivo = motivo
