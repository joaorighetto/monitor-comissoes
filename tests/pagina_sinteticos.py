"""Entradas sintéticas da PAG: retrato, status e arquivos de mudanças, e a gravação em disco.

Reaproveita `sinteticos.py` (itens e retrato) e `aviso_sinteticos.py` (eventos, mudanças e status),
que seguem os contratos da COL, da AGE e da MUD. Os ids, as identificações e os links vêm de itens
reais do `data/atual.json` de 20/10/2026.
"""

import json
from pathlib import Path
from typing import NamedTuple

import aviso_sinteticos as a
import sinteticos as s
from monitor_comissoes.saida import serializar

FIXTURES = Path(__file__).parent / "fixtures" / "pagina"
DIA = a.DIA
DADOS_CAMARA_EM = a.DADOS_CAMARA_EM

evento = a.evento
muitos_eventos = a.muitos_eventos
status_falha = a.status_falha
status_ok = a.status_ok

# Os campos que `sinteticos.item` aceita; qualquer outro é aplicado depois, sobre o dicionário.
_CAMPOS_DO_CONSTRUTOR = (
    "numero",
    "ano",
    "comissao",
    "situacao",
    "etiquetas",
    "relator",
    "relator_indeterminado",
    "apensado_a",
    "sequencia",
    "ultimo_status_em",
    "principal_nao_localizada",
)


class Entradas(NamedTuple):
    """Os caminhos que o CLI recebe: o `atual.json`, o `status.json` e a pasta de mudanças."""

    atual: Path
    status: Path
    mudancas: Path


def retrato_real() -> dict:
    """O `atual.json` real de 20/10/2026 (105 itens), versão 2 do formato."""
    return json.loads((FIXTURES / "atual-real.json").read_text(encoding="utf-8"))


def status_real() -> dict:
    """O `status.json` real de 20/10/2026, coerente com `retrato_real()`."""
    return json.loads((FIXTURES / "status-ok.json").read_text(encoding="utf-8"))


def item_completo(id: int = 1, **campos) -> dict:
    """Um item completo (versão 3); `campos` sobrescreve qualquer campo do contrato."""
    do_construtor = {n: campos.pop(n) for n in list(campos) if n in _CAMPOS_DO_CONSTRUTOR}
    item = s.item(id=id, **do_construtor)
    item.update(campos)
    return item


def retrato_com(itens, *, dia: str = DIA, dados_camara_em: str = DADOS_CAMARA_EM, **meta) -> dict:
    """Um `atual.json` coerente com `status_ok(dia=dia)` e com o arquivo de mudanças do dia."""
    return s.retrato(
        itens,
        gerado_em=f"{dia}T03:40:12-03:00",
        dados_camara_em=dados_camara_em,
        **meta,
    )


def arquivo_de_mudancas(
    dia: str = DIA,
    eventos=(),
    *,
    linha_de_base=None,
    dia_anterior: str | None = None,
    dados_camara_em: str | None = None,
) -> dict:
    """O arquivo de mudanças de `dia`, validado por `mudancas.validar_arquivo`."""
    retrato = {
        "dia": dia,
        "dados_camara_em": dados_camara_em or f"{dia}T04:31:26+00:00",
    }
    anterior = None
    if dia_anterior is not None:
        anterior = {"dia": dia_anterior, "dados_camara_em": f"{dia_anterior}T04:31:26+00:00"}
    return a.mudancas(
        eventos,
        linha_de_base=linha_de_base,
        retrato=retrato,
        retrato_anterior=anterior,
        dia=dia,
    )


def gravar_entradas(
    pasta: Path, retrato: dict, status: dict | None, arquivos: dict[str, dict] | None = None
) -> Entradas:
    """Grava `atual.json`, `status.json` e `mudancas/AAAA-MM-DD.json` em `pasta`."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    atual = pasta / "atual.json"
    atual.write_text(serializar(retrato), encoding="utf-8", newline="\n")
    caminho_status = pasta / "status.json"
    if status is not None:
        caminho_status.write_text(serializar(status), encoding="utf-8", newline="\n")
    pasta_mudancas = pasta / "mudancas"
    for dia, documento in (arquivos or {}).items():
        pasta_mudancas.mkdir(exist_ok=True)
        (pasta_mudancas / f"{dia}.json").write_text(
            serializar(documento), encoding="utf-8", newline="\n"
        )
    return Entradas(atual, caminho_status, pasta_mudancas)
