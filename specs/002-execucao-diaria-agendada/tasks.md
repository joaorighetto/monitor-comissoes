---

description: "Tarefas da feature AGE — Execução diária agendada"
---

# Tasks: AGE — Execução diária agendada

**Input**: `specs/002-execucao-diaria-agendada/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Prerequisites**: nenhuma tarefa precisa de rede. As fixtures reais da COL (`tests/fixtures/camara/`) já estão no repositório. A verificação real do workflow no GitHub (quickstart, passos 4 a 6) só é possível **depois do merge** e fica fora destas tarefas; ela é o passo 6 do fluxo (fechar).

**Tests**: **solicitados** (constituição, princípio IV; pedido do mantenedor: "as tarefas começam pelos testes: fixtures salvas e nenhum teste com rede"). Em cada fase, os testes vêm antes da implementação e devem **falhar** antes dela. O guarda `sem_rede` de `tests/conftest.py` vale para todos.

**Organization**: por história de usuário da spec. As fases 1 e 2 são a base comum. Os módulos citados estão em `src/monitor_comissoes/`. O comando da COL e o formato do `atual.json` **não mudam**: os testes existentes da COL continuam passando sem alteração.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência entre si)
- **[Story]**: US1 a US6, conforme `spec.md`
- Verificação completa: `uv run ruff check . && uv run ruff format --check . && uv run pytest`

## Phase 1: Setup

**Purpose**: constantes e configuração que as demais fases usam. Nenhuma lógica nova.

- [X] T001 Em `src/monitor_comissoes/erros.py`, acrescentar as categorias `ESTOQUE_IMPLAUSIVEL = "estoque_implausivel"` e `INTERNA = "interna"`, incluí-las em `CATEGORIAS` (agora nove) e criar `REPETIVEIS = (FONTE_INDISPONIVEL, ARQUIVOS_DESATUALIZADOS, ARQUIVO_INCOMPLETO, API_DEPUTADOS)`. Não repetem: `configuracao`, `formato_alterado`, `estoque_vazio`, `estoque_implausivel` e `interna` (research.md R6; `estoque_vazio` é decisão do plano, a ser refletida no FR-020 pelo `/speckit-analyze`). Não alterar `FalhaDeColeta`.
- [X] T002 [P] Em `config.toml`, acrescentar a tabela `[execucao]` com `tentativas = 4`, `espera_minutos = 30` e `limite_variacao_percentual = 20`, com um comentário por campo ("coletas por execução, contando a primeira"; "espera entre tentativas, em minutos"; "variação do estoque bruto acima da qual a execução falha, em %"). Os valores são os padrões de [data-model.md](data-model.md).

---

## Phase 2: Foundational (bloqueia todas as histórias)

**Purpose**: configuração nova, contagem do estoque bruto, divisão `coletar`/`executar` da COL e o módulo `status`, que as seis histórias usam.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase.

### Testes (escrever primeiro; devem falhar)

- [X] T003 [P] Em `tests/test_config.py`, acrescentar os casos de `[execucao]`: sem a tabela, valem os padrões (4, 30, 20) e um `config.toml` só com os campos da COL continua válido; tabela completa é lida; `execucao.tentativas` "Entre 1 e 10" (0 e 11 falham; 1 e 10 passam); `execucao.espera_minutos` "Entre 0 e 120" (-1 e 121 falham; 0 e 120 passam); `execucao.limite_variacao_percentual` "Entre 1 e 100" (0 e 101 falham; 1 e 100 passam); valor que não é inteiro (texto, decimal, booleano) falha; chave desconhecida em `[execucao]` falha. Cada falha é `FalhaDeColeta` de categoria `configuracao` com mensagem que nomeia o campo (por exemplo `execucao.tentativas`). O teste `test_config_do_repositorio_e_valida` já existente cobre o `config.toml` real, incluindo T002.
- [X] T004 [P] Escrever `tests/test_estoque_bruto.py`: (a) `contar_estoque_bruto` sobre um CSV sintético em `tmp_path`, com o cabeçalho completo das fixtures: conta PL e PLP cujo `ultimoStatus_siglaOrgao` está em `comissoes`; **não** conta REQ nem PDL na comissão, nem PL em outro órgão; conta um apensado pelo **próprio** órgão, ignorando a raiz; um arquivo sem linhas de dados devolve 0; (b) sobre as fixtures reais, o total de `coletar` é igual ao total contado de forma independente no próprio teste, lendo com `csv` os 24 arquivos `proposicoes-2003.csv` a `proposicoes-2026.csv` (`;`, `utf-8-sig`) e contando `siglaTipo` em `PL`/`PLP` com `ultimoStatus_siglaOrgao` em `CE`/`CREDN`; (c) `coletar(config, transporte, agora)` devolve documento (`meta` + `itens`) **idêntico** ao que `executar` grava, e **não cria arquivo nenhum**; `executar` continua gravando o mesmo arquivo de antes (comparar com o resultado de `coletar` serializado por `saida.serializar`).
- [X] T005 [P] Escrever `tests/test_status.py`: (a) `montar_status` de sucesso traz exatamente os campos de [contracts/status-json.md](contracts/status-json.md), na ordem fixa, com `falha = null`, `variacao_aceita = null` e `ultimo_retrato_bom` com `gerado_em`, `dados_camara_em`, `total_itens` e `estoque_bruto`; (b) de falha traz `falha = {"categoria", "motivo"}`, `variacao_aceita = null` e o retrato mantido; (c) `data_referencia` é a data de Brasília de `verificado_em`, inclusive perto da meia-noite (23h50 de Brasília, que já é o dia seguinte em UTC); (d) mesma entrada e mesmo relógio geram texto idêntico byte a byte; (e) um status de sucesso gerado depois de um de falha não carrega resto da falha; (f) `retrato_do_atual` lê `gerado_em`, `dados_camara_em` e `total_itens` do `meta` do `atual.json`, e devolve `None` se o arquivo não existir ou não tiver um `meta` válido (por exemplo `{"sentinela": true}`) **sem alterá-lo**; (g) `base_de_comparacao` devolve o `estoque_bruto` do status anterior só se o `gerado_em` do status for igual ao `meta.gerado_em` do `atual.json` em disco, e `None` se forem diferentes, se faltar um dos dois arquivos ou se o status for inválido; (h) `ler_status` devolve `None` para arquivo ausente e levanta erro claro para JSON inválido ou invariante violado ("`resultado = "ok"` ⇒ `falha = null` e `ultimo_retrato_bom ≠ null`"; "`resultado = "falha"` ⇒ `falha ≠ null`, `variacao_aceita = null`"); (i) `mensagem_commit` produz as três mensagens da tabela "Mensagem do commit" de [data-model.md](data-model.md), com o `±X,X%` com vírgula decimal; (j) `gravar_par(atual, status)` substitui os dois destinos em caso de sucesso; se a **preparação** do segundo temporário falhar (simulada com `monkeypatch`, que levanta `OSError`), **nenhum** destino é trocado (ambos idênticos byte a byte ao anterior) e nenhum `.tmp` sobra; `gravar_status` sozinho grava só o status.

### Implementação

- [X] T006 Em `config.py`, estender `Config` com `tentativas: int = 4`, `espera_minutos: int = 30` e `limite_variacao_percentual: int = 20` (valores padrão, para que `Config(comissoes=..., ano_minimo=...)` dos testes existentes continue válido) e ler a tabela opcional `[execucao]` aplicando literalmente as regras de T003, inclusive a recusa de chave desconhecida e de booleano como inteiro (T003 passa).
- [X] T007 Em `lote.py`, implementar `contar_estoque_bruto(caminho: Path, tipos: tuple[str, ...], comissoes: tuple[str, ...]) -> int`, em fluxo, lendo só `siglaTipo` e `ultimoStatus_siglaOrgao` com o `_linhas` existente (research.md R3).
- [X] T008 Em `coleta.py`, dividir `executar` (research.md R4): criar `Coletado` (dataclass congelada com `documento: dict`, `estoque_bruto: int` e `dados_camara_em: datetime`) e `coletar(config, transporte, agora) -> Coletado`, com todo o corpo atual **menos** a gravação, acrescentando, ainda dentro do diretório temporário, a soma de `contar_estoque_bruto(lote.proposicoes(ano), TIPOS, config.comissoes)` sobre todos os anos. `executar` passa a chamar `coletar`, gravar com `gravar_atomico` e devolver o mesmo `Resultado` de antes. A mensagem, a categoria `estoque_vazio` para lista vazia e o contrato da linha de comando da COL não mudam (T004 passa; todos os testes da COL seguem verdes sem edição).
- [X] T009 Criar `status.py` com `RetratoBom` (`NamedTuple` de quatro campos), `retrato_do_atual`, `base_de_comparacao`, `montar_status`, `ler_status`, `gravar_status` (reaproveita `saida.gravar_atomico` e `saida.serializar`), `gravar_par(atual, status)` (prepara os dois temporários com `fsync` e só então faz os dois `os.replace`, o `atual.json` primeiro; limpa os temporários em qualquer exceção) e `mensagem_commit`, conforme [contracts/status-json.md](contracts/status-json.md) e [data-model.md](data-model.md). Sem I/O de rede e sem relógio interno: `verificado_em` entra como parâmetro. Citar nos comentários as invariantes literais do contrato (T005 passa).

**Checkpoint**: configuração, estoque bruto, `coletar` e `status` funcionam, estão testados e a COL segue intacta.

---

## Phase 3: User Story 1 — Todo dia, o retrato do dia fica versionado (Priority: P1) 🎯 MVP

**Goal**: uma execução bem-sucedida grava `atual.json` e `status.json`, e o workflow os commita juntos, mesmo sem mudança na lista (FR-001 a FR-004, FR-010 a FR-012).

**Independent Test**: simular a execução sobre as fixtures e conferir os dois arquivos, a linha de saída e a mensagem; conferir por texto que o workflow tem o agendamento, o disparo manual e o commit do bot.

### Testes (escrever primeiro; devem falhar)

- [X] T010 [P] [US1] Escrever `tests/test_diaria.py` (parte do caminho feliz), chamando `main(["executar", ...], transporte=..., relogio=..., dormir=...)` com as fixtures: sucesso grava `atual.json` **idêntico** ao que `executar` da COL grava para as mesmas fixtures e relógio, e `status.json` com `resultado = "ok"`, `tentativas = 1`, `falha = null` e `ultimo_retrato_bom` igual ao `meta` do `atual.json` mais o `estoque_bruto`; sai com 0 e imprime em `stdout` `OK: N itens · estoque bruto B · tentativas 1 · dados da Câmara de DD/MM/AAAA`; sem `data/` prévia (primeiro dia), a pasta é criada e os dois arquivos existem; lista idêntica à do dia anterior ainda grava os dois arquivos, e ao menos `gerado_em` e `verificado_em` mudam; duas execuções com o mesmo relógio geram os dois arquivos idênticos byte a byte; o resultado de `mensagem` para o status de sucesso é `dados: AAAA-MM-DD · ok · N itens · estoque bruto B`; `mensagem` com status ausente ou inválido sai com 1 e escreve em `stderr`.
- [X] T011 [P] [US1] Escrever `tests/test_workflow.py` (parte do US1), **textual**, lendo `.github/workflows/coleta-diaria.yml` como texto: contém `cron: "37 6 * * *"`; contém `workflow_dispatch` com a entrada `aceitar_variacao`; **não** contém gatilho `push` nem `pull_request`; contém `permissions:` com `contents: write` e nenhum outro escopo; contém `timeout-minutes: 150`; usa os mesmos pins de `actions/checkout` e de `astral-sh/setup-uv` que `.github/workflows/ci.yml` (comparar as linhas `uses:` lendo os dois arquivos); chama `uv sync --locked` e `python -m monitor_comissoes.diaria executar`; usa `github-actions[bot]`; não contém `secrets.` (o `GITHUB_TOKEN` padrão vem do `checkout`).

### Implementação

- [X] T012 [US1] Criar `diaria.py` com o caminho feliz: `executar_diaria(config, transporte, atual, status, aceitar_variacao, relogio, dormir) -> int` (por ora uma só tentativa e sem plausibilidade: chama `coletar`, grava os dois arquivos de sucesso com `status.gravar_par` e devolve 0, research.md R9) e `main(argv=None, transporte=None, relogio=None, dormir=None)` com `argparse` e os subcomandos `executar` (`--config`, `--atual`, `--status`, `--aceitar-variacao`) e `mensagem` (`--status`), conforme [contracts/cli.md](contracts/cli.md). `relogio` é um chamável sem argumentos que devolve o `datetime` de agora, em Brasília por padrão; `transporte` padrão é `TransporteHttp()`. Terminar com `if __name__ == "__main__": raise SystemExit(main())` para `python -m monitor_comissoes.diaria` (T010 passa).
- [X] T013 [US1] Criar `.github/workflows/coleta-diaria.yml` conforme [contracts/workflow.md](contracts/workflow.md), caminho de sucesso: `schedule` com `cron: "37 6 * * *"`; `workflow_dispatch` com a entrada booleana `aceitar_variacao` (padrão `false`); um job com `permissions: contents: write` e `timeout-minutes: 150`; `actions/checkout` e `astral-sh/setup-uv` com os **mesmos pins** do `ci.yml`; `uv sync --locked`; identidade `github-actions[bot]` (`41898282+github-actions[bot]@users.noreply.github.com`); passo de coleta e commit em `bash` que roda `uv run python -m monitor_comissoes.diaria executar`, faz `git add data/atual.json data/status.json`, `git commit -m "$(uv run python -m monitor_comissoes.diaria mensagem)"`, `git pull --rebase` e `git push origin HEAD:${GITHUB_REF_NAME}`. Sem gatilho `push`, sem `secrets.` (T011 passa).

**Checkpoint**: um dia de sucesso funciona de ponta a ponta nas fixtures, e o workflow existe para o caminho de sucesso. Entregável como MVP.

---

## Phase 4: User Story 2 — Uma falha deixa o workflow vermelho e os dados bons intactos (Priority: P1)

**Goal**: em qualquer falha, `atual.json` byte a byte intacto, `status.json` com a falha commitado e workflow vermelho (FR-006 a FR-009, FR-013).

**Independent Test**: para cada categoria de falha da COL e para falha inesperada, conferir o código 1, o `atual.json` idêntico, o `status.json` de falha e a ausência de arquivo parcial; conferir por texto o ramo de falha do workflow.

### Testes (escrever primeiro; devem falhar)

- [X] T014 [P] [US2] Em `tests/test_diaria.py`, acrescentar os casos de falha, todos partindo de um `atual.json` e um `status.json` bons gravados por uma execução de sucesso (ou de um `atual.json` sentinela onde indicado): para **cada** categoria injetável pelo `TransporteFalso` (`fonte_indisponivel` com HTTP 503 em um arquivo, `formato_alterado` com coluna removida, `arquivos_desatualizados` por `Last-Modified` antigo e por dispersão acima de 6 horas, `arquivo_incompleto` por corte, `api_deputados` por erro, `estoque_vazio` por lista filtrada vazia) e para `configuracao` inválida: `main` sai com 1; `stderr` tem `FALHA [categoria]: motivo`; o `atual.json` é **idêntico byte a byte** ao anterior; o `status.json` tem `resultado = "falha"`, a `categoria` e o `motivo` certos, `ultimo_retrato_bom` igual ao retrato mantido (com `estoque_bruto` da base) e `variacao_aceita = null`; nenhum `.tmp` sobra em `data/`. Mais: (a) exceção inesperada dentro da coleta (transporte que levanta `KeyError`) → categoria `interna`, código 1, `atual.json` intacto; (b) falha no **primeiro** dia, sem `atual.json`: não existe `atual.json` depois, `status.json` registra a falha e `ultimo_retrato_bom` é `null`; (c) `atual.json` sentinela `{"sentinela": true}` + falha: arquivo intacto e `ultimo_retrato_bom` `null`; (d) falha seguida, no mesmo dia, de execução bem-sucedida: o `status.json` final é `ok`, com `falha = null` (sem resto); (e) falha de `configuracao` registra `tentativas = 0`; as demais registram o número de coletas tentadas; (f) se a preparação do `status.json` falhar (simulada com `monkeypatch`, nunca com permissão de pasta, que não vale para usuário `root`), `main` sai com 1, o `atual.json` **não é trocado** (idêntico byte a byte) e o `status.json` registra `interna`; se nem a gravação do status de falha for possível, `main` sai com 1 e escreve `FALHA [interna]` em `stderr`; (g) se a preparação do `atual.json` lançar exceção, o resultado é o mesmo: `interna`, nenhum dos dois trocado, `atual.json` anterior intacto.
- [X] T015 [P] [US2] Em `tests/test_workflow.py`, acrescentar (texto): o passo de coleta usa `set +e` e guarda o código de saída da coleta; em falha executa `git checkout -- data/atual.json` com tolerância a arquivo ausente (`|| true`); em falha adiciona **só** `data/status.json`; faz o commit e o push antes de terminar; termina o passo com `exit` do código da coleta; o `git add` de `data/atual.json` só ocorre no ramo de código zero.

### Implementação

- [X] T016 [US2] Em `diaria.py`, implementar o ramo de falha: capturar `FalhaDeColeta` (categoria e motivo próprios) e `Exception` (`INTERNA`, mensagem `TipoDaExceção: texto`) em volta de config, coleta e gravação; montar o status de falha com `ultimo_retrato_bom` recomposto por `retrato_do_atual` (do `atual.json` em disco) e `estoque_bruto` por `base_de_comparacao`; gravar **só** o `status.json`; imprimir `FALHA [categoria]: motivo` em `stderr`; devolver 1. Uma falha de `config` registra `tentativas = 0`. Se nem o status puder ser gravado, imprimir `FALHA [interna]: …` e devolver 1. O `atual.json` nunca é aberto para escrita no ramo de falha (T014 passa).
- [X] T017 [US2] No workflow, completar o passo de coleta e commit com o ramo de falha, conforme [contracts/workflow.md](contracts/workflow.md) e research.md R9: `set +e`; `codigo=$?` logo depois da coleta; `set -e`; se `codigo` diferente de zero, `git checkout -- data/atual.json || true` e `git add data/status.json`; se zero, também `git add data/atual.json`; commit, `git pull --rebase`, `git push origin HEAD:${GITHUB_REF_NAME}`; `exit $codigo` no fim (T015 passa).

**Checkpoint**: nenhuma falha altera o `atual.json`, e todas deixam o status e o workflow vermelho. US1 e US2 juntas cumprem o resultado verificável da linha AGE.

---

## Phase 5: User Story 3 — Estoque implausível não é publicado (Priority: P1)

**Goal**: bloquear estoque bruto vazio e variação de mais de 20% do estoque bruto; liberar o dia atípico só por disparo manual com confirmação (FR-014 a FR-018b).

**Independent Test**: com retratos sintéticos, conferir a fronteira de 20%, queda e alta, vazio, primeiro dia, base recomposta e a confirmação manual; conferir por texto que a confirmação só existe no disparo manual.

### Testes (escrever primeiro; devem falhar)

- [X] T018 [P] [US3] Escrever `tests/test_plausibilidade.py`, sobre `verificar(estoque_bruto, base, limite_percentual, aceitar)` com inteiros: 1531 → 1100 (queda de 28%) falha com `estoque_implausivel`, e o motivo traz os dois totais e a variação com vírgula decimal (`-28,2%`); alta de mais de 20% também falha; **exatamente 20%** (1000 → 800 e 1000 → 1200) passa, e 1000 → 799 e 1000 → 1201 falham ("só `mais de 20%` é implausível"); sem base (`None`) a variação não se aplica; `estoque_bruto = 0` falha com `estoque_vazio` com ou sem base e **mesmo com `aceitar = True`**; com `aceitar = True` e variação acima do limite, não falha e devolve `{"estoque_anterior", "estoque_novo", "variacao_percentual"}` com uma casa decimal; com `aceitar = True` e variação dentro do limite, devolve `None` (nada a registrar); o limite vem do parâmetro (com 50%, 1000 → 600 falha e 1000 → 500 passa); base `0` é tratada como sem base.
- [X] T019 [P] [US3] Em `tests/test_diaria.py`, acrescentar: (a) dia 1 grava; no dia 2 o transporte serve só uma fração dos anos de proposições (derivar das fixtures, mantendo o formato) de modo a derrubar o estoque bruto em mais de 20% → `main` sai com 1, categoria `estoque_implausivel`, `atual.json` do dia 1 intacto, `status.json` de falha com o retrato do dia 1; (b) variação dentro do limite grava normalmente; (c) a variação da **lista filtrada** do NOVO acima de 20% com estoque bruto estável **passa** (fixture derivada que remove os autores do NOVO de metade dos itens, sem mudar os órgãos); (d) estoque bruto zero (comissão da configuração sem nenhuma proposição) falha com `estoque_vazio` no primeiro dia; (e) lista filtrada vazia continua falhando com `estoque_vazio` (COL); (f) a base de comparação do dia seguinte a uma falha é o retrato **bom** (estoque do dia 1), não a execução que falhou; (g) sem base válida (status ausente, ou `gerado_em` do status diferente do `meta.gerado_em` do `atual.json`) a variação não se aplica e `stderr` diz `sem base para comparar a variação`; (h) `--aceitar-variacao` com variação acima do limite grava os dois arquivos, sai com 0, o `status.json` traz `variacao_aceita` e a mensagem de `mensagem` é `dados: AAAA-MM-DD · ok · variação aceita manualmente (A → B, ±X,X%)`; (i) com `--aceitar-variacao`, uma falha de **outra** categoria (`fonte_indisponivel`, `formato_alterado`) continua falhando; (j) no dia seguinte a uma variação aceita, sem confirmação, a base é o estoque aceito e o limite volta a valer (queda de 28% sobre o novo estoque falha).
- [X] T020 [P] [US3] Em `tests/test_workflow.py`, acrescentar (texto): `--aceitar-variacao` só aparece condicionado a `github.event_name == 'workflow_dispatch'` e à entrada `aceitar_variacao` verdadeira, e não aparece solto na linha do comando; a entrada `aceitar_variacao` tem `type: boolean` e `default: false`.

### Implementação

- [X] T021 [US3] Criar `plausibilidade.py` com `verificar(estoque_bruto: int, base: int | None, limite_percentual: int, aceitar: bool) -> dict | None`, em aritmética de inteiros (`abs(novo - base) * 100 > limite * base`), levantando `FalhaDeColeta` de categoria `ESTOQUE_VAZIO` (zero, sempre) ou `ESTOQUE_IMPLAUSIVEL` (variação), e devolvendo o dicionário de `variacao_aceita` quando a confirmação ignorou uma variação (T018 passa).
- [X] T022 [US3] Em `diaria.py`, ler a base de comparação no início (`base_de_comparacao(atual, status)`, com o aviso em `stderr` quando não houver) e chamar `verificar` entre `coletar` e a gravação, passando `config.limite_variacao_percentual` e `aceitar_variacao`; gravar `variacao_aceita` no status de sucesso; ligar o flag `--aceitar-variacao` (T019 passa).
- [X] T023 [US3] No workflow, acrescentar a passagem condicional do flag: `--aceitar-variacao` só quando `github.event_name == 'workflow_dispatch'` e `inputs.aceitar_variacao` for verdadeiro (por exemplo, via variável de ambiente do passo definida por expressão, nunca interpolando a entrada diretamente no script) (T020 passa).

**Checkpoint**: o produto bloqueia o arquivo truncado, deixa a lista filtrada fora do alarme e tem um caminho de liberação registrado. As três histórias P1 estão completas.

---

## Phase 6: User Story 4 — Novas tentativas diante de falha passageira (Priority: P2)

**Goal**: repetir a execução inteira, até 4 vezes com 30 minutos de espera, só para falhas repetíveis (FR-019 a FR-021).

**Independent Test**: simular sequências de resultados com `dormir` injetável, sem esperar tempo real.

### Testes (escrever primeiro; devem falhar)

- [X] T024 [P] [US4] Em `tests/test_diaria.py`, acrescentar, com um transporte falso que falha as `n` primeiras coletas e um `dormir` que só registra as esperas: falha repetível na 1ª coleta e sucesso na 2ª → código 0, `status.json` `ok` com `tentativas = 2`, e `dormir` chamado uma vez com `1800` segundos; falhas repetíveis nas tentativas 1 e 2 e sucesso na 3ª → `tentativas = 3`, duas esperas de 1800 s; **4 falhas repetíveis** → código 1, `status.json` de falha com `tentativas = 4`, categoria da última falha, três esperas de 1800 s e nenhuma depois da última tentativa; para cada categoria repetível (`fonte_indisponivel`, `arquivos_desatualizados` por idade e por dispersão, `arquivo_incompleto`, `api_deputados`) o laço repete; para cada categoria não repetível (`configuracao`, `formato_alterado`, `estoque_vazio`, `estoque_implausivel`, `interna`) **não** repete: `tentativas = 1` (`0` para `configuracao`) e nenhuma chamada a `dormir`; `execucao.tentativas = 2` e `espera_minutos = 5` no `config.toml` de teste mudam o laço (no máximo 2 coletas, espera de 300 s); cada tentativa que falha por causa repetível e ainda tem outra a seguir escreve em `stderr` `TENTATIVA n de N falhou [categoria]: motivo; nova tentativa em M minutos`; o relógio é lido de novo a cada tentativa (o `Last-Modified` aceito depende de `agora`); nenhum teste dorme de verdade (a suíte inteira desta fase roda em menos de alguns segundos).

### Implementação

- [X] T025 [US4] Em `diaria.py`, implementar o laço de tentativas em volta de `coletar`: até `config.tentativas` coletas; entre elas, `dormir(config.espera_minutos * 60)`, somente quando `falha.categoria in REPETIVEIS` e ainda houver tentativa; registrar `tentativas` no status; `interna` e as categorias não repetíveis saem do laço na hora. A plausibilidade (US3) fica **fora** do laço, depois da coleta bem-sucedida (T024 passa).

**Checkpoint**: um atraso passageiro da Câmara não custa um dia, e o workflow só fica vermelho se todas as tentativas falharem.

---

## Phase 7: User Story 5 — Reexecução no mesmo dia não duplica nem corrompe (Priority: P2)

**Goal**: duas execuções no mesmo dia dão a mesma lista, nunca rodam ao mesmo tempo e nenhuma execução bem-sucedida é descartada (FR-022 a FR-025).

**Independent Test**: duas execuções sobre as mesmas fixtures; conferir por texto o controle de concorrência do workflow.

### Testes (escrever primeiro; devem falhar)

- [X] T026 [P] [US5] Em `tests/test_diaria.py`, acrescentar: duas execuções bem-sucedidas no mesmo dia de Brasília, com relógios diferentes (09h00 e 11h00), geram `atual.json` com **itens e ordem idênticos**, e só `meta.gerado_em` difere; o `status.json` da segunda traz o `verificado_em` novo e o **mesmo** `data_referencia`; a segunda **grava** (não é descartada), mesmo com o resultado igual ao da primeira; uma execução de sucesso depois de uma falha do mesmo dia grava normalmente; `data_referencia` muda quando o relógio cruza a meia-noite de Brasília.
- [X] T027 [P] [US5] Em `tests/test_workflow.py`, acrescentar (texto): `concurrency:` com `group: coleta-diaria` e `cancel-in-progress: false`.

### Implementação

- [X] T028 [US5] No workflow, acrescentar o bloco `concurrency` com `group: coleta-diaria` e `cancel-in-progress: false`, conforme [contracts/workflow.md](contracts/workflow.md) e research.md R8 (T027 passa). Conferir que T026 passa sem mudança em `diaria.py` (nenhuma regra de descarte existe; se falhar, corrigir a causa em vez de acrescentar descarte).

**Checkpoint**: reexecuções são seguras, e a concorrência está controlada pelo agendador.

---

## Phase 8: User Story 6 — Risco de desativação do agendamento confirmado (Priority: P2)

**Goal**: entregar a confirmação documentada do risco de 60 dias, com a fonte e a data da consulta (FR-026, FR-027; SC-008).

**Independent Test**: o documento existe, com os links oficiais, a data da consulta e uma conclusão explícita.

- [X] T029 [P] [US6] Escrever `tests/test_docs.py` (leitura de texto, sem rede): `docs/agendamento-60-dias.md` existe e contém o link `https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows`, o link `https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow`, a frase oficial `scheduled workflows are automatically disabled when no repository activity has occurred in 60 days`, a data de consulta `2026-10-18` e as palavras `Conclusão` e `Mitigações` (devem falhar antes de T030).
- [X] T030 [US6] Escrever `docs/agendamento-60-dias.md` a partir de research.md R11: a regra oficial (com a frase em inglês e a tradução), **o que a fonte oficial não diz** (o que conta como atividade; se commits do `GITHUB_TOKEN` contam), as fontes não oficiais consultadas (com a ressalva de que não são oficiais), a data da consulta (`2026-10-18`), a **Conclusão** ("risco não confirmado nem afastado por fonte oficial; hipótese plausível: o commit diário do bot conta"), como o produto sinaliza o problema (ausência do commit diário e, na PAG, a faixa de "dados atrasados" depois de 30 horas), e as **Mitigações** possíveis, as quatro de R11, marcadas como **proposta para decisão do mantenedor, nenhuma implementada**. Incluir a instrução de reativação (aba Actions → Enable workflow, ou `gh workflow enable`) e a data de início da operação a anotar (T029 passa).

**Checkpoint**: o risco está documentado, e a decisão sobre mitigação é do mantenedor.

---

## Phase 9: Polish & verificação final

**Purpose**: fechar a feature sem aumentar o escopo.

- [X] T031 Rodar `uv run ruff format .` e `uv run ruff check .`, corrigir o que apontarem nos arquivos desta feature e conferir que **nenhum teste existente da COL foi editado** (`git diff --stat` não mostra mudança em `tests/test_aceitacao.py`, `test_falhas.py`, `test_lote.py`, `test_transporte.py`, `test_saida.py`, `test_deputados.py`, `test_estoque.py` nem `test_sem_rede.py`; `tests/test_config.py` só ganha casos).
- [X] T032 Rodar a verificação completa (`uv run ruff check . && uv run ruff format --check . && uv run pytest`) e **mostrar a saída**. A suíte inteira, inclusive a da COL, deve passar sem rede (SC-006).
- [X] T033 Executar os passos 1 a 3 de [quickstart.md](quickstart.md) e conferir o resultado esperado de cada um. Os passos 4 a 6 (workflow real no GitHub e as 60 dias) dependem do merge e ficam para o fechamento.
- [X] T034 Conferir os limites da spec (FR-030, FR-031, SC-009): nenhuma menção a Telegram, página, GitHub Pages, relatoria ou `data/mudancas/` no código e no workflow; nenhum segredo; o formato do `atual.json` e o comando da COL idênticos aos de antes (`git diff` de `contracts/atual-json.md` e `contracts/cli.md` da COL vazio).
- [X] T035 **Não alterar o `ROADMAP.md` aqui.** A linha AGE está `em andamento`; ela só vira `concluída` depois da verificação completa, dos casos de aceitação e do merge, por pedido do mantenedor (CLAUDE.md, "Status no ROADMAP.md").

---

## Dependencies & Execution Order

- **Fase 1** (T001, T002) → **Fase 2** (testes T003–T005 em paralelo, depois T006–T009; T008 depende de T007; T009 depende de T001 e T008 apenas para os tipos).
- **US1** (Fase 3) depende da Fase 2. **US2** depende de US1 (mesmo `diaria.py` e mesmo workflow). **US3** depende de US2 (usa o ramo de falha). **US4** depende de US2 (usa o status de falha e `tentativas`); pode andar em paralelo com US3 só se editarem trechos diferentes de `diaria.py`, o que não é recomendado: siga a ordem. **US5** depende de US1 e US2. **US6** é independente de tudo (só documento): pode rodar em paralelo com qualquer fase depois da Fase 1.
- **Polish** só depois de todas as histórias.
- Dentro de cada fase, os testes (`[P]`) são escritos primeiro e devem falhar antes da implementação.

## Parallel Example

- Fase 2: T003, T004 e T005 em paralelo (arquivos de teste diferentes); depois T006 e T007 em paralelo (`config.py` e `lote.py`), então T008, então T009.
- Fase 5: T018, T019 e T020 em paralelo antes de T021.
- US6 (T029, T030) pode ser feita a qualquer momento depois da Fase 1, por exemplo enquanto uma fase de código espera revisão.

## Implementation Strategy

1. **MVP**: Fases 1, 2 e 3 (US1). Já gera, a cada execução, os dois arquivos e a mensagem do commit, e o workflow commita o caminho de sucesso.
2. **P1 completo**: US2 e US3. Só aqui o resultado verificável da linha AGE (falha deixa o workflow vermelho e o último bom intacto) e a defesa contra arquivo truncado estão completos. **Não considerar a feature pronta antes de US2 e US3.**
3. **P2**: US4 (tentativas), US5 (reexecução e concorrência) e US6 (documento do risco de 60 dias).
4. Em cada checkpoint, rodar a verificação completa. Commits pequenos e descritivos por tarefa ou grupo de tarefas, **sem push**.
