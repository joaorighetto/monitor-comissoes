# Data Model: PAU — Pauta das reuniões

Os formatos exatos dos arquivos estão nos contratos: [pauta-json.md](contracts/pauta-json.md),
[status-pauta-json.md](contracts/status-pauta-json.md) e
[indice-autoria.md](contracts/indice-autoria.md). Aqui ficam as entidades, as regras de validação e
as transições.

## Entradas

| Entrada | Origem | Uso |
|---|---|---|
| Órgão da comissão | `/orgaos?sigla=` (R1) | id para consultar os eventos |
| Evento | `/orgaos/{id}/eventos` (R2) e `/eventos/{id}` (R6, R7) | reunião, janela, sumiço |
| Pauta | `/eventos/{id}/pauta` | itens |
| Deputados do NOVO em exercício | `/deputados?siglaPartido=NOVO` (reuso de `deputados.py`) | `autor hoje no NOVO`, `relatoria NOVO` |
| Índice de autoria | `cache/indice-autoria.json`, gravado pela coleta (R8) | `autoria NOVO`, autores, "autoria não verificada" |
| Inventário | `data/atual.json` (último bom) | "leva apensado do NOVO" |
| Última checagem registrada | arquivo mais recente de `data/pautas/` | alterações, "vista desde" |
| Configuração | `config.toml` (`comissoes`) | comissões acompanhadas |

## Entidades

### Reunião

| Campo | Regra |
|---|---|
| `id` | id do evento |
| `comissao` | sigla da configuração que trouxe o evento |
| `inicio` | `dataHoraInicio` da lista do órgão, `AAAA-MM-DDTHH:MM`, Brasília |
| `situacao` | `convocada`, `realizada`, `cancelada` ou `outra` (R3) |
| `situacao_camara` | texto original |
| `link` | `https://www.camara.leg.br/evento-legislativo/{id}` |
| `vista_desde` | momento da primeira checagem que a viu na janela; copiado da última checagem quando a reunião já estava nela; senão, o momento desta checagem |
| `itens` | itens listados de PL, PLP, PEC, MSC e PDL, na ordem do grupo (abaixo) |
| `requerimentos` | `total` e `listados` (REQ com etiqueta de autoria ou "autoria não verificada") |
| `outros` | `total` dos demais tipos |
| `pauta` | todos os itens, na ordem da pauta, com chave, título e proposição resumida: é o que a próxima checagem compara |

- Entra na checagem se `descricaoTipo == "Reunião Deliberativa"`, se um dos órgãos do evento é o
  da comissão e se a data de `inicio` está em `[D−7, D+7]`, D o dia da checagem em Brasília.
- Um evento ligado às duas comissões (sessão conjunta) aparece uma vez por comissão.
- Ordem: `inicio`, depois a ordem das comissões na configuração, depois `id`.

### Item da pauta

| Campo | Regra |
|---|---|
| `ordem` | `ordem` da pauta |
| `titulo` | `titulo` original |
| `regime` | `regime` original (pode ser nulo) |
| `proposicao` | proposição do item (R4): `id`, `tipo`, `numero`, `ano`, `identificacao` (`Tipo número/ano`), `ementa`, `link` |
| `relacionada` | só em REQ: a `proposicaoRelacionada_`, resumida (`id`, `identificacao`, `link`), ou nulo |
| `relator` | `relator` da pauta: `id`, `nome`, `partido` (nulo quando a API não traz) ou nulo |
| `etiquetas` | subconjunto ordenado de `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO` |
| `autoria_nao_verificada` | verdadeiro quando o id não está no índice de autoria |
| `leva_apensado_do_novo` | lista de apensados do inventário (abaixo); vazia quando não há |
| `resultado` | só em reunião `realizada`: `rotulo` (R5) e `texto` original; senão nulo |

- **Grupo do NOVO:** item com `etiquetas` ou `leva_apensado_do_novo` não vazios. Os do grupo vêm
  primeiro; dentro de cada grupo, a `ordem`.
- `autoria_nao_verificada` exclui `autoria NOVO` e `autor hoje no NOVO`; `relatoria NOVO` continua
  valendo pelo relator da pauta.
- **REQ listado:** tem `autoria NOVO`, `autor hoje no NOVO` ou `autoria_nao_verificada`.
  `relatoria NOVO` sozinha não lista o REQ.

### Etiquetas

| Etiqueta | Regra |
|---|---|
| `autoria NOVO` | o índice marca a proposição com autor que assinou como NOVO |
| `autor hoje no NOVO` | algum deputado autor no índice está entre os deputados do NOVO em exercício na checagem |
| `relatoria NOVO` | `relator.id` está entre os deputados do NOVO em exercício na checagem |

### Apensado do NOVO

Item do inventário (`data/atual.json`) com `apensado_a.id` igual ao id da proposição do item da
pauta. Campos: `id`, `identificacao`, `link` e `etiquetas`, copiados do inventário. Ordem: `id`.

### Resultado

`rotulo` ∈ {`retirado de pauta`, `vista`, `aprovado`, `rejeitado`, `não apreciado`,
`sem registro`, `outro`} e `texto` (o `situacaoItem` original, ou nulo).

### Chave de item

`p:{id}` da proposição do item, ou `t:{titulo}` quando não há proposição. A pauta de uma reunião é
um multiconjunto de chaves.

### Checagem

`checada_em` (ISO com fuso de Brasília), `janela` (`inicio` e `fim`, datas), `lote`
(`dados_camara_em` do índice), `inventario` (`gerado_em` do `atual.json`),
`deputados_novo_em_exercicio` (ids e nomes) e `reunioes`.

### Alteração de pauta

| Campo | Regra |
|---|---|
| `detectada_em` | `checada_em` da checagem que a detectou |
| `tipo` | `item_entrou`, `item_saiu`, `data_hora`, `cancelada` ou `retirada_da_agenda` |
| `reuniao` | `id`, `comissao`, `inicio` (o da checagem anterior) e `link` |
| `item` | nos tipos de item: `chave`, `titulo` e a proposição resumida; senão nulo |
| `de`, `para` | em `data_hora`: o `inicio` anterior e o novo; senão nulos |
| `detalhe` | em `retirada_da_agenda` de evento que ainda existe: o tipo e os órgãos atuais; senão nulo |

Ordem: `detectada_em`, `reuniao.inicio`, `reuniao.id`, ordem dos tipos (como na tabela), chave do
item.

### Arquivo de pauta do dia

`data/pautas/AAAA-MM-DD.json`, AAAA-MM-DD o dia da checagem em Brasília. Guarda a última checagem
do dia e as alterações do dia, cumulativas.

### Status da pauta

`data/status-pauta.json`: resultado da última execução (`ok` ou `falha`), `verificado_em`, `falha`
(`categoria` e `motivo`) e `ultima_checagem_boa` (o `checada_em` mais recente gravado, ou nulo).

### Índice de autoria

`cache/indice-autoria.json`, fora do Git: para cada proposição de PL, PLP, PEC, MSC, PDL e REQ do
lote, se algum autor assinou como NOVO e os ids dos deputados autores.

## Transições

### Uma checagem

```text
ler entradas (config, índice, inventário, última checagem) ── inválida ──► falha
      │
consultar deputados, órgãos, eventos, pautas ── erro de rede / formato ──► falha
      │
montar reuniões (janela, itens, etiquetas, marcas, resultado, vista desde)
      │
sem checagem anterior? ── sim ──► arquivo do dia = linha de base, sem alterações
      │ não
comparar reuniões convocadas da checagem anterior (R6), buscando as que sumiram ── erro ──► falha
      │
arquivo do dia = esta checagem + (alterações já gravadas no dia, se o arquivo é do mesmo dia)
               + alterações novas
      │
gravar arquivo do dia e status-pauta (tudo ou nada)
```

Em falha: nada em `data/pautas/` muda; `status-pauta.json` é gravado com `resultado: falha`, o
motivo e a `ultima_checagem_boa` de antes; o código de saída é 1.

### Linha de base

- Sem nenhum arquivo em `data/pautas/`: `meta.linha_de_base = {"motivo": "primeira checagem",
  "checada_em": ...}`, com o momento da checagem que criou a linha de base (mantido nas checagens
  seguintes do mesmo dia).
- Um arquivo do dia que nasceu como linha de base continua marcado assim nas checagens seguintes do
  mesmo dia, que registram alterações normalmente.
- Arquivo anterior ilegível, fora do contrato ou de versão desconhecida **não** vira linha de base:
  a checagem falha com o nome do arquivo.

## Validação das respostas da API

| Resposta | Exigido | Senão |
|---|---|---|
| `/orgaos?sigla=` | exatamente um órgão com a sigla, `id` inteiro | `formato_alterado` |
| eventos | `dados` lista; cada evento com `id` inteiro, `dataHoraInicio` `AAAA-MM-DDTHH:MM`, `situacao` texto, `descricaoTipo` texto, `orgaos` lista com `id`; `X-Total-Count` igual ao entregue | `formato_alterado` |
| pauta | `dados` lista; cada item com `ordem` inteiro, `titulo` texto; `proposicao_` e `proposicaoRelacionada_` objeto ou nulo, com `id` inteiro, `siglaTipo` texto, `numero` e `ano` inteiros ou textos só de dígitos quando objeto (a relacionada traz `"63"` e `"2026"` como texto); `relator` objeto com `id` e `nome`, ou nulo; `situacaoItem` texto ou nulo | `formato_alterado` |
| HTTP | 2xx (404 só aceito na busca de evento sumido, R7) | `fonte_indisponivel` |
