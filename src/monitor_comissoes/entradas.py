"""Leitura e conferência das entradas do aviso diário (AVI): mudanças, `atual.json` e status.

O aviso só lê: nenhuma regra de domínio é recalculada aqui. Qualquer arquivo ausente, ilegível,
de versão desconhecida ou incoerente com o `status.json` do dia falha o envio (constituição, III):
nunca vira "sem mudanças" em silêncio.
"""

import json
from pathlib import Path

from . import mudancas as mud
from .erros import FalhaDeEnvio
from .status import ler_status

VERSOES_DO_ATUAL = (2, 3)  # as que trazem identificacao, link, comissao e principal_nao_localizada
CAMPOS_DO_ITEM = ("id", "identificacao", "comissao", "link", "principal_nao_localizada")


def _lido(caminho: Path, o_que: str) -> dict:
    """O objeto JSON do arquivo; `FalhaDeEnvio` com o nome do arquivo se não for possível."""
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except FileNotFoundError as erro:
        raise FalhaDeEnvio(f"{o_que} {caminho} não existe") from erro
    except (OSError, UnicodeDecodeError) as erro:
        raise FalhaDeEnvio(f"não foi possível ler {o_que} {caminho}: {erro}") from erro
    try:
        documento = json.loads(texto)
    except ValueError as erro:
        raise FalhaDeEnvio(f"{o_que} {caminho} não é um JSON válido: {erro}") from erro
    if not isinstance(documento, dict):
        raise FalhaDeEnvio(f"{o_que} {caminho} deve conter um objeto JSON")
    return documento


def ler_status_do_dia(caminho: Path) -> dict | None:
    """O status gravado pela coleta, ou None se o arquivo não existe."""
    try:
        return ler_status(caminho)
    except ValueError as erro:
        raise FalhaDeEnvio(str(erro)) from erro


def ler_mudancas(caminho: Path, status: dict) -> dict:
    """O arquivo de mudanças do dia, conferido contra o `status.json` (ok, com retrato bom)."""
    documento = _lido(caminho, "arquivo de mudanças")
    meta = documento.get("meta")
    versao = meta.get("versao_formato") if isinstance(meta, dict) else None
    if versao != mud.VERSAO_FORMATO:
        raise FalhaDeEnvio(
            f"arquivo de mudanças {caminho}: versao_formato {versao!r} não suportada "
            f"(esperada {mud.VERSAO_FORMATO})"
        )
    try:
        mud.validar_arquivo(documento)
    except Exception as erro:  # validar_arquivo levanta FalhaDeColeta(INTERNA) com o motivo
        motivo = getattr(erro, "motivo", str(erro))
        raise FalhaDeEnvio(f"arquivo de mudanças {caminho} fora do contrato: {motivo}") from erro

    if meta["data"] != status["data_referencia"]:
        raise FalhaDeEnvio(
            f"arquivo de mudanças {caminho}: data {meta['data']} difere da data_referencia "
            f"{status['data_referencia']} do status.json"
        )
    retrato_bom = status["ultimo_retrato_bom"]
    if retrato_bom is None:
        raise FalhaDeEnvio(
            f"arquivo de mudanças {caminho}: o status.json não tem ultimo_retrato_bom para conferir"
        )
    if meta["retrato"]["dados_camara_em"] != retrato_bom["dados_camara_em"]:
        raise FalhaDeEnvio(
            f"arquivo de mudanças {caminho}: dados_camara_em {meta['retrato']['dados_camara_em']} "
            f"difere do ultimo_retrato_bom do status.json ({retrato_bom['dados_camara_em']})"
        )
    for posicao, evento in enumerate(documento["eventos"]):
        apensado = evento["destino"]["apensado_a"] if evento["tipo"] == "saiu" else None
        if apensado is not None and not (
            isinstance(apensado.get("identificacao"), str) and apensado["identificacao"].strip()
        ):
            raise FalhaDeEnvio(
                f"arquivo de mudanças {caminho}: eventos[{posicao}].destino.apensado_a sem "
                "identificacao"
            )
    return documento


def ler_itens_do_atual(caminho: Path, status: dict | None = None) -> list[dict]:
    """Os itens do `atual.json`, só com o que o aviso usa (versões 2 e 3 do formato).

    Com `status`, confere que o arquivo é o retrato bom que o `status.json` descreve.
    """
    documento = _lido(caminho, "atual.json")
    meta = documento.get("meta")
    versao = meta.get("versao_formato") if isinstance(meta, dict) else None
    if isinstance(versao, bool) or versao not in VERSOES_DO_ATUAL:
        raise FalhaDeEnvio(
            f"{caminho}: meta.versao_formato {versao!r} não suportada (esperada uma de "
            f"{list(VERSOES_DO_ATUAL)})"
        )
    if status is not None and status["ultimo_retrato_bom"] is not None:
        esperado = status["ultimo_retrato_bom"]["dados_camara_em"]
        if meta.get("dados_camara_em") != esperado:
            raise FalhaDeEnvio(
                f"{caminho}: meta.dados_camara_em {meta.get('dados_camara_em')!r} difere do "
                f"ultimo_retrato_bom do status.json ({esperado})"
            )
    itens = documento.get("itens")
    if not isinstance(itens, list):
        raise FalhaDeEnvio(f"{caminho}: o campo itens deve ser uma lista")
    saida = []
    for posicao, item in enumerate(itens):
        if not isinstance(item, dict):
            raise FalhaDeEnvio(f"{caminho}: itens[{posicao}] deve ser um objeto")
        for campo in CAMPOS_DO_ITEM:
            valor = item.get(campo)
            if campo == "principal_nao_localizada":
                certo = isinstance(valor, bool)
            elif campo == "id":
                certo = isinstance(valor, int) and not isinstance(valor, bool)
            else:
                certo = isinstance(valor, str) and bool(valor.strip())
            if not certo:
                raise FalhaDeEnvio(f"{caminho}: itens[{posicao}].{campo} ausente ou inválido")
        saida.append({campo: item[campo] for campo in CAMPOS_DO_ITEM})
    return saida
