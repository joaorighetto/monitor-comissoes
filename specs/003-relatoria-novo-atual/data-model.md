# Modelo de dados: REL

## Entradas novas

### Tramitação (API `/proposicoes/{id}/tramitacoes`)

| Campo | Tipo | Uso |
|---|---|---|
| `sequencia` | inteiro | Ordem de leitura. Única por proposição; repetida é falha |
| `dataHora` | texto `AAAA-MM-DDTHH:MM` | Data da designação (`designado_em`) |
| `siglaOrgao` | texto | Comissão da tramitação; `MESA`, `CCP` e `PLEN` são órgãos de apoio e ficam fora da regra |
| `codTipoTramitacao` | texto | Classe da tramitação (research R2) |
| `descricaoTramitacao` | texto | Só para detectar tipo novo de relatoria (contém "relator") |
| `uriUltimoRelator` | texto ou nulo | Em `320`, URI do designado; nas demais NÃO é lido |

### Proposição do lote (acréscimo)

`ultimoStatus_uriRelator` (URI de `/deputados/{id}` ou vazio) vira o campo `id_relator: int | None` de `Proposicao` e passa a ser coluna obrigatória do arquivo (ausente = `formato_alterado`).

### Deputado (API `/deputados/{id}`)

`dados.ultimoStatus.nomeEleitoral` e `dados.ultimoStatus.siglaPartido`. Usado só para relatores fora da lista do NOVO.

## Estruturas internas (sem I/O)

### `RelatorAtual`

| Campo | Descrição |
|---|---|
| `id` | id do deputado |
| `designado_em` | `dataHora` da tramitação `320` que vale |

### `ResultadoRelatoria` (saída de `relatoria.relator_atual(tramitacoes, comissao)`)

Um de três estados, mutuamente exclusivos:

- **com relator**: `RelatorAtual`;
- **sem relator**: nenhum relator na passagem atual;
- **indeterminado**: com `motivo` (texto curto).

#### Transições (por passagem, em ordem de `sequencia`)

```text
nova passagem (órgão muda, fora MESA/CCP/PLEN) → sem relator
320 em C com uriUltimoRelator            → com relator (id, dataHora)
320 em C sem uriUltimoRelator            → indeterminado
507 | 1250 | 1255 em C                   → sem relator
170 | 322 | 501 em C                     → (mantém o estado)
outro código com "relator" na descrição → indeterminado (até uma nova designação ou saída)
fim, com a última passagem fora de C     → indeterminado ("último órgão X difere de C")
```

A indeterminação por tipo desconhecido é limpa por uma nova `320`, `507`, `1250` ou `1255` posterior em C, porque a partir dali o estado é conhecido.

## Saída: campos novos do item do `atual.json`

| Campo | Tipo | Descrição |
|---|---|---|
| `etiquetas` | lista | Passa a poder conter `"relatoria NOVO"`, na ordem `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO`. Nunca vazia, **exceto** em candidato indeterminado sem outra etiqueta (ver abaixo) |
| `relator` | `null` ou objeto | Relator atual da referência: `{"id", "nome", "partido_hoje", "designado_em", "fonte"}` |
| `relator_indeterminado` | `null` ou objeto | `{"motivo": texto}` quando a regra não pôde decidir |

**Invariantes:**

- `relator` e `relator_indeterminado` nunca são ambos não nulos.
- `"relatoria NOVO" ∈ etiquetas` ⇔ `relator ≠ null` e `relator.id` está entre os deputados do NOVO em exercício.
- `relator.fonte` é o link oficial da **referência** (a própria proposição ou a principal), de onde as tramitações foram lidas.
- Um item só tem `etiquetas` vazio quando é candidato à relatoria NOVO com `relator_indeterminado`: nesse caso entra na lista assim mesmo (spec FR-011), e a ausência de etiqueta é o sinal de que nada foi confirmado nem negado.
- `partido_hoje` de relator do NOVO em exercício é `"NOVO"` sem consulta; nos demais vem de `/deputados/{id}`.

## Mudança de `meta`

Só `versao_formato`: 1 → 2. `total_itens` e `total_por_comissao` passam a contar também os itens só de relatoria.
