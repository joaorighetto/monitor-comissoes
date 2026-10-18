---

description: "Tarefas da feature COL — Coleta e estoque filtrado"
---

# Tasks: COL — Coleta e estoque filtrado

**Input**: `specs/001-coleta-estoque-filtrado/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Prerequisites**: acesso de rede a `dadosabertos.camara.leg.br` apenas para T005 e T042 (captura das fixtures e execução real). Todo o resto roda sem rede.

**Tests**: **solicitados** (constituição, princípio IV; pedido do mantenedor: "as tarefas começam pelos testes: fixtures salvas e nenhum teste com rede"). Em cada fase, os testes vêm antes da implementação e devem **falhar** antes dela.

**Organization**: por história de usuário da spec. As fases 1 e 2 são base comum. Os módulos citados estão em `src/monitor_comissoes/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência entre si)
- **[Story]**: US1 a US5, conforme `spec.md`
- Verificação completa: `uv run ruff check . && uv run ruff format --check . && uv run pytest`

## Phase 1: Setup

**Purpose**: esqueleto e fixtures reais. Nada de lógica de domínio.

- [X] T001 Criar `config.toml` na raiz com `comissoes = ["CE", "CREDN"]` e `ano_minimo = 2003`, com um comentário por campo (a lista é a do `PRODUCT.md` D1; o ano vem do art. 3º da Resolução 33/2022, `PRODUCT.md` §5.1).
- [X] T002 [P] Criar o pacote `src/monitor_comissoes/__init__.py` (vazio) e `src/monitor_comissoes/erros.py` com `FalhaDeColeta(Exception)` (atributos `categoria` e `motivo`) e as sete categorias de [data-model.md](data-model.md): `configuracao`, `fonte_indisponivel`, `formato_alterado`, `arquivos_desatualizados`, `arquivo_incompleto`, `api_deputados`, `estoque_vazio`.
- [X] T003 Tornar o pacote instalável pelo `uv` (decisão C1-A): em `pyproject.toml` acrescentar `[build-system]` com `requires = ["uv_build>=0.11,<0.12"]` (faixa compatível com o `uv` 0.11.x instalado) e `build-backend = "uv_build"`, e trocar `package = false` por `package = true` em `[tool.uv]`; manter `dependencies = []`. Rodar `uv lock` e comitar o `uv.lock` atualizado (o CI usa `uv sync --locked` e falharia com o lock desatualizado). Conferir com `uv run python -c "import monitor_comissoes"` depois de criar o pacote abaixo. Depende de T002.
- [X] T004 [P] Escrever `tests/capturar_fixtures.py` (só biblioteca padrão; não é teste: o nome não começa com `test_`). Ele baixa `proposicoes-{ano}.csv` e `proposicoesAutores-{ano}.csv` de **2003 a 2026** (o mesmo intervalo da produção, para que a raiz de qualquer cadeia seja achada; cerca de 1 GB baixado uma única vez, descartado depois da seleção), e `/api/v2/deputados?siglaPartido=NOVO&itens=100`, e grava recortes em `tests/fixtures/camara/` preservando o cabeçalho completo, o BOM UTF-8, o separador `;` e todos os campos entre aspas, com valores copiados sem alteração. Seleção de linhas: (a) PL 1843/2022, PL 3871/2024 e PL 4047/2019, achados por `siglaTipo`+`numero`+`ano`; (b) a cadeia de apensação completa de cada um, até a raiz; (c) os autores dessas proposições; (d) linhas de contraste: um REQ e um PDL na CE, um PL de outro partido na CE, um PL do NOVO fora da CE e da CREDN; (e) ao menos 2 linhas reais em **todo** arquivo de ano (um arquivo vazio é falha, FR-002). O script também grava `manifesto.json` com, por arquivo, `Last-Modified` real e `Content-Type`, e imprime se existe nos dados reais uma cadeia de apensação com 2 ou mais níveis, um ciclo e uma raiz fora dos anos lidos.
- [X] T005 Rodar `uv run python tests/capturar_fixtures.py` (com rede) e comitar `tests/fixtures/camara/` com um `README.md` que registra a data da captura, a lista de linhas escolhidas e o que é real. Conferir contra research.md (R2, R3, R4, R10): formato de data `AAAA-MM-DDTHH:MM:SS`, `Content-Length` presente, 31 colunas em proposições, 12 em autores. **Se algo divergir, parar e corrigir plan.md e research.md antes de seguir.** Depende de T004.

---

## Phase 2: Foundational (bloqueia todas as histórias)

**Purpose**: configuração, transporte HTTP, leitura validada dos arquivos, gravação atômica e infraestrutura de teste.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase.

### Testes (escrever primeiro; devem falhar)

- [X] T006 [P] Escrever `tests/test_config.py`: config válida; arquivo ausente; `comissoes` vazia ("Não vazia"); sigla repetida ("sem repetição"); sigla vazia ou não texto ("cada sigla é texto não vazio"); `ano_minimo` não inteiro; `ano_minimo` < 1990 ou > ano corrente ("Entre 1990 e o ano corrente"). Cada caso levanta `FalhaDeColeta` de categoria `configuracao` com mensagem que nomeia o campo.
- [X] T007 [P] Escrever `tests/test_transporte.py`, com servidor HTTP local ou função falsa, sem rede externa: 3 tentativas com espera injetável (2 s e 4 s, sem dormir de verdade); HTTP 503 em todas → `fonte_indisponivel`; falha na 1ª e sucesso na 2ª → sucesso; `Content-Length` maior que os bytes recebidos → `arquivo_incompleto`; ausência de `Content-Length` → `formato_alterado`; o `Last-Modified` é devolvido.
- [X] T008 [P] Escrever `tests/test_lote.py`: leitura de CSV com BOM, `;` e quebras de linha dentro de campo entre aspas, usando as fixtures; coluna obrigatória ausente → `formato_alterado` com o nome da coluna; linha com número de colunas diferente do cabeçalho → `arquivo_incompleto`; fim de arquivo dentro de campo entre aspas → `arquivo_incompleto`; arquivo só com cabeçalho → `arquivo_incompleto`; data fora de `AAAA-MM-DDTHH:MM:SS` em `ultimoStatus_dataHora` ou `dataApresentacao` → `formato_alterado` com o nome da coluna.
- [X] T009 [P] Escrever `tests/test_saida.py` (parte atômica): gravar cria `data/` se faltar; gravar sobre arquivo existente o substitui; exceção durante a escrita deixa o arquivo anterior **idêntico byte a byte** e não deixa `.tmp`; primeira execução com falha não cria `atual.json`.
- [X] T010 [P] Criar `tests/conftest.py` com `TransporteFalso`, que serve os arquivos de `tests/fixtures/camara/` recalculando `Content-Length` pelo corpo servido e usando o `Last-Modified` do `manifesto.json`. Ele permite injetar falhas por URL (status, corpo cortado, cabeçalho removido, `Last-Modified` antigo), registra as URLs pedidas e oferece a fixture `agora`. Sem acesso à rede em nenhum ponto: uma fixture `autouse` bloqueia `socket.socket.connect` para qualquer endereço que não seja `localhost`, de modo que um teste que tente usar a internet falhe (constituição, princípio IV; SC-006). O transporte falso aceita sobrescrever o conteúdo servido de um arquivo (para as variantes derivadas de T025). A configuração dos testes usa `ano_minimo = 2003`, como a produção, e `agora` = `2026-10-18T09:00:00-03:00`, de modo que o `Last-Modified` real das fixtures (17/10/2026) fique dentro das 36 horas.

### Implementação

- [X] T011 Implementar `config.py`: `Config(comissoes: tuple[str, ...], ano_minimo: int)` e `carregar_config(caminho, ano_corrente)` com `tomllib`, aplicando literalmente as regras de T006 (T006 passa).
- [X] T012 Implementar `transporte.py`: protocolo `Transporte` (obter JSON com cabeçalhos; baixar arquivo para um destino, em blocos) e `TransporteHttp` sobre `urllib.request`, com timeout de 60 s, 3 tentativas, espera injetável, comparação de bytes recebidos com `Content-Length` e devolução de `Last-Modified` (T007 passa).
- [X] T013 Implementar `lote.py`: baixar, para um diretório temporário, os dois arquivos de cada ano de `ano_minimo` ao ano corrente; validar cada arquivo (colunas obrigatórias, número de colunas por linha, leitura estrita, ao menos uma linha de dados); leitores em fluxo que devolvem só as colunas de [data-model.md](data-model.md); `csv.field_size_limit` ampliado; leitura como `utf-8-sig`; datas estritas (T008 passa).
- [X] T014 Implementar `saida.py`, parte atômica: `gravar_atomico(documento, destino)` com arquivo `.tmp` na mesma pasta, `flush`, `fsync` e `os.replace`; limpeza do `.tmp` em qualquer exceção (T009 passa).

**Checkpoint**: configuração, transporte, leitura validada e gravação atômica funcionam e estão testados.

---

## Phase 3: User Story 1 — Gerar o estoque filtrado (Priority: P1) 🎯 MVP

**Goal**: `uv run python -m monitor_comissoes` gera `data/atual.json` com os PL/PLP da CE e da CREDN com `autoria NOVO` e/ou `autor hoje no NOVO`.

**Independent Test**: com as fixtures, o comando grava um arquivo em que PL 1843/2022 tem `autoria NOVO`, PL 3871/2024 tem só `autor hoje no NOVO`, e REQ/PDL e itens fora da CE e da CREDN não aparecem. (O caso PL 4047/2019 depende do apensamento e é testado na US2.)

### Testes (escrever primeiro; devem falhar)

- [X] T015 [P] [US1] Escrever `tests/test_deputados.py`: parse da resposta real capturada (5 deputados em 17/10/2026, `id` e `nome`); paginação seguindo `rel: "next"` (resposta sintética de 2 páginas, marcada como sintética); total lido diferente de `X-Total-Count` → `api_deputados`; erro HTTP ou JSON inválido → `api_deputados`.
- [X] T016 [P] [US1] Escrever `tests/test_estoque.py` (etiquetas e filtros, com dados mínimos em memória): `autoria NOVO` ⇔ algum autor com `partido_na_data = "NOVO"`; `autor hoje no NOVO` ⇔ algum `id_deputado` na lista; as duas juntas; nenhuma → fora; autor sem `id_deputado` (Senado/Executivo) com partido NOVO → recebe `autoria NOVO` e nunca `autor hoje no NOVO`; só `PL` e `PLP` são candidatas; órgão fora de `comissoes` → fora; etiquetas em ordem fixa, sem repetição; autores ordenados por `ordem`.
- [X] T017 [P] [US1] Escrever `tests/test_aceitacao.py` (parte US1): sobre as fixtures reais e `TransporteFalso`, PL 1843/2022 aparece com `autoria NOVO`; PL 3871/2024 aparece com `autor hoje no NOVO` e sem `autoria NOVO`; o REQ, o PDL, o PL de outro partido e o PL do NOVO fora das comissões não aparecem; todo item tem `link` e ao menos uma etiqueta; o JSON respeita [contracts/atual-json.md](contracts/atual-json.md).

### Implementação

- [X] T018 [US1] Implementar `deputados.py`: `obter_deputados_novo(transporte)` → lista de `(id, nome)` ordenada por `id`, com paginação e conferência de `X-Total-Count` (T015 passa).
- [X] T019 [US1] Implementar em `estoque.py` as regras sem I/O: `etiquetar(autores, ids_deputados_novo)`, `montar_item(...)` (campos de [contracts/atual-json.md](contracts/atual-json.md); nesta fase a referência é a própria proposição), filtros de tipo e de comissão e `parado_ha_dias` em dias inteiros contra a data de Brasília (UTC−3 fixo, research.md R6) (T016 passa).
- [X] T020 [US1] Implementar em `coleta.py` as passadas de [research.md](research.md) R5, sem apensação: ler os autores dos anos para achar as candidatas; ler as proposições e guardar só as linhas das candidatas PL/PLP; segunda leitura dos autores só das candidatas que entram, para listar todos os autores. Memória não proporcional ao volume.
- [X] T021 [US1] Implementar em `saida.py` `montar_documento(itens, meta)` com a ordem dos itens (`ultimo_status_em` crescente, desempate por `id`) e o `meta` com os campos já conhecidos (`versao_formato`, `gerado_em`, `comissoes`, `ano_minimo`, `total_itens`, `total_por_comissao`).
- [X] T022 [US1] Implementar `__main__.py` e `coleta.executar(config, transporte, agora, saida)`: opções `--config` e `--saida`, linha `OK: …` em `stdout`, código de saída 0 (contrato em [contracts/cli.md](contracts/cli.md)).
- [X] T023 [US1] Rodar T015 a T017 até passarem; comitar.

**Checkpoint**: US1 funciona sozinha e é demonstrável (MVP).

---

## Phase 4: User Story 2 — Apensados seguem a principal (Priority: P1)

**Goal**: comissão, situação e "parado há" vêm da raiz da cadeia; raiz não localizada ou ciclo usam o status do próprio item com a marca.

**Independent Test**: PL 4047/2019 fica fora; cadeias de 2 níveis, raiz fora do intervalo e ciclo se comportam como na spec.

### Testes (escrever primeiro; devem falhar)

- [X] T024 [P] [US2] Estender `tests/test_estoque.py` com `resolver_referencia`: sem principal → própria; cadeia A→B (raiz B); cadeia A→B→C (raiz C, não B); raiz em outra comissão → item fora, mesmo que o status do próprio apensado seja da lista; raiz ausente → `principal_nao_localizada` com o status do próprio item; ciclo A→B→A → igual à raiz ausente; **raiz ausente com o próprio órgão fora da lista → fora** (esclarecimento 1); etiquetas sempre pelos autores do próprio apensado. Estruturas em memória, marcadas como sintéticas.
- [X] T025 [P] [US2] Estender `tests/test_aceitacao.py`: PL 4047/2019 **não** aparece (a raiz está na CFT); um apensado real do conjunto de fixtures aparece com `apensado_a` preenchido e comissão da raiz; casos **derivados**, criados no teste a partir das linhas reais com `uriPropPrincipal` alterada (raiz inexistente e ciclo) em um diretório temporário, nunca gravados em `tests/fixtures/`, para conferir `principal_nao_localizada: true` e `apensado_a: null`.

### Implementação

- [X] T026 [US2] Implementar em `estoque.py` `resolver_referencia(id, mapa_principal, linhas_necessarias)`: sobe a cadeia com conjunto de visitados (ciclo), devolve estado `própria`, `raiz` ou `não localizada` conforme [data-model.md](data-model.md) (T024 passa).
- [X] T027 [US2] Estender `coleta.py`: passada que monta o mapa `id → id da principal` somente para linhas com `uriPropPrincipal` (id = último trecho numérico da URI); resolução das raízes das candidatas; segunda leitura das proposições para extrair as linhas das candidatas e das raízes; avaliar comissão, situação e "parado há" pela referência.
- [X] T028 [US2] Estender `montar_item` e `montar_documento` com `apensado_a` (`id`, `identificacao`, `link`) e `principal_nao_localizada`, conforme [contracts/atual-json.md](contracts/atual-json.md) (T025 passa).
- [X] T029 [US2] Rodar a suíte inteira; comitar.

**Checkpoint**: US1 e US2 funcionam juntas.

---

## Phase 5: User Story 3 — Falhar de forma visível (Priority: P1)

**Goal**: toda falha termina com erro, motivo e arquivo anterior idêntico; nada parcial é gravado.

**Independent Test**: cada cenário de falha da US3 sai com código 1, mensagem `FALHA [categoria]: …` e `atual.json` anterior byte a byte igual.

### Testes (escrever primeiro; devem falhar)

- [X] T030 [P] [US3] Escrever `tests/test_falhas.py`, parametrizado, partindo de um `atual.json` sentinela já existente e conferindo, em cada caso, saída 1, categoria, mensagem com o motivo e arquivo intacto: HTTP 503 persistente (`fonte_indisponivel`); coluna ausente (`formato_alterado: coluna X`); `Last-Modified` com mais de 36 horas (`arquivos_desatualizados`, mensagem "a Câmara não atualizou os arquivos"); arquivo só com cabeçalho e arquivo ausente (404) (`arquivo_incompleto` e `fonte_indisponivel`); `Content-Length` maior que o corpo; última linha com colunas faltando (`arquivo_incompleto`); API de deputados fora do ar (`api_deputados`, e **nenhum** arquivo grande é pedido); estoque filtrado vazio (`estoque_vazio`); exceção forçada durante a gravação (arquivo anterior intacto, sem `.tmp`); exceção inesperada → `FALHA [interna]`, código 1. Também: o diretório temporário é apagado em sucesso e em falha.
- [X] T031 [P] [US3] Cobrir a **ordem de verificação** de [contracts/cli.md](contracts/cli.md) em `tests/test_falhas.py`: configuração inválida falha sem nenhum pedido de rede; falha da API de deputados ocorre antes de qualquer download de arquivo em lote.

### Implementação

- [X] T032 [US3] Implementar em `lote.py`/`coleta.py` a checagem de frescor: falha se o `Last-Modified` de qualquer arquivo tiver mais de 36 horas em relação a `agora` (T030 passa nesse ponto).
- [X] T033 [US3] Implementar em `coleta.py` a falha `estoque_vazio` (lista filtrada sem itens), sempre antes da gravação.
- [X] T034 [US3] Implementar em `coleta.py` e `__main__.py` a ordem de verificação do contrato (configuração → deputados → download e validação por ano → frescor → cálculo → estoque vazio → gravação), a conversão de `FalhaDeColeta` em `FALHA [categoria]: motivo` em `stderr` com código 1, a captura de exceção inesperada como `FALHA [interna]`, e a limpeza do diretório temporário em `finally` (T030 e T031 passam).
- [X] T035 [US3] Rodar a suíte inteira; comitar.

**Checkpoint**: nenhuma falha deixa saída parcial; US1 a US3 completas.

---

## Phase 6: User Story 4 — Comissões e ano mínimo configuráveis (Priority: P2)

**Goal**: trocar comissões ou ano mínimo muda o resultado sem alterar código.

**Independent Test**: mesmas fixtures, outra configuração, outro resultado.

### Testes

- [ ] T036 [P] [US4] Estender `tests/test_aceitacao.py`: com `comissoes = ["CE"]` sai só CE; com outra sigla presente nas fixtures, saem os itens dela e não os da CE; com `ano_minimo = 2022` a `TransporteFalso` registra pedidos só dos anos 2022 a 2026 e os itens apresentados antes entram como "principal não localizada" ou saem conforme as regras da US2; configuração inválida não faz nenhum pedido de rede.

### Implementação

- [ ] T037 [US4] Garantir que `coleta.py` e `lote.py` leiam `comissoes` e `ano_minimo` apenas da `Config` (sem valores fixos no código) e que `__main__.py` aceite `--config`. Ajustar o que T036 revelar (T036 passa).

**Checkpoint**: US4 independente de código.

---

## Phase 7: User Story 5 — Resultado repetível e auditável (Priority: P2)

**Goal**: mesma entrada gera os mesmos itens; `meta` completo para auditoria.

**Independent Test**: duas execuções com as mesmas fixtures e o mesmo relógio são idênticas byte a byte; `meta` traz tudo que o contrato lista.

### Testes

- [ ] T038 [P] [US5] Estender `tests/test_saida.py` e `tests/test_aceitacao.py`: duas execuções com o mesmo `agora` geram arquivos idênticos byte a byte; com `agora` diferente no mesmo dia, só `gerado_em` muda; `dados_camara_em` é o menor `Last-Modified`; `anos_lidos` = `[ano_minimo, ano corrente]`; `deputados_novo_em_exercicio` ordenada por `id`; `total_por_comissao` com uma chave por comissão da configuração, inclusive com 0; as sete invariantes do contrato (`meta.total_itens == len(itens) > 0`, soma por comissão, `link` e etiqueta em todo item, `comissao` ∈ `comissoes`, `principal_nao_localizada` ⇒ `apensado_a` nulo, `id`s únicos, repetibilidade); JSON UTF-8 sem escape de acentos, indentado com 2 espaços, com quebra de linha final.

### Implementação

- [ ] T039 [US5] Completar `meta` em `saida.py`/`coleta.py` (`dados_camara_em`, `anos_lidos`, `deputados_novo_em_exercicio`) e garantir serialização determinística: ordem fixa dos campos, listas ordenadas, `ensure_ascii=False`, `indent=2` (T038 passa).
- [ ] T040 [US5] Rodar a suíte inteira; comitar.

---

## Phase 8: Polish & verificação final

- [ ] T041 Remover `tests/test_ambiente.py` (teste provisório) e conferir que `uv run pytest` continua coletando testes reais (não sai com código 5).
- [ ] T042 Execução real (com rede): `uv run python -m monitor_comissoes --saida /tmp/atual-real.json`. Registrar em research.md R7 o tempo total, o pico de memória e o espaço em disco usados, e comparar `total_itens` com a ordem de grandeza da sondagem (~50). Explicar item a item qualquer diferença grande. **Não comitar** `data/atual.json` real: o commit diário é da feature AGE.
- [ ] T043 Executar os passos 2 a 5 de [quickstart.md](quickstart.md) e conferir, no resultado real, PL 1843/2022, PL 3871/2024 e PL 4047/2019 e dois links oficiais.
- [ ] T044 Rodar a verificação completa e mostrar a saída: `uv run ruff check . && uv run ruff format --check . && uv run pytest`.
- [ ] T045 Conferir cada requisito FR-001 a FR-023 e SC-001 a SC-008 da spec contra o código e os testes; anotar no relatório final o que ficou como limite conhecido.

---

## Dependencies & Execution Order

- **Fase 1**: T001, T002 e T004 podem ser paralelos; T003 depende de T002; T005 depende de T004 e de rede.
- **Fase 2**: depende da Fase 1 (T005 para as fixtures de T008 e T010). Testes T006–T010 em paralelo; implementação T011–T014 depois do respectivo teste (T011←T006, T012←T007, T013←T008 e T012, T014←T009).
- **US1 (Fase 3)**: depende da Fase 2. **US2** depende de US1 (reaproveita `estoque.py` e `coleta.py`). **US3** depende de US1 (e é mais completa com US2). **US4** e **US5** dependem de US1 e US2.
- **Fase 8**: depende de todas as histórias.

### Ordem recomendada (um desenvolvedor)

T001 → T002 → T003 → T004 → T005 → Fase 2 → US1 → US2 → US3 → US4 → US5 → Fase 8.

## Parallel Example

```bash
# Fase 2: testes juntos (arquivos diferentes)
Task: "tests/test_config.py"      # T006
Task: "tests/test_transporte.py"  # T007
Task: "tests/test_lote.py"        # T008
Task: "tests/test_saida.py"       # T009
Task: "tests/conftest.py"         # T010
```

## Implementation Strategy

### MVP primeiro (US1)

1. Fases 1 e 2. 2. US1. 3. **Parar e validar**: os casos 1 e 2 da aceitação passam sobre fixtures reais.

### Entrega incremental

US2 (apensados) → US3 (falhas) → US4 (configuração) → US5 (repetibilidade e `meta`) → Fase 8.

## Notes

- Commits pequenos e descritivos, por tarefa ou grupo lógico, **sem push** (pedido do mantenedor para a etapa de implementação; o `CLAUDE.md` exige pedido para commit e push fora dela).
- Fixtures: recortes reais copiados sem alteração; só as variantes de T025 são derivadas, e nascem dentro do teste, identificadas como tais.
- Se algum teste só puder ser escrito contra dados que a captura (T005) não trouxe, parar e voltar a T004/T005 em vez de inventar dados.
- Nenhuma dependência nova: tudo com biblioteca padrão (constituição, princípio I).
- Fora do escopo desta lista (limite da COL): relatoria, comparação com ontem, agendamento, `status.json`, Telegram, página, variação de 20%.
