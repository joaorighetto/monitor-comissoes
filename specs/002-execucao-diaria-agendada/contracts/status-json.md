# Contrato: `data/status.json`

Codificação UTF-8, sem escape de caracteres acentuados, indentação de 2 espaços, uma quebra de linha final. Ordem dos campos fixa (como abaixo), para que o diff diário no Git seja legível. Gravação atômica (mesmo mecanismo do `atual.json`).

O arquivo descreve a **última execução**. A feature PAG usa `verificado_em`, `resultado` e `falha` para a linha de atualização, a faixa de erro e a faixa de atraso. A feature AVI usa `falha` e `ultimo_retrato_bom.dados_camara_em` para a mensagem de erro com a data dos últimos dados bons. A AGE só grava.

## Exemplo: sucesso

```json
{
  "versao_formato": 1,
  "resultado": "ok",
  "verificado_em": "2026-10-19T03:41:12-03:00",
  "data_referencia": "2026-10-19",
  "tentativas": 2,
  "falha": null,
  "variacao_aceita": null,
  "ultimo_retrato_bom": {
    "gerado_em": "2026-10-19T03:41:10-03:00",
    "dados_camara_em": "2026-10-19T04:33:58+00:00",
    "total_itens": 23,
    "estoque_bruto": 1531
  }
}
```

## Exemplo: falha

```json
{
  "versao_formato": 1,
  "resultado": "falha",
  "verificado_em": "2026-10-20T05:20:48-03:00",
  "data_referencia": "2026-10-20",
  "tentativas": 4,
  "falha": {
    "categoria": "arquivos_desatualizados",
    "motivo": "a Câmara não atualizou os arquivos (o mais antigo tem 40 horas)"
  },
  "variacao_aceita": null,
  "ultimo_retrato_bom": {
    "gerado_em": "2026-10-19T03:41:10-03:00",
    "dados_camara_em": "2026-10-19T04:33:58+00:00",
    "total_itens": 23,
    "estoque_bruto": 1531
  }
}
```

Os valores acima são **ilustrativos do formato**, não resultado real.

## Exemplo: variação aceita manualmente

```json
{
  "versao_formato": 1,
  "resultado": "ok",
  "verificado_em": "2027-02-01T09:12:30-03:00",
  "data_referencia": "2027-02-01",
  "tentativas": 1,
  "falha": null,
  "variacao_aceita": {
    "estoque_anterior": 1531,
    "estoque_novo": 1100,
    "variacao_percentual": -28.2
  },
  "ultimo_retrato_bom": {
    "gerado_em": "2027-02-01T09:12:28-03:00",
    "dados_camara_em": "2027-02-01T04:33:58+00:00",
    "total_itens": 17,
    "estoque_bruto": 1100
  }
}
```

## Campos

| Campo | Tipo | Descrição |
|---|---|---|
| `versao_formato` | inteiro | 1 nesta feature. Muda se o formato mudar de forma incompatível |
| `resultado` | `"ok"` ou `"falha"` | |
| `verificado_em` | texto ISO 8601 com fuso | Momento em que a execução terminou, em Brasília (−03:00). É a base da faixa de atraso (30 horas) |
| `data_referencia` | texto `AAAA-MM-DD` | Data de Brasília de `verificado_em`, ou seja, do **fim** da execução (uma execução que cruzasse a meia-noite teria a data do dia seguinte; com o agendamento às 03h37 e janela de ~1h40, isso não ocorre). Permite distinguir a execução de hoje do retrato de ontem, e uma reexecução do mesmo dia |
| `tentativas` | inteiro ≥ 0 | Coletas efetivamente tentadas. 0 quando falhou antes de coletar (configuração inválida) |
| `falha` | `null` ou objeto | `{"categoria": texto, "motivo": texto}`. `null` se e somente se `resultado = "ok"`. Categorias em [../data-model.md](../data-model.md) |
| `variacao_aceita` | `null` ou objeto | `{"estoque_anterior": inteiro, "estoque_novo": inteiro, "variacao_percentual": número com 1 casa decimal}`. Só em sucesso com confirmação manual e variação acima do limite |
| `ultimo_retrato_bom` | `null` ou objeto | `gerado_em` e `dados_camara_em` (como no `meta` do `atual.json`), `total_itens` e `estoque_bruto`. Em sucesso descreve o retrato gravado; em falha, o retrato mantido. `null` se não existe `atual.json` (ou se ele não tem `meta` válido). `estoque_bruto` é `null` só no retrato mantido em falha quando não há base válida para ele (por exemplo, `atual.json` gerado pela COL antes da AGE) |

## Invariantes (cobertos por testes)

1. `resultado = "ok"` ⇒ `falha = null` e `ultimo_retrato_bom ≠ null`.
2. `resultado = "falha"` ⇒ `falha ≠ null`, `variacao_aceita = null`.
3. Um `status.json` de sucesso nunca carrega resto de falha anterior.
4. `ultimo_retrato_bom.gerado_em` é igual ao `meta.gerado_em` do `atual.json` em disco ao fim da execução. Quando não existe `atual.json`, é `null`.
5. Mesmos dados de entrada e mesmo relógio produzem arquivo idêntico byte a byte.
6. `data_referencia` é a data de Brasília de `verificado_em`.
