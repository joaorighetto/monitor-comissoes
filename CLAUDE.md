# Monitor de comissões

Monitor diário de PL e PLP de interesse do NOVO nas comissões da Câmara. O que o produto é e as
regras de domínio estão em `PRODUCT.md`; o recorte de cada feature está em `ROADMAP.md`.

## Ordem de autoridade

constitution (`.specify/memory/constitution.md`) → `PRODUCT.md` → `ROADMAP.md` → `spec.md` →
`plan.md` → `tasks.md` → código.

Cada documento obedece aos anteriores. Em conflito material entre dois deles, **pare e pergunte**;
não escolha um lado em silêncio.

## Fluxo por feature

Uma feature por vez, a da linha correspondente do `ROADMAP.md`:

1. `/speckit-specify`: só o recorte da linha. O "Não inclui" é limite.
2. `/speckit-clarify`, se a spec tiver pontos em aberto.
3. `/speckit-plan`: o "Constitution Check" avalia cada princípio; dependência nova se justifica aqui.
4. `/speckit-tasks`.
5. `/speckit-analyze`: corrija as inconsistências antes de implementar.
6. `/speckit-implement`.
7. Verificação completa (abaixo) e conferência dos casos de aceitação do `ROADMAP.md`.

## Status no ROADMAP.md

Mantenha a coluna Status fiel ao estado real da feature, usando só os valores definidos no
`ROADMAP.md`: `proposta` → `em andamento` quando a spec começar → `concluída` só depois que a
verificação completa e os casos de aceitação passarem. Atualize na mesma mudança que altera o estado.
Não invente valores novos; se o estado não couber nesses valores, pare e pergunte.

## Limites de ação

Não faça commit, push nem troca de branch sem eu pedir. Se um comando do Spec Kit tentar criar ou
trocar de branch, pare e pergunte.

## Verificação completa

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```
