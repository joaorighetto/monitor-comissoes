"""Falhas de coleta: toda interrupção visível da execução usa FalhaDeColeta."""

CONFIGURACAO = "configuracao"
FONTE_INDISPONIVEL = "fonte_indisponivel"
FORMATO_ALTERADO = "formato_alterado"
ARQUIVOS_DESATUALIZADOS = "arquivos_desatualizados"
ARQUIVO_INCOMPLETO = "arquivo_incompleto"
API_DEPUTADOS = "api_deputados"
ESTOQUE_VAZIO = "estoque_vazio"
ESTOQUE_IMPLAUSIVEL = "estoque_implausivel"
SEM_BASE_DE_COMPARACAO = "sem_base_de_comparacao"
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
    SEM_BASE_DE_COMPARACAO,
    INTERNA,
)

# Falhas que podem ser passageiras: a execução diária espera e tenta de novo (AGE, FR-019).
# As demais (configuração, formato, estoque vazio ou implausível, sem base, interna) repetir não
# resolve.
REPETIVEIS = (
    FONTE_INDISPONIVEL,
    ARQUIVOS_DESATUALIZADOS,
    ARQUIVO_INCOMPLETO,
    API_DEPUTADOS,
)

# Entrada local inválida da checagem da pauta (PAU): índice de autoria, inventário ou arquivo de
# pauta ausente ou fora do formato. Fica fora de CATEGORIAS e de REPETIVEIS: não é falha da coleta
# e nunca vai para o `status.json`.
ENTRADA_INVALIDA = "entrada_invalida"


class FalhaDeColeta(Exception):
    """Falha que interrompe a execução sem gravar nada."""

    def __init__(self, categoria: str, motivo: str) -> None:
        super().__init__(f"{categoria}: {motivo}")
        self.categoria = categoria
        self.motivo = motivo


class FalhaDeEnvio(Exception):
    """Falha do aviso diário (AVI): leitura das entradas, registro de envio ou Bot API.

    Não é uma `FalhaDeColeta`: não tem categoria e nunca vai para o `status.json`. A mensagem
    nunca contém token nem chat_id.
    """


class FalhaDePagina(Exception):
    """Falha da geração da página pública (PAG): leitura das entradas ou gravação da saída.

    Não é uma `FalhaDeColeta`: não tem categoria e nunca vai para o `status.json`. A mensagem traz
    o nome do arquivo quando a causa é um arquivo.
    """
