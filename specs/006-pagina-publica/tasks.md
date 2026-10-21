# Tasks: PAG — Página pública

**Input**: documentos de projeto em `specs/006-pagina-publica/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Pré-requisitos**: spec aprovada pelo mantenedor (20/10/2026). Plan e tasks aguardam o OK do mantenedor antes de `/speckit-implement`.

**Testes**: pedidos pelo fluxo (fixtures salvas, nenhum teste com rede). Em cada fase, os testes vêm **antes** da implementação e devem falhar primeiro.

**Formato**: `- [ ] T### [P?] [US?] Descrição com caminho`. `[P]` = arquivos diferentes, sem dependência de tarefa incompleta.

**Regras do repositório (CLAUDE.md)**: commits pequenos e descritivos, sem push; nenhuma troca de branch (a branch, se houver, é decisão do mantenedor); verificação completa: `uv run ruff check . && uv run ruff format --check . && uv run pytest`. Cada fase termina com a verificação completa verde e um ou mais commits (sugestões em "Commit"). O status da linha PAG no `ROADMAP.md` está `em andamento` desde o início da spec; só vira `concluída` depois da verificação completa, dos casos de aceitação, do OK do mantenedor e do merge (T028).

**Ordem das fases**: setup e fixtures → fundação (entradas, gravação) → US1 e US2 (P1) → US3 e US4 (P2) → US5 (P3) → fechamento (workflow, config, PRODUCT.md, verificação, conferência no navegador).

**Constantes fixas** (plan.md e research.md): `TETO_EVENTOS_POR_DIA = 20`; janela de `7` dias (`D-6` a `D`, `D` = dia de Brasília de `meta.gerado_em`); atraso acima de `30` horas (`30 h` exatas não contam); `versao_formato` do `atual.json` em `(2, 3)`, do `status.json` em `1`, do arquivo de mudanças em `1`; todo `href` vindo dos dados começa por `https://www.camara.leg.br/`; CSV com `;`, UTF-8 com BOM, `\r\n`, listas unidas por `" | "`; saída `site/`; arquivos `index.html`, `estilo.css`, `pagina.js`, `fontes/*.woff2`, `atual.json`, `itens.csv`.

**Reaproveitar, não reescrever**: `status.ler_status`, `mudancas.validar_arquivo`, `mudancas.VERSAO_FORMATO`, `mudancas.nome_do_arquivo`, `estoque.BRASILIA`, `resumo.dia_mes`, e em testes `tests/sinteticos.py` (`item`, `retrato`) e `tests/aviso_sinteticos.py` (`evento`, `mudancas`, `status_ok`, `status_falha`).

## Fase 1: Setup e fixtures (sem rede)

**Propósito**: esqueleto, ativos do DS e entradas salvas de que todos os testes dependem. Nenhuma tarefa desta fase usa rede.

- [X] T001 [P] Acrescentar `site/` ao `.gitignore`. Criar o subpacote `src/monitor_comissoes/pagina/` com `__init__.py` (vazio), `__main__.py` (`from .cli import main; raise SystemExit(main())`) e `cli.py` com um `main(argv=None) -> int` que por enquanto só monta o `argparse` do contrato (`gerar` com `--atual`, `--status`, `--mudancas`, `--saida`) e devolve `0`. Em `src/monitor_comissoes/erros.py`, criar `class FalhaDePagina(Exception)` ao lado de `FalhaDeEnvio`: docstring "Falha da geração da página (PAG): leitura das entradas ou gravação da saída. Não é uma `FalhaDeColeta`: não tem categoria e nunca vai para o `status.json`"; `CATEGORIAS` e `REPETIVEIS` **não mudam**.
- [X] T002 [P] Criar `tests/fixtures/pagina/` com os retratos e status, derivados dos arquivos reais: `atual-real.json` (cópia exata de `data/atual.json` de 2026-10-20: `versao_formato` 2, 105 itens, CE 96 e CREDN 9, `gerado_em` `2026-10-20T09:05:07-03:00`, `dados_camara_em` `2026-10-20T04:31:26+00:00`), `atual-formato-4.json` (a mesma cópia com `meta.versao_formato` 4), `status-ok.json` (`resultado` ok, `verificado_em` `2026-10-20T09:09:05-03:00`, `data_referencia` `2026-10-20`, `ultimo_retrato_bom` coerente com o `atual-real.json`), `status-falha.json` (`resultado` falha, `data_referencia` `2026-10-21`, `verificado_em` `2026-10-21T09:00:00-03:00`, `falha.categoria` `arquivos_desatualizados` e `falha.motivo` "a Câmara não atualizou os arquivos", `ultimo_retrato_bom` igual ao de `status-ok.json`), `status-falha-sem-retrato.json` (falha com `ultimo_retrato_bom: null`) e `status-retrato-outro.json` (ok, mas com `ultimo_retrato_bom.dados_camara_em` de outro dia). Escrever `tests/fixtures/pagina/LEIAME.md` dizendo qual arquivo é real e quais são derivados.
- [X] T003 [P] Criar `tests/fixtures/pagina/mudancas/` no formato de `specs/004-mudancas-desde-ontem/contracts/mudancas-json.md`, com ids, identificações e links de itens reais do `atual-real.json` e `meta.retrato.dados_camara_em` igual ao do `atual-real.json` no arquivo do dia 20: `2026-10-20.json` (um evento de **cada um dos seis tipos**, em CE e em CREDN, com `tramitacoes` em pelo menos dois), `2026-10-19.json` (zero eventos, sem linha de base), `2026-10-18.json` (`linha_de_base` "primeiro retrato", `total_itens` 105), `2026-10-16.json` (cobre de `2026-10-14` a `2026-10-16`, ou seja, `retrato_anterior.dia` três dias antes, com um evento `saiu` com `destino.apensado_a`). **Faltam de propósito** os dias 17 e 15 (dia sem arquivo). Acrescentar `tests/fixtures/pagina/mudancas-teto/2026-10-20.json` (25 eventos, para o teto de 20) e `tests/fixtures/pagina/mudancas-invalida-fora-da-janela/` com um `2026-10-20.json` válido e um `2026-10-10.json` **corrompido** (prova que arquivo fora da janela não é lido). Cada arquivo registrado no `LEIAME.md` da pasta como sintético.
- [X] T004 Em `tests/test_pagina_sinteticos.py` testar que cada arquivo de T002 e T003 respeita o contrato pelos validadores existentes (`mud.validar_arquivo` para as mudanças, `status.ler_status` para os status, e para o `atual-real.json` os campos listados em `data-model.md`, `ItemDaLista`), para as fixtures nunca divergirem dos contratos. Criar `tests/pagina_sinteticos.py` com construtores que **reaproveitam** `tests/sinteticos.py` e `tests/aviso_sinteticos.py`: `item_completo(**campos)` (um item v3 com todos os campos da página e `relator`, `apensado_a`, `principal_nao_localizada`, `relator_indeterminado` ajustáveis), `retrato_com(itens, **meta)`, `status_ok(...)`, `status_falha(...)`, `arquivo_de_mudancas(dia, eventos=(), linha_de_base=None, dia_anterior=None)` e `gravar_entradas(pasta, retrato, status, arquivos)` que escreve os três tipos de arquivo numa pasta temporária e devolve os caminhos.
- [X] T005 [P] Escrever `tests/test_pagina_estaticos.py` (R3, R13; os testes de estrutura do CSS e do JS entram aqui e nas fases de cada história): `estilo.css` não contém `http://` nem `https://` (nenhuma URL externa); toda `@font-face` usa `url("fontes/…")` **relativo**, nunca `url("/` ; os quatro `.woff2` citados existem em `estatico/fontes/`; os tokens trazem `--accent: #1d4fb8`, o bloco `prefers-color-scheme: dark` e `data-theme`; `.pf-chip` tem `min-height: 44px`; há uma regra `:focus-visible` e nenhum `outline: none`/`outline: 0` sem substituto; `.pf-chips` tem `overflow-x: auto`; `LEIAME.md` cita a origem (`../Portfolio/design-system`) e a data da cópia. Depois criar `src/monitor_comissoes/pagina/estatico/`: `estilo.css` (a ordem é os tokens de `../Portfolio/design-system/export/tokens.azul.css` **com `url("/fonts/…")` trocado por `url("fontes/…")`**, e depois os trechos usados de `components/bundle.css`: `.pf-wrap`, `.pf-label`, `.pf-muted`, `.pf-mark`, `.pf-h2`, `.pf-h3`, `.pf-btn--link`, `.pf-chips`, `.pf-chip` e suas variações), `fontes/` com os quatro `.woff2` copiados de `../Portfolio/design-system/fonts/` e `LEIAME.md` (origem, data da cópia 2026-10-20, o que foi alterado e como recopiar). **Sem JavaScript novo aqui.**

**Checkpoint**: fixtures e ativos válidos; `tests/test_pagina_sinteticos.py` e `tests/test_pagina_estaticos.py` verdes.

**Commit**: `test(PAG): fixtures, construtores e ativos do DS da página pública`.

---

## Fase 2: Fundação (bloqueia as histórias)

**Propósito**: leitura validada das entradas e gravação tudo-ou-nada, de que todas as histórias dependem.

- [X] T006 Em `tests/test_pagina_entradas.py` escrever os testes de `src/monitor_comissoes/pagina/entradas.py` (R10; `data-model.md`, "Validações"). `ler_atual(caminho)` devolve o documento e levanta `FalhaDePagina` com **o nome do arquivo** e o motivo para: arquivo ausente; JSON ilegível; documento que não é objeto; `meta.versao_formato` fora de `(2, 3)` (1, 4, ausente e `true`); `itens` ausente, não lista ou **vazia**; `meta.total_itens` diferente de `len(itens)`; campo faltando ou de tipo errado em qualquer item (`id` inteiro, `identificacao`, `ementa`, `link`, `comissao`, `situacao` textos não vazios, `autores` lista, `etiquetas` lista, `parado_ha_dias` inteiro, `principal_nao_localizada` booleano); `link`, `apensado_a.link` ou `relator.fonte` que não comece por `https://www.camara.leg.br/`. `ler_status_do_dia(caminho)` falha se o arquivo não existe (`status.json` é obrigatório) e usa `status.ler_status` (o `ValueError` vira `FalhaDePagina`; testar também um `status.json` com `versao_formato` 2). `conferir(atual, status)`: `resultado = "ok"` exige `status.ultimo_retrato_bom.dados_camara_em` igual a `atual.meta.dados_camara_em` e `gerado_em` igual; `resultado = "falha"` exige `ultimo_retrato_bom` **não nulo** e igual ao `atual.json` (o retrato mantido). Usar as fixtures de T002. Depois criar `entradas.py`. Mensagens no tom de `entradas.py` do AVI (`"{o_que} {caminho} …"`).
- [X] T007 Em `tests/test_pagina_entradas.py` (continuação) escrever os testes de `ler_janela(pasta, atual)`: o dia `D` é a data de Brasília de `atual.meta.gerado_em`; a janela é `D-6` a `D`, do mais recente ao mais antigo; para cada dia, se `AAAA-MM-DD.json` existe é lido; se não, o dia vem como ausente. Cada arquivo lido passa por `mud.validar_arquivo` e por `meta.versao_formato == mud.VERSAO_FORMATO`; inválido, de versão desconhecida, ilegível ou com `meta.data` diferente do nome do arquivo falha com `FalhaDePagina` e o nome do arquivo; arquivo **fora** da janela nunca é lido (usar `mudancas-invalida-fora-da-janela/`); o arquivo do dia `D` com `meta.retrato.dados_camara_em` diferente do do `atual.json` falha; pasta inexistente equivale a todos os dias ausentes (sem erro). O retorno é uma lista de 7 itens `(data, documento_ou_None)`. Depois implementar `ler_janela` em `entradas.py`.
- [X] T008 [P] Em `tests/test_pagina_site.py` escrever os testes de `src/monitor_comissoes/pagina/site.py` (R9; `contracts/site.md`, "Garantias"): `gravar(arquivos: dict[str, bytes], saida)` cria a pasta (e subpastas como `fontes/`) e grava cada arquivo por arquivo temporário e `os.replace`; sobrescreve os de nome fixo e **não apaga** outros arquivos da pasta; dois `gravar` seguidos com a mesma entrada dão bytes idênticos; se a gravação de um arquivo falhar (simular `os.replace` com `OSError`), levanta `FalhaDePagina` com "não foi possível gravar {caminho}: …" e nenhum arquivo temporário sobra; um dicionário vazio ou com caminho que sai da pasta (`../x`, caminho absoluto) falha. Depois criar `site.py` com `gravar` e `copiar_estaticos()` (devolve `{caminho: bytes}` de `estatico/estilo.css`, `estatico/fontes/*.woff2`; o `pagina.js` entra na US2).

**Checkpoint**: fundação verde. `uv run pytest tests/test_pagina_entradas.py tests/test_pagina_site.py`.

**Commit**: `feat(PAG): leitura validada das entradas e gravação tudo-ou-nada da página`.

---

## Fase 3: User Story 1 — Ver a lista de hoje e de quando ela é (P1)

**Objetivo**: linha de atualização, números e lista ordenada, com todos os campos do item (FR-001 a FR-009, exceto o que é das outras histórias).

**Teste independente**: gerar a página do `atual-real.json` e do `status-ok.json` e conferir, no HTML, a linha de atualização, os números, a ordem e os campos de cada item.

- [X] T009 [US1] Em `tests/test_pagina_modelo.py` escrever os testes de `src/monitor_comissoes/pagina/modelo.py` (`data-model.md`): `atualizacao(atual, status)` produz `Dados da Câmara de 20/10 (arquivo gerado às 09h05) · verificado em 20/10 às 09h09` para `atual-real.json` + `status-ok.json` (datas e horas em Brasília: `dados_camara_em` `2026-10-20T04:31:26+00:00` → `20/10`, e um caso de virada de dia, `2026-10-20T01:30:00+00:00` → `19/10`); `numeros(atual, janela)` devolve `total_itens` 105, `por_comissao` na ordem de `meta.comissoes` (`CE` 96, `CREDN` 9) e `mudancas` como um de `("eventos", n)` (arquivo do dia `D` com `meta.total_eventos` n), `("linha_de_base", motivo)` ou `("indisponivel", None)` (arquivo do dia `D` ausente) — **nunca `("eventos", 0)` quando o arquivo não existe**; `ordenar(itens)` por `(-parado_ha_dias, id)` com desempate estável e determinístico; `item_da_lista(item)` com autores `Nome (PARTIDO)` na ordem de `ordem`, relator `Nome (PARTIDO)` ou "sem relator atual" quando `relator` é `null`, `parado_ha_dias` com `1 dia` no singular e `N dias` no plural, e as marcas "principal não localizada" e "relator indeterminado". Depois criar `modelo.py` (dataclasses `frozen=True`, sem relógio, sem I/O); reusar `resumo.dia_mes` e `estoque.BRASILIA`.
- [X] T010 [US1] Em `tests/test_pagina_html.py` escrever os testes de `src/monitor_comissoes/pagina/html.py` conforme `contracts/pagina-html.md`, seções "Regras gerais", 1, 3 e 5 (só a lista, sem chips): `lang="pt-BR"`, `charset`, `viewport`, `color-scheme`, `<title>Monitor de comissões</title>`, um único `h1` com `.pf-mark`; `<link rel="stylesheet" href="estilo.css">` e `<script src="pagina.js" defer>` como **único** script; nenhum `<style>`/`<script>` embutido, nenhum atributo `on*`, nenhum caminho começando por `/`; `#atualizacao` com o texto da linha de atualização; a seção "Números" em `<dl>` com `Itens na lista`, uma linha por comissão e `Mudanças desde o retrato anterior` nos três estados (`3`, `linha de base: primeiro retrato`, `sem comparação ainda`); `ol#lista` com **105** `li.item` para o `atual-real.json`, na ordem `(-parado_ha_dias, id)`; cada item com `id="item-{id}"`, título como link para `item.link`, ementa, `dl.item-dados` com Comissão, Situação, "nesta situação há N dias", Autores com partido na data, Relator, e `apensado ao <a>` só quando `apensado_a`; marcas só quando valem; item sem etiqueta não tem `p.item-etiquetas`; **escape (FR-020)**: um item sintético com `<script>alert(1)</script>`, `&`, `"` e `'` na ementa, nos nomes e na situação sai como texto, sem nenhuma tag nova no HTML; todo `href` do documento começa por `https://www.camara.leg.br/` ou é `#…`/`atual.json`/`itens.csv`; duas gerações da mesma entrada dão o mesmo texto. Depois criar `html.py` (função `renderizar(modelo) -> str`; `esc()` é o único caminho de texto para o HTML) e acrescentar ao `estilo.css` os estilos da página (cabeçalho, `.lista`, `.item`, `dl.item-dados`, `.item-marca`, `.pagina-pular`) usando só tokens do DS, sem `outline: none`.
- [X] T011 [US1] Em `tests/test_pagina_cli.py` escrever os testes ponta a ponta de `gerar` (`main(argv)` com pastas temporárias de `gravar_entradas`): com o `atual-real.json` e o `status-ok.json` imprime em `stdout` `OK: página gerada com 105 itens · dados da Câmara de 20/10 · M dias de mudanças · {saida}` (com `M` = dias da janela que tinham arquivo), sai com 0 e grava `index.html`, `estilo.css`, `pagina.js` e `fontes/*.woff2`; **SC-001**: o número de `li.item` é `meta.total_itens`; **idempotência (SC-008)**: duas execuções em pastas diferentes dão arquivos idênticos byte a byte, e a saída não contém hora de geração; o `index.html` do retrato real tem menos de 400 000 bytes. Depois implementar `cli.main` (ler com `entradas`, montar o modelo, renderizar, `site.gravar`) e `site.montar(...)`, e criar `estatico/pagina.js` **mínimo** (`window.PaginaMonitor = {};` e `if (typeof module !== "undefined") module.exports = window.PaginaMonitor;`), que as fases seguintes preenchem; `copiar_estaticos` passa a incluí-lo.

**Checkpoint**: US1 verde. `uv run pytest tests/test_pagina_modelo.py tests/test_pagina_html.py tests/test_pagina_cli.py`.

**Commit**: `feat(PAG): página com linha de atualização, números e lista ordenada por parado há`.

---

## Fase 4: User Story 2 — Nunca confundir dado velho ou falha com lista nova (P1)

**Objetivo**: faixa de erro, faixa de atraso no navegador e geração que falha sem escrever (FR-010 a FR-013).

**Teste independente**: gerar com `status-falha.json` e conferir a faixa de erro; chamar `atrasada` com 30 h e 30 h + 1 s.

- [X] T012 [US2] Em `tests/test_pagina_modelo.py` e `tests/test_pagina_html.py` escrever os testes das faixas (`contracts/pagina-html.md`, seção 2): com `status-falha.json` o modelo traz `FaixaDeErro` e o HTML tem `<p id="faixa-erro" role="alert">` com o texto `A atualização de 21/10 falhou (a Câmara não atualizou os arquivos). Dados de 20/10.` (primeira data = `data_referencia`; segunda = `ultimo_retrato_bom.dados_camara_em` em Brasília); a lista continua a do `atual-real.json`; com `status-ok.json` **não** há `#faixa-erro`; a faixa de atraso existe **sempre**, com `hidden`, `role="status"`, `data-verificado-em` igual ao `verificado_em` do status e o texto `Dados atrasados: a última verificação foi em 20/10 às 09h09, há mais de 30 horas. A atualização diária pode ter parado.`; o significado está no texto: a frase de cada faixa diz sozinha o que aconteceu e o bloco de estilos da página não usa nenhuma cor fora dos tokens do DS (nenhum `#hex`, `rgb(` ou `hsl(`). Depois implementar `faixa_de_erro`/`faixa_de_atraso` em `modelo.py` e a renderização em `html.py` (`header`, depois de `#atualizacao`), e os estilos `.faixa` em `estilo.css` (borda `line-strong`, sem cor de status).
- [X] T013 [P] [US2] Em `tests/test_pagina_js.py` (requer `node`; usar `pytest.importorskip`-equivalente: `shutil.which("node")` e `pytest.skip` com motivo) escrever os testes de `estatico/pagina.js` carregado por `node -e` / `require`: `atrasada(verificadoEm, agora)` é verdadeiro **acima** de 30 horas e falso com 30 horas exatas, 29 h 59 min e em instante futuro; entrada inválida (`""`, `"x"`, `null`) devolve falso (a faixa só aparece com certeza); `verificarAtraso(documento, agora)` usa um `documento` falso mínimo (objeto com `getElementById` devolvendo `{hidden: true, dataset: {verificadoEm: "..."}}`) e remove `hidden` só quando atrasada. Depois implementar `atrasada` e `verificarAtraso` em `pagina.js`; ao carregar no navegador, `verificarAtraso(document, Date.now())` roda uma vez. O arquivo continua sem `eval`, sem `fetch`, sem `XMLHttpRequest` (conferir por busca de texto no teste).
- [X] T014 [US2] Em `tests/test_pagina_cli.py` acrescentar os testes de falha: para cada causa da tabela "Falha" de `contracts/pagina-cli.md` (atual ausente, status ausente, JSON inválido, `versao_formato` 4, lista vazia, `total_itens` diferente, retrato e status de momentos diferentes via `status-retrato-outro.json`, falha sem retrato bom via `status-falha-sem-retrato.json`, arquivo de mudanças da janela corrompido, link fora de `https://www.camara.leg.br/`) o `main` devolve **1**, imprime em `stderr` uma linha `FALHA [pagina]: …` com o nome do arquivo e **não cria** a pasta de saída (**SC-009**); com a pasta de saída já existente com uma página anterior, o conteúdo dela fica **inalterado**; exceção inesperada (simular `RuntimeError` em `html.renderizar`) vira `FALHA [pagina]: RuntimeError: …` e código 1; `status-falha.json` com retrato bom **gera** a página (código 0) com a faixa de erro; argumento inválido sai com 2. Depois completar `cli.main` com o tratamento de `FalhaDePagina` e de `Exception` (nenhuma falha termina sem aviso), em `cli.py`, e `_saida_em_utf8` como em `aviso.py`.

**Checkpoint**: US2 verde. `uv run pytest tests/test_pagina_html.py tests/test_pagina_js.py tests/test_pagina_cli.py`.

**Commit**: `feat(PAG): faixas de erro e de atraso e geração que falha sem escrever`.

---

## Fase 5: User Story 3 — Filtrar por comissão e por motivo, e funcionar sem JS (P2)

**Objetivo**: dois grupos de chips (FilterChips do DS), filtro no navegador e lista completa sem JS (FR-014, FR-015).

**Teste independente**: conferir os chips e os atributos no HTML e, com Node, todas as combinações de `filtrar`.

- [X] T015 [US3] Em `tests/test_pagina_modelo.py` e `tests/test_pagina_html.py` escrever os testes dos chips (`contracts/pagina-html.md`, seção 5; `data-model.md`, `Chip`): grupo Comissão = "Todas" + as siglas de `meta.comissoes` **que têm item**; grupo Motivo = "Todos" + `Autoria NOVO`, `Autor hoje no NOVO`, `Relatoria NOVO` **que têm item**; "Todas"/"Todos" começam com `aria-pressed="true"` e os demais `"false"`; cada chip é `<button class="pf-chip" type="button">` com `data-grupo` (`comissao`/`motivo`) e `data-valor` (sigla, ou `autoria`/`autor-hoje`/`relatoria`, ou vazio); `role="group"` com `aria-label` `Filtrar por comissão` e `Filtrar por motivo`; o contêiner `#filtros` tem o atributo `hidden`; `p#filtro-status` com `aria-live="polite"`; cada `li.item` carrega `data-comissao` e `data-etiquetas` (identificadores separados por espaço; vazio sem etiquetas); **os itens nunca têm `hidden`**; uma comissão sem item não gera chip (retrato sintético só com CE). Depois implementar `chips()` em `modelo.py` e a renderização em `html.py`.
- [X] T016 [P] [US3] Em `tests/test_pagina_js.py` acrescentar os testes de `filtrar(itens, comissao, motivo)` (devolve a lista de ids visíveis; `itens` são `{id, comissao, etiquetas: [...]}`): comissão `CE` só CE; comissão vazia = todas; motivo `relatoria` só quem tem a etiqueta (um item com duas etiquetas aparece sob as duas); **combinação** `CE` + `relatoria` = interseção; combinação sem resultado devolve lista vazia; ordem preservada; e de `aplicar(documento, comissao, motivo)` com um `documento` falso: alterna `hidden` em cada `li.item`, atualiza `aria-pressed` dos botões do grupo e escreve em `#filtro-status` `Mostrando N de M itens.` (`Mostrando 1 de 105 itens.`/`Mostrando 105 de 105 itens.` com `item` no singular se `M` for 1). Ao carregar no navegador o script remove `hidden` de `#filtros` e liga os cliques. Depois implementar em `pagina.js`; nenhum item é escondido antes do primeiro clique.
- [X] T017 [US3] Em `tests/test_pagina_estaticos.py` acrescentar: `#filtros` e os chips têm regras de foco e área de toque no `estilo.css`, `.pf-chips` rola na horizontal dentro do contêiner e a página não define `overflow-x: scroll` em `body`; o HTML gerado inteiro, **sem executar o JS**, contém os 105 itens visíveis (nenhum `hidden` em `li.item`, `#filtros` e `#faixa-atraso` são os únicos `hidden` do corpo da lista). Ajustar `estilo.css` se algum falhar.

**Checkpoint**: US3 verde. `uv run pytest tests/test_pagina_html.py tests/test_pagina_js.py tests/test_pagina_estaticos.py`.

**Commit**: `feat(PAG): chips de comissão e de motivo com filtro no navegador`.

---

## Fase 6: User Story 4 — Ver o que mudou nos últimos 7 dias (P2)

**Objetivo**: a seção "Mudou nos últimos 7 dias" com os seis tipos de evento, os estados do dia e o teto por dia (FR-016).

**Teste independente**: gerar a página com as fixtures de mudanças e conferir os 7 dias, os tipos, o teto e o "e mais N".

- [X] T018 [US4] Em `tests/test_pagina_modelo.py` escrever os testes de `dias_de_mudancas(janela)` (`data-model.md`, `DiaDeMudancas`): sete dias do mais recente ao mais antigo; `estado` `"eventos"`, `"sem_mudancas"` (arquivo sem evento e sem linha de base), `"linha_de_base"` (com `motivo` e `total_itens`) e `"sem_arquivo"`; `intervalo` preenchido só quando `meta.retrato_anterior.dia` é anterior ao dia anterior do arquivo (o de 2026-10-16 cobre 14 a 16); os `20` primeiros eventos "abertos" e o resto "recolhidos" na mesma ordem do arquivo (`mudancas-teto/`: 20 e 5); janela sem nenhum arquivo marca a seção toda como vazia (`vazia=True`). Depois implementar em `modelo.py` (constante `TETO_EVENTOS_POR_DIA = 20`).
- [X] T019 [US4] Em `tests/test_pagina_mudancas.py` escrever os testes da seção (`contracts/pagina-html.md`, seção 4; `data-model.md`, `EventoDaPagina`): `h2#t-mudancas` "Mudou nos últimos 7 dias"; um `article.dia` por dia com `h3` `DD/MM`; textos `Sem mudanças.`, `Linha de base criada com 105 itens (primeiro retrato).`, `Sem arquivo de mudanças neste dia.` e `Cobre de 14/10 a 16/10.`; sem nenhum arquivo, só `Ainda não há mudanças registradas.`; cada `li.evento` com `data-tipo`, rótulo do tipo, identificação como link para `evento.link` e a comissão; **cada um dos seis tipos** com o detalhe da tabela (`entrou`: `motivo.texto` e etiquetas; `saiu`: `motivo.texto`, `destino.orgao`/`situacao` e `apensado a` com link; `situacao`: `de → para` e "veio da CE" só quando `comissao_de` difere; `relator`: `designado`/`devolveu`/`substituído` com `Nome (PARTIDO)` de quem entra e de quem sai; `parecer`: só "parecer do relator" e **nenhuma** descrição de tramitação no texto principal; `etiquetas`: `ganhou: …` e `perdeu: …`); as tramitações, quando existem, num `details.tramitacoes` com `data_hora`, `orgao` e `descricao`; o excedente do teto num `details.mais` com `summary` `e mais 5 eventos de 20/10` (N exato) e **todos os 25 eventos presentes** no HTML (nenhum perdido); `ressalvas` do arquivo **não** aparecem na página; texto com `<`, `&` e aspas vindo de `motivo.texto` e de nomes sai escapado. Depois implementar a seção em `html.py` e os estilos `.dia`, `.eventos`, `.evento`, `details` em `estilo.css`.

**Checkpoint**: US4 verde. `uv run pytest tests/test_pagina_modelo.py tests/test_pagina_mudancas.py`.

**Commit**: `feat(PAG): seção "Mudou nos últimos 7 dias" com os seis tipos de evento`.

---

## Fase 7: User Story 5 — Baixar os dados e conhecer os limites (P3)

**Objetivo**: bloco "Limites", links de download, `atual.json` copiado e `itens.csv` (FR-009, FR-017).

**Teste independente**: gerar a página e conferir o bloco, os links e o CSV linha a linha contra o `atual-real.json`.

- [X] T020 [P] [US5] Em `tests/test_pagina_csv.py` escrever os testes de `src/monitor_comissoes/pagina/tabela.py` (`contracts/site.md`, `itens.csv`): `renderizar(itens) -> bytes` começa com o BOM `EF BB BF`; separador `;`; fim de linha `\r\n`; cabeçalho exato (`identificação;link oficial;ementa;comissão;situação;parado há (dias);etiquetas;autores;relator atual;apensado a;marcas`); uma linha por item, **na ordem da lista da página**; para o `atual-real.json` são 106 linhas (105 mais o cabeçalho) e cada campo bate com o `atual.json` (releitura com `csv.reader(delimiter=";")` sobre o texto decodificado em `utf-8-sig`); listas unidas por `" | "` (`autoria NOVO | autor hoje no NOVO`; `Nome (PARTIDO) | Nome (PARTIDO)`); `relator atual` e `apensado a` vazios quando não há; `marcas` com `principal não localizada`/`relator indeterminado`; campo com `;`, aspas e quebra de linha entre aspas, aspas dobradas; **acentos preservados** (`Altera a Lei nº 13.979`, `UNIÃO`); ementa começando com `=` **não é alterada** (risco aceito em `plan.md`); duas gerações dão os mesmos bytes. Depois criar `tabela.py` com `csv.writer`.
- [X] T021 [US5] Em `tests/test_pagina_html.py` e `tests/test_pagina_cli.py` escrever os testes do fim da página e do conjunto de arquivos: `h2#t-limites` "Limites" com os **sete** limites de `contracts/pagina-html.md` (cada um por trecho de texto: "dia anterior", "janela de um dia", "última tramitação", "em exercício", "partido na autoria", "publicação oficial", "relógio do aparelho") e **sem** o limite de arquivamento nem o volume da coleta; `h2#t-baixar` com `<a class="pf-btn pf-btn--link" href="atual.json" download>` e `href="itens.csv" download` e a linha `Fonte: Câmara dos Deputados · dados de 20/10`; `gerar` grava exatamente os arquivos de `contracts/site.md`, e `site/atual.json` é **idêntico byte a byte** a `data/atual.json` de entrada; `itens.csv` do `gerar` tem as 106 linhas; **nenhum arquivo gerado contém** `TELEGRAM`, `BOT_TOKEN` ou `chat_id` (FR-021, VI); com a coleta em falha, os links apontam para os arquivos do último retrato bom. Em `tests/test_sem_segredos.py` acrescentar `.js` e `.css` a `SUFIXOS`, para que o `pagina.js` e o `estilo.css` entrem na varredura de segredos (os `.woff2` binários continuam de fora). Depois implementar os blocos em `html.py`, incluir `atual.json` (bytes lidos do disco, sem reserializar) e `itens.csv` em `site.montar` e ajustar `estilo.css` (links de ação com `min-height: 44px`).

**Checkpoint**: US5 verde. `uv run pytest tests/test_pagina_csv.py tests/test_pagina_html.py tests/test_pagina_cli.py`.

**Commit**: `feat(PAG): bloco Limites, download de atual.json e itens.csv`.

---

## Fase 8: Fechamento (workflow, configuração, documentação, verificação)

**Propósito**: a publicação, o endereço no aviso do Telegram e o fechamento dos documentos.

- [X] T022 [P] Conferir, antes de escrever o workflow, a **versão estável mais recente** de `actions/configure-pages`, `actions/upload-pages-artifact` e `actions/deploy-pages` (documentação oficial ou `gh api repos/actions/<nome>/releases/latest`; nunca de memória) e a SHA de cada tag; registrar as versões e a data da consulta num comentário do workflow. Depois criar `tests/test_workflow_pagina.py` (verificação textual, no molde de `tests/test_workflow_aviso.py`) e `.github/workflows/publicar-pagina.yml` conforme `contracts/pagina-cli.md`: `name: Publicar página`; `on.workflow_run` com `workflows: ["Coleta diária"]` e `types: [completed]`, mais `workflow_dispatch`; `if` que aceita `workflow_dispatch` ou `github.event.workflow_run.head_branch == github.event.repository.default_branch`; **sem** filtro por `conclusion` (publica também depois de coleta em falha); `permissions` exatamente `contents: read`, `pages: write`, `id-token: write`; `concurrency` `group: pagina` com `cancel-in-progress: false`; checkout **sem `ref`**; `astral-sh/setup-uv` na mesma SHA do `ci.yml`; `uv sync --locked`; `.venv/bin/python -m monitor_comissoes.pagina gerar --saida site`; `configure-pages`, `upload-pages-artifact` com `path: site`, `deploy-pages` em `environment: github-pages` e impressão do endereço; nenhum `secrets.` e nenhum `git push`/`git commit` (o teste confere); o `gerar` roda antes do upload (ordem dos passos conferida).
- [X] T023 [P] Preencher `aviso.pagina_url` no `config.toml` com `"https://joaorighetto.github.io/monitor-comissoes/"` (e o comentário: endereço da página publicada pela feature PAG; confirmar no primeiro deploy, quickstart §5). **Atualizar o teste existente** `test_os_valores_de_aviso_do_config_toml_sao_os_padroes` em `tests/test_config.py`, que hoje exige `pagina_url == ""` no `config.toml` do repositório: passa a exigir o endereço acima (e a validação `https://`); renomear o teste para dizer o que confere. Em `tests/test_resumo.py` acrescentar um teste de que `destino_da_pagina` com esse `pagina_url` (termina em `/`) devolve `("veja a página", <o endereço>)` e que a mensagem montada com ele não contém `//` fora do `https://`. Conferir `src/monitor_comissoes/resumo.py` e só alterar se o teste falhar.
- [X] T024 **Só com o OK explícito do mantenedor sobre o diff** (o `PRODUCT.md` tem autoridade sobre a spec; mostrar o diff antes de gravar), emendar o `PRODUCT.md` sem mudar nenhuma regra de domínio: (1) §6.2 e §10, a página é publicada por workflow próprio, disparado ao fim da coleta (decisão de 20/10/2026), e os ativos do DS são copiados para o repositório; (2) §6.2, item 2, a primeira data da faixa de erro é o dia da execução que falhou; (3) §6.2, item 3, "mudanças desde o retrato anterior" diz "sem comparação ainda" quando o arquivo de mudanças do dia do retrato não existe. Em `tests/test_docs.py` (ou teste novo `tests/test_produto_pagina.py`) conferir que o `PRODUCT.md` contém os três textos.
- [X] T025 Conferir a página gerada **no navegador**, seguindo o `quickstart.md` §2 a §4 (gerar `site/`, `python -m http.server`): linha de atualização, números, 105 itens, chips (CE; CE + Relatoria NOVO), JS desligado (105 itens, sem chips, sem faixa de atraso), 360 px sem rolagem lateral, tema escuro, faixa de atraso com o instante alterado no console, faixa de erro com `status-falha.json`, seção de mudanças com `--mudancas tests/fixtures/pagina/mudancas`, links de download e abertura do `itens.csv` com acentos. Conferir também: **SC-003**, que a linha de atualização e a faixa de erro (com `status-falha.json`) aparecem na primeira tela de 360 × 640; e a página **dentro de um `<iframe>`** (criar um `iframe` de 360 px apontando para `http://localhost:8000/` pelo console), que renderiza e rola normalmente (FR do EmbedFrame, edge case "quadro incorporado"). Registrar o resultado (o que foi visto) no fim do `quickstart.md`, seção "Conferência no navegador", com a data. Corrigir o que estiver errado (CSS, texto) e rodar os testes de novo; falha de comportamento já coberta por teste vira teste novo antes da correção.
- [X] T026 Rodar a verificação completa e mostrar a saída: `uv run ruff check . && uv run ruff format --check . && uv run pytest`. Corrigir o que falhar na causa (nunca afrouxar teste). Confirmar que `git status` não mostra `site/` nem arquivos gerados.
- [X] T027 Conferir um a um os casos de aceitação da linha PAG do `ROADMAP.md` e os da spec, mapeando cada um a um teste (a tabela "Cobertura" do `quickstart.md` já existe: atualizar com os nomes reais dos testes) e confirmando que o "Não inclui" (busca, paginação, histórico de mais de 7 dias, página do portfólio) **não** foi implementado: `grep` por `busca`, `paginação`, `search` e `page` em `src/monitor_comissoes/pagina/` e relatório do resultado.
- [ ] T028 **Fora do `/speckit-implement`**: depois do OK do mantenedor e do merge, trocar o status da linha PAG no `ROADMAP.md` de `em andamento` para `concluída`, na mesma mudança que registra o merge.

**Checkpoint**: verificação completa verde; conferência no navegador registrada.

**Commit**: `feat(PAG): workflow publicar-pagina, pagina_url em config.toml e emenda do PRODUCT.md`.

---

## Dependências e ordem

```text
Fase 1 (T001-T005; T001, T002, T003 e T005 em paralelo; T004 depende de T002 e T003)
   └─> Fase 2 (T006 -> T007 em sequência no mesmo arquivo; T008 em paralelo)
          └─> US1 (T009 -> T010 -> T011)
                 └─> US2 (T012 e T013 em paralelo -> T014)
                 └─> US3 (T015 -> T016 [P] -> T017)       [T016 depende de T013 por compartilhar pagina.js e test_pagina_js.py]
                 └─> US4 (T018 -> T019)
                 └─> US5 (T020 [P] -> T021)
                        └─> Fechamento (T022 [P], T023 [P] -> T024 -> T025 -> T026 -> T027 -> T028)
```

- **US1 e US2 são P1** e juntas formam o MVP: a página com a lista, a data dos dados e o aviso de falha. As demais histórias acrescentam sobre ela sem mudar o que já existe.
- **US3 e US4** (P2) são independentes entre si; ambas editam `html.py`, `modelo.py` e `estilo.css`, então são sequenciais, não paralelas.
- **`pagina.js`** é editado pela T011 (mínimo), T013 (atraso) e T016 (filtro): sempre em sequência.
- **T024** exige o OK do mantenedor sobre o diff. **T028** só depois do merge.

## Estratégia de implementação

1. **MVP**: Fases 1 a 4 (setup, fundação, US1 e US2). Já dá uma página correta e que falha de forma visível; os testes cobrem a geração ponta a ponta.
2. **Incremental**: US3 (filtros), US4 (mudanças) e US5 (download e limites), cada uma com verificação completa verde e commit.
3. **Fechamento**: workflow, endereço no aviso, `PRODUCT.md`, conferência no navegador e verificação.
4. **Regras de conduta**: testes primeiro e vendo falhar; nenhuma dependência nova de pacote; nenhum segredo; nenhum commit além dos sugeridos; nenhum push; nenhuma troca de branch.

## Cobertura das exigências da spec

| Requisito | Tarefas |
|---|---|
| FR-001, FR-002 | T006, T007, T010, T011 |
| FR-003, FR-004, FR-005, FR-006, FR-007, FR-008 | T009, T010 |
| FR-009 | T021 |
| FR-010, FR-011, FR-012 | T012, T013 |
| FR-013 | T006, T007, T014 |
| FR-014, FR-015 | T015, T016, T017 |
| FR-016 | T018, T019 |
| FR-017 | T020, T021 |
| FR-018, FR-018a | T022, T008 |
| FR-018b | T023 |
| FR-019 | T005, T010, T017, T025 |
| FR-020 | T010, T019 |
| FR-021 | todas (fixtures, guarda de rede); T021 (sem segredos) |
| SC-001 a SC-010 | T011 (SC-001, SC-008), T014 (SC-002, SC-009), T012 e T025 (SC-003), T017 (SC-004), T016 (SC-005), T019 (SC-006), T025 (SC-007), T026 (SC-010) |
