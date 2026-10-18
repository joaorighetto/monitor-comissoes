"""Leitura e validação de config.toml (comissões acompanhadas e ano mínimo)."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .erros import CONFIGURACAO, FalhaDeColeta

PRIMEIRO_ANO_POSSIVEL = 1990

# Campos de [execucao] (AGE): nome, padrão, mínimo e máximo (data-model.md da AGE).
EXECUCAO = (
    ("tentativas", 4, 1, 10),
    ("espera_minutos", 30, 0, 120),
    ("limite_variacao_percentual", 20, 1, 100),
)


@dataclass(frozen=True)
class Config:
    comissoes: tuple[str, ...]
    ano_minimo: int
    tentativas: int = 4
    espera_minutos: int = 30
    limite_variacao_percentual: int = 20


def _falha(motivo: str) -> FalhaDeColeta:
    return FalhaDeColeta(CONFIGURACAO, motivo)


def carregar_config(caminho: Path, ano_corrente: int) -> Config:
    try:
        dados = tomllib.loads(Path(caminho).read_text(encoding="utf-8"))
    except OSError as erro:
        raise _falha(f"não foi possível ler {caminho}: {erro.strerror or erro}") from erro
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as erro:
        raise _falha(f"{caminho} não é um TOML válido: {erro}") from erro

    comissoes = dados.get("comissoes")
    if not isinstance(comissoes, list) or not comissoes:
        raise _falha("comissoes deve ser uma lista não vazia de siglas")
    if not all(isinstance(sigla, str) and sigla.strip() for sigla in comissoes):
        raise _falha("comissoes: cada sigla deve ser um texto não vazio")
    if any(sigla != sigla.strip() for sigla in comissoes):
        raise _falha("comissoes: sigla com espaço no começo ou no fim nunca casaria com a fonte")
    if len(set(comissoes)) != len(comissoes):
        raise _falha("comissoes: há sigla repetida")

    ano_minimo = dados.get("ano_minimo")
    if isinstance(ano_minimo, bool) or not isinstance(ano_minimo, int):
        raise _falha("ano_minimo deve ser um número inteiro")
    if not PRIMEIRO_ANO_POSSIVEL <= ano_minimo <= ano_corrente:
        raise _falha(
            f"ano_minimo deve estar entre {PRIMEIRO_ANO_POSSIVEL} e {ano_corrente}"
            f" (recebido: {ano_minimo})"
        )

    execucao = _ler_execucao(dados.get("execucao"))

    return Config(comissoes=tuple(comissoes), ano_minimo=ano_minimo, **execucao)


def _ler_execucao(tabela) -> dict[str, int]:
    """Lê a tabela opcional [execucao]; sem ela, valem os padrões."""
    if tabela is None:
        return {nome: padrao for nome, padrao, _, _ in EXECUCAO}
    if not isinstance(tabela, dict):
        raise _falha("execucao deve ser uma tabela [execucao]")
    conhecidos = {nome for nome, _, _, _ in EXECUCAO}
    for chave in tabela:
        if chave not in conhecidos:
            raise _falha(f"execucao.{chave} não é um campo conhecido de [execucao]")
    valores = {}
    for nome, padrao, minimo, maximo in EXECUCAO:
        valor = tabela.get(nome, padrao)
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise _falha(f"execucao.{nome} deve ser um número inteiro")
        if not minimo <= valor <= maximo:
            raise _falha(
                f"execucao.{nome} deve estar entre {minimo} e {maximo} (recebido: {valor})"
            )
        valores[nome] = valor
    return valores
