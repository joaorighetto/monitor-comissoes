"""Leitura e validação de config.toml (comissões acompanhadas e ano mínimo)."""

import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

from .erros import CONFIGURACAO, FalhaDeColeta

PRIMEIRO_ANO_POSSIVEL = 1990

# Campos de [execucao] (AGE): nome, padrão, mínimo e máximo (data-model.md da AGE).
EXECUCAO = (
    ("tentativas", 4, 1, 10),
    ("espera_minutos", 30, 0, 120),
    ("limite_variacao_percentual", 20, 1, 100),
)
PADROES = {nome: padrao for nome, padrao, _, _ in EXECUCAO}

# Campos de [aviso] (AVI): texto de cada um e seu valor padrão.
PAGINA_URL_PADRAO = ""
REPOSITORIO_PADRAO = "joaorighetto/monitor-comissoes"
PADRAO_REPOSITORIO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class Config:
    comissoes: tuple[str, ...]
    ano_minimo: int
    tentativas: int = PADROES["tentativas"]
    espera_minutos: int = PADROES["espera_minutos"]
    limite_variacao_percentual: int = PADROES["limite_variacao_percentual"]
    pagina_url: str = PAGINA_URL_PADRAO
    repositorio: str = REPOSITORIO_PADRAO


def _falha(motivo: str) -> FalhaDeColeta:
    return FalhaDeColeta(CONFIGURACAO, motivo)


def _ler_toml(caminho: Path) -> dict:
    try:
        return tomllib.loads(Path(caminho).read_text(encoding="utf-8"))
    except OSError as erro:
        raise _falha(f"não foi possível ler {caminho}: {erro.strerror or erro}") from erro
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as erro:
        raise _falha(f"{caminho} não é um TOML válido: {erro}") from erro


def carregar_config(caminho: Path, ano_corrente: int) -> Config:
    """Lê o config.toml. A tabela [aviso] é ignorada aqui: um valor errado nela não derruba a
    coleta (AVI, FR-016 e FR-026); quem a valida é `carregar_config_do_aviso`. Um TOML com
    sintaxe inválida continua falhando o arquivo inteiro, como sempre."""
    dados = _ler_toml(caminho)

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


def carregar_config_do_aviso(caminho: Path, ano_corrente: int) -> Config:
    """O `Config` completo, com a tabela [aviso] validada. Só o aviso diário a usa."""
    config = carregar_config(caminho, ano_corrente)
    return replace(config, **_ler_aviso(_ler_toml(caminho).get("aviso")))


def _ler_execucao(tabela) -> dict[str, int]:
    """Lê a tabela opcional [execucao]; sem ela, valem os padrões."""
    if tabela is None:
        return dict(PADROES)
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


def _ler_aviso(tabela) -> dict[str, str]:
    """Lê a tabela opcional [aviso]; sem ela, valem os padrões."""
    if tabela is None:
        return {"pagina_url": PAGINA_URL_PADRAO, "repositorio": REPOSITORIO_PADRAO}
    if not isinstance(tabela, dict):
        raise _falha("aviso deve ser uma tabela [aviso]")
    for chave in tabela:
        if chave not in ("pagina_url", "repositorio"):
            raise _falha(f"aviso.{chave} não é um campo conhecido de [aviso]")
    pagina_url = tabela.get("pagina_url", PAGINA_URL_PADRAO)
    if not isinstance(pagina_url, str) or (pagina_url and not pagina_url.startswith("https://")):
        raise _falha("aviso.pagina_url deve ser um texto vazio ou começar com https://")
    repositorio = tabela.get("repositorio", REPOSITORIO_PADRAO)
    if not isinstance(repositorio, str) or not PADRAO_REPOSITORIO.fullmatch(repositorio):
        raise _falha("aviso.repositorio deve ser um texto no formato dono/nome")
    return {"pagina_url": pagina_url, "repositorio": repositorio}
