"""Arquivos em lote da Câmara: download, validação e leitura em fluxo."""

import csv
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from .erros import ARQUIVO_INCOMPLETO, FORMATO_ALTERADO, FalhaDeColeta
from .transporte import Transporte

PROPOSICOES_COLUNAS = (
    "id",
    "siglaTipo",
    "numero",
    "ano",
    "ementa",
    "dataApresentacao",
    "uriPropPrincipal",
    "ultimoStatus_dataHora",
    "ultimoStatus_siglaOrgao",
    "ultimoStatus_descricaoSituacao",
)
AUTORES_COLUNAS = (
    "idProposicao",
    "idDeputadoAutor",
    "nomeAutor",
    "siglaPartidoAutor",
    "ordemAssinatura",
)
FORMATO_DATA = "%Y-%m-%dT%H:%M:%S"

# ementaDetalhada e keywords passam do limite padrão do leitor de CSV.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


class Proposicao(NamedTuple):
    id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    data_apresentacao: datetime
    id_principal: int | None
    ultimo_status_em: datetime
    orgao: str
    situacao: str


class Autor(NamedTuple):
    id_proposicao: int
    id_deputado: int | None
    nome: str
    partido_na_data: str
    ordem: int


def _formato_alterado(arquivo: str, coluna: str) -> FalhaDeColeta:
    return FalhaDeColeta(FORMATO_ALTERADO, f"{arquivo}: formato alterado: coluna {coluna}")


def _linhas(caminho: Path, colunas: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    """Lê o CSV em fluxo e devolve, por linha, só as colunas pedidas.

    Falha se o cabeçalho não tiver uma coluna pedida, se alguma linha tiver número de colunas
    diferente do cabeçalho ou se o arquivo terminar dentro de um campo entre aspas.
    """
    arquivo = caminho.name
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            leitor = csv.reader(f, delimiter=";", strict=True)
            cabecalho = next(leitor, None)
            if cabecalho is None:
                raise FalhaDeColeta(ARQUIVO_INCOMPLETO, f"{arquivo}: arquivo vazio")
            for coluna in colunas:
                if coluna not in cabecalho:
                    raise _formato_alterado(arquivo, coluna)
            indices = [cabecalho.index(coluna) for coluna in colunas]
            total = len(cabecalho)
            for numero, linha in enumerate(leitor, start=2):
                if len(linha) != total:
                    raise FalhaDeColeta(
                        ARQUIVO_INCOMPLETO,
                        f"{arquivo}: linha {numero} com {len(linha)} colunas em vez de {total}",
                    )
                yield tuple(linha[i] for i in indices)
    except csv.Error as erro:
        raise FalhaDeColeta(
            ARQUIVO_INCOMPLETO, f"{arquivo}: leitura interrompida ({erro})"
        ) from erro
    except UnicodeDecodeError as erro:
        raise FalhaDeColeta(FORMATO_ALTERADO, f"{arquivo}: codificação inesperada") from erro


def _inteiro(valor: str, coluna: str, arquivo: str) -> int:
    try:
        return int(valor)
    except ValueError:
        raise _formato_alterado(arquivo, coluna) from None


def _data(valor: str, coluna: str, arquivo: str) -> datetime:
    try:
        return datetime.strptime(valor, FORMATO_DATA)
    except ValueError:
        raise _formato_alterado(arquivo, coluna) from None


def _id_da_uri(uri: str, coluna: str, arquivo: str) -> int:
    return _inteiro(uri.rstrip("/").rsplit("/", 1)[-1], coluna, arquivo)


def validar_arquivo(caminho: Path, colunas: tuple[str, ...]) -> int:
    """Percorre o arquivo inteiro e devolve o número de linhas de dados."""
    total = sum(1 for _ in _linhas(caminho, colunas))
    if total == 0:
        raise FalhaDeColeta(ARQUIVO_INCOMPLETO, f"{caminho.name}: arquivo sem linhas de dados")
    return total


def ler_apensacao(caminho: Path) -> Iterator[tuple[int, int]]:
    """Pares (id, id da principal) das proposições apensadas."""
    arquivo = caminho.name
    for pid, uri in _linhas(caminho, ("id", "uriPropPrincipal")):
        if uri:
            yield _inteiro(pid, "id", arquivo), _id_da_uri(uri, "uriPropPrincipal", arquivo)


def ler_ids_com_autor_novo(caminho: Path, partido: str, ids_deputados: set[int]) -> set[int]:
    """Ids das proposições com autor do `partido` na data da autoria ou deputado em `ids_deputados`.

    Percorre só as três colunas necessárias, sem montar um Autor por linha.
    """
    arquivo = caminho.name
    achados = set()
    colunas = ("idProposicao", "idDeputadoAutor", "siglaPartidoAutor")
    for id_proposicao, id_deputado, sigla in _linhas(caminho, colunas):
        if sigla == partido or (
            id_deputado and _inteiro(id_deputado, "idDeputadoAutor", arquivo) in ids_deputados
        ):
            achados.add(_inteiro(id_proposicao, "idProposicao", arquivo))
    return achados


def ler_proposicoes(caminho: Path, ids: set[int] | None = None) -> Iterator[Proposicao]:
    """Proposições do arquivo; com `ids`, só essas (e só elas têm as datas interpretadas)."""
    arquivo = caminho.name
    for linha in _linhas(caminho, PROPOSICOES_COLUNAS):
        pid = _inteiro(linha[0], "id", arquivo)
        if ids is not None and pid not in ids:
            continue
        principal = linha[6]
        yield Proposicao(
            id=pid,
            tipo=linha[1],
            numero=_inteiro(linha[2], "numero", arquivo),
            ano=_inteiro(linha[3], "ano", arquivo),
            ementa=linha[4],
            data_apresentacao=_data(linha[5], "dataApresentacao", arquivo),
            id_principal=_id_da_uri(principal, "uriPropPrincipal", arquivo) if principal else None,
            ultimo_status_em=_data(linha[7], "ultimoStatus_dataHora", arquivo),
            orgao=linha[8],
            situacao=linha[9],
        )


def ler_autores(caminho: Path, ids: set[int] | None = None) -> Iterator[Autor]:
    """Autores do arquivo; com `ids`, só os das proposições indicadas."""
    arquivo = caminho.name
    for linha in _linhas(caminho, AUTORES_COLUNAS):
        pid = _inteiro(linha[0], "idProposicao", arquivo)
        if ids is not None and pid not in ids:
            continue
        yield Autor(
            id_proposicao=pid,
            id_deputado=_inteiro(linha[1], "idDeputadoAutor", arquivo) if linha[1] else None,
            nome=linha[2],
            partido_na_data=linha[3],
            ordem=_inteiro(linha[4], "ordemAssinatura", arquivo),
        )


@dataclass(frozen=True)
class Lote:
    diretorio: Path
    anos: tuple[int, ...]
    last_modified_min: datetime  # UTC; o mais antigo entre os arquivos

    def proposicoes(self, ano: int) -> Path:
        return self.diretorio / f"proposicoes-{ano}.csv"

    def autores(self, ano: int) -> Path:
        return self.diretorio / f"proposicoesAutores-{ano}.csv"


def baixar_lote(
    transporte: Transporte, url_base: str, ano_minimo: int, ano_corrente: int, diretorio: Path
) -> Lote:
    """Baixa e valida os dois arquivos de cada ano; interrompe no primeiro arquivo inválido."""
    anos = tuple(range(ano_minimo, ano_corrente + 1))
    modificados = []
    for ano in anos:
        for pasta, colunas in (
            ("proposicoesAutores", AUTORES_COLUNAS),
            ("proposicoes", PROPOSICOES_COLUNAS),
        ):
            nome = f"{pasta}-{ano}.csv"
            baixado = transporte.baixar(f"{url_base}/arquivos/{pasta}/csv/{nome}", diretorio / nome)
            validar_arquivo(baixado.caminho, colunas)
            modificados.append(baixado.last_modified)
    return Lote(diretorio=diretorio, anos=anos, last_modified_min=min(modificados))
