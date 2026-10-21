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

| Caso de aceitação | Onde se confere |
|---|---|
| Linha de atualização | Seção 3 (topo); `test_pagina_html` |
| Faixa de erro ou de atraso | Seção 3 e 7; `test_pagina_html`, `test_pagina_js` |
| Números | Seção 3; `test_pagina_modelo` |
| Mudanças de 7 dias | Seção 3; `test_pagina_mudancas` |
| Lista com chips de comissão e de motivo, ordenada por "parado há" | Seção 3; `test_pagina_html`, `test_pagina_js` |
| Bloco de limites | `test_pagina_html` |
| Download em JSON e CSV | Seção 4; `test_pagina_csv`, `test_pagina_cli` |
| Funciona sem JS | Seção 3; `test_pagina_html` |
