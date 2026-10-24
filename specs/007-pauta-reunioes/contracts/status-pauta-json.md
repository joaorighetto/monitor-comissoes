# Contrato: `data/status-pauta.json`

Versão de formato 1. Mesmo estilo de serialização do `data/status.json` da AGE. Gravado ao fim de
**toda** checagem, com sucesso ou falha, e commitado pelo workflow da pauta. Consumidores: SEM
(aviso de erro no dia) e PGP ("não atualizada desde DD/MM às HHhMM").

```json
{
  "versao_formato": 1,
  "resultado": "falha",
  "verificado_em": "2026-10-24T15:18:40-03:00",
  "falha": {
    "categoria": "fonte_indisponivel",
    "motivo": "pauta: HTTP 503"
  },
  "ultima_checagem_boa": "2026-10-24T05:49:12-03:00"
}
```

| Campo | Regra |
|---|---|
| `resultado` | `ok` ou `falha` |
| `verificado_em` | fim da execução, ISO com fuso de Brasília |
| `falha` | `null` em `ok`; em `falha`, `categoria` e `motivo` |
| `ultima_checagem_boa` | em `ok`, o `checada_em` desta checagem; em `falha`, o do status anterior, ou, sem status anterior, o `checada_em` do arquivo de pauta mais recente, ou `null` |

Categorias: `fonte_indisponivel`, `formato_alterado`, `api_deputados`, `entrada_invalida`,
`configuracao`, `interna`. As categorias e o arquivo da coleta (`data/status.json`) não mudam.

Um `status-pauta.json` anterior ilegível não impede a gravação do novo: o novo é gravado e a falha
de leitura vai para o `stderr` (o status é registro, não entrada da regra).
