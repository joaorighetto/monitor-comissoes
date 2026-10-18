# Modelo de dados: MUD — Mudanças desde ontem

Os formatos exatos dos arquivos estão em [contracts/](contracts/). Aqui ficam as entidades, as regras de comparação e as validações.

## Entidades

### Retrato

O `data/atual.json` de um dia (`versao_formato: 3`, ver [contracts/atual-json.md](contracts/atual-json.md)). A comparação usa, de cada item: `id`, `identificacao`, `link`, `comissao`, `situacao`, `etiquetas`, `relator`, `relator_indeterminado`, `apensado_a`, `ultimo_status_sequencia`. Do `meta`: `versao_formato`, `gerado_em`, `dados_camara_em`, `total_itens`.

- **Dia do retrato:** a data de `meta.gerado_em` em Brasília.
- **Referência do item:** `apensado_a.id` quando `apensado_a` não é nulo; senão, o próprio `id` (inclui "principal não localizada", em que `apensado_a` é nulo).

**Validação ao ler (`retratos.ler`):** objeto com `meta` e `itens`; `meta.versao_formato` inteiro; `meta.gerado_em` e `meta.dados_camara_em` com data e hora ISO válidas; `itens` é lista. Qualquer desvio é "retrato inválido" (falha `interna`). Se `versao_formato` é diferente de 3, a leitura para aí: o retrato é válido, mas **incompatível** (linha de base). Se é 3, cada item é validado nos campos acima (tipos e presença); ids repetidos são inválidos.

### Comparação preparada (`retratos.Comparacao`)

| Campo | Tipo | Descrição |
|---|---|---|
| `anterior` | retrato ou `None` | O retrato anterior comparável. `None` quando é linha de base |
| `motivo_linha_de_base` | `None`, `"primeiro retrato"` ou `"formato anterior incompatível"` | Preenchido quando `anterior` é `None` |
| `retrato_anterior` | `None` ou `{dia, dados_camara_em}` | Datas do retrato anterior, mesmo quando incompatível (informativo) |
| `copia_anterior` | `None` ou texto | Conteúdo exato (bytes decodificados) a gravar em `anterior.json`; `None` = não rotaciona |

A rotação grava o **texto original** do `atual.json` antigo, sem reserializar, para a cópia ser idêntica byte a byte.

### Estado de quem saiu (`estoque.EstadoDeSaida`)

Avaliação, pelo lote de hoje, de um id que estava no retrato anterior e não está na lista de hoje.

| Campo | Descrição |
|---|---|
| `existe` | Se a proposição está nas linhas lidas do lote. Falso → motivo "não determinado" |
| `referencia_id` | Id da referência hoje (raiz, ou a própria) |
| `orgao` | `ultimoStatus_siglaOrgao` da referência |
| `situacao` | `ultimoStatus_descricaoSituacao` da referência |
| `sequencia` | `ultimoStatus_sequencia` da referência |
| `apensado_a` | `{id, identificacao, link}` da raiz, ou `None` |
| `na_comissao` | Se `orgao` está na lista de comissões |

### Tramitação (`tramitacoes.Tramitacao`, REL)

Ganha o campo `despacho` (texto, vazio se a API trouxer nulo). Atributos: `sequencia`, `data_hora`, `orgao`, `codigo`, `descricao`, `despacho`, `id_relator`. No arquivo de mudanças saem `sequencia`, `data_hora`, `orgao`, `codigo` e `descricao`; o `despacho` não é gravado (só é usado na regra do art. 105).

### Evento

Uma mudança de um item. Tipos, na ordem de saída: `entrou`, `saiu`, `situacao`, `relator`, `parecer`, `etiquetas`. Campos comuns: `tipo`, `id`, `identificacao`, `comissao`, `link`, `tramitacoes`. Campos próprios em [contracts/mudancas-json.md](contracts/mudancas-json.md).

### Ressalva

Item para o qual a comparação de relator não foi possível (relator indeterminado em um dos retratos ou nos dois). Não é evento.

### Arquivo de mudanças do dia

`meta`, `eventos`, `ressalvas`. Linha de base: `meta.linha_de_base` preenchido, `eventos` e `ressalvas` vazios.

## Regras de comparação

Seja `A` o retrato anterior, `H` o documento de hoje, `ids(A)` e `ids(H)` os ids dos itens.

**Entrou:** `id ∈ ids(H) − ids(A)`. Motivo (R7): chegada à comissão posterior ao retrato anterior → `chegou_a_comissao`; senão, item com etiquetas → `ganhou_etiqueta`; senão `nao_determinado`.

**Saiu:** `id ∈ ids(A) − ids(H)`. Estado do lote (`EstadoDeSaida`). Motivo principal, na ordem do clarify (Q4):

1. `existe` falso → `nao_determinado`.
2. Situação da referência na tabela de situações finais (R2) → `arquivado_art_105`, `arquivado`, `transformado_em_norma`, `aprovado_segue_ao_senado` ou `encerrado`.
3. Referência hoje é uma raiz diferente da do retrato anterior **e** essa raiz não é item de hoje → `apensado_fora_da_lista`.
4. `na_comissao` falso → `outro_orgao` (destino: o órgão).
5. Senão (a referência continua numa comissão e o item não tem etiqueta) → `perdeu_etiquetas`, com as etiquetas que tinha no retrato anterior.

`outros_fatos` lista os demais códigos de 2 a 4 que também valiam. O de 5 só é avaliado quando `na_comissao` é verdadeiro. `destino` traz sempre `orgao` e `situacao` de hoje e, se houver, `apensado_a`.

**Itens nos dois retratos** (`id ∈ ids(A) ∩ ids(H)`), cada um com seu evento, sem fundir:

| Evento | Condição |
|---|---|
| `situacao` | `situacao` diferente → `de`, `para` |
| `relator` | os dois retratos têm relator determinado e o relator mudou: `relator` nulo → não nulo = `designado`; não nulo → nulo = `devolveu`; ids diferentes = `substituido` |
| `parecer` | alguma tramitação de código `322`, no órgão `comissao`, no intervalo |
| `etiquetas` | diferença de conjuntos: `ganhou` e/ou `perdeu` |

Relator indeterminado (`relator_indeterminado` não nulo) em qualquer dos dois retratos: sem evento de relator, e o item entra em `ressalvas`.

**Tramitações do intervalo**, por item, só se houve evento do item (ou é `entrou` ou `saiu`) e: a referência é a mesma e `ultimo_status_sequencia` mudou → `anterior < seq <= hoje`; referência diferente ou item que entrou ou saiu → data (R6, R7). Itens com sequência igual não buscam tramitações.

## Transições do arquivo `anterior.json`

| Situação | Efeito |
|---|---|
| Execução em dia novo, `atual.json` de dia anterior | `anterior.json` := texto do `atual.json` antigo; depois `atual.json` := o novo |
| Reexecução no mesmo dia | `anterior.json` não muda; `atual.json` := o novo |
| Falha em qualquer ponto | nenhum dos quatro arquivos muda |

## Ordem dos eventos

Por comissão (na ordem da configuração; comissão fora da configuração, depois, por sigla), depois pelo tipo (ordem acima), depois por `id` da proposição. Dentro de um evento, `tramitacoes` por `sequencia`; `etiquetas` na ordem fixa `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO`.
