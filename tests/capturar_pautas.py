"""Captura as respostas reais da API usadas como fixtures da PAU. Ferramenta de desenvolvimento.

Uso (com rede, uma vez):

    uv run python tests/capturar_pautas.py

Grava em tests/fixtures/pauta/, byte a byte: orgaos/{sigla}.json,
eventos/{orgao}-{inicio}-{fim}.json (janelas escolhidas), eventos/{id}.json (detalhe),
pautas/{id}.json (cada reunião deliberativa das janelas e as avulsas) e manifesto.json (endpoint e
momento de cada captura). Não é coletado pelo pytest: o nome não começa com `test_`.
"""

import json
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API = "https://dadosabertos.camara.leg.br/api/v2"
DESTINO = Path(__file__).parent / "fixtures" / "pauta"
REUNIAO = "Reunião Deliberativa"

ORGAOS = {"CE": 2009, "CREDN": 2018}
# Janelas de D−7 a D+7 (research R11): cada uma é a consulta de uma checagem no dia D.
JANELAS = [
    (2009, "2026-10-17", "2026-10-31"),  # D = 24/10/2026: 83091, convocada
    (2009, "2026-04-08", "2026-04-22"),  # D = 15/04/2026: 81366 e 81555
    (2018, "2026-04-08", "2026-04-22"),  # D = 15/04/2026: 81483 (MSC, PDL) e 81609 ("outro")
    (2009, "2025-11-26", "2025-12-10"),  # D = 03/12/2025: 80344, 80560, 80732 (cancelada)
    (2018, "2025-11-26", "2025-12-10"),  # D = 03/12/2025: 80594 (Encerrada (Termo)) e outras
]
DETALHES = [81555, 83091]
# 81862: o único caso real de "rejeitado" (2 itens) em 12 meses. 80265: "Prejudicado o Requerimento
# de Retirada de Pauta… Retirado de pauta…" (PL 725/2024), a exceção do §5.9 na mesma frase.
PAUTAS_AVULSAS = [80265, 81862]


def baixar_json(url: str, tentativas: int = 3) -> tuple[bytes, dict[str, str]]:
    """Corpo e cabeçalhos da resposta, com novas tentativas e uma pausa curta entre pedidos."""
    for numero in range(tentativas):
        try:
            requisicao = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(requisicao, timeout=60) as resp:
                corpo = resp.read()
                cabecalhos = {k.lower(): v for k, v in resp.headers.items()}
            time.sleep(0.1)
            return corpo, cabecalhos
        except OSError:
            if numero == tentativas - 1:
                raise
            time.sleep(2 * (numero + 1))
    raise AssertionError("tentativas deve ser maior que zero")


def main() -> int:
    manifesto: dict = {"arquivos": {}}

    def salvar(relativo: str, url: str) -> bytes:
        corpo, cabecalhos = baixar_json(url)
        caminho = DESTINO / relativo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(corpo)
        manifesto["arquivos"][relativo] = {
            "endpoint": url.removeprefix(API),
            "capturado_em": datetime.now(UTC).isoformat(timespec="seconds"),
            "x_total_count": cabecalhos.get("x-total-count"),
        }
        return corpo

    for sigla in ORGAOS:
        salvar(f"orgaos/{sigla}.json", f"{API}/orgaos?sigla={sigla}&itens=10")

    reunioes: set[int] = set(PAUTAS_AVULSAS)
    for orgao, inicio, fim in JANELAS:
        url = f"{API}/orgaos/{orgao}/eventos?dataInicio={inicio}&dataFim={fim}&itens=100"
        corpo = salvar(f"eventos/{orgao}-{inicio}-{fim}.json", url)
        reunioes |= {e["id"] for e in json.loads(corpo)["dados"] if e["descricaoTipo"] == REUNIAO}

    for id_evento in DETALHES:
        salvar(f"eventos/{id_evento}.json", f"{API}/eventos/{id_evento}")
    for id_evento in sorted(reunioes):
        salvar(f"pautas/{id_evento}.json", f"{API}/eventos/{id_evento}/pauta")

    (DESTINO / "manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(manifesto['arquivos'])} arquivos gravados em {DESTINO}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
