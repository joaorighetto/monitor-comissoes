"""Captura os recortes reais usados como fixtures. Ferramenta de desenvolvimento, não é teste.

Uso (com rede, uma vez; baixa cerca de 1 GB e descarta depois da seleção):

    uv run python tests/capturar_fixtures.py

Grava em tests/fixtures/camara/: proposicoes-AAAA.csv e proposicoesAutores-AAAA.csv (2003 a
2026), deputados-novo.json e manifesto.json. Os valores das linhas são copiados sem alteração;
só a serialização é refeita (BOM, ';', campos entre aspas, CRLF entre linhas, como na fonte).
"""

import csv
import json
import sys
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://dadosabertos.camara.leg.br"
ANOS = range(2003, 2027)
ALVOS = [("PL", "1843", "2022"), ("PL", "3871", "2024"), ("PL", "4047", "2019")]
COMISSOES = {"CE", "CREDN"}
FILLER = 2  # linhas reais mantidas em todo arquivo de ano, para que nenhum fique vazio
DESTINO = Path(__file__).parent / "fixtures" / "camara"

csv.field_size_limit(10**9)


def baixar(url: str, destino: Path) -> dict:
    with urllib.request.urlopen(url, timeout=120) as resp, open(destino, "wb") as saida:
        cabecalhos = {k.lower(): v for k, v in resp.headers.items()}
        while bloco := resp.read(1 << 20):
            saida.write(bloco)
    return cabecalhos


def ler(caminho: Path):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.reader(f, delimiter=";", strict=True)
        cabecalho = next(leitor)
        yield cabecalho
        yield from leitor


def id_da_uri(uri: str) -> int | None:
    return int(uri.rstrip("/").rsplit("/", 1)[1]) if uri else None


def gravar(caminho: Path, cabecalho: list[str], linhas: list[list[str]]) -> None:
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        w.writerow(cabecalho)
        w.writerows(linhas)


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        manifesto = {
            "capturado_em": datetime.now(UTC).isoformat(timespec="seconds"),
            "arquivos": {},
        }

        corpo_api = urllib.request.urlopen(
            urllib.request.Request(
                f"{BASE}/api/v2/deputados?siglaPartido=NOVO&itens=100",
                headers={"Accept": "application/json"},
            ),
            timeout=60,
        )
        total_api = corpo_api.headers.get("X-Total-Count")
        dados_api = corpo_api.read()
        deputados = {d["id"] for d in json.loads(dados_api)["dados"]}
        (DESTINO / "deputados-novo.json").write_bytes(dados_api)
        manifesto["deputados"] = {"x_total_count": total_api}

        for ano in ANOS:
            for tipo, pasta in (
                ("proposicoes", "proposicoes"),
                ("proposicoesAutores", "proposicoesAutores"),
            ):
                nome = f"{tipo}-{ano}.csv"
                cab = baixar(f"{BASE}/arquivos/{pasta}/csv/{nome}", tmp / nome)
                manifesto["arquivos"][nome] = {
                    "last_modified": cab.get("last-modified"),
                    "content_type": cab.get("content-type"),
                    "tamanho_original": int(cab["content-length"]),
                }
            print(f"baixado {ano}", file=sys.stderr)

        # Passada 1 (autores): proposições com ligação de autoria com o NOVO.
        novo = set()
        for ano in ANOS:
            leitor = ler(tmp / f"proposicoesAutores-{ano}.csv")
            cab = next(leitor)
            i_prop, i_dep, i_part = (
                cab.index(c) for c in ("idProposicao", "idDeputadoAutor", "siglaPartidoAutor")
            )
            for r in leitor:
                if r[i_part] == "NOVO" or (r[i_dep] and int(r[i_dep]) in deputados):
                    novo.add(int(r[i_prop]))

        # Passada 2 (proposições): mapa de apensação, alvos e candidatos de contraste.
        principal, todos, alvo_ids = {}, set(), {}
        contraste = {}
        for ano in ANOS:
            leitor = ler(tmp / f"proposicoes-{ano}.csv")
            cab = next(leitor)
            c = {
                n: cab.index(n)
                for n in (
                    "id",
                    "siglaTipo",
                    "numero",
                    "ano",
                    "uriPropPrincipal",
                    "ultimoStatus_siglaOrgao",
                )
            }
            for r in leitor:
                pid = int(r[c["id"]])
                todos.add(pid)
                if r[c["uriPropPrincipal"]]:
                    principal[pid] = id_da_uri(r[c["uriPropPrincipal"]])
                chave = (r[c["siglaTipo"]], r[c["numero"]], r[c["ano"]])
                if chave in ALVOS:
                    alvo_ids[chave] = pid
                tipo, orgao = r[c["siglaTipo"]], r[c["ultimoStatus_siglaOrgao"]]
                if orgao in COMISSOES and tipo in ("REQ", "PDL"):
                    contraste.setdefault(f"{tipo}_na_comissao", pid)
                if orgao in COMISSOES and tipo == "PL" and pid not in novo:
                    contraste.setdefault("PL_outro_partido_na_comissao", pid)
                if pid in novo and tipo == "PL" and orgao not in COMISSOES and pid not in principal:
                    contraste.setdefault("PL_novo_fora_das_comissoes", pid)

        faltando = [a for a in ALVOS if a not in alvo_ids]
        if faltando:
            print(f"ERRO: alvos não encontrados: {faltando}", file=sys.stderr)
            return 1

        def cadeia(pid):
            visto = [pid]
            while visto[-1] in principal and principal[visto[-1]] not in visto:
                visto.append(principal[visto[-1]])
            return visto

        # Exemplos reais de cadeia de 2+ níveis, de raiz ausente e de ciclo (se existirem).
        exemplos = {}
        for pid in principal:
            ch = cadeia(pid)
            ultimo = ch[-1]
            if len(ch) >= 3 and ultimo not in principal:
                exemplos.setdefault("cadeia_2_niveis", pid)
            if ultimo in principal:
                exemplos.setdefault("ciclo", pid)
            elif ultimo not in todos:
                exemplos.setdefault("raiz_ausente", pid)
        print("exemplos reais:", exemplos, file=sys.stderr)

        escolhidos = set(contraste.values()) | set(exemplos.values())
        escolhidos |= set(alvo_ids.values())
        for pid in list(escolhidos):
            escolhidos.update(cadeia(pid))
        manifesto["selecao"] = {
            "alvos": {f"{t} {n}/{a}": pid for (t, n, a), pid in alvo_ids.items()},
            "contraste": contraste,
            "exemplos_reais": exemplos,
            "total_ids_selecionados": len(escolhidos),
        }

        # Passada 3: grava os recortes de cada ano.
        for ano in ANOS:
            leitor = ler(tmp / f"proposicoes-{ano}.csv")
            cab = next(leitor)
            i_id = cab.index("id")
            linhas = [r for k, r in enumerate(leitor) if k < FILLER or int(r[i_id]) in escolhidos]
            gravar(DESTINO / f"proposicoes-{ano}.csv", cab, linhas)

            leitor = ler(tmp / f"proposicoesAutores-{ano}.csv")
            cab = next(leitor)
            i_prop = cab.index("idProposicao")
            linhas = [r for k, r in enumerate(leitor) if k < FILLER or int(r[i_prop]) in escolhidos]
            gravar(DESTINO / f"proposicoesAutores-{ano}.csv", cab, linhas)

        (DESTINO / "manifesto.json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print("fixtures gravadas em", DESTINO, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
