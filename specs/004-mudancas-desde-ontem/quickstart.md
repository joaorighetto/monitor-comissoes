# Quickstart: conferir a MUD

Guia de validação. Os formatos estão em [contracts/](contracts/) e as regras, em [data-model.md](data-model.md).

## 1. Verificação completa (sem rede)

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Esperado: ruff sem erros e todos os testes verdes, sem acesso à internet (a guarda de rede do `conftest.py` derruba qualquer tentativa). Os testes cobrem cada tipo de evento, cada motivo de saída e de entrada, as linhas de base, a reexecução no mesmo dia e cada falha.

## 2. Conferência manual (precisa de rede: baixa o lote, cerca de 1 GB)

Use uma pasta de trabalho para não mexer em `data/`:

```bash
D=$(mktemp -d)
ARGS="--atual $D/atual.json --status $D/status.json --anterior $D/anterior.json --mudancas $D/mudancas"
```

### 2.1 Primeiro dia: linha de base

```bash
uv run python -m monitor_comissoes.diaria executar $ARGS
ls $D $D/mudancas
python3 -c "import json,sys,glob; d=json.load(open(glob.glob('$D/mudancas/*.json')[0])); print(d['meta']['linha_de_base'], len(d['eventos']))"
```

Esperado: `OK: ... mudanças: linha de base (primeiro retrato)`; existem `atual.json`, `status.json` e `mudancas/AAAA-MM-DD.json`, mas **não** `anterior.json`; a última linha imprime `{'motivo': 'primeiro retrato', 'total_itens': N} 0`.

### 2.2 Reexecução no mesmo dia dá o mesmo arquivo

```bash
cp $D/mudancas/*.json $D/primeiro.json
uv run python -m monitor_comissoes.diaria executar $ARGS
cmp $D/primeiro.json $D/mudancas/*.json && echo IGUAL
```

Esperado: `IGUAL` (e `anterior.json` continua inexistente). Se o lote da Câmara for regenerado entre as duas execuções, o `dados_camara_em` muda e o `cmp` acusa diferença: refaça com o lote já estável.

### 2.3 Dia seguinte: simular um retrato de ontem alterado

Faça o `atual.json` parecer de ontem, com um item a menos e outro com situação diferente, e rode de novo:

```bash
python3 - <<EOF
import json
from datetime import date, timedelta
ontem = date.today() - timedelta(days=1)
p = "$D/atual.json"
d = json.load(open(p))
d["meta"]["gerado_em"] = f"{ontem}T09:00:00-03:00"
d["meta"]["dados_camara_em"] = f"{ontem}T04:30:00+00:00"
d["itens"].pop(0)                                       # este item vai aparecer em "entrou"
d["itens"][0]["situacao"] = "Situação inventada"        # este vai aparecer em "situacao"
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
EOF
uv run python -m monitor_comissoes.diaria executar $ARGS
python3 -c "import json,glob; d=json.load(open(glob.glob('$D/mudancas/*.json')[0])); print(d['meta']['total_por_tipo'], [ (e['tipo'], e['identificacao']) for e in d['eventos']])"
```

Esperado: `anterior.json` passa a existir (cópia do arquivo alterado); `total_por_tipo` com 1 `entrou` e 1 `situacao`; no `entrou`, o motivo tende a ser `ganhou_etiqueta` (o item está na comissão há muito tempo, então a chegada é anterior ao corte), e o evento de `situacao` traz `de: "Situação inventada"`. Confira cada evento na ficha oficial (`link`). Os dois eventos são fabricados pela simulação, não mudanças reais.

### 2.4 Retrato anterior corrompido falha, sem tocar nos arquivos

```bash
python3 - <<EOF
import json
from datetime import date, timedelta
p = "$D/atual.json"
d = json.load(open(p)); d["meta"]["gerado_em"] = f"{date.today() - timedelta(days=1)}T09:00:00-03:00"
del d["itens"]; json.dump(d, open(p, "w"))
EOF
sha256sum $D/atual.json $D/anterior.json $D/mudancas/*.json > $D/antes.sha
uv run python -m monitor_comissoes.diaria executar $ARGS; echo "saída=$?"
sha256sum -c $D/antes.sha
```

Esperado: `FALHA [interna]: retrato anterior inválido ...`, `saída=1`, e o `sha256sum -c` dá `OK` para os três arquivos (`atual.json`, `anterior.json` e o arquivo de mudanças). O `status.json` registra a falha.

## 3. Reparar um `atual.json` corrompido no repositório

Se a execução diária falhar com "retrato anterior inválido (data/atual.json)": restaure o último bom com `git checkout <commit-bom> -- data/atual.json` e faça commit, ou apague o arquivo para recomeçar com uma linha de base ("primeiro retrato"; um dia de eventos se perde, e o arquivo do dia diz isso).

### 3.1 Falha `formato_alterado` por sequência inconsistente

Se a execução falhar com "sequência regrediu" ou "a resposta não contém a sequência do lote" para uma proposição, a Câmara renumerou ou corrigiu as tramitações dela. A execução falha de propósito (nada é publicado pela metade) e continuará falhando até o retrato anterior deixar de conter o item com a sequência antiga. Para recuperar, com a decisão do mantenedor: apague `data/anterior.json` e `data/atual.json` (recomeça com uma linha de base; um dia de eventos se perde, e o arquivo do dia diz isso) e rode a coleta de novo. Registre o caso, com a proposição, em `docs/fontes.md`.

## 4. No Actions

Depois do merge, rode o workflow "Coleta diária" manualmente (`workflow_dispatch`). No primeiro dia espera-se o commit com `data/atual.json` (versão 3), `data/status.json`, `data/anterior.json` (cópia do `atual.json` anterior) e `data/mudancas/AAAA-MM-DD.json` como linha de base com o motivo "formato anterior incompatível". Rode de novo no mesmo dia: o commit traz o mesmo arquivo de mudanças. No dia seguinte, o primeiro arquivo com eventos reais; confira cada evento na ficha oficial (spec, SC-009).
