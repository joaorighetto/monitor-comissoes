# Tasks: REL — Relatoria NOVO atual

**Input**: documentos de projeto em `specs/003-relatoria-novo-atual/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Pré-requisitos**: plan.md e spec.md aprovados pelo mantenedor; as cinco "Decisões do mantenedor" do plano estão aprovadas.

**Testes**: pedidos pelo fluxo (fixtures salvas, nenhum teste com rede). Em cada fase, os testes vêm **antes** da implementação e devem falhar primeiro.

**Formato**: `- [ ] T### [P?] [US?] Descrição com caminho`. `[P]` = arquivos diferentes, sem dependência de tarefa incompleta.

**Regras do repositório (CLAUDE.md)**: commits pequenos e descritivos, sem push; nenhuma troca de branch; verificação completa: `uv run ruff check . && uv run ruff format --check . && uv run pytest`.

## Fase 1: Fixtures reais (únicas tarefas com rede)

**Propósito**: ter em disco as respostas reais que todos os testes usam. Depois desta fase, nada mais precisa de rede.

- [X] T001 Estender `tests/capturar_fixtures.py`: (a) acrescentar aos alvos PL 937/2022 (id 2319917), PL 3514/2023 (id 2373721) e PL 4501/2023 (id 2388105) com as cadeias de apensação completas; (b) selecionar também as linhas de CE e CREDN cujo `ultimoStatus_uriRelator` é de deputado do NOVO em exercício e **os apensados dessas raízes**; (c) salvar a resposta real de `/proposicoes/{id}/tramitacoes` de cada referência selecionada em `tests/fixtures/camara/tramitacoes/{id}.json` e a de `/deputados/{id}` de cada relator em `tests/fixtures/camara/deputados/{id}.json`, byte a byte; (d) registrar tudo em `manifesto.json`.
- [X] T002 Rodar a captura com rede (`uv run python tests/capturar_fixtures.py`, cerca de 1 GB) e comitar só as fixtures. Conferir no manifesto que PL 937/2022, PL 3514/2023, PL 4501/2023 e PL 1843/2022 estão presentes e anotar quais apensados reais de raiz com relator do NOVO foram capturados (se não houver nenhum, registrar em `tests/fixtures/camara/README.md` e manter o caso só derivado).
- [X] T003 Atualizar `tests/fixtures/camara/README.md` (tabelas das novas fixtures, o que é real e o que é derivado dentro do teste) e rodar a suíte inteira com as fixtures recapturadas; corrigir, **uma a uma e com o motivo no commit**, as diferenças em testes de COL e AGE causadas pela recaptura (data dos dados, deputados em exercício, novas linhas).

**Checkpoint**: fixtures em disco; suíte verde sem rede.

---

## Fase 2: Fundação (bloqueia todas as histórias)

**Propósito**: peças de I/O e de formato que todas as histórias usam. Cada tarefa começa pelo teste.

- [X] T004 [P] Em `tests/test_lote.py` escrever os testes da nova coluna: `ultimoStatus_uriRelator` obrigatória (ausente → `formato_alterado` com o nome da coluna) e `Proposicao.id_relator` = id da URI ou `None` quando vazio (URI inválida → `formato_alterado`). Depois acrescentar a coluna a `PROPOSICOES_COLUNAS` e o campo `id_relator: int | None` a `Proposicao` em `src/monitor_comissoes/lote.py`.
- [X] T005 [P] Em `tests/test_tramitacoes.py` escrever os testes de `obter_tramitacoes(transporte, url_base, id)` com as fixtures reais de `tests/fixtures/camara/tramitacoes/`: leitura válida de PL 937/2022 e PL 1843/2022; falham com `fonte_indisponivel` (erro de rede/HTTP, depois das tentativas do transporte) ou `formato_alterado` (todo o resto):  JSON inválido, `dados` ausente, não lista ou **vazia**, campo obrigatório ausente ou de tipo errado (`sequencia` não inteira, `codTipoTramitacao` não texto), `sequencia` repetida, link com `rel` diferente de `self`, `href` fora de `https://dadosabertos.camara.leg.br/api/`, URI de `320` que não termina em `/deputados/{inteiro}` (contrato em `contracts/api-camara.md`). Depois criar `src/monitor_comissoes/tramitacoes.py` com `Tramitacao` (NamedTuple: `sequencia`, `data_hora`, `orgao`, `codigo`, `descricao`, `id_relator`) e `obter_tramitacoes`, no estilo de `deputados.py` (sem X-Total-Count, que não existe nessa API).
- [X] T006 [P] Em `tests/test_deputados.py` escrever os testes de `obter_deputado(transporte, url_base, id)` com as fixtures reais de `tests/fixtures/camara/deputados/`: devolve nome (`ultimoStatus.nomeEleitoral`) e partido (`ultimoStatus.siglaPartido`); falham com `api_deputados`: rede/HTTP, JSON inesperado, campo ausente ou vazio. Depois implementar `obter_deputado` em `src/monitor_comissoes/deputados.py`.

**Checkpoint**: fundação verde; as histórias podem começar.

---

## Fase 3: História 1 — Enxergar a relatoria do NOVO que vale hoje (P1) 🎯 MVP

**Objetivo**: a etiqueta `relatoria NOVO` pelo relator atual (spec US1; FR-001 a FR-005). Um item pode entrar só por ela.

**Teste independente**: `tests/test_aceitacao.py` com as fixtures reais: PL 4501/2023 dentro (só `relatoria NOVO`, relator Luiz Lima), PL 937/2022 e PL 3514/2023 fora, PL 1843/2022 com `autoria NOVO` e `relatoria NOVO`.

### Testes (escrever primeiro, ver falhar)

- [X] T007 [P] [US1] Em `tests/test_relatoria.py` testar `relatoria.relator_atual(tramitacoes, comissao)` com tramitações **reais**: PL 937/2022 → sem relator (`507` depois da designação de Luiz Lima); PL 3514/2023 em CREDN → sem relator (designação em CESPO, passagem nova); PL 4501/2023 → Luiz Lima desde 2025-04-09T00:00; PL 1843/2022 → Adriana Ventura (o `500` "Mantido o parecer" e o `170` não zeram); PL 648/2024 e PL 4781/2025 → sem relator; um item recém-chegado sem designação → sem relator.
- [X] T008 [P] [US1] Em `tests/test_relatoria.py` testar, com tramitações reais alteradas **dentro do teste**: ordenação por `sequencia` e não pela ordem da lista (embaralhar a lista); devolução (`507`) depois da designação; substituição NOVO → outro partido e outro → NOVO (spec US1, cenários 6 e 7); redesignação do mesmo deputado depois de `1250`/`1255`; `1250`/`1255` sem redesignação encerram a relatoria; saída e volta à comissão (C → outra comissão → C) com designação só na primeira passagem → sem relator; passagem por `MESA`/`CCP`/`PLEN` não zera.
- [X] T009 [P] [US1] Em `tests/test_estoque.py` testar as etiquetas: `etiquetar` mantém a ordem `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO`; item só de relatoria entra; item sem etiqueta de autoria e sem relator do NOVO não entra; item com autoria NOVO e relator de outro partido fica só com autoria.
- [X] T010 [P] [US1] Em `tests/test_lote.py` testar `ler_ids_relator_novo(caminho, ids_deputados, comissoes)`: devolve os ids de linhas com `ultimoStatus_siglaOrgao` em `comissoes` e `id_relator` em `ids_deputados`, de qualquer tipo; ignora relator de outro partido e linhas fora das comissões.
- [X] T011 [US1] Em `tests/test_aceitacao.py` escrever os quatro casos de aceitação acima rodando a coleta completa sobre as fixtures com transporte falso (lote, `deputados-novo.json`, tramitações e `/deputados/{id}` salvos).

### Implementação

- [X] T012 [US1] Criar `src/monitor_comissoes/relatoria.py` (sem I/O) com `RelatorAtual`, o resultado de três estados (com relator, sem relator, indeterminado com motivo) e `relator_atual(tramitacoes, comissao)` conforme a máquina de estados de `data-model.md` e a tabela de tipos de `research.md` R2: órgãos de apoio `{"MESA", "CCP", "PLEN"}` ignorados; mudança de órgão zera; `320` define pelo id da própria tramitação; `507`, `1250`, `1255` zeram; `170`, `322`, `501` mantêm; ordenar por `sequencia`. Fazer T007 e T008 passarem.
- [X] T013 [US1] Em `src/monitor_comissoes/lote.py` implementar `ler_ids_relator_novo` (T010).
- [X] T014 [US1] Em `src/monitor_comissoes/estoque.py` acrescentar `ETIQUETA_RELATORIA = "relatoria NOVO"`, fazer `etiquetar` receber o relator atual e atribuir a etiqueta quando `relator.id` está em `ids_deputados_novo`, e fazer `construir_itens` incluir os candidatos confirmados (T009).
- [X] T015 [US1] Em `src/monitor_comissoes/coleta.py`: passada de candidatos por relatoria (R3), `necessarias` ampliadas, referência de cada candidato e de cada item com etiqueta de autoria, **uma leitura de tramitações por referência na comissão** (`obter_tramitacoes` + `relator_atual`), `VERSAO_FORMATO = 2`. Fazer T011 passar.

**Checkpoint**: a etiqueta funciona nos quatro casos; `uv run pytest` verde.

---

## Fase 4: História 2 — Apensados herdam o relator da principal (P1)

**Objetivo**: spec US2 (FR-004). **Teste independente**: um apensado cuja raiz tem relator do NOVO herda a etiqueta e mostra o relator da raiz.

- [X] T016 [P] [US2] Em `tests/test_estoque.py` testar a herança: apensado (um nível) cuja raiz tem relator atual do NOVO → `relatoria NOVO` e relator da raiz; cadeia A → B → C → relator de C; apensado com relator próprio do NOVO mas raiz sem relator do NOVO → sem etiqueta; raiz fora da lista de comissões → apensado fora; "principal não localizada" → usa o status e as tramitações do próprio item e mantém a marca. Usar linhas reais da fixture quando existirem (T002) e derivações dentro do teste nos demais casos.
- [X] T017 [P] [US2] Em `tests/test_aceitacao.py` testar a expansão de candidatos: apensados cuja raiz está no conjunto de `ler_ids_relator_novo` viram candidatos (inclusive os de outro tipo na raiz); a referência compartilhada é lida **uma vez** (contar as chamadas do transporte falso).
- [X] T018 [US2] Em `src/monitor_comissoes/coleta.py` e `src/monitor_comissoes/estoque.py` expandir os candidatos para os apensados das raízes encontradas (subir a cadeia com `subir_ate_a_raiz`), resolver o relator na **referência** e atribuir a etiqueta ao apensado. Fazer T016 e T017 passarem.

**Checkpoint**: histórias 1 e 2 funcionam juntas.

---

## Fase 5: História 3 — Relator e partido de hoje em todo item (P2)

**Objetivo**: spec US3 (FR-008, FR-009, FR-015). **Teste independente**: itens com relator do NOVO, de outro partido, sem relator e com relator que mudou de partido.

- [X] T019 [P] [US3] Em `tests/test_aceitacao.py` testar o conteúdo de `relator`: item com relator de outro partido (PL 3871/2024, relator Thiago de Joaldo) mostra nome e `partido_hoje` de `/deputados/{id}` sem `relatoria NOVO`; Luiz Lima (designado como PL, hoje NOVO) mostra `partido_hoje = "NOVO"` e `designado_em`; item sem relator (`relator = null`); `fonte` = link oficial da referência (a principal, no apensado); item só de autoria (ex.: PL 5594/2020) também traz o relator; relator do NOVO **não** gera consulta a `/deputados/{id}` (contar chamadas) e cada relator fora do NOVO gera **uma** consulta.
- [X] T020 [US3] Em `src/monitor_comissoes/coleta.py` e `src/monitor_comissoes/estoque.py` montar `relator` (`id`, `nome`, `partido_hoje`, `designado_em`, `fonte`) em todo item, consultando `obter_deputado` uma vez por relator fora da lista do NOVO, com os campos na ordem de `contracts/atual-json.md`. Fazer T019 passar.

---

## Fase 6: História 4 — Falhar de forma visível (P1)

**Objetivo**: spec US4 (FR-011 a FR-013). **Teste independente**: cada falha simulada termina com erro e motivo, com o `atual.json` anterior idêntico byte a byte; indeterminação marca o item.

- [X] T021 [P] [US4] Em `tests/test_falhas.py` testar, com o `atual.json` anterior comparado byte a byte: API de tramitações com erro de rede/5xx depois das tentativas → `fonte_indisponivel`; resposta com formato inesperado (campo ausente, `sequencia` repetida, lista vazia, link `next`) → `formato_alterado`; `/deputados/{id}` do relator com erro ou campo ausente → `api_deputados`; coluna `ultimoStatus_uriRelator` ausente no lote → `formato_alterado`. Em todos: código de saída 1, mensagem com o motivo, nada gravado.
- [X] T022 [P] [US4] Em `tests/test_relatoria.py` e `tests/test_estoque.py` testar a indeterminação: `320` sem relator identificado; tipo de tramitação novo com "relator" na descrição; última passagem em órgão diferente da comissão do lote; indeterminação limpa por nova `320`/`507`/`1250`/`1255`; item com `relator_indeterminado` = `{"motivo": …}`, `relator = null` e **sem** `relatoria NOVO`; candidato indeterminado **sem** outra etiqueta **entra** na lista com `etiquetas = []`; os demais itens não são afetados e a execução termina com código 0.
- [X] T023 [US4] Em `src/monitor_comissoes/relatoria.py`, `estoque.py` e `coleta.py` implementar o estado indeterminado, a marca `relator_indeterminado` e a inclusão do candidato indeterminado (sem etiqueta, como em FR-003). Fazer T021 e T022 passarem.

---

## Fase 7: História 5 — Repetível, auditável e testável sem rede (P2)

**Objetivo**: spec US5 (FR-014, FR-016, FR-017, FR-019). **Teste independente**: duas execuções idênticas; as regras de consistência do contrato.

- [X] T024 [P] [US5] Em `tests/test_aceitacao.py` testar a repetibilidade: duas execuções sobre as mesmas fixtures dão itens idênticos e na mesma ordem (parado há mais tempo primeiro, desempate por `id`); só `meta.gerado_em` pode diferir; a ordem das tramitações no JSON de entrada não altera o resultado.
- [X] T025 [P] [US5] Em `tests/test_saida.py` ou `tests/test_aceitacao.py` testar as cinco regras de consistência de `contracts/atual-json.md` sobre o documento gerado: `relator` e `relator_indeterminado` não são ambos não nulos; `relatoria NOVO` ⇔ `relator.id` em `meta.deputados_novo_em_exercicio`; `etiquetas` vazia só com `relator_indeterminado`; todo `relator` tem `fonte`; `meta.versao_formato == 2`, `total_itens` e `total_por_comissao` incluem os itens só de relatoria.
- [X] T026 [US5] Corrigir em `src/monitor_comissoes/estoque.py` e `src/monitor_comissoes/coleta.py` o que T024 e T025 apontarem (ordem determinística, campos na ordem do contrato, `meta`). *(nada a corrigir: T024 e T025 passaram de primeira)*
- [X] T027 [P] [US5] Em `tests/test_sem_rede.py` garantir que a suíte nova não abre socket (o teste existente cobre a suíte inteira); acrescentar o caso de `obter_tramitacoes` e `obter_deputado` com o transporte real bloqueado.

---

## Fase 8: Acabamento e verificação

- [ ] T028 **Decisões 1, 4 e 5 aprovadas em 18/10/2026 (plan.md, "Decisões do mantenedor"):** registrar em `PRODUCT.md` §5.4, em commit próprio, as regras acrescentadas (o relator que sai da comissão deixa de ser o atual; designação de passagem anterior não vale; marca "relator indeterminado" e candidato indeterminado na lista) e a decisão final em `specs/003-relatoria-novo-atual/research.md` (R2). Se `1250`/`1255` forem rejeitados, tirá-los da tabela de tipos de `src/monitor_comissoes/relatoria.py` e dos testes de T007/T008.
- [ ] T029 Rodar a verificação completa e mostrar a saída: `uv run ruff check . && uv run ruff format --check . && uv run pytest`.
- [ ] T030 Execução real com rede (`quickstart.md`, passos 3 a 5): conferir `data/atual.json` (casos de aceitação e consistência), registrar tempo da execução e número de pedidos em `research.md` (R3) e explicar item a item a diferença entre o total obtido e os 34 candidatos da sondagem (SC-007). **Não commitar o `data/atual.json` gerado localmente**: o commit diário é do bot da AGE.
- [ ] T031 Conferir os limites do `ROADMAP.md` ("Não inclui") contra o diff: nada de histórico de relatores, relator de outras comissões, comparação com ontem, eventos, Telegram ou página.

---

## Dependências e ordem de execução

- **Fase 1** (T001–T003) → **Fase 2** (T004–T006, em paralelo) → histórias.
- **US1** (T007–T015) é o MVP e libera as demais. **US2** depende de US1 (T012, T015). **US3** depende de US1 (relator já lido). **US4** depende de US1 e usa T005/T006 (validação já pronta); T023 mexe nos mesmos arquivos de US1–US3, então vem depois delas. **US5** fecha a verificação do documento e depende de US1–US4.
- Dentro de cada fase: testes `[P]` antes da implementação; implementação só depois de ver o teste falhar.

## Oportunidades de paralelismo

- Fase 2: T004, T005 e T006 tocam arquivos diferentes.
- US1: T007, T008, T009 e T010 (testes) em paralelo; T012 e T013 em paralelo (arquivos diferentes).
- US2: T016 e T017. US4: T021 e T022. US5: T024, T025 e T027.

## Estratégia de implementação

1. **MVP**: Fases 1, 2 e US1 (a etiqueta nos quatro casos). Parar e validar com `pytest`.
2. Acrescentar US2 (herança), US3 (relator em todos os itens) e US4 (falha e indeterminação), nessa ordem, com commit pequeno por tarefa ou par teste+implementação.
3. Fechar com US5 e a Fase 8. A revisão independente e o `/speckit-converge` vêm depois, conforme o fluxo.

## Totais

31 tarefas: Fase 1 = 3, Fase 2 = 3, US1 = 9, US2 = 3, US3 = 2, US4 = 3, US5 = 4, Fase 8 = 4.
