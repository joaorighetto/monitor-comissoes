# Contrato: `data/atual.json`

Codificação UTF-8, sem escape de caracteres acentuados, indentação de 2 espaços, uma quebra de linha final. Ordem dos campos fixa (como abaixo), para que o diff diário no Git seja legível.

## Estrutura

```json
{
  "meta": {
    "versao_formato": 1,
    "gerado_em": "2026-10-18T09:12:44-03:00",
    "dados_camara_em": "2026-10-17T04:33:58+00:00",
    "comissoes": ["CE", "CREDN"],
    "ano_minimo": 2003,
    "anos_lidos": [2003, 2026],
    "total_itens": 2,
    "total_por_comissao": {"CE": 1, "CREDN": 1},
    "deputados_novo_em_exercicio": [
      {"id": 204455, "nome": "Luiz Lima"}
    ]
  },
  "itens": [
    {
      "id": 2319917,
      "tipo": "PL",
      "numero": 937,
      "ano": 2022,
      "identificacao": "PL 937/2022",
      "ementa": "…",
      "data_apresentacao": "2022-03-29T10:15:00",
      "link": "https://www.camara.leg.br/propostas-legislativas/2319917",
      "autores": [
        {"nome": "…", "id_deputado": 204455, "partido_na_data": "PL", "ordem": 1}
      ],
      "etiquetas": ["autor hoje no NOVO"],
      "comissao": "CE",
      "situacao": "Aguardando Parecer",
      "ultimo_status_em": "2026-05-20T00:00:00",
      "parado_ha_dias": 151,
      "apensado_a": null,
      "principal_nao_localizada": false
    }
  ]
}
```

Os valores acima são **ilustrativos do formato**, não resultado real.

## Campos de `meta`

| Campo | Tipo | Descrição |
|---|---|---|
| `versao_formato` | inteiro | 1 nesta feature. Muda se o formato mudar de forma incompatível |
| `gerado_em` | texto ISO 8601 com fuso | Momento da geração, em Brasília (−03:00). **Único campo que pode variar entre duas execuções sobre os mesmos dados** |
| `dados_camara_em` | texto ISO 8601 em UTC | A mais antiga entre as datas `Last-Modified` dos arquivos lidos |
| `comissoes`, `ano_minimo` | como na configuração | Parâmetros usados |
| `anos_lidos` | `[primeiro, último]` | Intervalo de anos efetivamente lido |
| `total_itens` | inteiro | Igual ao tamanho de `itens`; maior que zero |
| `total_por_comissao` | objeto | Uma chave por comissão da configuração, na ordem dela, inclusive com 0 |
| `deputados_novo_em_exercicio` | lista | Deputados usados em `autor hoje no NOVO`, ordenados por `id` |

## Campos de cada item

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | inteiro | Identificador da proposição na Câmara |
| `tipo` | `"PL"` ou `"PLP"` | |
| `numero`, `ano` | inteiros | |
| `identificacao` | texto | `tipo numero/ano`, como a Câmara exibe |
| `ementa` | texto | |
| `data_apresentacao` | texto `AAAA-MM-DDTHH:MM:SS` | Horário de Brasília |
| `link` | texto (URL) | Página oficial da proposição (sempre presente) |
| `autores` | lista | Todos os autores da própria proposição, por `ordem` crescente. `id_deputado` é `null` para quem não é deputado |
| `etiquetas` | lista de textos | Subconjunto de `["autoria NOVO", "autor hoje no NOVO"]`, nessa ordem, nunca vazia |
| `comissao` | texto | Sigla da comissão da lista em que a referência está |
| `situacao` | texto | Situação do último status da referência |
| `ultimo_status_em` | texto `AAAA-MM-DDTHH:MM:SS` | Data e hora do último status da referência |
| `parado_ha_dias` | inteiro ≥ 0 | Dias inteiros entre `ultimo_status_em` e a data de Brasília de `gerado_em` |
| `apensado_a` | `null` ou objeto | `{"id", "identificacao", "link"}` da proposição principal (raiz), quando o item é apensado e a raiz foi localizada |
| `principal_nao_localizada` | booleano | `true` quando o item é apensado e a raiz não pôde ser determinada; nesse caso `apensado_a` é `null` e comissão e situação são do próprio item |

## Ordem dos itens

`ultimo_status_em` crescente (parado há mais tempo primeiro); em empate, `id` crescente.

## Invariantes (cobertos por testes)

1. `meta.total_itens == len(itens) > 0`.
2. `sum(total_por_comissao.values()) == total_itens`.
3. Todo item tem `link` e ao menos uma etiqueta.
4. `comissao` pertence a `meta.comissoes`.
5. `principal_nao_localizada == true` ⇒ `apensado_a == null`.
6. `id`s únicos.
7. Duas gerações com os mesmos dados de entrada e o mesmo relógio produzem arquivos idênticos byte a byte.
