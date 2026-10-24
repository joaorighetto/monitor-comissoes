"""Arquivos da checagem da pauta: o do dia (`data/pautas/AAAA-MM-DD.json`) e o `status-pauta.json`.

Contratos: specs/007-pauta-reunioes/contracts/pauta-json.md e status-pauta-json.md. A leitura do
arquivo anterior é a base da comparação, por isso é validada; o status é só registro, e um status
ilegível não impede a checagem.
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from ..erros import ENTRADA_INVALIDA, FalhaDeColeta
from ..estoque import BRASILIA
from ..saida import serializar
from ..status import gravar_todos

VERSAO_FORMATO = 1
SITUACOES = ("convocada", "realizada", "cancelada", "outra")
PADRAO_NOME = re.compile(r"(\d{4}-\d{2}-\d{2})\.json")
PADRAO_INICIO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
PADRAO_CHAVE = re.compile(r"p:\d+|t:.*", re.DOTALL)


def _invalida(caminho: Path, detalhe: str) -> FalhaDeColeta:
    return FalhaDeColeta(ENTRADA_INVALIDA, f"arquivo de pauta {caminho.name}: {detalhe}")


def ultimo_arquivo(pasta: Path, hoje: date) -> Path | None:
    """O arquivo `AAAA-MM-DD.json` mais recente com data até `hoje`, ou None.

    Outros nomes são ignorados. Um arquivo com data futura falha: comparar com ele faria a
    checagem de hoje registrar alterações contra um estado que ainda não existiu.
    """
    if not pasta.is_dir():
        return None
    datas = {}
    for caminho in pasta.iterdir():
        achado = PADRAO_NOME.fullmatch(caminho.name)
        if not achado:
            continue
        try:
            datas[date.fromisoformat(achado[1])] = caminho
        except ValueError:
            continue
    futuras = sorted(d for d in datas if d > hoje)
    if futuras:
        raise _invalida(datas[futuras[0]], f"data futura (hoje é {hoje.isoformat()})")
    return datas[max(datas)] if datas else None


def _com_fuso(valor) -> bool:
    if not isinstance(valor, str):
        return False
    try:
        return datetime.fromisoformat(valor).tzinfo is not None
    except ValueError:
        return False


def _validar_reuniao(reuniao, caminho: Path, posicao: int) -> None:
    def exigir(condicao: bool, campo: str) -> None:
        if not condicao:
            raise _invalida(caminho, f"reunião {posicao}: campo {campo} fora do formato")

    exigir(isinstance(reuniao, dict), "reunião")
    exigir(isinstance(reuniao.get("id"), int) and not isinstance(reuniao["id"], bool), "id")
    exigir(reuniao.get("situacao") in SITUACOES, "situacao")
    inicio = reuniao.get("inicio")
    exigir(isinstance(inicio, str) and PADRAO_INICIO.fullmatch(inicio) is not None, "inicio")
    exigir(_com_fuso(reuniao.get("vista_desde")), "vista_desde")
    pauta = reuniao.get("pauta")
    exigir(isinstance(pauta, list), "pauta")
    for item in pauta:
        chave = item.get("chave") if isinstance(item, dict) else None
        exigir(isinstance(chave, str) and PADRAO_CHAVE.fullmatch(chave) is not None, "pauta.chave")


def ler_pauta(caminho: Path) -> dict:
    """O arquivo do dia, validado como na seção "Validação na leitura" do contrato."""
    try:
        documento = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise _invalida(caminho, f"ilegível ({erro})") from erro
    if not isinstance(documento, dict):
        raise _invalida(caminho, "o conteúdo não é um objeto JSON")
    meta, checagem = documento.get("meta"), documento.get("checagem")
    if not isinstance(meta, dict) or meta.get("versao_formato") != VERSAO_FORMATO:
        raise _invalida(caminho, "meta ausente ou versao_formato desconhecida")
    if meta.get("data") != caminho.stem:
        raise _invalida(caminho, f"meta.data {meta.get('data')!r} difere do nome do arquivo")
    if not isinstance(checagem, dict) or not _com_fuso(checagem.get("checada_em")):
        raise _invalida(caminho, "checagem.checada_em ausente ou sem fuso")
    if not isinstance(checagem.get("reunioes"), list):
        raise _invalida(caminho, "checagem.reunioes não é lista")
    if not isinstance(documento.get("alteracoes"), list):
        raise _invalida(caminho, "alteracoes ausente ou não é lista")
    for posicao, reuniao in enumerate(checagem["reunioes"], start=1):
        _validar_reuniao(reuniao, caminho, posicao)
    return documento


def ler_status_pauta(caminho: Path) -> dict | None:
    """O status anterior, ou None se não existe ou está ilegível (com aviso no `stderr`)."""
    try:
        documento = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        print(f"AVISO: {caminho} ilegível, ignorado ({erro})", file=sys.stderr)
        return None
    valido = (
        isinstance(documento, dict)
        and documento.get("versao_formato") == VERSAO_FORMATO
        and documento.get("resultado") in ("ok", "falha")
        and _com_fuso(documento.get("verificado_em"))
        and "falha" in documento
        and (
            documento.get("ultima_checagem_boa") is None
            or _com_fuso(documento.get("ultima_checagem_boa"))
        )
    )
    if not valido:
        print(f"AVISO: {caminho} fora do formato, ignorado", file=sys.stderr)
        return None
    return documento


def montar_status_pauta(
    resultado: str, verificado_em: datetime, falha: dict | None, ultima_checagem_boa: str | None
) -> dict:
    """O `status-pauta.json`, na ordem de campos do contrato."""
    return {
        "versao_formato": VERSAO_FORMATO,
        "resultado": resultado,
        "verificado_em": verificado_em.astimezone(BRASILIA).isoformat(timespec="seconds"),
        "falha": falha,
        "ultima_checagem_boa": ultima_checagem_boa,
    }


def gravar(
    arquivo_do_dia: dict | None, caminho_dia: Path, status: dict, caminho_status: Path
) -> None:
    """Grava o arquivo do dia e o status juntos, tudo ou nada (`status.gravar_todos`).

    Sem arquivo do dia (falha da checagem), grava só o status.
    """
    escritas = [] if arquivo_do_dia is None else [(serializar(arquivo_do_dia), caminho_dia)]
    gravar_todos([*escritas, (serializar(status), caminho_status)])
