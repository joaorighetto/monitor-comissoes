# Specification Quality Checklist: MUD — Mudanças desde ontem

**Purpose**: Validar a completude e a qualidade da spec antes de planejar
**Created**: 2026-10-18
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Sem detalhes de implementação (linguagens, frameworks, APIs) — a spec cita os artefatos do produto (`atual.json`, `data/mudancas/`, API de tramitações, Git), como as specs 001 a 003; o mecanismo para obter o retrato anterior e para buscar motivo e destino fica para o `plan.md`
- [x] Focada no valor para o gabinete (saber o que entrou, saiu e mudou, e por quê)
- [x] Escrita de modo que o dono do produto a confira contra o `PRODUCT.md` (§5.6, §5.7, D6, D8)
- [x] Todas as seções obrigatórias preenchidas

## Requirement Completeness

- [x] Nenhum marcador `[NEEDS CLARIFICATION]` restante (0). **Cinco decisões estão proposta-com-padrão em Assumptions, marcadas "A confirmar no clarify"** (ver Notes)
- [x] Requisitos testáveis e sem ambiguidade (FR-001 a FR-025)
- [x] Critérios de sucesso mensuráveis (SC-001 a SC-009)
- [x] Critérios de sucesso sem detalhe de tecnologia
- [x] Cenários de aceitação definidos para as seis histórias
- [x] Casos de borda identificados (saída e volta, referência diferente, vários motivos, relator indeterminado, licença, dia de muitas mudanças, mudança de formato)
- [x] Escopo delimitado: FR-025 repete o "Não inclui" da linha (envio, página) e acrescenta o que fica com AVI e PAG
- [x] Dependências e premissas identificadas (COL, AGE e REL concluídas; acréscimo ao formato do `atual.json`; commit do arquivo novo pelo workflow)

## Feature Readiness

- [x] Todos os requisitos funcionais têm cenário de aceitação ou critério de sucesso correspondente
- [x] As histórias cobrem o fluxo principal (entrou/saiu, mudanças, linha de base, repetibilidade, falha)
- [x] A feature atende aos resultados mensuráveis de SC-001 a SC-009
- [x] Nenhum detalhe de implementação vaza para a spec além do citado no primeiro item

## Notes

- **Pontos a confirmar no `/speckit.clarify`** (cada um tem um padrão proposto em Assumptions, mas muda contrato ou regra de domínio, então a decisão é do mantenedor):
  1. **Ampliar o `atual.json`** com a sequência do último status da referência (FR-015): altera o contrato da COL e da REL e sobe a versão de formato.
  2. **Transição v1 → v2:** tratar o `atual.json` commitado (formato 1, sem relator) como não comparável, de modo que o primeiro arquivo seja linha de base (FR-002).
  3. **Origem do retrato anterior:** a spec fixa o comportamento (último retrato bom de um dia anterior; nunca o do próprio dia) e deixa o mecanismo para o plano.
  4. **Mudança de sequência sem evento** (só um despacho): sem evento, portanto sem tramitações no arquivo.
  5. **Precedência do motivo de saída** quando mais de um vale. O PRODUCT.md não a define.
- **Risco de conflito com o PRODUCT.md, a verificar no clarify:** nenhum conflito material encontrado. O motivo de "entrou" ("chegou à comissão" vs. "ganhou etiqueta") exige as tramitações do item, porque o retrato anterior só guarda os itens da lista. O PRODUCT.md, §5.6, não diz de onde vem esse dado; a spec admite o motivo "não determinado" em vez de inventar.
- Os itens acima não bloqueiam o `/speckit.clarify` nem o `/speckit.plan`.
