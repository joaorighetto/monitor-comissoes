# Contrato: `data/atual.json` (diferenças da COL)

Vale tudo o que está em [`specs/001-coleta-estoque-filtrado/contracts/atual-json.md`](../../001-coleta-estoque-filtrado/contracts/atual-json.md), com as mudanças abaixo. Mesma codificação, indentação e ordem fixa dos campos.

## Mudanças

- `meta.versao_formato`: **2**.
- Cada item ganha, **depois de `principal_nao_localizada`**, os campos `relator` e `relator_indeterminado`.
- `etiquetas` passa a ser subconjunto de `["autoria NOVO", "autor hoje no NOVO", "relatoria NOVO"]`, nessa ordem.

## Exemplo (ilustrativo do formato, não resultado real)

```json
{
  "id": 2388105,
  "tipo": "PL",
  "numero": 4501,
  "ano": 2023,
  "identificacao": "PL 4501/2023",
  "etiquetas": ["relatoria NOVO"],
  "comissao": "CE",
  "situacao": "Aguardando Parecer",
  "apensado_a": null,
  "principal_nao_localizada": false,
  "relator": {
    "id": 204455,
    "nome": "Luiz Lima",
    "partido_hoje": "NOVO",
    "designado_em": "2025-04-09T00:00:00",
    "fonte": "https://www.camara.leg.br/propostas-legislativas/2388105"
  },
  "relator_indeterminado": null
}
```

(Os demais campos são os da COL e foram omitidos.)

## Campos novos

| Campo | Tipo | Descrição |
|---|---|---|
| `relator` | `null` ou objeto | Relator atual da **referência** (apensados herdam o da principal). `null` quando não há relator atual ou quando é indeterminado |
| `relator.id` | inteiro | Id do deputado |
| `relator.nome` | texto | Nome de exibição: o da lista do NOVO ou o `nomeEleitoral` de `/deputados/{id}` |
| `relator.partido_hoje` | texto | Partido de hoje, nunca o da data da designação |
| `relator.designado_em` | texto `AAAA-MM-DDTHH:MM:SS` | Data e hora da designação que vale (a mais recente da passagem atual) |
| `relator.fonte` | texto (URL) | Ficha oficial da referência de onde o relator foi lido |
| `relator_indeterminado` | `null` ou `{"motivo": texto}` | Presente quando as tramitações não permitiram decidir |

## Regras de consistência (verificadas nos testes)

1. `relator` e `relator_indeterminado` não são ambos não nulos.
2. `"relatoria NOVO"` em `etiquetas` se e somente se `relator.id` está em `meta.deputados_novo_em_exercicio`.
3. `etiquetas` só é vazia em item com `relator_indeterminado` não nulo.
4. Todo item com `relator` tem `relator.fonte`.
5. Duas execuções sobre os mesmos dados dão itens idênticos, na mesma ordem (parado há mais tempo primeiro, desempate por `id`).
