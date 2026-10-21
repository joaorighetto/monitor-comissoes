# Quickstart: PAG — Página pública

Como conferir a feature, do mais barato ao mais real. Contratos em [contracts/](contracts/); modelo em [data-model.md](data-model.md).

## 1. Verificação completa (sem rede)

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Esperado: tudo verde. Os testes de entradas, modelo, HTML, mudanças, CSV, geração ponta a ponta, estáticos, JS (precisa de `node`; sem ele o teste é pulado) e workflow cobrem os casos da spec; nenhum usa a internet.

## 2. Gerar a página

Com os dados de hoje do repositório (os números mudam a cada dia):

```bash
uv run python -m monitor_comissoes.pagina gerar --saida site
```

Esperado: `OK: página gerada com N itens · dados da Câmara de DD/MM · …` e a pasta `site/` com `index.html`, `estilo.css`, `pagina.js`, `fontes/`, `atual.json` e `itens.csv`.

Os passos abaixo que citam números (105 itens, CE 96, CREDN 9) valem para o retrato salvo de 20/10/2026, que não muda. Para repeti-los a qualquer dia, gere dele:

```bash
uv run python -m monitor_comissoes.pagina gerar --atual tests/fixtures/pagina/atual-real.json --status tests/fixtures/pagina/status-ok.json --saida site
```

(O `--mudancas` padrão é a pasta `mudancas/` ao lado do `--atual`, ou seja, as fixtures de mudanças.)

Idempotência:

```bash
uv run python -m monitor_comissoes.pagina gerar --atual tests/fixtures/pagina/atual-real.json --status tests/fixtures/pagina/status-ok.json --saida site-b
```

(Compare com o `site/` gerado do mesmo retrato salvo, comando acima.)

Esperado: os arquivos de `site-b` são idênticos aos de `site` (`diff -r site site-b` sem saída). Apague `site-b` depois.

Falha sem escrever (SC-009): apontar para um `atual.json` quebrado.

```bash
uv run python -m monitor_comissoes.pagina gerar --atual tests/fixtures/pagina/atual-formato-4.json --status tests/fixtures/pagina/status-ok.json --saida site-falha
```

Esperado: `FALHA [pagina]: …versao_formato 4 não suportada…`, código de saída 1 e **nenhuma** pasta `site-falha`.

## 3. Ver no navegador, com e sem JavaScript

```bash
uv run python -m http.server 8000 --directory site
```

Abrir `http://localhost:8000/` e conferir:

- **Topo:** a linha de atualização (`Dados da Câmara de DD/MM (arquivo gerado às HHhMM) · verificado em DD/MM às HHhMM`), sem faixa de erro, e os números (105 itens; CE 96; CREDN 9).
- **Lista:** 105 itens, o mais parado primeiro; cada um com link oficial, ementa, autores com partido, etiquetas, situação, relator, "nesta situação há N dias" e "apensado ao PL X" nos apensados.
- **Chips:** escolher `CE` mostra 96; `CE` + `Relatoria NOVO` mostra só a interseção; "Mostrando N de 105 itens." acompanha. "Todas" e "Todos" voltam a mostrar tudo.
- **Sem JS:** desligar o JavaScript do navegador (DevTools → Settings → Debugger → Disable JavaScript) e recarregar. Esperado: os 105 itens, a mesma ordem, **nenhum** chip e nenhuma faixa de atraso.
- **Celular:** emular 360 px de largura. Esperado: sem rolagem horizontal da página; os chips rolam dentro da própria linha; alvos de toque de pelo menos 44 px; tema escuro legível (emular `prefers-color-scheme: dark`).
- **Faixa de atraso:** no console, `document.getElementById("faixa-atraso").dataset.verificadoEm = "2026-10-18T09:00:00-03:00"` e rodar `PaginaMonitor.verificarAtraso(document, Date.now())`. Esperado: a faixa aparece com o texto de "Dados atrasados".
- **Mudanças:** sem arquivos em `data/mudancas/` (como hoje neste checkout), a seção diz "Ainda não há mudanças registradas." e "Mudanças desde o retrato anterior" diz "sem comparação ainda". Com os arquivos de `tests/fixtures/pagina/mudancas/` (`--mudancas`), a seção mostra os dias, os seis tipos de evento e, no dia de teste, o "e mais N eventos".

Falha da coleta (faixa de erro):

```bash
uv run python -m monitor_comissoes.pagina gerar --atual tests/fixtures/pagina/atual-real.json --status tests/fixtures/pagina/status-falha.json --saida site-erro
```

Esperado: a faixa `A atualização de DD/MM falhou (motivo). Dados de DD/MM.` no topo, e a lista continua a do último retrato bom.

## 4. Baixar dados

Em `http://localhost:8000/`, "Baixar dados": `atual.json` igual ao `data/atual.json` (`diff`), e `itens.csv` abrindo no Excel em português **direto**, em colunas, com os acentos corretos e uma linha por item (105 mais o cabeçalho).

## 5. Ativação no GitHub (uma vez, pelo mantenedor, nesta ordem)

1. Em *Settings → Pages → Source*, escolher **GitHub Actions**. (O código não faz isso: é configuração da conta.)
2. Fazer o merge da PAG.
3. Disparar à mão *Actions → Publicar página → Run workflow* (o `workflow_run` só vale a partir da próxima coleta).
4. Conferir o endereço impresso no passo de deploy. Se não for `https://joaorighetto.github.io/monitor-comissoes/`, corrigir `aviso.pagina_url` no `config.toml`.
5. Abrir o endereço no celular e repetir a seção 3 contra a página publicada.

Esperado: workflow verde, página no ar, `atual.json` e `itens.csv` baixáveis nos endereços de [contracts/site.md](contracts/site.md).

## 6. Conferir a integração com o aviso do Telegram

```bash
uv run python -m monitor_comissoes.aviso texto
```

Esperado (num dia com eventos acima do teto): a mensagem termina com "e mais N, veja a página" e o link é o da página publicada (sem barra duplicada). Com `pagina_url` vazio ela cairia no "veja o arquivo do dia".

## 7. Falha visível

- **Geração falha:** estragar o `atual.json` numa branch de teste e disparar *Publicar página*. Esperado: workflow vermelho, e a página publicada continua a de antes.
- **Coleta que falhou:** depois de uma coleta em falha, o *Publicar página* roda sozinho. Esperado: a página no ar mostra a faixa de erro com o motivo do `status.json` e a lista do último retrato bom.
- **Coleta que não rodou:** 30 horas depois da última verificação, abrir a página. Esperado: a faixa de atraso aparece (com JS).

## Notas operacionais

- **O `workflow_run` só vale a partir do branch padrão.** Até a PAG ser mergeada, só o `workflow_dispatch` funciona.
- **Publicação duplicada:** disparar o workflow duas vezes no mesmo dia publica a mesma página; nada é commitado.
- **DS atualizado:** se o portfólio mudar os tokens ou os chips, recopie conforme `src/monitor_comissoes/pagina/estatico/LEIAME.md`.
- **Coleta em andamento:** o workflow só dispara quando ela termina; um disparo manual no meio de uma coleta publica o último commit existente.

## Limites a lembrar

- A página mostra dados do **dia anterior** (o lote da Câmara sai por volta das 2h; PRODUCT.md, §8).
- A faixa de atraso só aparece com JavaScript e depende do relógio do aparelho.
- A página de projeto no portfólio (EmbedFrame) é feita no repositório Portfolio.

## Cobertura (casos de aceitação da linha PAG do ROADMAP.md)

| Caso de aceitação (ROADMAP.md, linha PAG) | Onde se confere |
|---|---|
| Linha de atualização | `test_pagina_html::test_linha_de_atualizacao`, `test_pagina_modelo::test_linha_de_atualizacao_*`; seção 3 |
| Faixa de erro | `test_pagina_html::test_faixa_de_erro_em_texto_com_role_alert_e_lista_do_ultimo_retrato_bom`, `test_pagina_cli::test_falha_da_coleta_com_retrato_bom_gera_a_pagina_com_a_faixa`; seção 3 |
| Faixa de atraso | `test_pagina_js::test_atrasada_so_acima_de_30_horas`, `test_verificar_atraso_mostra_a_faixa_so_quando_atrasada`, `test_pagina_html::test_faixa_de_atraso_existe_escondida_*`; seção 3 |
| Números | `test_pagina_modelo::test_numeros_*`, `test_pagina_html::test_numeros_em_lista_de_definicoes` |
| Mudanças de 7 dias | `test_pagina_modelo::test_sete_dias_*`, `test_pagina_mudancas` (seis tipos, teto por dia, dia sem arquivo, linha de base) |
| Lista com chips de comissão e de motivo | `test_pagina_modelo::test_chips_*`, `test_pagina_html::test_chips_sao_botoes_*`, `test_pagina_js::test_filtrar_*`, `test_aplicar_*`, `test_clique_*` |
| Ordenada por "parado há" | `test_pagina_modelo::test_ordem_*`, `test_pagina_html::test_a_lista_real_tem_os_105_itens_na_ordem_de_parado_ha` |
| Bloco de limites | `test_pagina_html::test_bloco_de_limites_com_os_sete_limites_do_leitor` |
| Download em JSON e CSV | `test_pagina_csv`, `test_pagina_cli::test_atual_json_publicado_e_identico_byte_a_byte_ao_de_entrada`, `test_itens_csv_publicado_tem_106_linhas`; seção 4 |
| Funciona sem JS | `test_pagina_html::test_os_itens_nunca_nascem_escondidos_*`, `test_pagina_js` (o JS só acrescenta); seção 3 |
| Falha visível: nada é escrito | `test_pagina_cli::test_entrada_ruim_falha_com_codigo_1_e_nao_cria_a_saida`, `test_falha_nao_altera_a_pagina_ja_gerada` |
| Idempotência | `test_pagina_cli::test_duas_execucoes_dao_arquivos_identicos_byte_a_byte` |
| Publicação no Pages | `test_workflow_pagina` (verificação textual); o deploy real é a seção 5 |

**Não inclui** (busca, paginação, histórico de mais de 7 dias, página do portfólio): conferido por busca de texto em `src/monitor_comissoes/pagina/` por `busca`, `search`, `paginação`, `histórico`, `EmbedFrame` e `<input`: nenhuma ocorrência.

## Conferência no navegador (2026-10-20)

Feita no navegador do app (Chromium), com a página gerada do retrato real de 20/10 (`tests/fixtures/pagina/atual-real.json` e `status-ok.json`) e servida por `python -m http.server`.

| O que | Resultado |
|---|---|
| Linha de atualização, números e 105 itens | Certos: "Dados da Câmara de 20/10 (arquivo gerado às 09h05) · verificado em 20/10 às 09h09"; 105, CE 96, CREDN 9, mudanças 6 |
| Fonte do DS | Schibsted Grotesk e IBM Plex Mono carregadas dos arquivos locais |
| Chips | CE: 96; CE + Relatoria NOVO: 80; CREDN + Relatoria NOVO: 4; Autoria NOVO: 20; Todas/Todos: 105. Todos bateram com a contagem feita nos dados do `atual.json`; "Mostrando N de 105 itens." acompanhou |
| Faixa de atraso | Escondida; com `verificadoEm` de 18/10 e `PaginaMonitor.verificarAtraso(document, Date.now())`, apareceu com o texto de "Dados atrasados" |
| Faixa de erro (`status-falha.json`) | "A atualização de 21/10 falhou (a Câmara não atualizou os arquivos). Dados de 20/10." na primeira tela de 360 × 640 (SC-003) |
| Sem JavaScript | Não dá para desligar o JS neste navegador. Conferido o HTML bruto lido com `DOMParser` (que não executa scripts): 105 itens, nenhum `hidden`; só `#filtros` e `#faixa-atraso` nascem escondidos |
| 360 px | Sem rolagem lateral da página; as linhas de chips rolam dentro do próprio contêiner; chips com 44 px |
| Alvos de toque | A primeira medição achou 60 links de "apensado ao PL X" com 19 a 20 px de altura; corrigido com `min-height: var(--touch-min)` e medido de novo: nenhum link, botão ou `summary` com menos de 44 px |
| Temas | Claro e escuro legíveis, com a faixa de erro visível nos dois |
| Quadro incorporado | Um `<iframe>` de 360 px com a página: renderizou, 105 itens, chips funcionando (CREDN: 9), sem rolagem lateral |
| Downloads | `atual.json` (148 573 caracteres) e `itens.csv` (BOM `EF BB BF`, 42 644 bytes) servidos nos endereços de `contracts/site.md` |

**Não conferido aqui:** a abertura do `itens.csv` no Excel em português (não há Excel neste ambiente; a conferência é do mantenedor, seção 4), a página no celular real e o deploy no GitHub Pages (seção 5).
