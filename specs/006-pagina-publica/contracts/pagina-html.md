# Contrato: `index.html`

Estrutura, textos e atributos da página. É o que os testes de `test_pagina_html.py` e `test_pagina_mudancas.py` conferem. Valores de exemplo seguem o `atual.json` de 20/10/2026. Modelos em [../data-model.md](../data-model.md).

## Regras gerais

- `<!doctype html>`, `<html lang="pt-BR">`, `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">`, `<meta name="color-scheme" content="light dark">`, `<title>Monitor de comissões</title>`.
- Um `<link rel="stylesheet" href="estilo.css">` e um `<script src="pagina.js" defer></script>`. Nenhum outro script, nenhum `<style>` ou `<script>` embutido, nenhum atributo `on*`, nenhuma URL fora de `https://www.camara.leg.br/` e do próprio site.
- Todo caminho próprio é **relativo** (`estilo.css`, `pagina.js`, `fontes/…`, `atual.json`, `itens.csv`): a página fica em `/monitor-comissoes/`.
- Todo texto vindo dos dados passa por `html.escape(…, quote=True)`.
- Datas e horas em Brasília: `DD/MM`, `HHhMM`.
- Sem emoji. Textos em português do Brasil.
- Saída determinística: nenhuma hora de geração, nenhum identificador aleatório.

## Ordem das seções

```text
<body>
  <a class="pagina-pular" href="#lista">Ir para a lista</a>
  <header class="pf-wrap">
    <h1>Monitor de <span class="pf-mark">comissões</span></h1>
    <p id="atualizacao" class="pf-muted">…linha de atualização…</p>
    <p id="faixa-erro" role="alert">…</p>            # só se status.resultado = "falha"
    <p id="faixa-atraso" role="status" hidden …>…</p> # sempre; o JS a mostra
  </header>
  <main class="pf-wrap">
    <section aria-labelledby="t-numeros">…números…</section>
    <section aria-labelledby="t-mudancas">…Mudou nos últimos 7 dias…</section>
    <section aria-labelledby="t-lista">…chips + lista…</section>
    <section aria-labelledby="t-limites">…Limites…</section>
    <section aria-labelledby="t-baixar">…Baixar dados…</section>
  </main>
</body>
```

## 1. Linha de atualização

`<p id="atualizacao">` com o texto:

`Dados da Câmara de 20/10 (arquivo gerado às 09h05) · verificado em 20/10 às 09h09`

Em falha da última execução a linha continua dizendo de quando são os dados exibidos e quando a última verificação aconteceu.

## 2. Faixas

| Faixa | Quando | Marcação | Texto |
|---|---|---|---|
| Erro | `status.resultado = "falha"` | `<p id="faixa-erro" role="alert" class="faixa">` (sem `hidden`) | `A atualização de 21/10 falhou (a Câmara não atualizou os arquivos). Dados de 20/10.` |
| Atraso | sempre emitida | `<p id="faixa-atraso" role="status" class="faixa" hidden data-verificado-em="2026-10-20T09:09:05-03:00">` | `Dados atrasados: a última verificação foi em 20/10 às 09h09, há mais de 30 horas. A atualização diária pode ter parado.` |

As faixas têm borda `line-strong` e um rótulo em texto (`Erro` ou `Atraso`) antes da frase: o significado nunca depende de cor (FR-012). O JS remove `hidden` da faixa de atraso quando `Date.now() - Date.parse(data-verificado-em) > 30 h`.

## 3. Números

`<section aria-labelledby="t-numeros">`, `<h2 id="t-numeros">Números</h2>` e uma lista de definições (`<dl>`):

| Termo | Valor |
|---|---|
| `Itens na lista` | `105` |
| `{sigla}` (uma por comissão de `meta.comissoes`) | `96`, `9` |
| `Mudanças desde o retrato anterior` | um de: `3` · `linha de base: primeiro retrato` · `sem comparação ainda` |

## 4. Mudou nos últimos 7 dias

`<h2 id="t-mudancas">Mudou nos últimos 7 dias</h2>`. Um bloco `<article class="dia">` por dia, do mais recente ao mais antigo:

```html
<article class="dia" id="dia-2026-10-20">
  <h3>20/10</h3>
  <!-- um destes: -->
  <p>Sem mudanças.</p>
  <p>Linha de base criada com 105 itens (primeiro retrato).</p>
  <p>Sem arquivo de mudanças neste dia.</p>
  <p class="pf-muted">Cobre de 18/10 a 20/10.</p>   <!-- só se o arquivo cobre mais de um dia -->
  <ul class="eventos"> <li class="evento" data-tipo="entrou">…</li> … </ul>
  <details class="mais"><summary>e mais 12 eventos de 20/10</summary><ul class="eventos">…</ul></details>
</article>
```

- Se nenhum dos 7 dias tem arquivo: no lugar dos blocos, `<p>Ainda não há mudanças registradas.</p>`.
- Os 20 primeiros eventos do dia ficam em `ul.eventos`; o excedente, em `details.mais`, na mesma ordem do arquivo. O `summary` diz o número exato.
- Cada `li.evento` traz `data-tipo`, o rótulo do tipo em texto, a identificação como `<a href="{link}">`, a comissão e o detalhe da tabela de `data-model.md` (`EventoDaPagina`). As tramitações, quando houver, vão num `<details class="tramitacoes">` por evento.
- O parecer informa que houve parecer do relator; não reproduz o conteúdo.

## 5. Lista

`<h2 id="t-lista">Lista</h2>`, depois:

```html
<div id="filtros" hidden>
  <div class="pf-chips" role="group" aria-label="Filtrar por comissão">
    <button class="pf-chip" type="button" aria-pressed="true" data-grupo="comissao" data-valor="">Todas</button>
    <button class="pf-chip" type="button" aria-pressed="false" data-grupo="comissao" data-valor="CE">CE</button>
    …
  </div>
  <div class="pf-chips" role="group" aria-label="Filtrar por motivo">
    <button … data-grupo="motivo" data-valor="">Todos</button>
    <button … data-grupo="motivo" data-valor="autoria">Autoria NOVO</button> …
  </div>
  <p class="pf-muted" id="filtro-status" aria-live="polite"></p>   <!-- "Mostrando 12 de 105 itens." -->
</div>
<ol id="lista" class="lista">
  <li class="item" id="item-2267727" data-id="2267727" data-comissao="CE" data-etiquetas="autoria autor-hoje">…</li>
  …
</ol>
```

- `#filtros` nasce `hidden`; o JS o libera (FR-015). Os itens nunca nascem escondidos.
- Chips: só os que têm item (`data-model.md`, `Chip`), na ordem de `meta.comissoes` e `Autoria`, `Autor hoje`, `Relatoria`. "Todas" e "Todos" sempre existem e começam com `aria-pressed="true"`.
- A ordem do `ol` é `(-parado_ha_dias, id)`.

### Cada item

```html
<li class="item" …>
  <h3 class="item-titulo"><a href="https://www.camara.leg.br/propostas-legislativas/2267727">PL 5594/2020</a></h3>
  <p class="item-ementa">Altera a Lei nº 13.979, …</p>
  <p class="item-etiquetas"><span class="etiqueta">autoria NOVO</span> <span class="etiqueta">autor hoje no NOVO</span></p>
  <dl class="item-dados">
    <dt>Comissão</dt><dd>CE</dd>
    <dt>Situação</dt><dd>Aguardando Parecer</dd>
    <dt>Parado há</dt><dd>nesta situação há 1302 dias</dd>
    <dt>Autores</dt><dd>Adriana Ventura (NOVO), Paula Belmonte (CIDADANIA), Aline Sleutjes (PSL)</dd>
    <dt>Relator</dt><dd>Diego Garcia (UNIÃO)</dd>
    <dt>Apensado</dt><dd>apensado ao <a href="…">PL 155/2019</a></dd>        <!-- só se apensado_a -->
  </dl>
  <p class="item-marca">principal não localizada</p>                         <!-- só se a marca vale -->
  <p class="item-marca">relator indeterminado</p>
</li>
```

- `Relator`: `Nome (PARTIDO)`; se `relator` é `null`, `sem relator atual`. Se `relator_indeterminado` não é nulo, a marca `relator indeterminado` aparece além do campo.
- `Parado há`: `nesta situação há N dias` (singular `1 dia`).
- `Autores`: na ordem de `autores[].ordem`, cada um `Nome (PARTIDO na data)`.
- Item sem etiqueta: `data-etiquetas=""` e nenhum `p.item-etiquetas`.

## 6. Limites

`<h2 id="t-limites">Limites</h2>` e uma lista (`<ul>`) com os limites do PRODUCT.md, §8 que valem para o leitor, em linguagem do leitor:

1. Os dados são do dia anterior: o lote da Câmara é gerado por volta das 2h.
2. O motivo de entrada tem janela de um dia: um item que chegou à comissão na madrugada do dia do lote anterior pode aparecer como "ganhou etiqueta".
3. A última tramitação de cada retrato: as intermediárias vêm da API, só para os itens da lista.
4. "Hoje no NOVO" quer dizer em exercício: deputado licenciado ou afastado perde as etiquetas enquanto estiver fora.
5. O partido na autoria é o que a Câmara registra, com sobreposições curtas nas trocas.
6. Esta página não é publicação oficial: o link de cada item leva à página oficial da Câmara, que é onde vale conferir.
7. O aviso de dados atrasados é calculado no navegador, com o relógio do aparelho, e não aparece sem JavaScript.

(O limite do §8 sobre arquivamento e o volume da coleta não afetam o leitor da página e ficam fora do bloco.)

## 7. Baixar dados

`<h2 id="t-baixar">Baixar dados</h2>`, dois links com `download`:

- `<a class="pf-btn pf-btn--link" href="atual.json" download>Baixar atual.json</a>`
- `<a class="pf-btn pf-btn--link" href="itens.csv" download>Baixar itens.csv</a>`

Junto, a linha de fonte: `Fonte: Câmara dos Deputados · dados de {DD/MM}` (a mesma data da linha de atualização), para o EmbedFrame do portfólio citar.

## Comportamento do `pagina.js`

- Ao carregar: remove `hidden` de `#filtros`; mostra `#faixa-atraso` se a verificação passou de 30 horas.
- Clique em chip: `aria-pressed` passa para o clicado e sai dos outros do mesmo grupo; cada `li.item` fica visível se (`comissao` vazia ou igual a `data-comissao`) e (`motivo` vazio ou contido em `data-etiquetas`); `#filtro-status` recebe `Mostrando N de M itens.`
- Nenhum outro efeito. Sem requisição de rede.
- O arquivo expõe `window.PaginaMonitor = {filtrar, atrasada, aplicar, verificarAtraso}` para os testes com Node e para a conferência manual do quickstart: `atrasada(verificadoEm, agora)` e `filtrar(itens, comissao, motivo)` são puras; `aplicar(documento, comissao, motivo)` e `verificarAtraso(documento, agora)` são a cola de DOM, que recebem o `document` por parâmetro. Em Node, `module.exports` traz as mesmas funções.
