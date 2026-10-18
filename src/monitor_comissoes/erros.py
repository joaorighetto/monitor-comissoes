"""Falhas de coleta: toda interrupção visível da execução usa FalhaDeColeta."""

CONFIGURACAO = "configuracao"
FONTE_INDISPONIVEL = "fonte_indisponivel"
FORMATO_ALTERADO = "formato_alterado"
ARQUIVOS_DESATUALIZADOS = "arquivos_desatualizados"
ARQUIVO_INCOMPLETO = "arquivo_incompleto"
API_DEPUTADOS = "api_deputados"
ESTOQUE_VAZIO = "estoque_vazio"

CATEGORIAS = (
    CONFIGURACAO,
    FONTE_INDISPONIVEL,
    FORMATO_ALTERADO,
    ARQUIVOS_DESATUALIZADOS,
    ARQUIVO_INCOMPLETO,
    API_DEPUTADOS,
    ESTOQUE_VAZIO,
)


class FalhaDeColeta(Exception):
    """Falha que interrompe a execução sem gravar nada."""

    def __init__(self, categoria: str, motivo: str) -> None:
        super().__init__(f"{categoria}: {motivo}")
        self.categoria = categoria
        self.motivo = motivo
