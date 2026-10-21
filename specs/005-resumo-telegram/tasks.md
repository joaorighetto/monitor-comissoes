# Tasks: AVI — Resumo diário no Telegram

**Input**: documentos de projeto em `specs/005-resumo-telegram/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Pré-requisitos**: spec aprovada pelo mantenedor (20/10/2026). Plan e tasks aguardam o OK do mantenedor antes de `/speckit-implement`.

**Testes**: pedidos pelo fluxo (fixtures salvas, nenhum teste com rede nem credencial real). Em cada fase, os testes vêm **antes** da implementação e devem falhar primeiro.

**Formato**: `- [ ] T### [P?] [US?] Descrição com caminho`. `[P]` = arquivos diferentes, sem dependência de tarefa incompleta.

**Regras do repositório (CLAUDE.md)**: commits pequenos e descritivos, sem push; nenhuma troca de branch; verificação completa: `uv run ruff check . && uv run ruff format --check . && uv run pytest`. Cada fase termina com a verificação completa verde e um ou mais commits (sugestões em "Commit" ao fim de cada fase). O status da linha AVI no `ROADMAP.md` só vira `concluída` depois da verificação completa, dos casos de aceitação e do OK do mantenedor.

**Ordem das fases**: fixtures → fundação (config, entradas, registro, cliente da Bot API) → US1 a US5 (todas P1, na ordem da spec) → US6 e US7 (P2) → fechamento (workflow, PRODUCT.md, verificação). A US3 (teto) recebe os avisos já formatados como texto e reserva o espaço deles; a US6 produz esses avisos depois.

**Constantes fixas** (plan.md e research.md): teto `4096` unidades UTF-16; lista de itens de cada aviso até `1200` unidades; `3` tentativas de envio, esperas de `5` s e `15` s, `retry_after` aceito até `60` s; cron `17 10 * * *`; variáveis `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.

## Fase 1: Fixtures (sem rede)

**Propósito**: entradas salvas e construtores sintéticos de que todos os testes dependem. Nenhuma tarefa desta fase usa rede.

- [X] T001 [P] Criar `tests/fixtures/aviso/` com **uma pasta por cenário**, cada uma com `atual.json`, `status.json` e `mudancas/AAAA-MM-DD.json` (o nome do arquivo de mudanças é a `data_referencia` do `status.json`, que o CLI usa para achá-lo), no formato dos contratos (`specs/004-mudancas-desde-ontem/contracts/mudancas-json.md`, `specs/004-mudancas-desde-ontem/contracts/atual-json.md`, `status.json` da AGE). Cenários: `completo/` (um evento de **cada um dos seis tipos**, em CE e CREDN, e uma ressalva de relator indeterminado; `status` ok de 2026-10-20), `sem-eventos/`, `linha-base-primeiro/` (`motivo` "primeiro retrato"), `linha-base-formato/` (`motivo` "formato anterior incompatível"), `intervalo/` (`retrato_anterior.dia` três dias antes de `retrato.dia`), `falha/` (`status` de falha com `falha.{categoria,motivo}` reais da AGE, por exemplo `arquivos_desatualizados`; sem arquivo de mudanças do dia) e `sem-retrato/` (falha com `ultimo_retrato_bom: null`). O `atual.json` de cada pasta tem `meta.versao_formato` 3 e **itens completos no formato da versão 3** (derivados de itens reais do `data/atual.json`, acrescentando `ultimo_status_sequencia`), de modo que passem em `retratos.ler`; dois deles têm `principal_nao_localizada: true`. Ids, identificações e links vêm de itens reais; o que for inventado (motivos, relatores trocados) fica anotado em `tests/fixtures/aviso/README.md`, que também diz que os arquivos são sintéticos e derivados dos contratos.
- [X] T002 [P] Criar `tests/fixtures/aviso/telegram/` com as respostas da Bot API no formato publicado pelo Telegram: `ok.json` (`{"ok": true, "result": {...}}`), `erro-400.json` (`"Bad Request: message is too long"`), `erro-401.json` (`"Unauthorized"`), `erro-403.json` (`"Forbidden: bot was kicked from the group chat"`), `erro-429.json` (`"error_code": 429` com `parameters.retry_after: 3`) e `erro-429-longo.json` (`retry_after: 600`). Nenhum deles contém token nem chat_id. Registrar no `tests/fixtures/aviso/README.md` que são exemplos do formato, não capturas.
- [X] T003 Criar `tests/aviso_sinteticos.py` com construtores de dicionários que seguem os contratos: `evento(tipo, comissao="CE", id=..., **campos)` (os seis tipos, com `identificacao`, `link` e os campos próprios do contrato), `mudancas(eventos=(), ressalvas=(), linha_de_base=None, dia="2026-10-20", dia_anterior="2026-10-19")` (com `meta.total_eventos` e `total_por_tipo` calculados), `status_ok(...)`, `status_falha(...)`, `atual(itens=(), versao=3)` e `muitos_eventos(n, comissoes=("CE", "CREDN"))`. Em `tests/test_aviso_sinteticos.py` testar que cada arquivo de T001 (`atual.json` por `retratos.ler`) e cada saída dos construtores passa em `mudancas.validar_arquivo`/`status.ler_status`/`retratos.ler` conforme o caso, para as fixtures nunca divergirem dos contratos.

**Checkpoint**: fixtures e construtores válidos pelos validadores existentes.

**Commit**: `test(AVI): fixtures e construtores sintéticos do resumo diário`.

---

## Fase 2: Fundação (bloqueia as histórias)

**Propósito**: peças pequenas que várias histórias usam. Cada tarefa começa pelo teste.

- [X] T004 [P] Em `tests/test_config.py` escrever os testes da tabela `[aviso]`: sem a tabela valem `pagina_url = ""` e `repositorio = "joaorighetto/monitor-comissoes"`; `pagina_url` deve ser "texto, vazio ou começando com `https://`" (`http://`, número e espaços no começo → falha `configuracao`); `repositorio` deve ser "texto no formato `dono/nome`" (sem barra, com duas barras, vazio → falha); campo desconhecido em `[aviso]` falha, como em `[execucao]`; `aviso` que não é tabela falha. Depois, em `src/monitor_comissoes/config.py`, acrescentar `pagina_url: str = ""` e `repositorio: str = "joaorighetto/monitor-comissoes"` a `Config` (**no fim**, com padrão) e `_ler_aviso(tabela)` no molde de `_ler_execucao`. Os testes atuais de `Config` continuam passando sem alteração.
- [X] T005 [P] Em `tests/test_entradas.py` escrever os testes de `src/monitor_comissoes/entradas.py` (FR-001, FR-022; regras 1 a 7 de `data-model.md`): `ler_mudancas(caminho, status)` devolve o documento quando o arquivo existe, tem `meta`, `eventos` e `ressalvas`, `meta.versao_formato == 1`, `meta.data == status.data_referencia`, `meta.retrato.dados_camara_em == status.ultimo_retrato_bom.dados_camara_em`, `meta.total_eventos == len(eventos)` e a soma de `meta.total_por_tipo` também, todo evento com `tipo` conhecido, `identificacao`, `comissao` e `link` não vazio e os campos próprios do tipo, e linha de base com `eventos` e `ressalvas` vazios. Cada violação levanta `FalhaDeEnvio` (nasce em `src/monitor_comissoes/erros.py` ao lado de `FalhaDeColeta`, **sem categoria** e sem tocar em `CATEGORIAS` nem em `REPETIVEIS`; `telegram.py` a importa de lá) com o nome do arquivo e o motivo: arquivo ausente, JSON ilegível, versão desconhecida, data diferente, retrato diferente do `status.json`, contagem que não bate, evento sem `link`, tipo desconhecido, linha de base com evento. `ler_itens_do_atual(caminho)` devolve os itens com `identificacao`, `comissao`, `link` e `principal_nao_localizada` e exige `meta.versao_formato` 2 ou 3 (versão 1, 4 ou ausente falha) e os quatro campos em todo item (ausente ou de tipo errado falha). `ler_status_do_dia(caminho)` devolve `None` para arquivo ausente e usa `status.ler_status` (inválido propaga `ValueError`, que a orquestração converte em `FalhaDeEnvio`). Depois criar `entradas.py`.
- [X] T006 [P] Em `tests/test_envio.py` escrever os testes de `src/monitor_comissoes/envio.py` (`contracts/envio-json.md`): `ler_registro(caminho)` devolve `{"normal": None, "erro": None}` para arquivo ausente; lê o arquivo válido; falha (`FalhaDeEnvio`, com o nome do arquivo) para JSON ilegível, não objeto, `versao_formato` diferente de `1`, campo a mais ou a menos em `ultimo_envio`, valor que não é `null` nem `AAAA-MM-DD`. `ja_enviado(registro, tipo, dia)` é verdadeiro só quando `registro[tipo] == dia`. `gravar_registro(caminho, tipo, dia)` grava com `saida.gravar_atomico` (ordem de campos fixa `versao_formato`, `ultimo_envio.normal`, `ultimo_envio.erro`; UTF-8, indentação de 2 espaços, quebra de linha no fim), preserva o outro tipo, cria a pasta se faltar e, se a gravação falhar, o arquivo anterior fica como estava. Depois criar `envio.py`.
- [X] T007 [P] Em `tests/test_telegram.py` escrever os testes de `src/monitor_comissoes/telegram.py` com `abrir` e `dormir` falsos e as respostas de T002 (R1, R9, R10; `contracts/aviso-cli.md`): `ClienteTelegram(token, chat_id, abrir=..., dormir=...).enviar(texto)` faz **um** `POST` para `https://api.telegram.org/bot<TOKEN>/sendMessage`, `Content-Type: application/json`, corpo com `chat_id`, `text` e `link_preview_options: {"is_disabled": true}`, **sem** `parse_mode`; sucesso é HTTP 200 e `ok: true`. Repetem, no máximo **3 tentativas** no total: erro de rede/timeout e HTTP 5xx (esperas de 5 s e 15 s) e HTTP 429 (espera `parameters.retry_after`, mas `retry_after > 60` falha na hora). Não repetem: 400, 401, 403, 404 e `ok: false` — a falha (`FalhaDeEnvio`) traz o código HTTP e a `description` do Telegram. Resposta que não é JSON ou sem `ok` falha. Segredo: com um token falso reconhecível (`"111111:TOKEN-FALSO-DE-TESTE"`) e um chat_id falso, **nem a mensagem das exceções, nem `str()`, nem `repr()`, nem o log, nem `capsys`** contêm o token ou o chat_id, inclusive quando a exceção do `urllib` repete a URL (`URLError` e `HTTPError` simulados com o token na URL). `abrir` falso é o único meio de rede (o `conftest.py` já bloqueia o resto). Depois criar `telegram.py` com `ClienteTelegram`, a constante `LIMITE_TENTATIVAS`, e `_sem_segredos(texto, token, chat_id)`. Sem dependência nova: só `urllib`, `json`, `time`.
- [X] T008 [P] Em `tests/test_resumo.py` (novo) escrever os testes dos auxiliares de `src/monitor_comissoes/resumo.py`: `tamanho(texto)` conta unidades UTF-16 (`"a"` vale 1, `"⚠"` 1, `"😀"` 2); `dia_mes(iso)` formata `DD/MM` no fuso de Brasília (`"2026-10-20T04:31:26+00:00"` → `"20/10"`; `"2026-10-20T01:30:00+00:00"` → `"19/10"`); `destino_da_pagina(config, dia)` devolve `("veja a página", pagina_url)` com `pagina_url` e `("veja o arquivo do dia", "https://github.com/{repositorio}/blob/main/data/mudancas/AAAA-MM-DD.json")` sem ela (FR-011). Depois criar `resumo.py` com esses três auxiliares e `LIMITE = 4096`, `LIMITE_AVISO = 1200`.

**Checkpoint**: fundação verde; as histórias podem começar.

**Commit**: `feat(AVI): configuração [aviso], leitura das entradas, registro de envio e cliente da Bot API`.

---

## Fase 3: User Story 1 — Ler, todo dia, o que mudou (P1)

**Objetivo**: a mensagem normal com eventos agrupados por comissão e link oficial em cada um (FR-001 a FR-003).

**Teste independente**: formatar `mudancas-completo.json` e conferir agrupamento, conteúdo por tipo e link de cada evento.

- [X] T009 [US1] Em `tests/test_resumo.py` escrever os testes de `montar_normal(mudancas, status, config, hoje)` (sem teto ainda; todos os eventos cabem), conforme `contracts/mensagem.md`: linha 1 `Monitor de comissões · dados de DD/MM · N itens` (com `N = status.ultimo_retrato_bom.total_itens`); linha 2 `K eventos:` com contagens por tipo de `meta.total_por_tipo`, só tipos com contagem maior que zero, na ordem entrou, saiu, situação, relator, parecer, etiquetas (`1 evento:` no singular); um grupo por comissão **com evento**, na ordem de `config.comissoes`, o nome em linha própria e linha em branco entre grupos; cada evento é `• Rótulo: IDENT — detalhe` e, logo abaixo, o link recuado em dois espaços; detalhe por tipo exatamente como na tabela do contrato (`entrou`: `motivo.texto`; `saiu`: `motivo.texto` + ` (apensado a IDENT)` / ` (destino: ÓRGÃO)` / ` (SITUAÇÃO)` nos casos descritos; `situacao`: `DE → PARA` e ` (veio da COMISSÃO_DE)` quando `comissao_de` difere; `relator`: `designado NOME (PARTIDO)`, `devolveu NOME (PARTIDO)`, `NOME_DE (PARTIDO) → NOME_PARA (PARTIDO)`; `parecer`: `parecer do relator`; `etiquetas`: `ganhou A, B; perdeu C`). Conferir também: evento de **parecer não reproduz** tramitações nem conteúdo; nenhum texto de tramitação aparece; a mensagem **não** começa com `⚠`; duas formatações da mesma entrada dão o texto idêntico (FR-025); um item com dois eventos mostra os dois; e `texto` sem espaço no fim de linha; **caracteres especiais** (`_ * [ ] ( ) < > & # ~ \` ` e aspas, vindos de `identificacao`, `motivo.texto`, `de`/`para` e nomes de relator) saem **exatamente como entraram**, sem escape nem remoção (texto puro, FR-018). Depois implementar `montar_normal` em `src/monitor_comissoes/resumo.py` com um `_linha_do_evento(evento)` por tipo.

**Checkpoint**: US1 verde. `uv run pytest tests/test_resumo.py`.

**Commit**: `feat(AVI): mensagem normal com eventos por comissão e links oficiais`.

---

## Fase 4: User Story 2 — Mensagem mesmo sem mudanças (P1)

**Objetivo**: dia sem mudanças, linha de base e intervalo de vários dias (FR-004 a FR-006).

**Teste independente**: formatar `mudancas-sem-eventos.json`, as duas linhas de base e `mudancas-intervalo.json`.

- [X] T010 [US2] Em `tests/test_resumo.py` escrever os testes: arquivo sem eventos e sem linha de base → `Monitor de comissões` + `sem mudanças · N itens · dados de DD/MM` (sem linha de totais, sem grupos); linha de base `"primeiro retrato"` → `linha de base criada com N itens · dados de DD/MM` e `Primeiro retrato: ainda não há com o que comparar.`, com `N = meta.linha_de_base.total_itens`; linha de base `"formato anterior incompatível"` → a mesma segunda linha e `O retrato anterior estava num formato incompatível: a comparação recomeça amanhã.`; retrato anterior com mais de um dia de distância → linha `Cobre de DD/MM a DD/MM: um dia ficou sem retrato.` **logo depois da última linha do cabeçalho** (a linha de totais, ou a linha `sem mudanças · ...`), antes de qualquer grupo; com distância de um dia, nenhuma linha extra; nenhuma dessas mensagens começa com `⚠`. Depois estender `montar_normal` para escolher entre eventos, sem mudanças e linha de base.

**Checkpoint**: US2 verde.

**Commit**: `feat(AVI): mensagem sem mudanças, linha de base e intervalo de vários dias`.

---

## Fase 5: User Story 3 — Dia de muitas mudanças cabe em uma mensagem (P1)

**Objetivo**: teto de 4.096 unidades, seleção alternando entre comissões e "e mais N" exato (FR-008 a FR-011, FR-025).

**Teste independente**: `muitos_eventos(300)` e conferir tamanho, N, alternância e rodapé.

- [X] T011 [US3] Em `tests/test_resumo.py` escrever os testes do teto (`contracts/mensagem.md`, invariantes 1 a 5; research R3, R4, R5): com `muitos_eventos(300)` em CE e CREDN, `tamanho(texto) <= 4096`; as **duas** comissões aparecem; a seleção alterna (CE, CREDN, CE, CREDN... na ordem do arquivo dentro de cada uma) e a mensagem mostra cada grupo na ordem da configuração; a seleção **para** no primeiro evento que não cabe (não pula para um menor); o rodapé é `e mais N, veja a página` + a URL com `pagina_url`, e `e mais N, veja o arquivo do dia` + a URL do arquivo do dia sem ela, e `N == meta.total_eventos − eventos exibidos`; a linha de totais conta **todos** os eventos, inclusive os omitidos; sem excedente não há rodapé; evento exibido nunca aparece sem a linha do link; texto com caracteres fora do BMP (`😀`) é medido em UTF-16 e nunca passa do teto; uma única comissão com todos os eventos também respeita o teto; um evento **sozinho maior que o espaço livre** (campos de 5.000 caracteres) nunca é exibido cortado: a seleção para, `N` conta todos os omitidos e o texto continua dentro do teto; o parâmetro `avisos` (tupla de blocos de texto já formatados, usado pela US6) é **reservado antes** dos eventos e aparece inteiro depois dos grupos e antes do rodapé; um bloco de aviso muito grande é recusado com `ValueError` (quem o monta respeita `LIMITE_AVISO`, T017). Depois implementar a seleção em `montar_normal`: reservar cabeçalho, totais, avisos e o rodapé de pior caso (com a quantidade de dígitos do total de eventos); montar as filas por comissão; retirar um por comissão por vez; medir cada evento inteiro (linha de texto + linha do link) com `tamanho`.
- [X] T012 [US3] Em `tests/test_resumo.py` escrever o teste de propriedade de `montar_normal`: para 40 combinações pseudoaleatórias **fixas** (semente constante, sem relógio) de número de eventos (0 a 400), comprimento dos campos e proporção entre as comissões, o texto tem no máximo 4.096 unidades, `N` bate e cada link de evento exibido aparece exatamente uma vez. Se alguma combinação falhar, corrigir `montar_normal` (não afrouxar o teste).

**Checkpoint**: US3 verde.

**Commit**: `feat(AVI): teto de 4.096 caracteres com seleção alternada e "e mais N"`.

---

## Fase 6: User Story 4 — Saber, no Telegram, que a atualização falhou (P1)

**Objetivo**: mensagem de erro da coleta, "a coleta de hoje não rodou", decisão do tipo e envio com falha visível (FR-012 a FR-018, FR-022).

**Teste independente**: `status-falha.json` e `status-sem-retrato.json` na formatação; Bot API simulada recusando o envio.

- [X] T013 [US4] Em `tests/test_resumo.py` escrever os testes de `montar_erro_da_coleta(status, hoje)` e `montar_coleta_nao_rodou(status_ou_none, hoje)`: a primeira linha é `⚠ ERRO · Monitor de comissões · DD/MM` (sempre `⚠ ERRO`); falha: `A atualização de DD/MM falhou: <motivo> [<categoria>]` com o motivo **sem reescrever** (para cada categoria de `erros.CATEGORIAS` com `status.falha`), e `Nenhuma lista nova foi publicada. Últimos dados bons: dados de DD/MM (N itens).`; sem retrato bom (`ultimo_retrato_bom: null`): `Nenhuma lista nova foi publicada. Ainda não há dados bons.`; sem eventos nem totais do dia (FR-013); coleta que não rodou: `A coleta de hoje (DD/MM) não rodou. Último registro: DD/MM, <resultado>.` e, sem `status.json`, `A coleta de hoje (DD/MM) não rodou. Não há registro de coleta.` (FR-013a); `motivo` enorme (10.000 caracteres) é cortado no fim com `…` e o texto tem no máximo 4.096 unidades. Depois implementar as duas funções em `resumo.py`.
- [X] T014 [US4] Em `tests/test_aviso.py` (novo) escrever os testes de `montar_mensagem_do_dia(caminhos, config, hoje)` em `src/monitor_comissoes/aviso.py` (`caminhos` é a dataclass `Caminhos(atual, status, mudancas, envio)`, com os padrões ao lado do `atual`) (decisão de tipo, research R6; `data-model.md`): `status.json` ausente → tipo `erro`, "não rodou"; `data_referencia` diferente de `hoje` → `erro`, "não rodou", com o último registro; `resultado == "falha"` do dia → `erro` com o motivo; `resultado == "ok"` do dia → `normal`. Falha **sem mensagem** (levanta `FalhaDeEnvio` com o motivo, FR-022): arquivo de mudanças ausente, de versão desconhecida, de data diferente, de retrato diferente do `status.json`, com evento sem link; `status.json` inválido. O dia de Brasília vem de `hoje` (nunca de `datetime.now()` dentro da função). Depois criar `aviso.py` com `Mensagem(tipo, dia, texto)` e `montar_mensagem_do_dia`, usando `entradas.py` e `resumo.py`.
- [X] T015 [US4] Em `tests/test_aviso.py` escrever os testes de `enviar(...)` (sem registro ainda; o registro é a US5), com `ClienteTelegram` de transporte falso injetado e as respostas de T002: sucesso → saída `OK: mensagem normal de DD/MM enviada (N caracteres)` e código `0`; `TELEGRAM_BOT_TOKEN` ou `TELEGRAM_CHAT_ID` ausente ou vazio → `FALHA [envio]: variável TELEGRAM_BOT_TOKEN ausente` (o **nome**, nunca o valor), código `1`, nada enviado; Bot API recusa (400, 401, 403) → `FALHA [envio]: ...` com o código HTTP e a descrição do Telegram, código `1`; fora do ar depois das 3 tentativas → código `1`; **nenhum arquivo de dados é tocado** em qualquer falha (comparar `atual.json`, `status.json`, `mudancas/` e `anterior.json` byte a byte antes e depois — a coleta e o commit do dia continuam, FR-016); o token falso nunca aparece em `stdout`/`stderr`. Depois implementar `enviar` em `aviso.py`.

**Checkpoint**: US4 verde.

**Commit**: `feat(AVI): mensagem de erro, "coleta não rodou" e envio com falha visível`.

---

## Fase 7: User Story 5 — Reexecutar no mesmo dia não duplica (P1)

**Objetivo**: registro de envio e idempotência (FR-019 a FR-021; `contracts/envio-json.md`).

**Teste independente**: duas execuções seguidas com o mesmo `hoje` e o cliente falso contando chamadas.

- [X] T016 [US5] Em `tests/test_aviso.py` escrever os testes de idempotência (cenários 1 a 5 da US5): primeira execução envia **uma** vez e grava `data/envio.json` com `ultimo_envio.normal` do dia; a segunda, no mesmo dia e mesmos dados, **não chama** o cliente, imprime `JÁ ENVIADO: mensagem normal de DD/MM` e sai com `0`; lote regenerado no mesmo dia (arquivo de mudanças de outro conteúdo, mesmo `hoje`) **não** reenvia; falha de envio **não** grava o registro (uma nova execução envia); mensagem de erro do dia enviada e, depois, execução com `status` ok do mesmo dia → envia a **normal** (tipos independentes) e preserva `erro` no registro; normal já enviada e depois falha real do mesmo dia → envia o erro; registro inválido → `FALHA [envio]` sem enviar e **sem sobrescrever** o arquivo; gravação do registro que falha **depois** de o Telegram aceitar → código `1` e mensagem que diz que a mensagem **foi** enviada; dia seguinte envia de novo. Depois estender `enviar` para consultar o registro depois de montar a mensagem e gravá-lo só após o sucesso do cliente.

**Checkpoint**: US5 verde.

**Commit**: `feat(AVI): registro de envio e execução idempotente no dia`.

---

## Fase 8: User Story 6 — Nada que o produto sabe pode sumir (P2)

**Objetivo**: avisos de "relator indeterminado" e "principal não localizada" (FR-007).

**Teste independente**: `mudancas-completo.json` (com ressalva) e `atual.json` (dois itens "principal não localizada").

- [ ] T017 [US6] Em `tests/test_resumo.py` escrever os testes de `blocos_de_aviso(ressalvas, itens_sem_principal, config)`: `⚠ N itens com relator indeterminado:` (singular `1 item`) vindo das `ressalvas`, depois `⚠ N itens com principal não localizada:` vindo dos itens do `atual.json`; cada item `• IDENT (COMISSÃO)` + link recuado; ordem dos itens: comissão da configuração, depois `id`; sem ressalvas e sem itens, nenhum bloco; a **contagem é inteira** e a lista de cada aviso ocupa no máximo **1.200 unidades** — o que não couber vira `• e mais M itens` (sem link, `M` exato, e `contagem == itens exibidos + M`); aviso aparece também na mensagem **sem mudanças** e na **linha de base** (o de "principal não localizada"; na linha de base não há ressalvas); em dia com excedente de eventos o aviso continua inteiro e antes do rodapé. Depois implementar `blocos_de_aviso` em `resumo.py` e passá-lo a `montar_normal`.
- [ ] T018 [US6] Em `tests/test_aviso.py` escrever o teste de ponta a ponta: com `atual.json` e arquivo de mudanças de T001, `montar_mensagem_do_dia` traz os dois avisos; `atual.json` de versão 1 ou 4, sem `principal_nao_localizada` ou com item sem `link` → `FalhaDeEnvio` (nunca aviso omitido em silêncio, constituição III). Depois ligar `entradas.ler_itens_do_atual` a `montar_mensagem_do_dia` (só no tipo normal) e a `enviar`.

**Checkpoint**: US6 verde.

**Commit**: `feat(AVI): avisos de relator indeterminado e principal não localizada`.

---

## Fase 9: User Story 7 — Conferir e testar sem enviar (P2)

**Objetivo**: `texto` sem credencial, sem rede, sem gravar, e garantia de que nenhum segredo vaza (FR-015, FR-023, FR-024).

**Teste independente**: `uv run python -m monitor_comissoes.aviso texto --atual tests/fixtures/aviso/atual.json ...` sem variáveis de ambiente.

- [ ] T019 [US7] Em `tests/test_aviso.py` escrever os testes do CLI `main(argv, ...)`: `texto --hoje AAAA-MM-DD` usa essa data como "hoje" (padrão: a data de Brasília do relógio; a opção existe **só** em `texto`, para conferir um dia salvo; `enviar` não a aceita e `argparse` sai com erro) e imprime `TIPO: normal` (ou `erro`) e o texto, **sem** ler variáveis de ambiente, **sem** cliente, **sem** tocar em `data/envio.json` (arquivo inexistente continua inexistente); `enviar` e `texto` aceitam `--config`, `--atual`, `--status`, `--mudancas`, e `--envio` (só `enviar`) com os padrões **ao lado do `--atual`** (uma execução com `--atual` em `tmp_path` nunca grava em `data/` do repositório); sem subcomando, `argparse` sai com erro; `python -m monitor_comissoes.aviso` roda (`__main__`). Depois implementar `main` e `if __name__ == "__main__"` em `aviso.py` (relógio, cliente e ambiente injetáveis, como `diaria.main`). O CLI não lê `.env`.
- [ ] T020 [US7] Criar `tests/test_sem_segredos.py`: percorre os arquivos versionados do repositório (`src/`, `tests/`, `.github/`, `config.toml`, `data/`, `docs/`, `specs/`, ignorando `.git`, `.venv` e caches) e falha se encontrar algo que case com o formato de token de bot do Telegram (`\b\d{6,}:[A-Za-z0-9_-]{30,}\b`) ou `TELEGRAM_BOT_TOKEN=` / `TELEGRAM_CHAT_ID=` seguido de valor; confere que `.gitignore` contém `.env`; confere que o código não faz `os.environ[...]`/`print` com o token fora de `aviso.py`/`telegram.py` (busca textual). Os tokens falsos dos testes (`111111:TOKEN-FALSO-DE-TESTE`) são curtos o bastante para não casar, e isto fica documentado no próprio teste.

**Checkpoint**: US7 verde.

**Commit**: `feat(AVI): comando texto sem envio e guarda contra segredos versionados`.

---

## Fase 10: Fechamento (workflow, documentação, verificação)

**Propósito**: o agendamento, a configuração real e o fechamento dos documentos.

- [ ] T021 [P] Criar `tests/test_workflow_aviso.py` (verificação textual, no molde de `tests/test_workflow.py`) e depois `.github/workflows/aviso-diario.yml` conforme `contracts/aviso-cli.md`: `cron: "17 10 * * *"`; `workflow_dispatch:` sem entradas; sem gatilho de `push` nem de `pull_request`; `concurrency` com `group: coleta-diaria` e `cancel-in-progress: false` (o **mesmo** grupo de `coleta-diaria.yml`, conferido lendo os dois arquivos); `permissions: contents: write`; pins de `actions/checkout` e `astral-sh/setup-uv` **iguais** aos de `coleta-diaria.yml`; `TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}` e `TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}` só em `env`, nunca dentro de `run:`; nenhum valor de segredo no arquivo; o passo de envio usa `set +e`, guarda o código, em falha restaura `data/envio.json` (`git checkout -- data/envio.json || true`), commita só se `data/envio.json` mudou (`git add data/envio.json` e **nada além disso**), faz `git pull --rebase` e `git push` com segunda tentativa e sai com o código guardado; a mensagem do commit é `aviso: AAAA-MM-DD · normal|erro`.
- [ ] T022 [P] Acrescentar a tabela `[aviso]` comentada a `config.toml` (`pagina_url = ""` e `repositorio = "joaorighetto/monitor-comissoes"`, com os comentários do contrato) e conferir em `tests/test_config.py` que o `config.toml` real carrega com os padrões de `[aviso]`.
- [ ] T023 **Só com o OK explícito do mantenedor sobre o diff** (o `PRODUCT.md` tem autoridade sobre a spec; mostrar o diff antes de gravar), emendar o `PRODUCT.md` (sem mudar nenhuma regra de domínio): D8 passa a listar `data/envio.json` entre os arquivos de histórico; §6.1 diz que o envio roda em workflow próprio, depois da coleta, e que, se a coleta do dia não rodou, a mensagem de erro "a coleta de hoje não rodou" é enviada; §7, na linha "A execução não roda", acrescenta esse aviso e mantém que a falta do resumo continua sendo o sinal se o próprio envio não rodar. Atualizar `tests/test_docs.py` só se um teste já existente depender do texto emendado.
- [ ] T024 Rodar a verificação completa e mostrar a saída: `uv run ruff check . && uv run ruff format --check . && uv run pytest`. Corrigir o que falhar na causa (nunca afrouxar teste).
- [ ] T025 Conferir um a um os casos de aceitação da linha AVI do `ROADMAP.md` e da spec, mapeando cada um a um teste (tabela curta no fim de `specs/005-resumo-telegram/quickstart.md`, seção "Cobertura"): uma mensagem por dia mesmo sem mudanças (T010, T016); links oficiais (T009); até 4.096 caracteres e teto de eventos (T011, T012); "e mais N, veja a página" (T011); falha gera mensagem de erro com a data dos últimos dados bons (T013); segredos fora do código (T007, T020); testes de formatação sem rede (todos). Rodar `uv run python -m monitor_comissoes.aviso texto --atual tests/fixtures/aviso/completo/atual.json --hoje 2026-10-20` (quickstart, passo 2) e conferir o resultado esperado. **Não** mudar o status da linha AVI: ele só vira `concluída` depois da revisão, do OK do mantenedor e do merge.

**Checkpoint**: verificação completa verde.

**Commit**: `feat(AVI): workflow aviso-diario, [aviso] em config.toml e emenda do PRODUCT.md`.

---

## Dependências e ordem

```text
Fase 1 (T001-T003)
   └─> Fase 2 (T004-T008, em paralelo: arquivos diferentes; T005 usa FalhaDeEnvio de erros.py)
          └─> US1 (T009) ─> US2 (T010) ─> US3 (T011-T012)
          └─> US4 (T013-T015)  [depende da US1 para a mensagem normal e de T007 para o envio]
                 └─> US5 (T016)
                 └─> US6 (T017-T018)  [depende da US3 para a reserva dos avisos]
                 └─> US7 (T019-T020)
                        └─> Fase 10 (T021-T025)
```

- T004 a T007 mexem em arquivos diferentes e podem ser feitas em paralelo; T008 também, mas cria `resumo.py`, que as fases 3 a 8 estendem **em sequência** (mesmo arquivo).
- `src/monitor_comissoes/erros.py` ganha `FalhaDeEnvio` já em T005 (T007 a importa). `CATEGORIAS` e `REPETIVEIS` **não mudam**.
- Nenhuma tarefa altera `diaria.py`, `status.py`, `coleta.py`, `mudancas.py` ou o formato do `status.json`.

## Estratégia de implementação

1. **MVP (US1 + US2 + US3 + US4)**: já entrega uma mensagem completa, com teto e envio, e mensagem de erro.
2. **US5** fecha a idempotência: sem ela o workflow não pode ir ao ar (constituição, V).
3. **US6 e US7** completam os avisos e a conferência local; entram antes do workflow.
4. O workflow (T021) só é ativado depois do merge e da configuração dos secrets pelo mantenedor (quickstart, passos 3 e 4); a ordem de ativação está lá.

## Cobertura das exigências da spec

| Exigência | Tarefas |
|---|---|
| FR-001 a FR-003 | T009 |
| FR-004 a FR-006 | T010 |
| FR-007 | T017, T018 |
| FR-008 a FR-011 | T011, T012, T008 |
| FR-012, FR-013, FR-013a | T013, T014 |
| FR-014 a FR-018 | T007, T015 |
| FR-017a | T021 |
| FR-019 a FR-021 | T014, T016 |
| FR-022 | T005, T014, T018 |
| FR-023 | T019 |
| FR-024 | todos os testes; T001 a T003 |
| FR-025 | T009, T011 |
| FR-026 | T024, T025 (nenhum arquivo de coleta, relatoria ou comparação é alterado) |
