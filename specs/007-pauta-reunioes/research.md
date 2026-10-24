# Research: PAU — Pauta das reuniões

Consultas à API v2 em 24/10/2026, além da sondagem de 23/10/2026 (`docs/fontes.md`, §5). As 48
pautas deliberativas da CE e da CREDN de 23/10/2025 a 31/10/2026 foram baixadas para conferência
no scratchpad da sessão, fora do repositório; só os recortes escolhidos viram fixtures (R11).

## R1. Órgão de cada comissão

- **Decisão:** obter o id do órgão pela sigla em `/api/v2/orgaos?sigla={sigla}`, a cada checagem,
  e falhar se a resposta não trouxer exatamente um órgão com aquela sigla.
- **Por quê:** a configuração guarda siglas (`["CE", "CREDN"]`), e trocar de comissão não pode
  exigir código (PRODUCT.md, D1). Conferido: CE → 2009, CREDN → 2018.
- **Alternativas:** fixar os ids em `config.toml` (duplicaria a sigla e poderia divergir dela);
  guardar em cache (mais um arquivo a validar, para economizar duas chamadas).

## R2. Eventos da janela

- **Decisão:** `/api/v2/orgaos/{id}/eventos?dataInicio=D-7&dataFim=D+7&itens=100`, com paginação
  pelos `links` do corpo e conferência do `X-Total-Count`, no mesmo padrão de
  `deputados.obter_deputados_novo`. Filtrar `descricaoTipo == "Reunião Deliberativa"` no código.
- **Por quê:** o filtro de datas da API é inclusivo nos dois extremos (consulta de 15/04 a 15/04
  devolveu os dois eventos do dia). Nenhum mês passou de 100 eventos na sondagem, mas a paginação
  é conferida assim mesmo: uma página perdida esconderia uma reunião.
- **Observação:** `dataHoraInicio` vem sem fuso e é hora de Brasília. A lista do órgão e o detalhe
  do evento podem divergir na hora: o evento 81555 aparece como `10:11` na lista (início real) e
  `10:00` no detalhe (hora convocada). Por isso a alteração "data ou hora mudou" compara sempre a
  lista com a lista (R6), e o detalhe só decide a data de uma reunião que sumiu.

## R3. Situação da reunião

| Texto da Câmara | Situação normalizada |
|---|---|
| `Convocada` | convocada |
| `Encerrada`, `Encerrada (Final)`, `Encerrada (Termo)` | realizada |
| `Cancelada` | cancelada |
| qualquer outro (por exemplo, `Em Andamento`, `Suspensa`) | outra |

Em 12 meses de eventos deliberativos da CE e da CREDN: 39 `Encerrada (Final)`, 5 `Cancelada`,
2 `Encerrada (Termo)`, 1 `Encerrada` e 1 `Convocada`. Uma situação nova não é formato alterado:
vira "outra" com o texto original (spec, Edge Cases).

## R4. Proposição do item

- **Decisão:** se `proposicao_.siglaTipo == "REQ"`, a proposição do item é a `proposicao_`;
  senão, a `proposicaoRelacionada_` quando existe; senão, a `proposicao_`; senão, nenhuma (o item
  conta em "outros" pelo título).
- **Por quê:** PRODUCT.md, §5.8, com a emenda de 24/10/2026. Pares (`proposicao_`, relacionada) em
  12 meses: PRL→PL 527, PRL→MSC 38, REQ→REQ 15, PRL→PLP 11, **REQ→PL 10**, REL→SOR 4,
  **REQ→PEC 3**, PRV→PL 3, PES→PL 3, PRL→PDL 2. Os 13 REQ→PL/PEC levaram à ampliação da emenda
  (decidida pelo mantenedor no plano): sem ela, o REQ 17/2026 CE ("Aprovado o Requerimento")
  apareceria como "PL 1778/2020 · aprovado". Nenhum item de pauta veio sem proposição.
- **Consequência para a sondagem:** as 2 PEC "pautadas" na CE (`docs/fontes.md`, §5) eram o
  REQ 217/2025 CE, que se refere à PEC 573/2006, pautado três vezes. O plano não corrige o
  `docs/fontes.md`; a correção é sugerida ao mantenedor no fechamento.
- **Repetição:** 2 pautas tinham a mesma proposição duas vezes. A comparação de itens trata a
  pauta como multiconjunto (R6).

## R5. Resultado (§5.9)

- **Decisão:** sobre o texto em minúsculas, sem alterar acentos:
  1. "retirado de pauta": `retirad[oa] de pauta` em alguma ocorrência que **não** faz parte de
     "requerimento de retirada de pauta" (as ocorrências da expressão excluída são removidas antes
     da busca, e não o texto inteiro);
  2. "vista": a palavra `vista` (`\bvista\b`);
  3. "aprovado": `\baprovad[oa]\b`;
  4. "rejeitado": `\brejeitad[oa]\b`;
  5. "não apreciado": `adiad`, `não apreciad`, `não deliberad`, `encerrada a reunião` ou
     `encerramento da reunião`;
  6. "sem registro": texto vazio ou ausente (depois de tirar espaços);
  7. "outro".
- **Por quê:** aplicada aos 542 itens de PL, PLP, PEC, MSC e PDL das reuniões realizadas em
  12 meses: aprovado 215, retirado de pauta 162, não apreciado 78, sem registro 41, vista 41,
  rejeitado 2, outro 3 (antes do ajuste da regra 1). Os 2 "outro" de "Prejudicado o Requerimento
  de Retirada de Pauta… Retirado de pauta…" passam a "retirado de pauta" com a remoção só da
  expressão, como o §5.9 pede ("exceto em 'Requerimento de Retirada de Pauta'"). O
  "Não deliberado." é o texto mais comum de "não apreciado".
- **Alternativas:** excluir o texto inteiro quando ele contém a expressão (rejeitada: classifica
  como "outro" um item que foi retirado).

## R6. Alteração de pauta e identidade do item

- **Chave do item:** `p:{id}` da proposição do item (R4) ou, sem proposição, `t:{título}`. A pauta
  é um multiconjunto de chaves: duas ocorrências da mesma proposição são dois itens.
- **Quando comparar:** só a reunião que estava `convocada` na última checagem registrada.
  - Ainda na janela e ainda `convocada`: "item entrou" e "item saiu" pela diferença dos
    multiconjuntos; "data ou hora mudou" quando o `dataHoraInicio` da lista mudou.
  - Ainda na janela e agora `cancelada`: só "reunião cancelada".
  - Ainda na janela e agora `realizada` ou `outra`: nenhuma alteração. Durante e depois da
    reunião, a lista pode mudar a hora para o início real (R2) e receber itens "sobre a mesa"; isso
    não é pauta alterada (FR-015).
  - **Sumiu da janela:** busca em `/api/v2/eventos/{id}` (R7). `Cancelada` → "reunião cancelada";
    data fora da janela → "data ou hora mudou" (com a data nova), salvo quando a data é a mesma (a
    reunião só ficou para trás da janela: nenhuma alteração); 404 → "reunião retirada da
    agenda". Se o evento existe, na janela, mas deixou de ser "Reunião Deliberativa" da comissão,
    também vale "retirada da agenda", com o tipo e os órgãos atuais no detalhe: ela saiu da agenda
    deliberativa. Falhar nesse caso travaria todas as checagens seguintes, porque a última checagem
    boa nunca mudaria.
  - **Sumiu da lista, mas o detalhe mantém** (deliberativa da comissão, na janela): a lista e o
    detalhe divergiram (R2). A reunião volta à checagem montada pelo detalhe, com a pauta buscada
    pelo id, e é comparada como as outras; sem isso, ela sairia do arquivo sem aviso (princípio
    III). Decidido pelo mantenedor na revisão.
- **Registro único:** a última checagem registrada é a do arquivo de pauta mais recente (do mesmo
  dia ou anterior). Como cada checagem compara com a anterior gravada, uma alteração detectada já
  está na checagem gravada e não aparece de novo. Duas checagens sobre a mesma fonte não acrescentam
  nada.
- **Alternativas:** guardar um estado "reuniões já avisadas" à parte (rejeitada: a última checagem
  já é esse estado).

## R7. Evento inexistente

- **Decisão:** o `TransporteHttp` passa a levantar `RecursoInexistente`, subclasse de
  `FalhaDeColeta` com a mesma categoria `fonte_indisponivel`, para HTTP 404. Só a busca de evento
  sumido (R6) a captura; em qualquer outro lugar ela continua sendo falha.
- **Por quê:** `/eventos/99999999` e `/eventos/99999999/pauta` respondem 404. Hoje a 404 vira
  `FalhaDeColeta` genérica, e distinguir pelo texto da mensagem seria frágil. A subclasse não muda
  o comportamento de quem já captura `FalhaDeColeta`.

## R8. Autores sem baixar o lote a cada checagem

- **Problema:** a autoria vem do lote (ROADMAP, linha PAU), e o lote tem cerca de 1 GB. A checagem
  roda três vezes por dia e não pode baixá-lo. A proposição de uma pauta pode ser qualquer PL, PLP,
  PEC, MSC, PDL ou REQ desde 2003: cerca de 20 mil por ano, perto de 480 mil no total.
- **Decisão:** a coleta diária, que já percorre o lote, grava um **índice de autoria** com todas as
  proposições desses seis tipos: para cada id, se algum autor assinou como NOVO e os ids dos
  deputados autores. O índice é gravado em `cache/indice-autoria.json` (fora do Git) junto com os
  demais arquivos da coleta, tudo ou nada, e o workflow da coleta o guarda no **cache do GitHub
  Actions**. A checagem restaura o índice mais recente. "Não está no índice" é exatamente "não está
  no último lote bom" (FR-008a).
- **Por quê:**
  - O índice é derivado do lote, não é histórico (D8): não precisa de versão no Git, e um arquivo de
    ~15 MB mudando todo dia pesaria no repositório público.
  - O cache do Actions é do próprio GitHub (stack fixada), sem servidor. A checagem acessa o índice
    três vezes por dia, então ele nunca fica 7 dias sem uso, que é o prazo de despejo.
  - "Autor hoje no NOVO" usa a lista de deputados lida na checagem, não a da coleta: o índice
    guarda todos os deputados autores, e não só os do NOVO.
- **Falha visível:** índice ausente, ilegível ou de versão desconhecida falha a checagem
  (`entrada_invalida`). Isso acontece, por exemplo, antes da primeira coleta com a PAU.
- **Alternativas rejeitadas:**
  - commitar o índice (peso no Git; diff diário sem valor de histórico);
  - restringir o índice às proposições com último status na CE ou na CREDN (menor, mas uma
    proposição fora dele seria marcada "autoria não verificada" sem estar fora do lote);
  - consultar `/proposicoes/{id}/autores` na API (não traz o partido na data; mudaria a fonte de
    "autoria pelo lote" fixada no ROADMAP);
  - artefato do Actions (exige descobrir a última execução boa por API; o cache faz isso com a
    restauração por prefixo).

## R9. Horários das checagens (garantias do §5.8)

| Checagem | Brasília | Cron (UTC) | Garantia |
|---|---|---|---|
| Manhã | 05:47 | `47 8 * * *` | Termina antes do envio das 07:17, com 90 min de folga para o atraso do agendador |
| Tarde | 15:17 | `17 18 * * *` | Depois do horário das reuniões (42 de 47 começaram entre 9h e 11h40) |
| Noite | 22:47 | `47 1 * * *` (dia seguinte em UTC) | Fim do dia: pega a pauta anunciada ao fim da reunião |

Os minutos ficam fora do topo da hora, como os demais workflows. A checagem da noite ainda é do
mesmo dia em Brasília, e o arquivo é nomeado pelo dia de Brasília. O atraso do agendador pode
passar da meia-noite; nesse caso o arquivo é o do dia seguinte, o que não quebra nenhuma garantia.

## R10. Workflow e commit concorrente

- **Decisão:** workflow novo `checagem-pauta.yml`, grupo de concorrência próprio `pauta` (sem
  cancelar a que roda). Ele commita só `data/pautas/` e `data/status-pauta.json`; a coleta commita
  `data/atual.json`, `data/anterior.json`, `data/mudancas/` e `data/status.json`; o aviso,
  `data/envio.json`. Como os conjuntos de arquivos são disjuntos, o `git pull --rebase` antes do
  push nunca tem conflito, e o push é repetido uma vez, como nos outros workflows.
- **Por quê:** a pauta não deve esperar a coleta de até 200 minutos, e a falha de uma não barra a
  outra (PRODUCT.md, §7).
- **Mudança no workflow da coleta:** um passo `actions/cache/save` depois do commit, só em sucesso,
  com a chave `indice-autoria-${{ github.run_id }}-${{ github.run_attempt }}`. O resto da coleta não
  muda.
- **Versão da ação:** `actions/cache` v6.1.0 (`releases/latest`, conferido em 24/10/2026), fixada
  pelo SHA do commit, como as ações de terceiros dos outros workflows.

## R11. Fixtures

- **Decisão:** ferramenta de desenvolvimento `tests/capturar_pautas.py` (com rede, fora da suíte),
  no padrão de `tests/capturar_fixtures.py`, que grava respostas byte a byte em
  `tests/fixtures/pauta/` com um `manifesto.json` (endpoint e data de cada arquivo):
  - `orgaos/{sigla}.json` (CE, CREDN);
  - `eventos/{orgao}-{inicio}-{fim}.json` (janelas escolhidas);
  - `eventos/{id}.json` (detalhe, para o caso do evento que sumiu);
  - `pautas/{id}.json`.
- **Recortes reais:** CE 83091 (28/10/2026, convocada, 19 PL + REQ 70→REQ 63); CE 81555
  (15/04/2026, PL 5432/2016 com o PL 3701/2020 apensado no inventário, REQ 17→PL 1778/2020,
  `relator.siglaPartido` nulo para Luiz Lima); uma reunião da CREDN com MSC e PDL; uma cancelada;
  uma `Encerrada (Termo)`; itens com cada rótulo do §5.9, inclusive "Prejudicado o Requerimento de
  Retirada de Pauta… Retirado de pauta".
- **Sintéticos derivados:** as alterações (item entrou ou saiu, hora, cancelamento, sumiço) e as
  falhas (HTTP, JSON inválido, campo ausente, paginação incompleta) são variações das respostas
  reais montadas nos testes, como em `tests/sinteticos.py`.
- **Inventário e índice:** um `atual.json` salvo do dia (para a marca "leva apensado do NOVO") e um
  índice de autoria pequeno, gerado pelos testes a partir das fixtures do lote que já existem
  (`tests/fixtures/camara/`), acrescido das linhas dos PL e REQ dos recortes.

## R12. Link oficial do evento

`https://www.camara.leg.br/evento-legislativo/{id}` (respondeu 200 para o evento 83091). Para a
proposição, o mesmo `link_oficial` do inventário
(`https://www.camara.leg.br/propostas-legislativas/{id}`).

## R13. Registro de falha da pauta

- **Decisão:** `data/status-pauta.json`, separado do `data/status.json` da coleta, gravado em toda
  checagem (sucesso ou falha) e commitado, no padrão do `status.json` da AGE.
- **Por quê:** a SEM e a PGP precisam do motivo e do momento da última checagem boa (spec,
  User Story 6) sem que uma falha da pauta sobrescreva o status da coleta, ou o contrário.

## R14. Dependências

Nenhuma dependência Python nova: `json`, `urllib`, `re`, `datetime`, `dataclasses` (biblioteca
padrão). A única peça externa nova é a ação `actions/cache` do GitHub (R8, R10), justificada no
plano.
