# Ativos do Design System (cópia)

A página pública usa o Design System do portfólio (PRODUCT.md, D9 e §10). A geração roda no GitHub Actions, onde o repositório do portfólio não existe, e a página não pode depender de um CDN; por isso os ativos são **copiados** para cá.

**Origem:** `../Portfolio/design-system` (repositório Portfolio), opção Azul institucional. **Data da cópia:** 2026-10-20.

| Arquivo aqui | Origem |
|---|---|
| `estilo.css` (tokens) | `export/tokens.azul.css`, sem mudança de conteúdo, exceto as fontes (abaixo) |
| `estilo.css` (componentes) | trechos de `components/bundle.css`: base, `.pf-wrap`, `.pf-label`, `.pf-muted`, `.pf-mark`, `.pf-h2`, `.pf-h3`, `.pf-btn--link` e FilterChips (`.pf-chips`, `.pf-chip`) |
| `estilo.css` (página) | estilos da própria página, no fim do arquivo, só com `var()` dos tokens |
| `fontes/*.woff2` | `fonts/`: Schibsted Grotesk (variável) e IBM Plex Mono 400, 500 e 600 |

**Mudança feita na cópia:** as `@font-face` saíram de `url("/fonts/…")` para `url("fontes/…")`, porque a página fica em `/monitor-comissoes/` e não na raiz do domínio.

**Como recopiar** (quando o DS mudar os tokens ou os chips): trocar o bloco dos tokens e os trechos de componentes pelos novos, repetir a troca de `url("/fonts/` por `url("fontes/`, copiar as fontes de novo, atualizar a data acima e rodar `uv run pytest tests/test_pagina_estaticos.py`. Os estilos da página (fim do `estilo.css`) não vêm do DS e ficam como estão.
