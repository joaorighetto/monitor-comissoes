# Modelo de dados: AVI — Resumo diário no Telegram

A AVI **lê** `data/mudancas/AAAA-MM-DD.json` (MUD), `data/atual.json` (COL/REL/MUD) e `data/status.json` (AGE) e **grava** só `data/envio.json`. Nenhum desses contratos muda.

## Entradas (só leitura)

### Status do dia (`data/status.json`, AGE)

Usado: `resultado`, `data_referencia`, `falha.{categoria,motivo}`, `ultimo_retrato_bom.{dados_camara_em,total_itens}`. Validado por `ler_status` da AGE (versão de formato 1). Arquivo ausente é tratado como "sem registro de coleta".

### Arquivo de mudanças (`data/mudancas/AAAA-MM-DD.json`, MUD, `versao_formato` 1)

Usado: `meta.{data,retrato,retrato_anterior,linha_de_base,total_eventos,total_por_tipo}`, `eventos[]` e `ressalvas[]`. Contrato em [`specs/004-.../contracts/mudancas-json.md`](../004-mudancas-desde-ontem/contracts/mudancas-json.md).

Validações da AVI (falha visível se alguma falhar, sem mensagem):

| # | Regra |
|---|---|
| 1 | O arquivo existe e é JSON de objeto com `meta`, `eventos`, `ressalvas` |
| 2 | `meta.versao_formato == 1` |
| 3 | `meta.data == status.data_referencia` |
| 4 | `meta.retrato.dados_camara_em == status.ultimo_retrato_bom.dados_camara_em` |
| 5 | `meta.total_eventos == len(eventos)` e a soma de `meta.total_por_tipo` também |
| 6 | Todo evento tem `tipo` conhecido, `identificacao`, `comissao`, `link` não vazio; os campos próprios do tipo existem |
| 7 | Com `meta.linha_de_base` preenchido, `eventos` e `ressalvas` são vazios |

### Itens do `atual.json`

Usado: `meta.versao_formato` (2 ou 3) e, por item, `identificacao`, `comissao`, `link`, `principal_nao_localizada`. Só serve para o aviso "principal não localizada". Itens sem esses campos ou outra versão: falha visível.

## Registro de envio (`data/envio.json`, novo)

```json
{
  "versao_formato": 1,
  "ultimo_envio": {"normal": "2026-10-20", "erro": null}
}
```

| Campo | Tipo | Regra |
|---|---|---|
| `versao_formato` | inteiro | `1` |
| `ultimo_envio.normal` | `null` ou `AAAA-MM-DD` | Dia da última mensagem **normal** aceita pelo Telegram |
| `ultimo_envio.erro` | `null` ou `AAAA-MM-DD` | Dia da última mensagem de **erro** (da coleta, ou "a coleta de hoje não rodou") aceita pelo Telegram |

Arquivo ausente equivale a `{normal: null, erro: null}`. Arquivo ilegível, com campo a mais ou a menos, ou com versão desconhecida falha o envio (não envia e não finge que enviou). Detalhes em [contracts/envio-json.md](contracts/envio-json.md).

## Entidades do código

### `Destino` (para o "veja a página")

| Campo | Descrição |
|---|---|
| `texto` | `"veja a página"` (com `aviso.pagina_url`) ou `"veja o arquivo do dia"` (sem) |
| `url` | `aviso.pagina_url` ou `https://github.com/{repositorio}/blob/main/data/mudancas/AAAA-MM-DD.json` |

### `Mensagem`

| Campo | Descrição |
|---|---|
| `tipo` | `"normal"` ou `"erro"` (a chave do registro de envio) |
| `dia` | Dia da execução, em Brasília (`AAAA-MM-DD`) |
| `texto` | Texto final, até 4.096 unidades UTF-16 |

Uma `Mensagem` é gerada de forma pura a partir de dicionários e de `hoje` (sem relógio, sem rede). A mesma entrada dá o mesmo texto (FR-025).

### `Aviso`

Duas famílias, cada uma com a contagem inteira e a lista de itens limitada a 1.200 unidades:

| Aviso | Fonte | Itens |
|---|---|---|
| Principal não localizada | itens do `atual.json` com `principal_nao_localizada` verdadeiro | `identificacao`, `comissao`, `link` |
| Relator indeterminado | `ressalvas` do arquivo de mudanças | `identificacao`, `comissao`, `link` |

### `FalhaDeEnvio`

Exceção definida em `erros.py` (sem categoria), não uma `FalhaDeColeta` (o `status.json` e as categorias da AGE não mudam). Carrega só texto sem segredo.

## Decisão do tipo de mensagem (estados)

```
status.json ausente ou data_referencia != hoje  →  erro: "a coleta de hoje não rodou"
resultado == "falha"                            →  erro: motivo do status.json
resultado == "ok"                               →  normal (com eventos | sem mudanças | linha de base)
```

O registro é consultado **depois** de a mensagem ser montada: `ultimo_envio[tipo] == hoje` → "já enviou", saída 0, sem enviar.
