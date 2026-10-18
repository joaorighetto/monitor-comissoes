# Tasks: MUD — Mudanças desde ontem

**Input**: documentos de projeto em `specs/004-mudancas-desde-ontem/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Pré-requisitos**: spec aprovada pelo mantenedor (18/10/2026). **plan.md e tasks.md aprovados** em 18/10/2026, incluindo as seis "Decisões do mantenedor" (D1 a D6). A tabela de situações finais (D1) está decidida com os **quatro grupos** de `research.md` R2, e a T008 a cria assim.

**Testes**: pedidos pelo fluxo (fixtures salvas, nenhum teste com rede). Em cada fase, os testes vêm **antes** da implementação e devem falhar primeiro.

**Formato**: `- [ ] T### [P?] [US?] Descrição com caminho`. `[P]` = arquivos diferentes, sem dependência de tarefa incompleta.

**Regras do repositório (CLAUDE.md)**: commits pequenos e descritivos, sem push; nenhuma troca de branch; verificação completa: `uv run ruff check . && uv run ruff format --check . && uv run pytest`. Cada fase termina com a verificação completa verde e um ou mais commits (sugestões em "Commit" ao fim de cada fase).

**Ordem das fases**: as histórias da spec são todas P1, mas a User Story 3 (linha de base) constrói o esqueleto de ponta a ponta (retrato anterior, arquivo do dia, quatro arquivos gravados, workflow). Por isso ela vem antes da 1 e da 2, que preenchem a comparação.

## Fase 1: Inventário das fixtures (rede só se faltar algo)

**Propósito**: saber quais respostas reais já salvas servem a cada teste. A suíte atual (514 testes) roda offline e tem 55 respostas de tramitações em `tests/fixtures/camara/tramitacoes/`.

- [X] T001 Inventariar, **só lendo** `tests/fixtures/camara/tramitacoes/*.json` e `tests/fixtures/camara/proposicoes-*.csv`, os casos reais dos testes e registrá-los numa nova seção "Usos na MUD" de `tests/fixtures/camara/README.md` (id, o que serve de exemplo): (a) tramitação `502` com "Artigo 105" no `despacho` (proposição 2086175, sequência 42; também 495615 e 2183535); (b) `322` "Parecer do(a) Relator(a)" (proposição 2330962, órgão CCTI); (c) designação `320` e devolução `507` (casos da REL: PL 937/2022, PL 4501/2023); (d) pelo menos uma resposta em que a matéria **chega** à CE ou à CREDN (mudança de órgão para a comissão) e uma que **sai** dela; (e) no lote, linhas reais para saídas: apensado a principal fora das comissões (como PL 4047/2019, principal na CFT), `Transformado em Norma Jurídica`, `Aguardando Apreciação pelo Senado Federal`, e uma referência que continua numa comissão. Se algum item (a) a (e) faltar, anotar o que falta.
- [X] T002 Se T001 achou falta, estender `tests/capturar_fixtures.py` (alvos novos, no mesmo estilo dos da REL) e rodar a captura **com rede** (`uv run python tests/capturar_fixtures.py`, cerca de 1 GB), salvando as respostas byte a byte e registrando-as em `manifesto.json` e no README. Qualquer diferença nos testes existentes por causa da recaptura é corrigida uma a uma, com o motivo no commit. Se T001 não achou falta, registrar "captura não necessária" no README e não rodar nada.

**Checkpoint**: todo caso dos testes das fases seguintes tem uma fixture real indicada, ou é derivado dentro do teste a partir de uma fixture real (nunca de rede).

**Commit**: `docs(MUD): inventário das fixtures reais usadas pela MUD` (e, se houver captura, outro commit só com as fixtures).

---

## Fase 2: Fundação (bloqueia todas as histórias)

**Propósito**: peças pequenas de formato e de I/O que todas as histórias usam. Cada tarefa começa pelo teste.

- [X] T003 [P] Em `tests/test_lote.py` escrever os testes da nova coluna: `ultimoStatus_sequencia` obrigatória em `proposicoes-*.csv` (ausente → `formato_alterado` com o nome da coluna e do arquivo) e `Proposicao.ultimo_status_sequencia` inteiro; valor não inteiro, vazio ou menor que 1 → `formato_alterado`. Depois, em `src/monitor_comissoes/lote.py`, acrescentar a coluna **no fim** de `PROPOSICOES_COLUNAS` (os índices de `ler_proposicoes` não podem se deslocar) e o campo `ultimo_status_sequencia: int = 0` **como último campo** de `Proposicao` (o padrão `0` existe só para não quebrar construtores dos testes atuais; `ler_proposicoes` sempre o preenche).
- [X] T004 [P] Em `tests/test_tramitacoes.py` escrever os testes do campo `despacho`: texto da API é lido; `null` ou ausente vira `""`; tipo diferente de texto → `formato_alterado` ("campo despacho"). Depois, em `src/monitor_comissoes/tramitacoes.py`, acrescentar `despacho: str` a `Tramitacao` (**no fim**, com padrão `""`, para os construtores posicionais da REL continuarem valendo; desvio registrado na implementação) e lê-lo com `_texto(..., anulavel=True) or ""`.
- [X] T005 [P] Em `tests/test_status.py` (seção nova, depois dos de `gravar_par`) escrever os testes de `gravar_todos(escritas)`, onde `escritas` é uma lista de pares `(texto, Path)`: (a) substitui todos os destinos; (b) falha ao preparar o k-ésimo temporário (`OSError`) não troca nenhum destino e não deixa temporário; (c) falha na troca do k-ésimo restaura os k−1 já trocados ao conteúdo anterior, **em ordem inversa**, e remove os que não existiam; (d) dupla falha (a troca e a restauração) propaga a **causa original** com uma nota sobre a restauração (como em `test_status.py::test_gravar_par_com_dupla_falha_propaga_a_causa_original_com_nota`); (e) pasta de destino inexistente é criada. Depois implementar `gravar_todos` **em `src/monitor_comissoes/status.py`** (e não em `saida.py`: os `monkeypatch` de `status.escrever_temporario` e `status._restaurar` em `test_diaria.py` e `test_status.py` dependem do módulo) generalizando o algoritmo de `gravar_par` (R8 da pesquisa) e reescrever `gravar_par` como invólucro (serializa os dois documentos e chama `gravar_todos`). Os 5 testes `test_gravar_par_*` e os de `test_diaria.py` continuam passando **sem alteração**. *(Desvio de lugar registrado na implementação.)*
- [X] T006 [P] Em `tests/test_estoque.py` e `tests/test_aceitacao.py` escrever os testes do campo novo do item: `ultimo_status_sequencia` aparece **depois de `ultimo_status_em`** e antes de `parado_ha_dias`; é inteiro positivo; apensado e principal têm o mesmo valor, a mesma `situacao` e o mesmo `ultimo_status_em`; "principal não localizada" usa o valor do próprio item; `meta.versao_formato` é `3`. Depois: em `src/monitor_comissoes/estoque.py` `_item` grava `status.ultimo_status_sequencia` (da referência) e levanta `FalhaDeColeta(INTERNA, ...)` se o valor for menor que 1; em `src/monitor_comissoes/coleta.py` `VERSAO_FORMATO = 3`. Ajustar, uma a uma e com o motivo no commit, os testes existentes que listam os campos do item ou conferem a versão (`tests/test_aceitacao.py`, em torno das linhas 269 e 327, e `tests/test_estoque.py`).
- [X] T007 [P] Em `tests/test_retratos.py` (novo) escrever os testes de `retratos.ler(texto, origem, *, validar_itens=True)`, que devolve `Retrato(documento, dia, gerado_em, dados_camara_em, compativel)` (`validar_itens=False` só confere o `meta`, para o `atual.json` do próprio dia) ou levanta `FalhaDeColeta(INTERNA, "retrato ... inválido (<origem>): <campo>")`. Casos que **falham**: texto que não é JSON; JSON que não é objeto; sem `meta` ou sem `itens`; `meta.versao_formato` não inteiro; `meta.gerado_em` ou `meta.dados_camara_em` ausentes ou sem data e hora ISO válidas **com fuso**; versão 3 com `itens` que não é lista, item que não é objeto, campo exigido ausente ou de tipo errado em qualquer item (`id`, `identificacao`, `link`, `comissao`, `situacao` texto; `etiquetas` lista de textos; `relator` nulo ou objeto com `id` inteiro, `nome` e `partido_hoje` texto; `relator_indeterminado` nulo ou objeto; `apensado_a` nulo ou objeto com `id`; `ultimo_status_sequencia` inteiro ≥ 1) ou `id` repetido. Casos que **passam**: versão 3 válida; versões 1 e 2 com `meta` válido (devolvem `compativel=False` e **não** validam os itens, que podem ter outro formato). `dia` é a data de `gerado_em` em Brasília (um `gerado_em` em outro fuso é convertido). Depois criar `src/monitor_comissoes/retratos.py` com `Retrato` e `ler`.
- [X] T008 [P] Em `tests/test_mudancas.py` (novo) escrever os testes do formato do arquivo (parte 1; `contracts/mudancas-json.md`): `montar_arquivo(...)` produz `meta`, `eventos` e `ressalvas` na **ordem fixa de campos**; `meta.total_por_tipo` sempre com as seis chaves, na ordem `entrou`, `saiu`, `situacao`, `relator`, `parecer`, `etiquetas`; `total_eventos` bate; a serialização usa `saida.serializar` (UTF-8, `ensure_ascii` desligado, indentação de 2 espaços, uma quebra de linha no fim); `validar_arquivo(documento)` aceita um arquivo válido e rejeita cada violação das regras de consistência 1 a 6 do contrato (totais que não batem, linha de base com evento, `motivo` vazio, evento sem `link`, tipo repetido para o mesmo item, tramitações fora de ordem ou repetidas). Depois criar `src/monitor_comissoes/mudancas.py` com: as constantes `TIPOS` (na ordem acima), `CODIGO_PARECER = "322"`, `CODIGO_ARQUIVAMENTO = "502"`, o padrão do art. 105 (`art(igo|\.)?\s*105`, sem diferenciar maiúsculas), a tabela `SITUACOES_FINAIS` (situação → código do motivo, conforme research R2 e o que o mantenedor decidir em D1), `montar_arquivo`, `validar_arquivo` e `ordenar_eventos` (comissão na ordem da configuração, depois tipo, depois `id`).

**Checkpoint**: fundação verde; as histórias podem começar.

**Commit**: um por tarefa (`feat(MUD): coluna ultimoStatus_sequencia`, `feat(MUD): despacho nas tramitações`, `feat(MUD): gravar_todos`, `feat(MUD): ultimo_status_sequencia e formato 3`, `feat(MUD): leitura do retrato`, `feat(MUD): formato do arquivo de mudanças`).

---

## Fase 3: História 3 — O primeiro dia registra a linha de base (P1) 🎯 esqueleto de ponta a ponta

**Objetivo**: o fluxo diário já grava os quatro arquivos, decide o retrato anterior por data e produz a linha de base nos três casos (spec US3; FR-001 a FR-004, FR-019 a FR-021, FR-023). Ainda sem eventos.

**Teste independente**: `tests/test_diaria.py` e `tests/test_retratos.py` com arquivos em `tmp_path`: sem retrato anterior → linha de base "primeiro retrato"; `atual.json` de dia anterior em versão 1 ou 2 → linha de base "formato anterior incompatível" e `anterior.json` idêntico ao antigo.

### Testes (escrever primeiro, ver falhar)

- [X] T009 [P] [US3] Em `tests/test_retratos.py` testar `retratos.preparar(atual, anterior, hoje)` (`hoje` é uma `date` em Brasília) → `Comparacao(anterior, motivo_linha_de_base, retrato_anterior, copia_anterior)`, **uma linha por caso** da tabela de research R5: (1) sem `atual.json` → linha de base "primeiro retrato", sem cópia; (2) `atual.json` de dia anterior, versão 3, válido → `anterior` é ele, `copia_anterior` é o **texto original** do arquivo, byte a byte (inclusive com espaços finais), sem reserializar; (3) dia anterior, versão 1 ou 2 → linha de base "formato anterior incompatível", `retrato_anterior` preenchido (informativo), `copia_anterior` com o texto; (4) dia anterior ilegível ou fora do contrato → `FalhaDeColeta(INTERNA)` com o nome do arquivo; (5) `atual.json` de hoje e `anterior.json` válido de versão 3 → `anterior` é a cópia, sem rotação; (6) `atual.json` de hoje e `anterior.json` ausente → "primeiro retrato"; (7) `atual.json` de hoje e `anterior.json` ilegível → `FalhaDeColeta(INTERNA)`; (8) `atual.json` de hoje com `meta` legível mas `itens` estragados, com `anterior.json` válido → **não** falha (será sobrescrito); `atual.json` sem `meta` legível (JSON inválido, sem `gerado_em`) → `FalhaDeColeta(INTERNA)`, porque o dia dele não se pode saber; (9) `atual.json` de data futura → `FalhaDeColeta(INTERNA)` ("de data futura"); (10) `anterior.json` de versão antiga na reexecução do dia → "formato anterior incompatível", sem rotação.
- [X] T010 [P] [US3] Em `tests/test_mudancas.py` testar `comparar(...)` sem retrato anterior: devolve o arquivo de **linha de base** (`meta.linha_de_base = {motivo, total_itens}`, `eventos` e `ressalvas` vazios, `total_eventos` 0) para os dois motivos; `meta.retrato_anterior` é `null` em "primeiro retrato" e preenchido em "formato anterior incompatível"; a função de tramitações injetada **não é chamada** (uma função que levanta se chamada); `meta.data` é a data da execução e `meta.retrato` traz `dia` e `dados_camara_em` do documento de hoje; nenhum horário de execução aparece no arquivo.
- [X] T011 [US3] Em `tests/test_diaria.py` (ler antes os auxiliares existentes e seguir o estilo) testar `executar_diaria` com `anterior=` e `mudancas=`: (a) primeiro dia grava `atual.json`, `status.json` e `mudancas/AAAA-MM-DD.json` e **não** cria `anterior.json`; a linha `OK:` termina com `mudanças: linha de base (primeiro retrato)`; (b) `atual.json` de dia anterior em versão 2 → `anterior.json` fica com o texto idêntico ao antigo e o arquivo do dia traz o motivo "formato anterior incompatível"; (c) a data do arquivo é a da execução em Brasília; (d) `meta.versao_formato` do `atual.json` novo é 3; (e) em falha da coleta só o `status.json` é gravado e a pasta de mudanças não é criada.
- [X] T012 [P] [US3] Em `tests/test_workflow.py` ajustar, de propósito e uma a uma, as asserções textuais do passo "Coleta e commit" ao contrato (`contracts/execucao-diaria.md`): em falha, restaurar com `git checkout -- <caminho> || true` **por caminho** (`data/atual.json`, `data/anterior.json`, `data/mudancas`) e remover o arquivo novo com `git clean -fdq -- data/mudancas`; em sucesso, `git add data/atual.json`, `git add data/mudancas` e `[ -e data/anterior.json ] && git add data/anterior.json`; `git add data/status.json` continua antes do `if` e incondicional. Em `tests/test_workflow_script.py` estender o Python falso (`FAKE_MODO` `ok` grava também `data/mudancas/2000-01-01.json` e, quando `FAKE_ROTACIONA` está definido, `data/anterior.json`; `falha` pode sujar os quatro) e acrescentar: sucesso no primeiro dia (sem `anterior.json`) commita `atual`, `status` e `mudancas` sem tropeçar no `git add`; sucesso com rotação commita os quatro; falha restaura `atual.json` e `anterior.json`, descarta o arquivo de mudanças novo e commita só o `status.json`; falha com um arquivo de mudanças **já rastreado** do mesmo dia o restaura.

### Implementação

- [X] T013 [US3] Implementar `retratos.preparar` e `Comparacao` em `src/monitor_comissoes/retratos.py` conforme a tabela de research R5 e `data-model.md` (T009).
- [X] T014 [US3] Em `src/monitor_comissoes/mudancas.py` implementar `comparar(comparacao, documento_hoje, estados_de_saida, obter_tramitacoes, comissoes, hoje)`, nesta fase só o ramo da linha de base (T010); o ramo com retrato anterior levanta `NotImplementedError` até a Fase 4. `meta.retrato.dados_camara_em` e `dia` vêm de `documento_hoje["meta"]`; **nenhum** campo de horário de execução.
- [X] T015 [US3] Em `src/monitor_comissoes/coleta.py`: `coletar(config, transporte, agora, comparacao=None)` devolve em `Coletado` também `mudancas` (o documento do dia, ou `None` quando `comparacao` é `None`). O comando da COL (`executar`, em `cli.py`) continua sem comparação e sem mudança de comportamento.
- [X] T016 [US3] Em `src/monitor_comissoes/diaria.py`: opções `--anterior` (padrão `data/anterior.json`) e `--mudancas` (padrão `data/mudancas`); em **cada tentativa**, depois de `agora = relogio()`, chamar `retratos.preparar(atual, anterior, agora_em_brasilia.date())` e passar a `Comparacao` a `coletar`; gravar com `saida.gravar_todos` na ordem `atual.json`, `anterior.json` (só se `copia_anterior` não for `None`), arquivo de mudanças, `status.json`; a linha `OK:` ganha o resumo da comparação (`contracts/execucao-diaria.md`). Falha continua gravando só o `status.json` (`_registrar_falha` não muda). T011 passa.
- [X] T017 [US3] Em `.github/workflows/coleta-diaria.yml` aplicar as mudanças do passo "Coleta e commit" descritas em `contracts/execucao-diaria.md` (T012). Nada mais no workflow muda. Acrescentar também ao `.gitignore` a linha `data/**/*.tmp` (os temporários de `gravar_todos` ficam ao lado de cada destino, inclusive em `data/mudancas/`), com um teste simples em `tests/test_workflow.py` que lê o `.gitignore`.

**Checkpoint**: o fluxo diário grava os quatro arquivos e produz a linha de base; `uv run pytest` verde.

**Commit**: `feat(MUD): preparar o retrato anterior e a rotação`, `feat(MUD): linha de base e gravação dos quatro arquivos`, `feat(MUD): workflow commita anterior.json e mudancas`.

---

## Fase 4: História 1 — O que entrou e o que saiu, e por quê (P1)

**Objetivo**: eventos `entrou` e `saiu` com motivo e destino (spec US1; FR-005 a FR-007, FR-013, FR-016).

**Teste independente**: `tests/test_mudancas.py` com dois retratos sintéticos derivados do `data/atual.json` real, estados de saída montados de linhas reais do lote e tramitações reais salvas.

### Testes (escrever primeiro, ver falhar)

- [X] T018 [P] [US1] Em `tests/test_estoque.py` testar `estado_de_saida(id, linhas, mapa_principal, comissoes)` → `EstadoDeSaida(existe, referencia_id, orgao, situacao, sequencia, apensado_a, na_comissao)` (`data-model.md`) com **linhas reais do lote** (T001 (e)): apensado a uma principal na CFT → `apensado_a` preenchido, `orgao` "CFT", `na_comissao` falso; `Transformado em Norma Jurídica`; `Aguardando Apreciação pelo Senado Federal`; referência que continua na CE/CREDN → `na_comissao` verdadeiro; id ausente de `linhas` → `existe` falso e demais campos `None`; cadeia com "principal não localizada" usa o próprio item.
- [X] T019 [P] [US1] Em `tests/test_mudancas.py` testar o evento **`entrou`**: (a) chegada à comissão em data igual ou posterior à data de `dados_camara_em` do retrato anterior → `chegou_a_comissao`, com as tramitações da chegada (regra de data, research R7); (b) chegada anterior e item com etiqueta → `ganhou_etiqueta`, e o `texto` diz qual ("ganhou etiqueta: autor hoje no NOVO"); (c) chegada anterior e item sem etiqueta (candidato com relator indeterminado) → `nao_determinado`; (d) chegada **no mesmo dia** do corte conta como posterior (janela de um dia, D5 do plano); (e) o evento traz `etiquetas` de hoje, `comissao` de hoje e o `link` da ficha; (f) tramitações lidas só até a sequência de hoje; (g) a "chegada" é o **início da passagem mais recente** pela comissão (uma matéria que saiu e voltou usa a volta); (h) uma ida e volta pela MESA, CCP ou PLEN (por exemplo, "Notificação de Apensação" na MESA e novo "Recebimento" na CE) **não** é chegada nova; testar também `relatoria.inicio_da_passagem` diretamente com tramitações reais (T001 (d)), em `tests/test_relatoria.py`.
- [X] T020 [P] [US1] Em `tests/test_mudancas.py` testar o evento **`saiu`**, um teste por código de `motivo` (`contracts/mudancas-json.md`): `arquivado_art_105` com a tramitação **real** `502` de 2086175 (sequência 42); `arquivado` com a mesma tramitação com o `despacho` trocado dentro do teste; `transformado_em_norma`; `aprovado_segue_ao_senado`; `encerrado` (um exemplo do grupo, conforme D1); `apensado_fora_da_lista` (raiz diferente da do retrato anterior e fora dos itens de hoje); `outro_orgao` com `destino.orgao`; `perdeu_etiquetas` (referência ainda na comissão; o `texto` lista as etiquetas que tinha); `nao_determinado` com `existe` falso (`destino.orgao` e `destino.situacao` nulos). Mais: **precedência** (situação final > apensado fora > outro órgão > perdeu etiquetas) e `outros_fatos` com os demais códigos que valiam, na ordem; `comissao` do evento é a do retrato anterior; as tramitações do intervalo (sequência: anterior < s ≤ hoje, na mesma referência; data, se a referência mudou) acompanham o evento; uma situação fora da tabela de situações finais cai em `outro_orgao`, sem erro; quando a **principal** sai da comissão, cada apensado que estava na lista tem o seu `saiu` com o mesmo motivo e o mesmo destino da principal (spec, caso de borda "Principal arquivada ou saída da principal").
- [X] T021 [US1] Em `tests/test_diaria.py` (ou `tests/test_aceitacao.py`) um teste de ponta a ponta com transporte falso: lote e tramitações salvos, `atual.json` de ontem sintético (versão 3) com um item a mais e um a menos que o real; o arquivo do dia contém um `entrou` e um `saiu` com os motivos esperados e passa em `validar_arquivo`; a linha `OK:` termina com `mudanças: 2 eventos (1 entrou, 1 saiu)`.

### Implementação

- [X] T022 [US1] Em `src/monitor_comissoes/estoque.py` criar `EstadoDeSaida` e `estado_de_saida` reaproveitando `resolver_referencia` (T018).
- [X] T023 [US1] Em `src/monitor_comissoes/coleta.py`: quando `comparacao.anterior` existe, acrescentar os ids do retrato anterior (e as raízes das cadeias deles, por `subir_ate_a_raiz`) ao conjunto `necessarias` — sem alterar `examinar` nem `candidatas`, que continuam decidindo a lista —, montar `EstadoDeSaida` para os que não estão nos itens de hoje, e criar `obter_tramitacoes_cacheado(id)` (um dicionário por execução, chamando `tramitacoes.obter_tramitacoes`) para passar a `comparar`. Nada disso é feito quando não há `comparacao`.
- [X] T024 [US1] Em `src/monitor_comissoes/mudancas.py` implementar o intervalo de tramitações (regra de sequência para a mesma referência, regra de data para referência diferente ou item que entrou ou saiu; exige a sequência de hoje na resposta), a chegada à comissão (R7; acrescentar `inicio_da_passagem` a `src/monitor_comissoes/relatoria.py`, compartilhando `_comissoes` e o laço de passagens com `relator_atual`, sem mudar o resultado de `relator_atual`), `entrou` e `saiu` com precedência, `destino`, `outros_fatos` e o texto dos motivos (T019, T020). `art. 105`: tramitação de código `502` no intervalo cujo `despacho` casa com o padrão (R3). Fazer T021 passar. **Remover o `xfail(strict=True)`** de `tests/test_diaria.py::test_a_data_de_referencia_muda_na_virada_do_dia_de_brasilia` (marcado na Fase 3 porque roda dois dias seguidos e precisa desta comparação) e confirmar que ele passa.

**Checkpoint**: entram e saem itens com motivo; `uv run pytest` verde.

**Commit**: `feat(MUD): estado de quem saiu a partir do lote`, `feat(MUD): eventos entrou e saiu com motivo e destino`.

---

## Fase 5: História 2 — O que mudou nos itens que continuam (P1)

**Objetivo**: eventos `situacao`, `relator`, `parecer` e `etiquetas`, com todas as tramitações do intervalo (spec US2; FR-008 a FR-014, FR-016).

**Teste independente**: `tests/test_mudancas.py` com retratos sintéticos que diferem em um campo por vez.

### Testes (escrever primeiro, ver falhar)

- [X] T025 [P] [US2] Em `tests/test_mudancas.py` testar `situacao` (de → para, texto exato), `relator` (`designado`, `devolveu`, `substituido`, com `de` e `para` com `id`, `nome` e `partido_hoje`; mesmo relator = sem evento) e `etiquetas` (`ganhou`, `perdeu`, ambos no mesmo item; ordem fixa `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO`). Um item com várias mudanças gera **um evento por tipo**, sem fundir; um item sem diferença não gera nada.
- [X] T026 [P] [US2] Em `tests/test_mudancas.py` testar `parecer`: tramitação real `322` (proposição 2330962) no intervalo e com `orgao` igual à `comissao` do item sintético → um evento, com o `link` da ficha e as tramitações; duas `322` no intervalo → **um** evento com as duas em `tramitacoes`; `322` de outro órgão, `501`, `330` e `336` → nenhum evento; `322` fora do intervalo (sequência ≤ anterior ou > hoje) → nenhum evento.
- [X] T027 [P] [US2] Em `tests/test_mudancas.py` testar o **intervalo de tramitações** (FR-014, FR-017): sequência anterior 41 e de hoje 43 → só 42 e 43, em ordem de `sequencia` mesmo com a resposta embaralhada; a API devolve também 44 e 45 (lançadas depois do lote) → **não** entram; sequência igual nos dois retratos → a função de tramitações **não é chamada** para o item; apensado e principal (mesma referência) → uma só leitura; referência diferente → regra de data (research R6).
- [X] T028 [P] [US2] Em `tests/test_mudancas.py` testar `ressalvas`: relator indeterminado só no retrato anterior, só no de hoje e nos dois → **nenhum** evento de relator e uma ressalva com o `motivo` correspondente ("relator indeterminado ontem", "... hoje", "... nos dois retratos"); a marca em si não vira evento; os demais eventos do item continuam.

### Implementação

- [X] T029 [US2] Em `src/monitor_comissoes/mudancas.py` implementar a comparação dos itens presentes nos dois retratos conforme a tabela de `data-model.md` ("Itens nos dois retratos"): `situacao`, `relator`, `parecer` (código `322` no órgão da comissão, D4), `etiquetas`, as `ressalvas` e a leitura de tramitações **só** para itens cuja referência mudou ou cuja `ultimo_status_sequencia` mudou. Fazer T025 a T028 passarem.
- [X] T030 [US2] Em `tests/test_aceitacao.py` acrescentar o caso de ponta a ponta de um item que continua na lista com situação e relator novos, passando pelo `executar_diaria` com transporte falso e tramitações reais; o arquivo do dia passa em `validar_arquivo` e traz um evento de cada tipo esperado; a linha `OK:` mostra a contagem por tipo no formato de `contracts/execucao-diaria.md`.

**Checkpoint**: os seis tipos de evento funcionam; `uv run pytest` verde.

**Commit**: `feat(MUD): eventos de situação, relator, parecer e etiquetas`, `feat(MUD): ressalvas de relator indeterminado`.

---

## Fase 6: História 4 — Resultado repetível e que cobre os dias sem retrato (P1)

**Objetivo**: reexecutar no mesmo dia dá o mesmo arquivo; o dia perdido é coberto (spec US4; FR-001, FR-004, FR-017, FR-020, FR-022).

**Teste independente**: `tests/test_diaria.py` com duas execuções seguidas e com um `atual.json` de dois dias antes.

### Testes (escrever primeiro, ver falhar)

- [X] T031 [US4] Em `tests/test_diaria.py` testar: (a) execução 1 (retrato anterior de ontem, com mudanças) e execução 2 **depois de o `atual.json` do dia ter sido gravado** → `data/mudancas/AAAA-MM-DD.json` idêntico byte a byte, `anterior.json` idêntico ao da execução 1 (não rotacionou de novo), eventos não duplicados; (b) execução 2 com lote **mais novo** (`dados_camara_em` maior) → o arquivo reflete a comparação contra o **mesmo** retrato anterior, e `meta.retrato.dados_camara_em` muda; (c) `atual.json` de **dois dias antes** → `meta.retrato_anterior.dia` é o de anteontem, o intervalo é coberto e as tramitações vêm do intervalo todo; (d) tramitações lançadas depois do lote (sequências acima da de hoje) em duas execuções com respostas diferentes da API → arquivos idênticos; (e) a ordem dos itens de entrada embaralhada → eventos na mesma ordem (comissão da configuração, tipo, `id`); (f) **encadeamento de dois dias**: o dia 1 grava a linha de base, o dia 2 (com o `atual.json` do dia 1 em versão 3, alterado) usa esse retrato como anterior e gera eventos normalmente (spec, User Story 3, cenário 3).
- [X] T032 [P] [US4] Em `tests/test_mudancas.py` testar `ordenar_eventos` com comissão fora da configuração (depois das da configuração, por sigla) e `id` como desempate, e que `comparar` é função pura: duas chamadas com as mesmas entradas dão documentos iguais.

### Implementação

- [X] T033 [US4] Corrigir o que T031 e T032 mostrarem (esperado: ordem determinística, uso da data de `dados_camara_em` e nenhuma dependência de horário de execução), sem criar mecanismo novo além do já previsto em research R5 e R6. *(Resultado: os testes passaram sem mudança de código; as Fases 3 e 4 já tinham a ordem determinística, a data de `dados_camara_em` e o limite pela sequência de hoje.)*

**Checkpoint**: repetibilidade e dia perdido verdes.

**Commit**: `teste(MUD): repetibilidade e dia sem retrato`.

---

## Fase 7: História 5 — Falhar de forma visível (P1)

**Objetivo**: nenhuma falha deixa arquivo pela metade nem passa por "nada mudou" (spec US5; FR-003, FR-018, FR-019; constituição, III).

**Teste independente**: `tests/test_mudancas_falhas.py` (novo) comparando os quatro arquivos antes e depois, byte a byte.

### Testes (escrever primeiro, ver falhar)

- [X] T034 [US5] Em `tests/test_mudancas_falhas.py` (novo), cada cenário confere: código de saída 1, mensagem que diz o motivo e o arquivo ou a proposição, e `atual.json`, `anterior.json` e `data/mudancas/` **idênticos byte a byte** (só o `status.json` muda, com a categoria): (a) erro de rede ou HTTP nas tramitações → `fonte_indisponivel`, e a execução repete como a REL; (b) tramitações malformadas (JSON inválido, `dados` vazio, sequência repetida, campo ausente) → `formato_alterado`; (c) resposta sem a tramitação de sequência igual à do lote de hoje → `formato_alterado` ("a sequência N do lote não existe"); (d) sequência de hoje **menor** que a do retrato anterior para a mesma referência → `formato_alterado`; (e) `atual.json` de dia anterior corrompido → `interna`, **sem repetir**; (f) `anterior.json` corrompido na reexecução do dia → `interna`; (g) `atual.json` de data futura → `interna`; (h) falha ao gravar o k-ésimo dos quatro arquivos (`OSError` simulado, para cada k) → nenhum dos quatro muda e nenhum temporário sobra; (i) falha da coleta antes da comparação → nenhum arquivo de mudanças é gravado.
- [X] T035 [P] [US5] Em `tests/test_mudancas_falhas.py` testar que um retrato anterior corrompido **nunca** vira linha de base em silêncio (o arquivo de mudanças do dia não existe depois da falha) e que a categoria e o motivo ficam no `status.json` (`falha.categoria`, `falha.motivo`).

### Implementação

- [X] T036 [US5] Corrigir o que T034 e T035 mostrarem: levantar `FalhaDeColeta` com as categorias de `contracts/execucao-diaria.md` em `retratos.py`, `mudancas.py` e `coleta.py`; garantir que a comparação roda **dentro** do laço de novas tentativas da coleta, e que `diaria.py` só grava depois de a comparação e a validação do arquivo (`validar_arquivo`) terem passado. *(Resultado: sem mudança de código; `preparar` e `coletar` já rodam dentro do laço de tentativas, e `coletar` valida o arquivo antes de devolvê-lo.)*

**Checkpoint**: todas as falhas do contrato verdes.

**Commit**: `feat(MUD): falhas visíveis da comparação e gravação atômica`.

---

## Fase 8: História 6 — Conferível item a item e testável sem rede (P2)

**Objetivo**: cada evento aponta para a fonte oficial e nenhum teste usa a rede (spec US6; FR-013, FR-024).

- [ ] T037 [P] [US6] Ler `tests/test_sem_rede.py` e fazer a guarda cobrir os módulos novos (`retratos.py`, `mudancas.py`) da mesma forma que cobre os existentes; confirmar que os testes novos rodam com a guarda de rede do `conftest.py` ativa.
- [ ] T038 [P] [US6] Em `tests/test_mudancas.py` acrescentar um teste parametrizado que gera o arquivo a partir de todos os cenários das Fases 4 e 5 e confere, com `validar_arquivo`, que **todo** evento tem `link` iniciado por `https://www.camara.leg.br/propostas-legislativas/`, `motivo` não vazio (nos tipos que o têm) e `tramitacoes` em ordem de `sequencia`.

**Checkpoint**: conformidade de rastreabilidade e de testes sem rede.

**Commit**: `teste(MUD): rastreabilidade dos eventos e guarda de rede`.

---

## Fase 9: Acabamento e verificação

**Propósito**: registrar as regras, conferir os casos de aceitação do roadmap e rodar a verificação completa.

- [ ] T039 Registrar no `PRODUCT.md` §5.6, em **commit próprio** (o mantenedor revisa o diff), as regras que hoje só existem na spec e no plano (D6): linha de base com motivo; retrato anterior por data e a cópia rotativa; precedência dos motivos de saída; tabela de situações finais (conforme a decisão D1); intervalo das tramitações e seu limite superior; janela de um dia da entrada; arquivo do dia sem teto de eventos. Nenhuma regra existente muda de sentido; se alguma coisa parecer mudar, parar e perguntar.
- [ ] T040 [P] Registrar em `docs/fontes.md` os fatos de API conferidos: tipos `322` e `502`, o campo `despacho` das tramitações e o texto "Arquivado nos termos do Artigo 105", a lista oficial de situações (`/referencias/proposicoes/codSituacao`, 99 entradas em 18/10/2026) e a coluna `ultimoStatus_sequencia` do lote.
- [ ] T041 [P] Atualizar `tests/fixtures/camara/README.md` com o que é real e o que é derivado dentro do teste nos casos da MUD.
- [ ] T042 Rodar a verificação completa e mostrar a saída: `uv run ruff check . && uv run ruff format --check . && uv run pytest`. Corrigir o que aparecer, com commits pequenos.
- [ ] T043 Conferir os casos de aceitação do `ROADMAP.md` para a MUD, um a um, indicando o teste que cobre cada um: (1) `data/mudancas/AAAA-MM-DD.json` lista entrou, saiu (com motivo e destino), situação, relator, parecer e etiquetas, com todas as tramitações desde o retrato anterior (T020, T025 a T027, T030); (2) o primeiro dia registra "linha de base" (T010, T011); (3) motivo "arquivado, art. 105" (T020); (4) testes com retratos sintéticos (todos). Conferir o "Não inclui" (envio, página): nenhum módulo de Telegram, HTML ou teto de eventos foi criado (`git diff --stat` contra a base).
- [ ] T044 Roteiro manual da seção 2 do `quickstart.md` (precisa de rede, cerca de 1 GB) — **a executar pelo mantenedor ou com o OK dele**; registrar o resultado no relatório final, **inclusive o tempo medido da execução** contra a meta do plano (menos de 2 minutos a mais em dia comum). Não faz parte da suíte.

**Não fazer nesta feature**: alterar a coluna Status do `ROADMAP.md` para `concluída`. Isso só acontece depois da verificação completa, dos casos de aceitação **e do OK do mantenedor com o merge** (CLAUDE.md). Já está `em andamento`.

---

## Dependências e ordem de execução

- **Fase 1** → **Fase 2** (T003 a T008 em paralelo entre si, exceto que T006 e T008 tocam `estoque.py`/`coleta.py` e `mudancas.py` respectivamente: sem conflito).
- **Fase 3** depende da Fase 2 (usa `retratos.ler`, `gravar_todos`, `montar_arquivo`, formato 3). T009 a T012 (testes) em paralelo; T013 → T014 → T015 → T016; T017 depende de T012.
- **Fase 4** depende da Fase 3 (T024 completa o ramo que T014 deixou) e da decisão D1 (tabela de situações).
- **Fase 5** depende da Fase 4 (reaproveita o intervalo de tramitações de T024).
- **Fase 6** e **Fase 7** dependem das Fases 4 e 5; podem andar em paralelo entre si.
- **Fase 8** depende das Fases 4 e 5.
- **Fase 9** depende de todas; T039 e T040 podem começar assim que D1 e D5 estiverem decididas.

## Oportunidades de paralelismo

- Fase 2: T003, T004, T005, T006, T007, T008 (arquivos diferentes).
- Fase 3: T009, T010, T012 (testes); depois T013 e T014 em paralelo; T015 a T017 em sequência.
- Fase 4: T018, T019, T020 (testes em arquivos/seções diferentes).
- Fase 5: T025 a T028 (testes).
- Fase 9: T040 e T041.

## Estratégia de implementação

1. Fases 1 e 2: fixtures conferidas e a fundação (formato 3, `gravar_todos`, retrato, formato do arquivo).
2. **Fase 3 (esqueleto):** já entrega o fluxo diário de ponta a ponta com a linha de base. É o primeiro marco verificável e o que o primeiro dia real do Actions vai exercitar.
3. Fases 4 e 5: preencher a comparação (entrou/saiu, depois os outros quatro tipos).
4. Fases 6 e 7: provar repetibilidade, dia perdido e falhas.
5. Fases 8 e 9: rastreabilidade, documentação e verificação completa.
6. Cada fase fecha com a verificação completa verde e commits pequenos, sem push.

## Totais

44 tarefas: Fase 1: 2 · Fase 2: 6 · Fase 3 (US3): 9 · Fase 4 (US1): 7 · Fase 5 (US2): 6 · Fase 6 (US4): 3 · Fase 7 (US5): 3 · Fase 8 (US6): 2 · Fase 9: 6. Testes são escritos antes da implementação em cada fase; a única tarefa que pode usar rede é T002 (e só se o inventário T001 achar falta); T044 é conferência manual fora da suíte.
