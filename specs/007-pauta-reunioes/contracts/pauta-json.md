# Contrato: `data/pautas/AAAA-MM-DD.json`

Versão de formato 1. UTF-8, `ensure_ascii=False`, indentação de 2 espaços, `\n` no fim (o mesmo
`saida.serializar` dos outros arquivos). Campos na ordem abaixo. Consumidores: SEM e PGP.

```json
{
  "meta": {
    "versao_formato": 1,
    "data": "2026-10-24",
    "comissoes": ["CE", "CREDN"],
    "linha_de_base": null
  },
  "checagem": {
    "checada_em": "2026-10-24T05:49:12-03:00",
    "janela": {"inicio": "2026-10-17", "fim": "2026-10-31"},
    "lote": {"dados_camara_em": "2026-10-24T04:31:37+00:00"},
    "inventario": {"gerado_em": "2026-10-24T03:58:02-03:00"},
    "deputados_novo_em_exercicio": [{"id": 204455, "nome": "Luiz Lima"}],
    "reunioes": [
      {
        "id": 83091,
        "comissao": "CE",
        "inicio": "2026-10-28T10:00",
        "situacao": "convocada",
        "situacao_camara": "Convocada",
        "link": "https://www.camara.leg.br/evento-legislativo/83091",
        "vista_desde": "2026-10-23T22:47:30-03:00",
        "itens": [
          {
            "ordem": 2,
            "titulo": "PL 1234/2025",
            "regime": "Ordinária (Art. 151, III, RICD)",
            "proposicao": {
              "id": 2500000,
              "tipo": "PL",
              "numero": 1234,
              "ano": 2025,
              "identificacao": "PL 1234/2025",
              "ementa": "…",
              "link": "https://www.camara.leg.br/propostas-legislativas/2500000"
            },
            "relacionada": null,
            "relator": {"id": 204455, "nome": "Luiz Lima", "partido": null},
            "etiquetas": ["relatoria NOVO"],
            "autoria_nao_verificada": false,
            "leva_apensado_do_novo": [],
            "resultado": null
          }
        ],
        "requerimentos": {"total": 1, "listados": []},
        "outros": {"total": 0},
        "pauta": [
          {
            "chave": "p:2645503",
            "ordem": 1,
            "titulo": "REQ 70/2026 CE",
            "proposicao": {
              "id": 2645503,
              "identificacao": "REQ 70/2026",
              "link": "https://www.camara.leg.br/propostas-legislativas/2645503"
            }
          }
        ]
      }
    ]
  },
  "alteracoes": [
    {
      "detectada_em": "2026-10-24T05:49:12-03:00",
      "tipo": "item_entrou",
      "reuniao": {
        "id": 83091,
        "comissao": "CE",
        "inicio": "2026-10-28T10:00",
        "link": "https://www.camara.leg.br/evento-legislativo/83091"
      },
      "item": {
        "chave": "p:2500000",
        "titulo": "PL 1234/2025",
        "proposicao": {
          "id": 2500000,
          "identificacao": "PL 1234/2025",
          "link": "https://www.camara.leg.br/propostas-legislativas/2500000"
        }
      },
      "de": null,
      "para": null,
      "detalhe": null
    }
  ]
}
```

## Campos

- `meta.data`: dia da checagem em Brasília; é o nome do arquivo.
- `meta.linha_de_base`: `null`, ou `{"motivo": "primeira checagem"}` quando não havia checagem
  anterior em nenhum arquivo. Fica no arquivo do dia mesmo depois de outras checagens do dia.
- `checagem`: só a **última** checagem do dia. Cada checagem nova do dia a substitui.
- `checagem.janela`: datas inclusivas, D−7 e D+7.
- `checagem.lote.dados_camara_em`: do índice de autoria usado (R8).
- `checagem.inventario.gerado_em`: `meta.gerado_em` do `atual.json` usado.
- `reunioes[].situacao`: `convocada`, `realizada`, `cancelada` ou `outra` (research R3).
- `reunioes[].itens`: PL, PLP, PEC, MSC e PDL; o grupo do NOVO primeiro, depois a `ordem`.
- `reunioes[].requerimentos.listados`: itens no mesmo formato de `itens`, dos REQ com etiqueta de
  autoria ou `autoria_nao_verificada`, na ordem da pauta. `relacionada` só é preenchida em REQ.
- `reunioes[].pauta`: todos os itens da pauta, na ordem da pauta. `proposicao` é `null` quando o
  item não tem proposição. É a base da comparação da próxima checagem.
- `etiquetas`: na ordem `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO`.
- `leva_apensado_do_novo[]`: `{"id", "identificacao", "link", "etiquetas"}`, ordenados por `id`.
- `resultado`: `{"rotulo", "texto"}` só em reunião `realizada`; senão `null`.
- `alteracoes`: todas as alterações registradas no dia, cumulativas, na ordem do data-model.
  - `tipo`: `item_entrou`, `item_saiu`, `data_hora`, `cancelada`, `retirada_da_agenda`.
  - `reuniao.inicio`: o da checagem anterior (para `data_hora`, o `de`).
  - `item`: só nos tipos de item.
  - `de` e `para`: só em `data_hora` (`AAAA-MM-DDTHH:MM`).
  - `detalhe`: só em `retirada_da_agenda` de evento que ainda existe, com o tipo e os órgãos atuais
    (`"agora: Audiência Pública (CE)"`).

## Garantias

- Todo item listado, apensado, reunião e alteração tem link oficial.
- Duas checagens seguidas sobre a mesma fonte dão o mesmo arquivo, exceto `checagem.checada_em`,
  `checagem.lote` e `checagem.inventario` quando essas entradas mudaram entre as duas.
- Nenhuma alteração é repetida no conjunto dos arquivos: uma alteração só é detectada contra a
  última checagem gravada.
- Em falha, o arquivo não é gravado (nem criado nem alterado).

## Validação na leitura

Quem lê o arquivo anterior (a própria checagem) confere: JSON válido, `meta.versao_formato == 1`,
`meta.data` igual ao nome do arquivo, `checagem.checada_em` com fuso, e, em cada reunião, `id`,
`situacao`, `inicio`, `vista_desde` e `pauta` com `chave`. Qualquer desvio falha a checagem com o
nome do arquivo (`entrada_invalida`).
