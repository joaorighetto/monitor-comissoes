# Tasks: PAU — Pauta das reuniões

**Input**: documentos de projeto em `specs/007-pauta-reunioes/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Pré-requisitos**: spec e emendas ao PRODUCT.md aprovadas pelo mantenedor (24/10/2026). Plan e tasks aguardam o OK do mantenedor antes de `/speckit-implement`.

**Testes**: pedidos pelo fluxo. Fixtures salvas, nenhum teste com rede. Em cada fase, os testes vêm **antes** da implementação e devem falhar primeiro. A única tarefa com rede é a captura das fixtures (T001), feita uma vez por uma ferramenta fora da suíte.

**Formato**: `- [ ] T### [P?] [US?] Descrição com caminho`. `[P]` = arquivos diferentes, sem dependência de tarefa incompleta.

**Regras do repositório (CLAUDE.md)**: commits pequenos e descritivos, sem push; nenhuma troca de branch; verificação completa: `uv run ruff check . && uv run ruff format --check . && uv run pytest`. Cada fase termina com a verificação completa verde e um commit (sugestão em "Commit"). O status da linha PAU no `ROADMAP.md` só vira `concluída` depois da verificação completa, dos casos de aceitação, do OK do mantenedor e do merge.

**Ordem das fases**: fixtures → fundação (erros, transporte, índice de autoria na coleta, API da pauta, arquivos) → US1, US2, US3, US4 e US6 (P1, na ordem da spec; a US6 fecha a CLI) → US5 e US7 (P2) → fechamento.

**Constantes fixas** (plan.md e research.md): janela D−7 a D+7, inclusive; tipos listados `PL, PLP, PEC, MSC, PDL`; tipos do índice `MSC, PDL, PEC, PL, PLP, REQ`; tipo de reunião `"Reunião Deliberativa"`; crons `47 8 * * *`, `17 18 * * *`, `47 1 * * *`; grupo de concorrência `pauta`; `actions/cache` v6.1.0 pelo SHA `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`; links `https://www.camara.leg.br/evento-legislativo/{id}` e `https://www.camara.leg.br/propostas-legislativas/{id}`.

## Fase 1: Fixtures (sem rede nos testes)

**Propósito**: respostas reais salvas e construtores sintéticos de que todos os testes dependem.

- [X] T001 Criar `tests/capturar_pautas.py`, ferramenta de desenvolvimento com rede no padrão de `tests/capturar_fixtures.py` (docstring de uso; não é coletado pelo pytest porque não começa com `test_`). Grava **byte a byte** em `tests/fixtures/pauta/`: `orgaos/CE.json` e `orgaos/CREDN.json` (`/orgaos?sigla=`); `eventos/2009-2026-10-17-2026-10-31.json`, `eventos/2009-2026-04-08-2026-04-22.json` e uma janela da CREDN com reunião que teve MSC e PDL e uma cancelada (escolher pelas pautas de 12 meses, research R11); `eventos/{id}.json` (detalhe) de 81555 e 83091; `pautas/{id}.json` de 83091, 81555 e de cada reunião das janelas salvas; e `manifesto.json` com, para cada arquivo, o endpoint e a data e hora da captura. Rodar uma vez e commitar as fixtures com `tests/fixtures/pauta/README.md` (o que cada recorte cobre: 83091 com 19 PL e REQ 70→REQ 63; 81555 com PL 5432/2016, REQ 17→PL 1778/2020 e relator Luiz Lima com `siglaPartido` nulo; MSC, PDL, cancelada, `Encerrada (Termo)`; um texto "Prejudicado o Requerimento de Retirada de Pauta… Retirado de pauta…"). As pautas salvas DEVEM cobrir, com texto real de `situacaoItem` em item listado de reunião realizada, **os sete rótulos do §5.9** (escolher pelas 48 pautas de 12 meses do research, inclusive uma com "rejeitado"); se algum rótulo não tiver caso real na fonte, anotar no README qual e por quê.
- [X] T002 [P] Salvar em `tests/fixtures/pauta/atual.json` uma cópia do `data/atual.json` de 24/10/2026 (inventário com o PL 3701/2020 apensado ao PL 5432/2016) e anotá-la no README.
- [X] T003 Criar `tests/pauta_sinteticos.py` com: `TransportePauta` (implementa `obter_json` por URL a partir de `tests/fixtures/pauta/`, com respostas sobrepostas por URL, `HTTPError` simulado, inclusive 404, e registro das URLs pedidas; `baixar` levanta erro); `evento(id, inicio, situacao="Convocada", tipo="Reunião Deliberativa", orgao=2009)`; `item_pauta(ordem, proposicao=None, relacionada=None, relator=None, situacao_item=None)` no formato da API (com `numero` e `ano` como texto na relacionada, R4); `indice(proposicoes)` no formato de `contracts/indice-autoria.md`; e `deputados_novo(ids)`. Em `tests/test_pauta_sinteticos.py` conferir que as fixtures de T001 e T002 carregam e que os construtores produzem o formato das respostas reais (mesmas chaves).

**Checkpoint**: fixtures carregam; nenhum teste usa rede.

**Commit**: `test(PAU): fixtures reais de pauta e construtores sintéticos`.

---

## Fase 2: Fundação (bloqueia as histórias)

**Propósito**: peças que todas as histórias usam. Cada tarefa começa pelo teste.

- [X] T004 [P] Em `tests/test_transporte.py` escrever o teste: HTTP 404 em `obter_json` levanta `RecursoInexistente`, que é `FalhaDeColeta` com categoria `fonte_indisponivel` e não é repetida; 500 e 429 continuam repetidos; 400 continua `FalhaDeColeta` comum. Depois criar `RecursoInexistente` em `src/monitor_comissoes/transporte.py` (R7). Em `src/monitor_comissoes/erros.py` acrescentar `ENTRADA_INVALIDA = "entrada_invalida"` **fora** de `CATEGORIAS` e de `REPETIVEIS` (a coleta e o `status.json` não mudam).
- [X] T005 [P] Em `tests/test_indice.py` escrever os testes de `src/monitor_comissoes/indice.py` (`contracts/indice-autoria.md`): `construir_indice(lote, gerado_em)` sobre o lote de fixtures (`tests/fixtures/camara/`) inclui toda proposição dos tipos `MSC, PDL, PEC, PL, PLP, REQ` dos arquivos `proposicoes-{ano}`, com `[autoria_novo, deputados]` ("`1` se alguma linha de `proposicoesAutores` da proposição tem `siglaPartidoAutor == "NOVO"`"; deputados "sem repetição, em ordem crescente"), `[0, []]` sem autor, e exclui outros tipos; `serializar_indice` é JSON compacto com os campos na ordem do contrato; `ler_indice(caminho)` devolve o índice e falha com `FalhaDeColeta(ENTRADA_INVALIDA, ...)` com o caminho para arquivo ausente, JSON inválido, `versao_formato` diferente de 1, campo ausente e valor fora do formato. Depois criar `indice.py`, reaproveitando `lote._linhas` para ler só as colunas necessárias.
- [X] T006 Em `tests/test_diaria.py` escrever os testes: `executar_diaria(..., indice=caminho)` grava `cache/indice-autoria.json` em sucesso, no mesmo `gravar_todos` (o conteúdo bate com `construir_indice` do mesmo lote, e `gerado_em`, `dados_camara_em` e `anos_lidos` batem com o `meta` do `atual.json`); em qualquer falha (coleta, plausibilidade, gravação) o índice anterior fica byte a byte; a saída do comando e o `status.json` não mudam. Depois: em `src/monitor_comissoes/coleta.py`, `Coletado` ganha `indice: dict | None = None`, montado dentro do bloco do lote por `construir_indice`; em `src/monitor_comissoes/diaria.py`, opção `--indice` (padrão `cache/indice-autoria.json`) e o índice serializado entra em `escritas`. `python -m monitor_comissoes` (COL) não grava índice. Acrescentar `cache/` ao `.gitignore`.
- [X] T007 [P] Em `tests/test_pauta_api.py` escrever os testes de `src/monitor_comissoes/pauta/api.py` com `TransportePauta` (data-model.md, "Validação das respostas da API"): `obter_orgao(transporte, sigla)` devolve o id (CE → 2009) e falha `formato_alterado` sem órgão, com dois ou com sigla diferente; `obter_eventos(transporte, id_orgao, inicio, fim)` monta a URL com `dataInicio`, `dataFim` e `itens=100`, segue a paginação dos `links` do corpo, falha se `X-Total-Count` difere do entregue, se o link de paginação sai da API ou repete página, e valida cada evento ("`id` inteiro, `dataHoraInicio` `AAAA-MM-DDTHH:MM`, `situacao` texto, `descricaoTipo` texto, `orgaos` lista com `id`"); `obter_evento(transporte, id)` devolve o evento ou `None` em 404 (`RecursoInexistente`), e qualquer outro erro propaga; `obter_pauta(transporte, id)` valida cada item ("`ordem` inteiro, `titulo` texto; `proposicao_` e `proposicaoRelacionada_` objeto ou nulo, com `id` inteiro, `siglaTipo` texto, `numero` e `ano` inteiros ou textos só de dígitos quando objeto; `relator` objeto com `id` e `nome`, ou nulo; `situacaoItem` texto ou nulo") e falha `formato_alterado` com o campo; erro de rede vira `fonte_indisponivel` com o endpoint no motivo. Depois criar `src/monitor_comissoes/pauta/__init__.py` e `api.py`.
- [X] T008 [P] Em `tests/test_pauta_arquivos.py` escrever os testes de `src/monitor_comissoes/pauta/arquivos.py` (`contracts/pauta-json.md`, `contracts/status-pauta-json.md`): `ultimo_arquivo(pasta, hoje)` devolve o arquivo `AAAA-MM-DD.json` mais recente com data ≤ hoje (ignora outros nomes; falha `entrada_invalida` se houver arquivo com data futura); `ler_pauta(caminho)` aplica a validação na leitura do contrato e falha com o nome do arquivo; `ler_status_pauta(caminho)` devolve `None` para ausente e para ilegível (avisando no `stderr`); `montar_status_pauta(resultado, verificado_em, falha, ultima_checagem_boa)` na ordem de campos do contrato; `gravar(arquivo_do_dia, caminho_dia, status, caminho_status)` grava os dois com `status.gravar_todos` (tudo ou nada; em falha da segunda troca, a primeira é desfeita). Depois criar `arquivos.py`.

**Checkpoint**: fundação verde; a coleta grava o índice; as histórias podem começar.

**Commit**: `feat(PAU): índice de autoria na coleta, API da pauta e arquivos da checagem`.

---

## Fase 3: User Story 1 — Reuniões da semana e o que está na pauta (P1)

**Objetivo**: reuniões da janela com itens listados, REQ e outros contados, links oficiais (FR-001 a FR-007).

**Teste independente**: montar a checagem com as fixtures da CE de 28/10/2026 e de 15/04/2026 e conferir janela, situação, itens e contagens.

- [X] T009 [P] [US1] Em `tests/test_pauta_regras.py` escrever os testes de `src/monitor_comissoes/pauta/regras.py`: `situacao(texto)` pela tabela do research R3 (`Encerrada`, `Encerrada (Final)`, `Encerrada (Termo)` → `realizada`; `Convocada` → `convocada`; `Cancelada` → `cancelada`; outro, como `Em Andamento`, → `outra`); `proposicao_do_item(item)` pela regra do R4 ("se `proposicao_.siglaTipo == "REQ"`, a proposição do item é a `proposicao_`; senão, a `proposicaoRelacionada_` quando existe; senão, a `proposicao_`; senão, nenhuma"), com os pares reais PRL→PL, PRL→MSC, REQ→REQ (REQ 70→63), REQ→PL (REQ 17→PL 1778/2020), REQ→PEC, PRV→PL e item sem proposição; `grupo(tipo)` → `listado` para `PL, PLP, PEC, MSC, PDL`, `req` para `REQ`, `outro` para os demais e para item sem proposição; `chave(item)` → `p:{id}` ou `t:{titulo}`; `identificacao` `Tipo número/ano` com `numero` e `ano` em texto ou inteiro. Depois criar `regras.py`, puro.
- [X] T010 [US1] Em `tests/test_pauta_checagem.py` escrever os testes de `montar_reunioes(eventos_por_comissao, pautas, contexto)` em `src/monitor_comissoes/pauta/checagem.py` (sem etiquetas ainda: `contexto` com índice e deputados vazios): só `descricaoTipo == "Reunião Deliberativa"`; janela por **data** de `inicio` entre D−7 e D+7, inclusive (eventos em D−8, D−7, D, D+7 e D+8); cancelada continua; campos da reunião na ordem do data-model (`id`, `comissao`, `inicio`, `situacao`, `situacao_camara`, `link`, `vista_desde`, `itens`, `requerimentos`, `outros`, `pauta`); `itens` só com os listados; `requerimentos.total` e `outros.total` contados; `pauta` com todos os itens na ordem da pauta (`chave`, `ordem`, `titulo`, `proposicao` resumida ou `null`), inclusive itens repetidos; cada item listado com os campos do contrato e `link` oficial; ordem das reuniões por `inicio`, ordem das comissões na configuração e `id`; evento ligado às duas comissões aparece uma vez em cada; pauta vazia dá zero itens sem erro; dia sem reunião dá lista vazia. Com a fixture 83091: 19 itens listados, `requerimentos.total == 1`, REQ 70/2026 na `pauta` com chave `p:2645503`. Com 81555: o REQ 17/2026 é só contado, e o PL 1778/2020 não está em `itens`. Depois implementar em `checagem.py`.

**Checkpoint**: US1 verde.

**Commit**: `feat(PAU): reuniões da janela, itens listados e contagens`.

---

## Fase 4: User Story 2 — Itens com ligação com o NOVO (P1)

**Objetivo**: etiquetas, "autoria não verificada", "leva apensado do NOVO" e o grupo do NOVO primeiro (FR-005, FR-007 a FR-010).

**Teste independente**: com as fixtures 81555 e 83091, o inventário salvo e um índice sintético, conferir etiquetas e marcas item a item.

- [X] T011 [P] [US2] Em `tests/test_pauta_etiquetas.py` escrever os testes de `src/monitor_comissoes/pauta/etiquetas.py`: `etiquetas(proposicao, relator, indice, ids_novo)` dá `autoria NOVO` quando o índice tem `autoria_novo == 1`; `autor hoje no NOVO` quando algum deputado autor do índice está em `ids_novo`, mesmo com autoria por outro partido; `relatoria NOVO` quando `relator.id` está em `ids_novo`, com `relator.siglaPartido` nulo (Luiz Lima em 81555); ordem fixa das etiquetas; proposição **fora do índice** → sem as duas de autoria, `autoria_nao_verificada = True`, e `relatoria NOVO` continua valendo; `apensados_do_novo(id_proposicao, inventario)` lista os itens do `atual.json` com `apensado_a.id` igual, cada um com `id`, `identificacao`, `link` e `etiquetas` do inventário, ordenados por `id`, e não inclui a própria proposição; com o inventário salvo, o PL 5432/2016 (2086175) leva o PL 3701/2020 com `autoria NOVO` e `autor hoje no NOVO`. Depois criar `etiquetas.py`, puro.
- [X] T012 [US2] Em `tests/test_pauta_checagem.py` acrescentar os testes de integração das etiquetas em `montar_reunioes`: itens do grupo do NOVO (com `etiquetas` ou `leva_apensado_do_novo` não vazios) vêm primeiro e, dentro de cada grupo, a `ordem`; `autoria_nao_verificada` não põe o item no grupo do NOVO; REQ é listado em `requerimentos.listados` só com `autoria NOVO`, `autor hoje no NOVO` ou `autoria_nao_verificada` ("`relatoria NOVO` sozinha não lista o REQ"), com `relacionada` preenchida (REQ 17 → PL 1778/2020 com link); todos os REQ continuam contados; nenhum item é incluído nem excluído por etiqueta (a soma de listados, REQ e outros é sempre o total da pauta). Depois ligar `etiquetas.py` a `checagem.py`.

**Checkpoint**: US2 verde.

**Commit**: `feat(PAU): etiquetas do NOVO, autoria não verificada e apensados do NOVO na pauta`.

---

## Fase 5: User Story 3 — Resultado das reuniões realizadas (P1)

**Objetivo**: rótulo do §5.9 com o texto original, só em reunião realizada (FR-011).

**Teste independente**: classificar os textos reais das fixtures e conferir cada rótulo.

- [X] T013 [P] [US3] Em `tests/test_pauta_resultado.py` escrever os testes de `resultado(texto)` em `src/monitor_comissoes/pauta/regras.py` (research R5), com textos reais das fixtures: "Retirado de pauta, por acordo, a pedido do governo." → `retirado de pauta`; texto com "Requerimento de Retirada de Pauta" e aprovação do parecer → `aprovado`; "Prejudicado o Requerimento de Retirada de Pauta… Retirado de pauta…" → `retirado de pauta` (a expressão excluída é removida, não o texto inteiro); vista e aprovação → `vista`; "Aprovado o Parecer", "Aprovada" → `aprovado`; "Rejeitado", "Rejeitada" → `rejeitado`; "Não deliberado.", adiado, não apreciado, reunião encerrada antes do item → `não apreciado`; `None`, `""` e só espaços → `sem registro`; texto sem regra → `outro`; maiúsculas e minúsculas indiferentes; o resultado é `{"rotulo", "texto"}` com o texto original intacto. Teste de cobertura (US3, cenário 9; SC-004): sobre todos os itens listados das reuniões realizadas nas fixtures, todo item tem rótulo e texto, cada um dos sete rótulos aparece ao menos uma vez em **caso real** (exceto os anotados como sem caso real no README de T001, cobertos por sintético derivado), e `outro` só em texto sem regra. Depois implementar `resultado` em `regras.py`.
- [X] T014 [US3] Em `tests/test_pauta_checagem.py` acrescentar: em reunião `realizada`, todo item listado (inclusive REQ listado) tem `resultado`; em `convocada`, `cancelada` e `outra`, `resultado` é `null`. Depois ligar em `checagem.py`.

**Checkpoint**: US3 verde.

**Commit**: `feat(PAU): resultado dos itens das reuniões realizadas (§5.9)`.

---

## Fase 6: User Story 4 — Pauta alterada ou reunião caída, uma vez só (P1)

**Objetivo**: cinco tipos de alteração, registro único, linha de base e "vista desde" (FR-003, FR-012 a FR-017).

**Teste independente**: sequências de checagens sobre variações das fixtures, conferindo cada alteração uma vez só.

- [X] T015 [US4] Em `tests/test_pauta_alteracoes.py` escrever os testes de `comparar(anterior, reunioes, buscar_evento, checada_em, janela)` em `src/monitor_comissoes/pauta/checagem.py` (research R6): só reuniões `convocada` na checagem anterior; ainda convocada → `item_entrou` e `item_saiu` pela diferença de multiconjuntos de chaves (proposição repetida conta duas vezes), `data_hora` com `de` e `para` quando `inicio` muda; agora `cancelada` → só `cancelada`; agora `realizada` ou `outra` → nada, mesmo com item novo e hora mudada (FR-015); só ordem diferente → nada; **sumiu da janela** → `buscar_evento(id)`: data fora da janela → `data_hora` com a data nova; `Cancelada` → `cancelada`; `None` (404) → `retirada_da_agenda`; existe na janela, mas não é mais "Reunião Deliberativa" da comissão → `retirada_da_agenda` com `detalhe` (`"agora: Audiência Pública (CE)"`); erro de `buscar_evento` propaga. Cada alteração tem os campos e a ordem do contrato, `detectada_em = checada_em` e `reuniao.inicio` da checagem anterior. Depois implementar `comparar`.
- [X] T016 [US4] Em `tests/test_pauta_alteracoes.py` escrever os testes de `montar_arquivo(hoje, comissoes, checagem, anterior, alteracoes_novas)` em `checagem.py`: sem arquivo anterior → `meta.linha_de_base = {"motivo": "primeira checagem"}` e nenhuma alteração, com `vista_desde = checada_em` em toda reunião; arquivo anterior do **mesmo dia** → alterações já gravadas + novas, `linha_de_base` herdada; arquivo de **dia anterior** → só as novas, no arquivo de hoje; `vista_desde` copiado da checagem anterior para reunião que já estava nela, e o momento desta checagem para reunião nova (inclusive a que entra na janela porque o dia avançou, que não gera alteração); sequência de três checagens no dia, cada uma com uma alteração diferente → três alterações, cada uma com seu `detectada_em`, e a terceira checagem como última; a mesma fonte checada de novo (no mesmo dia e no dia seguinte) **não** acrescenta alteração; duas checagens sobre a mesma fonte dão arquivos idênticos exceto `checagem.checada_em`. Depois implementar.

**Checkpoint**: US4 verde.

**Commit**: `feat(PAU): alterações de pauta registradas uma vez, linha de base e vista desde`.

---

## Fase 7: User Story 6 — Falhar de forma visível, só na pauta (P1)

**Objetivo**: a CLI `checar` e `mensagem`, com status da pauta e nenhuma gravação parcial (FR-016, FR-022 a FR-024).

**Teste independente**: para cada falha simulada, saída 1, motivo no status, `data/pautas/` e arquivos da coleta byte a byte.

- [X] T017 [US6] Em `tests/test_pauta_cli.py` escrever os testes ponta a ponta de `main(argv, transporte, agora)` em `src/monitor_comissoes/pauta/cli.py` (`contracts/pauta-cli.md`), num diretório temporário com `config.toml`, o inventário salvo, um índice sintético que contém **todas** as proposições das pautas usadas (`[0, []]` salvo as autorias que o teste declarar; sem isso, todo item ganharia "autoria não verificada") e `TransportePauta`: `checar` grava `data/pautas/AAAA-MM-DD.json` (dia de Brasília de `agora`) e `data/status-pauta.json` com `resultado: ok` e `ultima_checagem_boa = checada_em`; imprime a linha `OK: …` do contrato (com `linha de base` na primeira); segunda execução com a mesma fonte imprime `0 alterações novas`; nunca toca em `atual.json`, `anterior.json`, `mudancas/`, `status.json` nem `envio.json` (comparados byte a byte); `mensagem` imprime `pauta: AAAA-MM-DD HH:MM · ok · N reuniões · K alterações`, `· linha de base` e `· falha · categoria`, e sai 1 sem status. Depois criar `cli.py` e `__main__.py` (`python -m monitor_comissoes.pauta`), com a orquestração: config → índice → inventário (`retratos.ler` do `atual.json`) → última checagem → deputados (`obter_deputados_novo`) → órgãos → eventos → pautas → montar → comparar → gravar.
- [X] T018 [US6] Em `tests/test_pauta_falhas.py` escrever os testes de falha, um por cenário da User Story 6 e do FR-022: HTTP 503 depois das tentativas em eventos e em pauta (`fonte_indisponivel`); JSON inválido e campo ausente (`formato_alterado` com o campo); paginação incompleta; a pauta de **uma** reunião falha → checagem inteira falha; deputados falham (`api_deputados`); índice ausente ou inválido, `atual.json` ausente ou inválido, arquivo de pauta anterior ilegível e arquivo com data futura (`entrada_invalida`, com o nome do arquivo; o anterior ilegível **não** vira linha de base); erro na busca de evento sumido que não é 404; exceção inesperada (`interna`). Em todos: saída 1; `FALHA [categoria]: motivo` no `stderr`; `data/pautas/` byte a byte (nenhum arquivo criado ou alterado); `status-pauta.json` com `resultado: falha`, o motivo e a `ultima_checagem_boa` anterior (do status anterior ou, sem ele, do `checada_em` do arquivo de pauta mais recente, ou `null`); arquivos da coleta intocados. Teste também que a falha da coleta (um `status.json` com `resultado: falha`) não impede a checagem. Depois ajustar `cli.py`.

**Checkpoint**: US6 verde; a CLI está completa.

**Commit**: `feat(PAU): CLI da checagem da pauta com falha visível e status próprio`.

---

## Fase 8: User Story 5 — Checar várias vezes ao dia (P2)

**Objetivo**: workflow com as três garantias e o índice levado pelo cache (FR-020, FR-021).

**Teste independente**: verificação textual dos workflows.

- [X] T019 [P] [US5] Em `tests/test_workflow_pauta.py` (no padrão de `tests/test_workflow_aviso.py`) escrever os testes de `.github/workflows/checagem-pauta.yml`: os três crons do contrato e nenhum outro; a checagem da manhã termina antes de `17 10 * * *` (cron do aviso) com folga de ao menos 60 minutos; uma checagem depois das 14h de Brasília e outra depois das 22h; `workflow_dispatch` sem entradas; sem `push` nem `pull_request`; `concurrency` `pauta` sem cancelar e **diferente** de `coleta-diaria`; `permissions: contents: write` só; `timeout-minutes`; mesmo SHA do setup-uv dos outros workflows; `actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9` com `path: cache/indice-autoria.json` e `restore-keys: indice-autoria-`; o passo roda `.venv/bin/python -m monitor_comissoes.pauta checar`, guarda o código, em falha faz `git checkout -- data/pautas` e `git clean -fdq -- data/pautas`, faz `git add` só de `data/status-pauta.json` e (em sucesso) `data/pautas`, commita com `pauta mensagem`, `git pull --rebase`, push com uma nova tentativa e devolve o código. Depois criar o workflow.
- [X] T020 [P] [US5] Em `tests/test_workflow.py` acrescentar: o workflow da coleta tem, **depois** do passo "Coleta e commit", um passo `actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9` com `if: success()`, `path: cache/indice-autoria.json` e `key: indice-autoria-${{ github.run_id }}-${{ github.run_attempt }}`; os demais testes do workflow continuam passando sem alteração. Depois acrescentar o passo em `.github/workflows/coleta-diaria.yml`.

**Checkpoint**: US5 verde.

**Commit**: `ci(PAU): checagem da pauta três vezes por dia e índice de autoria no cache`.

---

## Fase 9: User Story 7 — Conferível e testável sem rede (P2)

**Objetivo**: casos reais da spec ponta a ponta e manifesto das fixtures (SC-001 a SC-004, SC-008).

- [X] T021 [US7] Em `tests/test_pauta_aceitacao.py` escrever os casos de aceitação com as fixtures reais, pela CLI com `TransportePauta` e um índice que contém todas as proposições das pautas salvas (como em T017), com as autorias do lote de fixtures quando existirem: (a) checagem em 24/10/2026 com a janela da CE salva → a reunião 83091 com 19 PL listados e 1 REQ contado, todos com link (SC-002); (b) checagem em 15/04/2026 com a janela da CE de abril → o PL 5432/2016 traz `leva_apensado_do_novo` com o PL 3701/2020, `autoria NOVO` e `autor hoje no NOVO`, e vem antes dos itens sem ligação (SC-003); o REQ 17/2026 só contado; o item do PL 3464/2025 com `relatoria NOVO` (Luiz Lima); todo item listado com `resultado` e texto (SC-004); (c) a reunião cancelada e a CREDN com MSC e PDL listados; (d) toda reunião, item, apensado e alteração tem `link` começando com `https://www.camara.leg.br/` (SC-001). Teste também que todo arquivo de `tests/fixtures/pauta/` está no `manifesto.json` com endpoint e data. Se algum caso falhar por regra, corrigir o código da fase correspondente, nunca a fixture.

**Checkpoint**: casos de aceitação verdes.

**Commit**: `test(PAU): casos de aceitação com pautas reais`.

---

## Fase 10: Fechamento

- [X] T022 [P] Conferir que `src/monitor_comissoes/pauta/` não importa nada de `pagina/`, `aviso.py`, `resumo.py` nem `envio.py` e que nenhum arquivo de PRZ, SEM ou PGP foi criado (escopo, princípio VII); registrar no fim deste arquivo, em "Notas da implementação", qualquer desvio do plano.
- [X] T023 Rodar a verificação completa `uv run ruff check . && uv run ruff format --check . && uv run pytest` e guardar a saída para o relatório. O status da PAU no `ROADMAP.md` continua `em andamento` até o OK do mantenedor e o merge.

---

## Dependências e ordem

- Fase 1 → Fase 2 → Fases 3 a 7 → Fases 8 e 9 → Fase 10.
- Na Fase 2, T004, T005, T007 e T008 são paralelas; T006 depende de T005.
- US1 (T009–T010) antes de US2 (T011–T012) e US3 (T013–T014), porque estas acrescentam campos a `montar_reunioes`. T011 e T013 (módulos puros) podem andar em paralelo.
- US4 (T015–T016) depende de US1 (estrutura da reunião e chaves).
- US6 (T017–T018) depende de US1 a US4 (a CLI orquestra tudo).
- US5 (T019–T020) só depende da CLI existir (T017); T019 e T020 são paralelas.
- US7 (T021) depende de US1 a US6.

### Paralelismo por história

```text
Fase 2:  T004 ∥ T005 ∥ T007 ∥ T008   (depois T006)
US2/US3: T011 ∥ T013                 (depois T012, T014)
US5:     T019 ∥ T020
```

## Estratégia de implementação

1. **MVP = US1 + US6**: reuniões e itens da janela, gravados com falha visível. Já responde "o que vai a voto".
2. US2 acrescenta o que distingue o produto (ligação com o NOVO); US3, o resultado; US4, as alterações para a véspera da SEM.
3. US5 liga o agendamento; US7 fecha os casos reais.
4. Cada fase termina verde e com commit, sem push.

## Cobertura das exigências da spec

| Exigência | Tarefas |
|---|---|
| FR-001 a FR-003 (reuniões, janela, situação, vista desde) | T009, T010, T016 |
| FR-004 a FR-007 (proposição do item, listagem, ordem) | T009, T010, T012 |
| FR-008, FR-008a, FR-009, FR-010 (etiquetas e marcas) | T005, T011, T012 |
| FR-011 (resultado) | T013, T014 |
| FR-012 a FR-015 (alterações, linha de base) | T015, T016 |
| FR-016 a FR-019 (arquivo do dia, idempotência, versão, sem `mudancas/`) | T008, T016, T017 |
| FR-020, FR-021 (agendamento, commit) | T019, T020 |
| FR-022 a FR-024 (falha visível) | T004, T007, T018 |
| FR-025 (testes sem rede) | T001 a T003, todas |
| FR-026 (limites) | T022 |
| SC-001 a SC-009 | T021 (SC-001 a SC-004), T016 (SC-005), T018 (SC-006), T019 (SC-007), T023 (SC-008), T022 (SC-009) |

## Notas da implementação (desvios registrados)

- **T020:** `test_a_entrada_nao_e_interpolada_dentro_do_script` (em `tests/test_workflow.py`)
  conferia a ausência de `${{` do script da coleta até o fim do arquivo. O passo novo de
  `actions/cache/save` precisa de `${{ github.run_id }}` na chave, então o teste passou a olhar
  só até o passo seguinte. A intenção (nenhuma interpolação dentro do script) não mudou.
- **T021 (b):** no dado real, o PL 5432/2016 não tem etiqueta própria; quem traz `autoria NOVO`
  e `autor hoje no NOVO` é o apensado PL 3701/2020, dentro de `leva_apensado_do_novo` (as
  etiquetas vêm do inventário). O teste confere assim. O link de cada item fica em
  `proposicao.link`, como no contrato `pauta-json.md`.
- **T021 (manifesto):** a conferência de que toda resposta salva está no `manifesto.json`, com
  endpoint e data, já existia em `tests/test_pauta_sinteticos.py` (T001) e não foi repetida. O
  `atual.json` das fixtures não é resposta da API e está descrito no README das fixtures.
- **T022:** `src/monitor_comissoes/pauta/` só importa `coleta`, `config`, `deputados`, `erros`,
  `estoque`, `indice`, `retratos`, `saida`, `status` e `transporte`; nenhum arquivo de PRZ, SEM
  ou PGP foi criado.
- **Revisão, rodada 1 (R6, reunião que sumiu):** a regra "data fora da janela → data ou hora
  mudou" registrava a alteração também quando a data **não** mudou e a reunião só tinha ficado
  para trás da janela (deixada "Convocada" depois de realizada, ou dias sem checagem boa), com
  `de` igual a `para`. Agora: `Cancelada` decide primeiro (também fora da janela); fora da
  janela com a mesma data, nenhuma alteração; com outra data, "data ou hora mudou".
- **Revisão, rodada 1 (R5, §5.9):** a exceção "Requerimento de Retirada de Pauta" passa a
  cobrir a grafia "Requerimento de Retirado de Pauta", que aparece no texto real do PL
  4242/2021 (80344, ordem 16) e o fazia sair "retirado de pauta" em vez de "aprovado". O README
  das fixtures foi recontado: retirado 41, aprovado 83; a linha "sem registro" dizia 49 porque
  contava a reunião cancelada e a convocada; nas realizadas são 7.
- **Revisão, rodada 1 (validação):** cada órgão do evento passa a exigir `sigla` (texto); sem
  ela, uma reunião que sumiu seria dada como "retirada da agenda" por engano.
