# Quickstart: validar a COL

Guia para provar que a feature funciona de ponta a ponta. Contratos em [contracts/](contracts/), modelo em [data-model.md](data-model.md).

## Pré-requisitos

- `uv` instalado; Python 3.13 (o `uv` resolve pelo `.python-version`).
- Para o passo 3 (execução real): acesso de rede a `dadosabertos.camara.leg.br`, cerca de 1 GB de disco livre e alguns minutos.
- Os passos 1 e 2 não precisam de rede.

## 1. Verificação completa (sem rede)

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

**Esperado:** os três comandos terminam com código 0; todos os testes passam, inclusive os três casos de aceitação (`tests/test_aceitacao.py`) e os de falha (`tests/test_falhas.py`).

## 2. Falha deixa o arquivo anterior intacto (sem rede)

Coberto por `tests/test_falhas.py`. Conferência manual do comportamento:

```bash
echo '{"sentinela": true}' > /tmp/anterior.json
printf 'comissoes = []\nano_minimo = 2003\n' > /tmp/config-invalida.toml
uv run python -m monitor_comissoes --config /tmp/config-invalida.toml --saida /tmp/anterior.json
echo "codigo=$?"; cat /tmp/anterior.json
```

**Esperado:** `FALHA [configuracao]: …` em stderr, `codigo=1` e `/tmp/anterior.json` ainda com `{"sentinela": true}`.

## 3. Execução real (com rede)

```bash
uv run python -m monitor_comissoes
echo "codigo=$?"
```

**Esperado:**
- Código 0 e uma linha `OK: N itens (CE: a, CREDN: b) · dados da Câmara de DD/MM/AAAA`.
- `data/atual.json` criado, conforme [contracts/atual-json.md](contracts/atual-json.md).
- N da mesma ordem de grandeza da sondagem: cerca de 50 itens somando `autoria NOVO` e `autor hoje no NOVO` (a sondagem contou 56 incluindo `relatoria NOVO`, que esta feature não gera). Diferenças precisam ser explicáveis item a item.
- Tempo e memória registrados em `research.md` (R7).

## 4. Conferência dos casos de aceitação (manual, sobre `data/atual.json`)

```bash
python3 - <<'EOF'
import json
d = json.load(open("data/atual.json", encoding="utf-8"))
por_ident = {i["identificacao"]: i for i in d["itens"]}
for ident in ("PL 1843/2022", "PL 3871/2024", "PL 4047/2019"):
    i = por_ident.get(ident)
    print(ident, "->", "FORA" if i is None else (i["etiquetas"], i["comissao"], i["apensado_a"]))
EOF
```

**Esperado:**
- `PL 1843/2022` → dentro, com `autoria NOVO`.
- `PL 3871/2024` → dentro, com `autor hoje no NOVO` e sem `autoria NOVO`.
- `PL 4047/2019` → `FORA`.

Depois, abra o `link` de dois itens e confirme que a ficha da Câmara é da mesma proposição.

## 5. Repetibilidade

```bash
cp data/atual.json /tmp/a.json
uv run python -m monitor_comissoes
diff <(python3 -c "import json;d=json.load(open('/tmp/a.json'));d['meta'].pop('gerado_em');print(json.dumps(d,sort_keys=True))") \
     <(python3 -c "import json;d=json.load(open('data/atual.json'));d['meta'].pop('gerado_em');print(json.dumps(d,sort_keys=True))") && echo IGUAIS
```

**Esperado:** `IGUAIS` (a execução repetida no mesmo dia só difere em `gerado_em`).
