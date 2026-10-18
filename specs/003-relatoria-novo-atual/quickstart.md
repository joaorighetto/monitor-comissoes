# Quickstart: validar a REL

Guia para provar que a feature funciona de ponta a ponta. Contratos em [contracts/](contracts/), modelo em [data-model.md](data-model.md).

## Pré-requisitos

- `uv` instalado; Python 3.13.
- Passos 1 e 2: sem rede.
- Passo 3 (execução real): rede para `dadosabertos.camara.leg.br`, cerca de 1 GB de disco e alguns minutos.
- Recaptura das fixtures (só quando necessário): `uv run python tests/capturar_fixtures.py`, com rede.

## 1. Verificação completa (sem rede)

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

**Esperado:** código 0; todos os testes passam, inclusive `tests/test_relatoria.py`, `tests/test_tramitacoes.py` e os casos de `tests/test_aceitacao.py`.

## 2. Falha de tramitações deixa o arquivo anterior intacto (sem rede)

Coberto por `tests/test_falhas.py`. Esperado em cada cenário: saída com erro `FALHA [fonte_indisponivel]: …`, `[formato_alterado]` ou `[api_deputados]`, código 1 e `data/atual.json` idêntico byte a byte.

## 3. Execução real (com rede)

```bash
uv run python -m monitor_comissoes
echo "codigo=$?"
```

**Esperado:** código 0, linha `OK: N itens (…)` e `data/atual.json` com `meta.versao_formato = 2`.

## 4. Conferência dos casos de aceitação (manual, sobre `data/atual.json`)

```bash
python3 - <<'EOF'
import json
d = json.load(open("data/atual.json", encoding="utf-8"))
por = {i["identificacao"]: i for i in d["itens"]}
for nome in ("PL 4501/2023", "PL 937/2022", "PL 3514/2023", "PL 1843/2022"):
    i = por.get(nome)
    print(nome, "->", None if i is None else (i["etiquetas"], i["relator"] and i["relator"]["nome"]))
EOF
```

**Esperado (com os dados da sondagem de 17–18/10/2026):**

- `PL 4501/2023`: presente, etiquetas `['relatoria NOVO']`, relator Luiz Lima.
- `PL 937/2022` e `PL 3514/2023`: ausentes (`None`).
- `PL 1843/2022`: etiquetas `['autoria NOVO', 'relatoria NOVO']`, relatora Adriana Ventura.

Se a Câmara mudou a situação desses itens, a diferença precisa ser explicável pelas tramitações reais (`https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}/tramitacoes`).

## 5. Consistência do arquivo

```bash
python3 - <<'EOF'
import json
d = json.load(open("data/atual.json", encoding="utf-8"))
novo = {x["id"] for x in d["meta"]["deputados_novo_em_exercicio"]}
for i in d["itens"]:
    assert not (i["relator"] and i["relator_indeterminado"]), i["identificacao"]
    assert ("relatoria NOVO" in i["etiquetas"]) == bool(i["relator"] and i["relator"]["id"] in novo), i["identificacao"]
    assert i["etiquetas"] or i["relator_indeterminado"], i["identificacao"]
print("ok", len(d["itens"]), "itens")
EOF
```

**Esperado:** `ok N itens`, sem `AssertionError`.
