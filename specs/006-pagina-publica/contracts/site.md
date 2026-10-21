# Contrato: arquivos publicados

O comando `gerar` produz a pasta abaixo (`site/` no workflow) e o workflow a publica inteira no GitHub Pages. Nada disso é commitado.

## Arquivos e endereços

Endereço-base previsto: `https://joaorighetto.github.io/monitor-comissoes/` (a confirmar no primeiro deploy; plan.md, "Riscos aceitos").

| Caminho | Endereço | Conteúdo |
|---|---|---|
| `index.html` | `{base}/` | A página ([pagina-html.md](pagina-html.md)) |
| `estilo.css` | `{base}/estilo.css` | Tokens azuis do DS, estilos dos componentes usados e da página |
| `pagina.js` | `{base}/pagina.js` | Chips e faixa de atraso |
| `fontes/*.woff2` | `{base}/fontes/…` | As quatro fontes do DS |
| `atual.json` | `{base}/atual.json` | Cópia **byte a byte** de `data/atual.json` |
| `itens.csv` | `{base}/itens.csv` | A lista em CSV (abaixo) |

Os nomes `atual.json` e `itens.csv` são estáveis: o EmbedFrame do portfólio e quem baixa os dados dependem deles. Mudá-los é uma mudança de contrato.

## `itens.csv`

- Codificação **UTF-8 com BOM** (`EF BB BF`), separador `;`, fim de linha `\r\n`, aspas `"` só quando o campo as exige (`;`, `"` ou quebra de linha), aspas internas dobradas.
- Uma linha de cabeçalho e uma linha por item de `atual.itens`, **na mesma ordem da lista da página** `(-parado_ha_dias, id)`.
- O conteúdo de cada campo é o do `atual.json`. O CSV não traz dado que a página não mostra.

| # | Coluna | Origem | Formato |
|---|---|---|---|
| 1 | `identificação` | `identificacao` | texto |
| 2 | `link oficial` | `link` | URL |
| 3 | `ementa` | `ementa` | texto |
| 4 | `comissão` | `comissao` | sigla |
| 5 | `situação` | `situacao` | texto |
| 6 | `parado há (dias)` | `parado_ha_dias` | inteiro |
| 7 | `etiquetas` | `etiquetas` | rótulos unidos por ` \| ` |
| 8 | `autores` | `autores` | `Nome (PARTIDO)` unidos por ` \| `, na ordem de `ordem` |
| 9 | `relator atual` | `relator` | `Nome (PARTIDO)`; vazio se não há relator |
| 10 | `apensado a` | `apensado_a.identificacao` | texto; vazio se não é apensado |
| 11 | `marcas` | `principal_nao_localizada`, `relator_indeterminado` | `principal não localizada`, `relator indeterminado`, unidos por ` \| `; vazio se nenhuma |

Exemplo (linha do PL 5594/2020, quebrada aqui só para leitura):

```text
PL 5594/2020;https://www.camara.leg.br/propostas-legislativas/2267727;Altera a Lei nº 13.979, …;CE;Aguardando Parecer;1302;autoria NOVO | autor hoje no NOVO;Adriana Ventura (NOVO) | Paula Belmonte (CIDADANIA) | Aline Sleutjes (PSL);Diego Garcia (UNIÃO);;
```

## Garantias

1. **Idempotência**: a mesma entrada produz os mesmos bytes em todos os arquivos.
2. **Tudo ou nada**: a pasta só é escrita depois de todos os arquivos estarem prontos na memória; falha na geração não escreve nada.
3. **Sem segredos**: nenhum arquivo contém `TELEGRAM_*`, token ou `chat_id`.
4. **Sem terceiros**: nenhuma requisição a outro domínio além de `www.camara.leg.br`, que só é aberto por clique do leitor.
