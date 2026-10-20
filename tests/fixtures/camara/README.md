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

## Usos na MUD (inventário de 18/10/2026)

A MUD (comparação entre o retrato de hoje e o anterior) **não captura nenhuma fixture nova**: tudo o que ela precisa já está aqui. Os retratos de dois dias são sintéticos e derivados do `data/atual.json` dentro do teste.

| Caso da MUD | Fixture real |
|---|---|
| Arquivamento "nos termos do Artigo 105" (tramitação `502`, `despacho` com o texto) | `tramitacoes/2086175.json` (sequência 42, 31/01/2019); também `495615.json` (sequências 36 e 59) e `2183535.json` (sequência 19) |
| Parecer do relator (`322`, junto com o `501` no mesmo minuto) | `tramitacoes/2330962.json` (CCTI, 18/10/2023) |
| Designação (`320`), devolução sem manifestação (`507`) e saída do relator da comissão (`1250`) | `tramitacoes/2319917.json` (PL 937/2022) e `tramitacoes/2388105.json` (PL 4501/2023) |
| Chegada à comissão (recebimento que inicia a passagem) | `tramitacoes/1212477.json` (sequência 15, 28/04/2015, da CCP para a CE) |
| Ida e volta pela MESA que **não** é chegada nova (`Notificação de Apensação` na MESA e novo `Recebimento` na CE) | `tramitacoes/1212477.json` (sequências 19 a 23 e 47 a 51) |
| Saída por apensação a uma principal fora das comissões | lote: PL 4047/2019 (id 2211957) → PL 2346/2015 → PL 982/2011 → PL 3047/2015 (raiz, na CFT) |
| Saída por `Transformado em Norma Jurídica` | lote: ids 2141142 (PL 7843/2017) e 593065 (PL 4476/2020), ambos na MESA |
| Saída por `Aguardando Apreciação pelo Senado Federal` | lote: ids 267841 (PL 30/2015) e 381872 (PL 12/2016), ambos na MESA |
| Referência que continua numa comissão | lote: PL 1843/2022 (id 2331032, CE) |

Todas as 145 linhas PL/PLP do lote têm `ultimoStatus_sequencia` inteiro. "Arquivada" não aparece em nenhuma linha PL/PLP do lote salvo: os testes derivam essa situação, dentro do teste, de uma linha real com a situação alterada em memória. O mesmo vale para o despacho de arquivamento sem menção ao art. 105, derivado do `502` real de 2086175.

## O que é real e o que é derivado nos testes da MUD

- **Real:** as tramitações (arquivamento pelo art. 105, parecer, designação e devolução, idas e voltas pela MESA, chegada à comissão), as linhas do lote (apensado a principal fora das comissões, norma jurídica, Senado, referência na CE) e a sequência do último status de todas elas.
- **Derivado dentro do teste, nunca em arquivo:** os retratos de "ontem" (sintéticos, em `tests/sinteticos.py`, ou o `atual.json` de hoje alterado em memória); a situação "Arquivada" (não existe em linha PL/PLP do lote salvo); o despacho de arquivamento sem menção ao art. 105 (o `502` real com o texto trocado); a matéria que saiu e voltou da comissão; tramitações lançadas depois do lote (sequências acrescentadas à resposta real); respostas de tramitações sem a sequência de hoje (lista neutra do `TransporteFalso`); e o `atual.json`/`anterior.json` corrompidos, de data futura ou em versão antiga.
- Os casos em que o PL 7843/2017 (id 2141142) "estava ontem na lista" usam a mesma sequência do lote (134), para não precisar das tramitações dele, que não estão nas fixtures.

## O que não é real

Devolução, substituição, passagem anterior pela mesma comissão, tipo de tramitação desconhecido, designação sem relator e sequência repetida não existem (ou não de forma controlável) nas tramitações reais. Os testes os derivam, dentro do próprio teste, de tramitações reais alteradas em memória. Nenhum arquivo derivado fica neste diretório.

Ciclo de apensação e "principal não localizada" para PL/PLP não existem nos dados reais. Os testes os derivam, dentro do próprio teste, a partir de linhas reais com `uriPropPrincipal` alterada. Nenhum arquivo derivado fica neste diretório.

## Recapturar

```bash
uv run python tests/capturar_fixtures.py   # com rede; baixa cerca de 1 GB; leva alguns minutos
```

Depois de recapturar, os testes de aceitação podem precisar de ajuste (por exemplo, se um deputado deixar o NOVO).
