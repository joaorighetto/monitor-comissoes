# Contrato: `data/atual.json` (diferenças da REL)

Vale tudo o que está em [`specs/003-relatoria-novo-atual/contracts/atual-json.md`](../../003-relatoria-novo-atual/contracts/atual-json.md) e, por ele, na COL, com a mudança abaixo. Mesma codificação, indentação e ordem fixa dos campos.

## Mudanças

- `meta.versao_formato`: **3**.
- Cada item ganha, **depois de `ultimo_status_em`**, o campo `ultimo_status_sequencia`.

## Campo novo

| Campo | Tipo | Descrição |
|---|---|---|
| `ultimo_status_sequencia` | inteiro | `ultimoStatus_sequencia` da **referência** do item (a raiz da cadeia de apensação, ou a própria proposição). É o número da tramitação que deu origem a `situacao` e a `ultimo_status_em` |

## Exemplo (ilustrativo do formato, não resultado real)

```json
{
  "comissao": "CE",
  "situacao": "Aguardando Parecer",
  "ultimo_status_em": "2023-03-28T00:00:00",
  "ultimo_status_sequencia": 41,
  "parado_ha_dias": 1300
}
```

(Os demais campos são os da COL e da REL e foram omitidos.)

## Regras de consistência (verificadas nos testes)

1. `ultimo_status_sequencia` é inteiro positivo em todo item.
2. Itens com a mesma referência (um apensado e a principal) têm o mesmo `ultimo_status_sequencia`, o mesmo `situacao` e o mesmo `ultimo_status_em`.
3. As regras de consistência da REL continuam valendo.
4. Duas execuções sobre os mesmos dados dão itens idênticos, na mesma ordem.

## Compatibilidade

- **AGE:** lê `meta.gerado_em`, `meta.dados_camara_em` e `meta.total_itens`. Não muda.
- **Retrato anterior em outra versão:** a MUD o trata como incompatível e grava linha de base (spec, User Story 3). O `atual.json` commitado antes da MUD está na versão 1 ou 2 e é descartado como base de comparação, sem ser alterado.
- **Quem lê o arquivo** (AVI, PAG) deve conferir `meta.versao_formato`.
