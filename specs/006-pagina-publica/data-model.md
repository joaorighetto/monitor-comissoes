# Modelo de dados: PAG — Página pública

A feature **não cria arquivo de dados** e não altera nenhum contrato existente. Ela lê os três arquivos abaixo e produz um conjunto de arquivos de saída (ver [contracts/site.md](contracts/site.md)). Os modelos desta página são valores em memória, imutáveis, montados por `modelo.py` a partir de dicionários já validados por `entradas.py`.

## Entradas (contratos já existentes)

| Entrada | Contrato | O que a página usa |
|---|---|---|
| `data/atual.json` | [COL](../001-coleta-estoque-filtrado/contracts/), [REL](../003-relatoria-novo-atual/contracts/atual-json.md), [MUD](../004-mudancas-desde-ontem/contracts/atual-json.md); `versao_formato` 2 ou 3 | `meta.gerado_em`, `meta.dados_camara_em`, `meta.comissoes`, `meta.total_itens`, `meta.total_por_comissao` e, por item, os campos listados em `ItemDaLista` |
| `data/status.json` | [AGE](../002-execucao-diaria-agendada/contracts/status-json.md); `versao_formato` 1 | `resultado`, `verificado_em`, `data_referencia`, `falha.motivo`, `ultimo_retrato_bom.dados_camara_em` |
| `data/mudancas/AAAA-MM-DD.json` | [MUD](../004-mudancas-desde-ontem/contracts/mudancas-json.md); `versao_formato` 1 | `meta.data`, `meta.retrato`, `meta.retrato_anterior`, `meta.linha_de_base`, `meta.total_eventos`, `eventos`. As `ressalvas` não são exibidas |

## Valores da página

### `Atualizacao` (a linha de atualização)

| Campo | Origem | Observação |
|---|---|---|
| `dados_camara_em` | `atual.meta.dados_camara_em` | UTC no arquivo; exibida em Brasília, `DD/MM` |
| `gerado_em` | `atual.meta.gerado_em` | exibida `HHhMM` em Brasília |
| `verificado_em` | `status.verificado_em` | exibida `DD/MM às HHhMM`; vai também em `data-verificado-em` (ISO) para a faixa de atraso |

Texto: `Dados da Câmara de {DD/MM} (arquivo gerado às {HHhMM}) · verificado em {DD/MM} às {HHhMM}`.

### `FaixaDeErro` (opcional)

Existe se e somente se `status.resultado = "falha"`. Campos: `data_da_execucao` (`status.data_referencia`), `motivo` (`status.falha.motivo`), `dados_de` (`status.ultimo_retrato_bom.dados_camara_em`, `DD/MM` em Brasília). Texto: `A atualização de {DD/MM} falhou ({motivo}). Dados de {DD/MM}.`

### `FaixaDeAtraso` (sempre emitida, escondida)

Campos: `verificado_em` (ISO) e o texto fixo `Dados atrasados: a última verificação foi em {DD/MM às HHhMM}, há mais de 30 horas. A atualização diária pode ter parado.` Nasce com `hidden`; só o JS a mostra (FR-011).

### `Numeros`

| Campo | Origem |
|---|---|
| `total_itens` | `atual.meta.total_itens` |
| `por_comissao` | `atual.meta.total_por_comissao`, na ordem de `atual.meta.comissoes` |
| `mudancas` | do arquivo de mudanças do dia do retrato, um de: `("eventos", total_eventos)`, `("linha_de_base", motivo)`, `("indisponivel", None)` |

`mudancas` nunca vira `0` quando o arquivo não existe (plan.md, emenda 3).

### `ItemDaLista`

Um por item de `atual.itens`, na ordem `(-parado_ha_dias, id)`.

| Campo | Origem do `atual.json` | Uso |
|---|---|---|
| `id` | `id` | desempate da ordem; âncora `item-{id}` |
| `identificacao`, `link` | `identificacao`, `link` | título e link oficial |
| `ementa` | `ementa` | texto |
| `autores` | `autores[].nome`, `.partido_na_data` | "Nome (PARTIDO)"; "Nome" se o partido na data é vazio (autor que não é deputado) |
| `etiquetas` | `etiquetas` | rótulos; atributo `data-etiquetas` com os identificadores curtos |
| `comissao` | `comissao` | atributo `data-comissao` e texto |
| `situacao` | `situacao` | texto |
| `parado_ha_dias` | `parado_ha_dias` | "nesta situação há N dias" (não recalculado) |
| `apensado_a` | `apensado_a.identificacao`, `.link` | "apensado ao PL X" |
| `principal_nao_localizada` | `principal_nao_localizada` | marca |
| `relator` | `relator.nome`, `.partido_hoje` ou `null` | "Relator: Nome (PARTIDO)" ou "sem relator atual" |
| `relator_indeterminado` | `relator_indeterminado` | marca "relator indeterminado" |

Identificadores curtos de etiqueta (`data-etiquetas`): `autoria` ← `autoria NOVO`; `autor-hoje` ← `autor hoje no NOVO`; `relatoria` ← `relatoria NOVO`. Um item pode ter de zero a três.

### `Chip`

| Grupo | Chips | Regra |
|---|---|---|
| Comissão | "Todas" + um por sigla em `atual.meta.comissoes` | a sigla só aparece se há item dela; "Todas" sempre |
| Motivo | "Todos" + `Autoria NOVO`, `Autor hoje no NOVO`, `Relatoria NOVO` | o chip só aparece se há item com a etiqueta; "Todos" sempre |

Seleção única por grupo; os grupos se combinam por "e". Campos: `rotulo`, `valor` (sigla ou identificador curto, `""` para "Todas"/"Todos") e `ativo` (só "Todas"/"Todos" no HTML inicial).

### `DiaDeMudancas`

Sete, de `D` a `D-6` (D = dia de `atual.meta.gerado_em` em Brasília).

| Campo | Origem |
|---|---|
| `data` | o dia |
| `estado` | `"eventos"` (arquivo com eventos), `"sem_mudancas"` (arquivo sem evento e sem linha de base), `"linha_de_base"`, `"sem_arquivo"` |
| `intervalo` | `meta.retrato_anterior.dia` → `meta.retrato.dia`, só quando cobre mais de um dia |
| `linha_de_base` | `meta.linha_de_base` (`motivo`, `total_itens`) |
| `eventos` | `eventos`, na ordem do arquivo; os 20 primeiros "abertos", o resto "recolhidos" |

Se nenhum dos 7 dias tem arquivo, a seção toda vira o texto "Ainda não há mudanças registradas.".

### `EventoDaPagina`

O evento do arquivo de mudanças, sem alteração: `tipo`, `id`, `identificacao`, `comissao`, `link` e os campos próprios do tipo. A página mostra, por tipo:

| Tipo | Linha principal | Detalhe |
|---|---|---|
| `entrou` | `{identificacao}` entrou na lista · `{motivo.texto}` | etiquetas de hoje |
| `saiu` | `{identificacao}` saiu da lista · `{motivo.texto}` | `destino.orgao`, `destino.situacao`, "apensado a {identificacao}" (link) |
| `situacao` | `{identificacao}` · `{de}` → `{para}` | "veio da {comissao_de}" quando `comissao_de` ≠ `comissao` |
| `relator` | `{identificacao}` · relator `{designado/devolveu/substituído}` | `de` e `para`, "Nome (PARTIDO)" |
| `parecer` | `{identificacao}` · parecer do relator | só o informe; sem conteúdo |
| `etiquetas` | `{identificacao}` · etiquetas | `ganhou: …` e `perdeu: …` |

As tramitações (`tramitacoes`) vão numa lista recolhida por evento, com `data_hora`, `orgao` e `descricao`.

## Validações (resumo; texto completo em [contracts/pagina-cli.md](contracts/pagina-cli.md))

1. `atual.itens` não vazia e com o tamanho de `meta.total_itens`.
2. Todo `link` exibido começa com `https://www.camara.leg.br/`.
3. `status` e `atual` descrevem o mesmo retrato (`dados_camara_em`); se `resultado = "falha"`, `ultimo_retrato_bom` existe.
4. O arquivo de mudanças do dia `D`, se existir, tem o mesmo `meta.retrato.dados_camara_em` do `atual.json`.
5. Qualquer arquivo lido, inválido ou de versão desconhecida: `FalhaDePagina` com o nome do arquivo; nada é gravado.

## Transições de estado

Nenhuma: a página não guarda estado. Cada execução produz o site inteiro a partir dos arquivos do dia.
