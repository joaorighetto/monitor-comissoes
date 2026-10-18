# Fixtures da Câmara

Recortes **reais** dos Dados Abertos da Câmara, capturados em 18/10/2026 por `tests/capturar_fixtures.py` (dados da Câmara de 18/10/2026, `Last-Modified` entre 04:33 e 05:21 UTC; API consultada às 16:49 UTC). Recapturadas na feature REL para acrescentar a relatoria; a COL e a AGE foram capturadas antes, em 17/10/2026. Servem para testar sem rede (constituição, princípio IV).

## O que há aqui

| Arquivo | Conteúdo |
|---|---|
| `proposicoes-AAAA.csv`, `proposicoesAutores-AAAA.csv` (2003 a 2026) | Cabeçalho completo da fonte e as linhas selecionadas (abaixo), mais 2 linhas reais de preenchimento por arquivo, para nenhum ano ficar vazio |
| `deputados-novo.json` | Resposta real de `/api/v2/deputados?siglaPartido=NOVO&itens=100` (5 deputados; `X-Total-Count: 5`) |
| `tramitacoes/{id}.json` | Resposta real de `/api/v2/proposicoes/{id}/tramitacoes` de cada referência que a coleta consulta (itens com etiqueta de autoria, candidatos à relatoria NOVO e os casos da sondagem), byte a byte |
| `deputados/{id}.json` | Resposta real de `/api/v2/deputados/{id}` de cada deputado designado relator nessas tramitações (partido de hoje) |
| `manifesto.json` | `Last-Modified`, `Content-Type` e tamanho original de cada arquivo; ids e motivo das linhas selecionadas; relatores consultados |

Os **valores** das linhas são copiados sem alteração. Só a serialização é refeita: BOM UTF-8, separador `;`, todos os campos entre aspas e CRLF entre linhas, como na fonte. O tamanho dos arquivos aqui difere do original; os testes recalculam o `Content-Length` pelo corpo servido.

## Linhas selecionadas

- **Casos de aceitação:** PL 1843/2022 (id 2331032, `autoria NOVO`), PL 3871/2024 (id 2461936, `autor hoje no NOVO`; Luiz Lima assinou pelo PL), PL 4047/2019 (id 2211957).
- **REL, casos da sondagem de relatoria:** PL 937/2022 (id 2319917, relator do NOVO devolveu sem manifestação), PL 3514/2023 (id 2373721, relator do NOVO era da CESPO) e PL 4501/2023 (id 2388105, autoria de outro partido, relator do NOVO na CE).
- **REL, universo da lista:** todo PL/PLP com etiqueta de autoria cuja referência está na CE ou na CREDN (`selecao.itens_com_etiqueta_de_autoria`); as linhas das comissões cujo último relator é deputado do NOVO (`selecao.relator_novo_no_lote`) e os apensados dessas raízes (`selecao.apensados_de_raiz_com_relator_novo`), com as cadeias completas.
- **Cadeia de apensação real do PL 4047/2019**, completa: PL 4047/2019 → PL 2346/2015 → PL 982/2011 → **PL 3047/2015 (raiz, na CFT)**. Por isso o PL 4047/2019 fica fora, embora o próprio status dele seja da CE.
- **Contraste:** um REQ e um PDL na CE; um PL de outro partido na CE; um PL do NOVO fora da CE e da CREDN.
- **Exemplos reais de cadeia:** uma raiz ausente dos arquivos (id 29517, o SBT 1/0 aponta para o id 15718, que não existe em nenhum arquivo) e uma cadeia de 2 níveis (REQ 248/2003). Não são PL/PLP, então servem só para testar a resolução da referência. Não existe ciclo real nos dados.

## O que não é real

Devolução, substituição, passagem anterior pela mesma comissão, tipo de tramitação desconhecido, designação sem relator e sequência repetida não existem (ou não de forma controlável) nas tramitações reais. Os testes os derivam, dentro do próprio teste, de tramitações reais alteradas em memória. Nenhum arquivo derivado fica neste diretório.

Ciclo de apensação e "principal não localizada" para PL/PLP não existem nos dados reais. Os testes os derivam, dentro do próprio teste, a partir de linhas reais com `uriPropPrincipal` alterada. Nenhum arquivo derivado fica neste diretório.

## Recapturar

```bash
uv run python tests/capturar_fixtures.py   # com rede; baixa cerca de 1 GB; leva alguns minutos
```

Depois de recapturar, os testes de aceitação podem precisar de ajuste (por exemplo, se um deputado deixar o NOVO).
