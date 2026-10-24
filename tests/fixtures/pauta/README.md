# Fixtures da pauta (PAU)

Respostas reais da API de Dados Abertos da Câmara, gravadas byte a byte por
`tests/capturar_pautas.py` em 24/10/2026 (o `manifesto.json` traz o endpoint e o momento de cada
captura, e o `X-Total-Count` das listas). Os testes não usam rede: servem estes arquivos pelo
`TransportePauta` de `tests/pauta_sinteticos.py`.

## Arquivos

| Caminho | Endpoint | Para quê |
|---|---|---|
| `orgaos/CE.json`, `orgaos/CREDN.json` | `/orgaos?sigla=` | CE → 2009, CREDN → 2018 |
| `eventos/{orgao}-{inicio}-{fim}.json` | `/orgaos/{id}/eventos?dataInicio&dataFim&itens=100` | a janela D−7 a D+7 de uma checagem no dia D |
| `eventos/81555.json`, `eventos/83091.json` | `/eventos/{id}` | detalhe (busca de reunião que sumiu da janela) |
| `pautas/{id}.json` | `/eventos/{id}/pauta` | cada reunião deliberativa das janelas e duas avulsas |
| `atual.json` | cópia do `data/atual.json` | o inventário de 24/10/2026 (`gerado_em` 08:34:13), 105 itens |

## Janelas

| Arquivo | D | Reuniões deliberativas |
|---|---|---|
| `2009-2026-10-17-2026-10-31` | 24/10/2026 | 83091 (convocada para 28/10) |
| `2009-2026-04-08-2026-04-22` | 15/04/2026 | 81366, 81555 |
| `2018-2026-04-08-2026-04-22` | 15/04/2026 | 81483, 81609 |
| `2009-2025-11-26-2025-12-10` | 03/12/2025 | 80344, 80560, 80732 (cancelada) |
| `2018-2025-11-26-2025-12-10` | 03/12/2025 | 80375, 80376, 80594 (`Encerrada (Termo)`), 80712 |

As janelas também trazem eventos que não são reunião deliberativa (audiência pública, mesa
redonda, seminário, visita técnica, palestra), que a checagem ignora.

## Casos cobertos

- **83091** (CE, 28/10/2026, `Convocada`): 19 PL e o REQ 70/2026 (id 2645503) com relacionada
  REQ 63/2026: o item é o próprio REQ (PRODUCT §5.8). Sem texto de resultado.
- **81555** (CE, 15/04/2026): PL 5432/2016 (id 2086175) "Retirado de pauta"; REQ 17/2026 com
  relacionada PL 1778/2020 (o item continua sendo o REQ); PL 3464/2025 com relator Luiz Lima
  (204455) e `siglaPartido` nulo. Na lista, `dataHoraInicio` é 10:11 (início real); no detalhe,
  10:00 (hora convocada).
- **80594** (CREDN, `Encerrada (Termo)`): reunião realizada sem nenhum texto, rótulo "sem
  registro".
- **80732** (CE, `Cancelada`): 23 itens sem texto.
- **81483** (CREDN): MSC (3) e PDL (1) entre os tipos listados.
- **80265** (avulsa): PL 3906/2023 com "Prejudicado o Requerimento de Retirada de Pauta… Vista…"
  e PL 725/2024 com "Prejudicado o Requerimento de Retirada de Pauta… Retirado de pauta…", a
  exceção do §5.9 na mesma frase.
- **80344**: "Votação nominal… do Requerimento de Retirada de Pauta…" (rótulo "outro", não
  "retirado de pauta") e "Não deliberado.".
- **81862** (avulsa): os dois únicos itens "rejeitado" das 48 pautas de 12 meses.

### Os sete rótulos do §5.9

Contagem sobre os itens de tipo listado (PL, PLP, PEC, MSC, PDL) das reuniões realizadas salvas:

| Rótulo | Itens | Exemplo |
|---|---|---|
| retirado de pauta | 41 | 81555, PL 5432/2016 |
| vista | 14 | 80375, MSC 516/2018 |
| aprovado | 83 | 80265, PL 3205/2021 |
| rejeitado | 2 | 81862, PL 26/2025 |
| não apreciado | 58 | 80344, PL 4216/2024 |
| sem registro | 7 | 80594, PLP 258/2019 |
| outro | 2 | 80344, PL 1655/2022; 81609, PL 622/2026 |

Todos os rótulos têm caso real.

## `atual.json`

Cópia de `data/atual.json` de 24/10/2026 (formato 3, 105 itens), com o PL 3701/2020 apensado ao
PL 5432/2016 (id 2086175): o item da pauta de 81555 é o principal de um apensado do inventário.

## Recapturar

```bash
uv run python tests/capturar_pautas.py
```

Usa a rede. Os números acima mudam se a Câmara alterar os registros; confira os testes depois.
