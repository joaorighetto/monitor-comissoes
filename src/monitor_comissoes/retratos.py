"""O retrato (`data/atual.json`) como base de comparação da MUD (data-model.md, "Retrato").

`ler` valida o arquivo e diz de que dia ele é. Um retrato de outra versão de formato é válido,
mas incompatível: a comparação o trata como linha de base. Um retrato ilegível ou fora do
contrato nunca vira linha de base em silêncio: levanta `FalhaDeColeta(INTERNA)`.
"""

import json
from datetime import date, datetime
from typing import NamedTuple

from .erros import INTERNA, FalhaDeColeta
from .estoque import BRASILIA

# A versão de formato que a comparação entende (a de `coleta.VERSAO_FORMATO`; um teste confere).
VERSAO_COMPARAVEL = 3


class Retrato(NamedTuple):
    documento: dict
    dia: date  # a data de `meta.gerado_em`, em Brasília
    gerado_em: datetime
    dados_camara_em: datetime
    compativel: bool  # `meta.versao_formato` igual a `VERSAO_COMPARAVEL`


def _invalido(origem: str, detalhe: str) -> FalhaDeColeta:
    return FalhaDeColeta(INTERNA, f"retrato anterior inválido ({origem}): {detalhe}")


def _inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _data_e_hora(meta: dict, campo: str, origem: str) -> datetime:
    valor = meta.get(campo)
    if not isinstance(valor, str):
        raise _invalido(origem, f"campo meta.{campo}")
    try:
        momento = datetime.fromisoformat(valor)
    except ValueError:
        raise _invalido(origem, f"campo meta.{campo} ({valor!r} não é data e hora ISO)") from None
    if momento.tzinfo is None:
        raise _invalido(origem, f"campo meta.{campo} ({valor!r} sem fuso horário)")
    return momento


def _texto(valor, caminho: str, origem: str) -> None:
    if not isinstance(valor, str):
        raise _invalido(origem, f"campo {caminho}")


def _objeto_ou_nulo(valor, caminho: str, origem: str, campos: dict[str, type]) -> None:
    """`valor` é nulo ou um objeto com os `campos` (texto ou inteiro, conforme o tipo)."""
    if valor is None:
        return
    if not isinstance(valor, dict):
        raise _invalido(origem, f"campo {caminho}")
    for campo, tipo in campos.items():
        if campo not in valor:
            raise _invalido(origem, f"campo {caminho}.{campo}")
        if tipo is int:
            if not _inteiro(valor[campo]):
                raise _invalido(origem, f"campo {caminho}.{campo}")
        else:
            _texto(valor[campo], f"{caminho}.{campo}", origem)


def _validar_item(item, posicao: int, origem: str) -> int:
    caminho = f"itens[{posicao}]"
    if not isinstance(item, dict):
        raise _invalido(origem, f"campo {caminho}")
    for campo in (
        "id",
        "identificacao",
        "link",
        "comissao",
        "situacao",
        "etiquetas",
        "relator",
        "relator_indeterminado",
        "apensado_a",
        "ultimo_status_sequencia",
    ):
        if campo not in item:
            raise _invalido(origem, f"campo {caminho}.{campo}")
    if not _inteiro(item["id"]):
        raise _invalido(origem, f"campo {caminho}.id")
    for campo in ("identificacao", "link", "comissao", "situacao"):
        _texto(item[campo], f"{caminho}.{campo}", origem)
    etiquetas = item["etiquetas"]
    if not isinstance(etiquetas, list) or not all(isinstance(e, str) for e in etiquetas):
        raise _invalido(origem, f"campo {caminho}.etiquetas")
    _objeto_ou_nulo(
        item["relator"], f"{caminho}.relator", origem, {"id": int, "nome": str, "partido_hoje": str}
    )
    _objeto_ou_nulo(
        item["relator_indeterminado"], f"{caminho}.relator_indeterminado", origem, {"motivo": str}
    )
    _objeto_ou_nulo(
        item["apensado_a"],
        f"{caminho}.apensado_a",
        origem,
        {"id": int, "identificacao": str, "link": str},
    )
    sequencia = item["ultimo_status_sequencia"]
    if not _inteiro(sequencia) or sequencia < 1:
        raise _invalido(origem, f"campo {caminho}.ultimo_status_sequencia")
    return item["id"]


def ler(texto: str, origem: str, *, validar_itens: bool = True) -> Retrato:
    """Valida o texto de um `atual.json` e devolve o retrato.

    `origem` é o nome do arquivo, só para a mensagem. Com `validar_itens=False` basta o `meta`
    estar legível (o `atual.json` do próprio dia será sobrescrito, mas o dia dele precisa ser
    conhecido). Em versão de formato diferente da comparável, os itens não são validados.
    """
    try:
        documento = json.loads(texto)
    except ValueError as erro:
        raise _invalido(origem, f"o arquivo deve conter um objeto JSON ({erro})") from erro
    if not isinstance(documento, dict):
        raise _invalido(origem, "o arquivo deve conter um objeto JSON")
    meta = documento.get("meta")
    if not isinstance(meta, dict):
        raise _invalido(origem, "campo meta")
    if "itens" not in documento:
        raise _invalido(origem, "campo itens")
    versao = meta.get("versao_formato")
    if not _inteiro(versao):
        raise _invalido(origem, "campo meta.versao_formato")
    gerado_em = _data_e_hora(meta, "gerado_em", origem)
    dados_camara_em = _data_e_hora(meta, "dados_camara_em", origem)
    compativel = versao == VERSAO_COMPARAVEL

    if compativel and validar_itens:
        itens = documento["itens"]
        if not isinstance(itens, list):
            raise _invalido(origem, "campo itens")
        vistos: set[int] = set()
        for posicao, item in enumerate(itens):
            identificador = _validar_item(item, posicao, origem)
            if identificador in vistos:
                raise _invalido(origem, f"campo itens[{posicao}].id (id repetido: {identificador})")
            vistos.add(identificador)

    return Retrato(
        documento=documento,
        dia=gerado_em.astimezone(BRASILIA).date(),
        gerado_em=gerado_em,
        dados_camara_em=dados_camara_em,
        compativel=compativel,
    )
