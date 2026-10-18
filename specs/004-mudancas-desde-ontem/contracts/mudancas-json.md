# Contrato: `data/mudancas/AAAA-MM-DD.json`

Um arquivo por dia de execução. `AAAA-MM-DD` é a data da execução em Brasília. Codificação UTF-8, `ensure_ascii` desligado, indentação de 2 espaços, uma quebra de linha no fim, ordem de campos **fixa** (a mesma do `atual.json`). O arquivo não traz hora de execução: só datas e o `dados_camara_em` do lote, para que duas execuções sobre os mesmos dados deem o mesmo arquivo, byte a byte.

## Estrutura

```json
{
  "meta": {
    "versao_formato": 1,
    "data": "2026-10-19",
    "retrato": {"dia": "2026-10-19", "dados_camara_em": "2026-10-19T04:31:36+00:00"},
    "retrato_anterior": {"dia": "2026-10-18", "dados_camara_em": "2026-10-18T04:31:36+00:00"},
    "linha_de_base": null,
    "total_eventos": 3,
    "total_por_tipo": {"entrou": 1, "saiu": 1, "situacao": 1, "relator": 0, "parecer": 0, "etiquetas": 0}
  },
  "eventos": [],
  "ressalvas": []
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `meta.versao_formato` | inteiro | `1` |
| `meta.data` | texto `AAAA-MM-DD` | Data da execução (igual ao nome do arquivo) |
| `meta.retrato` | objeto | `dia` (data de `gerado_em`, Brasília) e `dados_camara_em` (do `meta` do `atual.json` de hoje) |
| `meta.retrato_anterior` | `null` ou objeto | Mesmos campos do retrato anterior. `null` quando não há retrato anterior. Em linha de base por formato incompatível, vem preenchido (informativo) |
| `meta.linha_de_base` | `null` ou objeto | `{"motivo": "primeiro retrato" \| "formato anterior incompatível", "total_itens": N}`. Quando preenchido, `eventos` e `ressalvas` são `[]` |
| `meta.total_eventos` | inteiro | `len(eventos)` |
| `meta.total_por_tipo` | objeto | Contagem por tipo, com as seis chaves sempre presentes, na ordem fixa |
| `eventos` | lista | Ordem: comissão (a da configuração), tipo, `id` |
| `ressalvas` | lista | Ordem por `id` |

O intervalo coberto vai de `retrato_anterior.dia` a `retrato.dia`, e pode ter mais de um dia.

## Campos comuns do evento

Nesta ordem: `tipo`, `id`, `identificacao`, `comissao`, `link`, os campos próprios do tipo, `tramitacoes`.

| Campo | Descrição |
|---|---|
| `tipo` | `entrou`, `saiu`, `situacao`, `relator`, `parecer` ou `etiquetas` |
| `id`, `identificacao`, `link` | O item (a proposição que consta da lista), com o link oficial da ficha |
| `comissao` | Comissão do item hoje; em `saiu`, a comissão do retrato anterior |
| `tramitacoes` | Lista possivelmente vazia, por `sequencia`. Cada elemento: `sequencia` (inteiro), `data_hora` (`AAAA-MM-DDTHH:MM`, como a API entrega), `orgao`, `codigo`, `descricao` |

## Campos próprios

### `entrou`

```json
{"motivo": {"codigo": "chegou_a_comissao", "texto": "chegou à comissão"},
 "etiquetas": ["autoria NOVO"]}
```

`motivo.codigo`: `chegou_a_comissao`, `ganhou_etiqueta` (o `texto` diz qual: "ganhou etiqueta: autor hoje no NOVO") ou `nao_determinado`. `etiquetas`: as de hoje.

### `saiu`

```json
{"motivo": {"codigo": "arquivado_art_105", "texto": "arquivado, art. 105"},
 "destino": {"orgao": "MESA", "situacao": "Arquivada", "apensado_a": null},
 "outros_fatos": ["outro_orgao"]}
```

| Campo | Descrição |
|---|---|
| `motivo.codigo` | `arquivado_art_105`, `arquivado`, `transformado_em_norma`, `aprovado_segue_ao_senado`, `encerrado`, `apensado_fora_da_lista`, `outro_orgao`, `perdeu_etiquetas` ou `nao_determinado` |
| `motivo.texto` | Texto de leitura: "arquivado, art. 105", "arquivado", "transformado em norma jurídica", "aprovado, segue ao Senado", "encerrado" (a situação vai em `destino`), "apensado a uma proposição fora da lista", "foi para outro órgão", "perdeu as etiquetas: autoria NOVO, relatoria NOVO", "não determinado" |
| `destino.orgao` | Órgão da referência hoje; `null` se a proposição não está no lote |
| `destino.situacao` | Situação da referência hoje; `null` se a proposição não está no lote |
| `destino.apensado_a` | `null` ou `{id, identificacao, link}` da raiz |
| `outros_fatos` | Lista (possivelmente vazia) de códigos que também valiam, entre `situação final` (o código do motivo correspondente), `apensado_fora_da_lista` e `outro_orgao`, na ordem de precedência |

### `situacao`

`{"de": "Aguardando Parecer", "para": "Pronta para Pauta"}`

### `relator`

```json
{"mudanca": "substituido",
 "de": {"id": 204528, "nome": "Adriana Ventura", "partido_hoje": "NOVO"},
 "para": {"id": 204455, "nome": "Luiz Lima", "partido_hoje": "NOVO"}}
```

`mudanca`: `designado` (`de` é `null`), `devolveu` (`para` é `null`) ou `substituido`.

### `parecer`

Sem campos próprios. O `link` é o da ficha da referência; as tramitações de código `322` do intervalo vão em `tramitacoes`, junto com as demais do intervalo.

### `etiquetas`

`{"ganhou": ["relatoria NOVO"], "perdeu": []}`. Pelo menos uma das listas não é vazia. Ordem fixa: `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO`.

## Ressalva

```json
{"id": 2388105, "identificacao": "PL 4501/2023", "comissao": "CE", "link": "https://www.camara.leg.br/propostas-legislativas/2388105",
 "motivo": "comparação de relator impossível: relator indeterminado hoje"}
```

`motivo`: "relator indeterminado ontem", "relator indeterminado hoje" ou "relator indeterminado nos dois retratos".

## Regras de consistência (verificadas nos testes)

1. `meta.total_eventos` e `meta.total_por_tipo` batem com `eventos`.
2. Linha de base: `eventos` e `ressalvas` vazios, `linha_de_base` preenchido; com `linha_de_base` nulo, `retrato_anterior` é não nulo.
3. Nenhum `motivo` vazio; todo evento tem `link` oficial.
4. Um item aparece no máximo uma vez por tipo.
5. Em `saiu`, o `id` não está no `atual.json` de hoje. Em `entrou`, está. Nos demais tipos, está nos dois retratos.
6. As `tramitacoes` de cada evento estão em ordem de `sequencia`, sem repetição.
7. Duas execuções no mesmo dia sobre os mesmos dados dão o mesmo arquivo, byte a byte.
