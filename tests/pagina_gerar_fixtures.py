"""Gera as fixtures derivadas de `tests/fixtures/pagina/` a partir de `pagina_sinteticos`.

Uso (só quando o contrato mudar): `uv run python tests/pagina_gerar_fixtures.py`. Os arquivos são
versionados; `test_pagina_sinteticos.py` confere que eles continuam iguais ao que este script grava.
Não geradas aqui: `atual-real.json` e `status-ok.json` (cópias dos arquivos reais de 20/10/2026) e
`atual-formato-4.json` (a cópia do primeiro com `meta.versao_formato` 4).
"""

import json
from datetime import date, datetime
from pathlib import Path

import pagina_sinteticos as p
from monitor_comissoes.saida import serializar
from monitor_comissoes.status import montar_status
from monitor_comissoes.tramitacoes import Tramitacao

RAIZ = p.FIXTURES
CORROMPIDO = "{ isto não é um JSON válido\n"


def _status_ok_real() -> dict:
    return json.loads((RAIZ / "status-ok.json").read_text(encoding="utf-8"))


def _status_de_falha() -> dict:
    return montar_status(
        resultado="falha",
        verificado_em=datetime.fromisoformat("2026-10-21T09:00:00-03:00"),
        data_referencia=date(2026, 10, 21),
        tentativas=4,
        falha={
            "categoria": "arquivos_desatualizados",
            "motivo": "a Câmara não atualizou os arquivos",
        },
        variacao_aceita=None,
        retrato=_status_ok_real()["ultimo_retrato_bom"],
    )


def _status_retrato_outro() -> dict:
    ok = _status_ok_real()
    ok["ultimo_retrato_bom"] = {
        **ok["ultimo_retrato_bom"],
        "dados_camara_em": "2026-10-19T04:31:26+00:00",
    }
    return ok


def _mudancas_do_dia_20() -> dict:
    tramitacoes = [
        Tramitacao(41, "2026-10-19T10:15", "CE", "320", "Designado Relator, Dep. Luiz Lima", None),
        Tramitacao(42, "2026-10-20T08:00", "CE", "322", "Parecer do Relator, Dep. Luiz Lima", None),
    ]
    return p.arquivo_de_mudancas(
        p.DIA,
        [
            p.evento("entrou", "ce_a"),
            p.evento("saiu", "ce_b"),
            p.evento("situacao", "ce_c", tramitacoes=tramitacoes[:1]),
            p.evento("relator", "ce_d"),
            p.evento("parecer", "ce_e", tramitacoes=tramitacoes),
            p.evento("etiquetas", "credn_a"),
        ],
        dia_anterior="2026-10-19",
    )


def _mudancas_do_dia_16() -> dict:
    apensado = {
        "id": 2190633,
        "identificacao": "PL 155/2019",
        "link": "https://www.camara.leg.br/propostas-legislativas/2190633",
    }
    saiu = p.evento(
        "saiu",
        "ce_b",
        motivo={
            "codigo": "apensado_fora_da_lista",
            "texto": "apensado a uma proposição fora da lista",
        },
        destino={"orgao": "CFT", "situacao": "Aguardando Parecer", "apensado_a": apensado},
    )
    return p.arquivo_de_mudancas("2026-10-16", [saiu], dia_anterior="2026-10-14")


def arquivos() -> dict[Path, str]:
    """Caminho -> texto de cada fixture derivada."""
    base_primeiro = p.arquivo_de_mudancas(
        "2026-10-18",
        linha_de_base={"motivo": "primeiro retrato", "total_itens": 105},
    )
    return {
        RAIZ / "status-falha.json": serializar(_status_de_falha()),
        RAIZ / "status-falha-sem-retrato.json": serializar(
            p.status_falha(dia="2026-10-21", com_retrato_bom=False)
        ),
        RAIZ / "status-retrato-outro.json": serializar(_status_retrato_outro()),
        RAIZ / "mudancas" / "2026-10-20.json": serializar(_mudancas_do_dia_20()),
        RAIZ / "mudancas" / "2026-10-19.json": serializar(
            p.arquivo_de_mudancas("2026-10-19", dia_anterior="2026-10-18")
        ),
        RAIZ / "mudancas" / "2026-10-18.json": serializar(base_primeiro),
        RAIZ / "mudancas" / "2026-10-16.json": serializar(_mudancas_do_dia_16()),
        RAIZ / "mudancas-teto" / "2026-10-20.json": serializar(p.muitos_eventos(25)),
        RAIZ / "mudancas-invalida-fora-da-janela" / "2026-10-20.json": serializar(
            p.arquivo_de_mudancas(p.DIA, [p.evento("entrou", "ce_a")], dia_anterior="2026-10-19")
        ),
        RAIZ / "mudancas-invalida-fora-da-janela" / "2026-10-10.json": CORROMPIDO,
    }


if __name__ == "__main__":
    for caminho, texto in arquivos().items():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8", newline="\n")
        print(caminho.relative_to(RAIZ.parent.parent.parent))
