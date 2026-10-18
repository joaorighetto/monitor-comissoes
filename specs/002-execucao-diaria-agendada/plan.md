# Implementation Plan: AGE — Execução diária agendada

**Branch**: `claude/sharp-tesla-tvtc79` (sem branch própria de feature) | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-execucao-diaria-agendada/spec.md`

## Summary

Um workflow do GitHub Actions roda todo dia às 03h37 de Brasília (e sob demanda), executa a coleta da COL por um novo módulo, `monitor_comissoes.diaria`, e faz o commit de `data/atual.json` e `data/status.json` pelo bot. O módulo repete a coleta inteira, até 4 vezes com 30 minutos de espera, quando a falha pode ser passageira; confere se o estoque bruto de PL/PLP nas comissões não variou mais de 20% em relação ao último retrato bom; e grava o `status.json` com o resultado, a base do dia seguinte e a data dos últimos dados bons. Em qualquer falha, o `atual.json` não é tocado, só o `status.json` é commitado, e o workflow termina vermelho. Um disparo manual com a confirmação "aceito esta variação" libera um dia legitimamente atípico, só naquela execução.

Abordagem técnica (detalhes em [research.md](research.md)): só biblioteca padrão; a lógica de decisão vive em Python testável sem rede, e o YAML só instala, chama o módulo e faz `git add/commit/push`. A COL ganha uma divisão compatível (`coletar` + gravar) e uma contagem de estoque bruto, sem mudar o formato do `atual.json` nem o comando existente.

## Technical Context

**Language/Version**: Python 3.13 (fixado na constituição e em `.python-version`)

**Primary Dependencies**: nenhuma nova. Biblioteca padrão (`argparse`, `json`, `datetime`, `time`, `pathlib`, `tomllib`). No workflow: `git`, `actions/checkout` e `astral-sh/setup-uv`, os mesmos já usados pelo `ci.yml`. Dependências de desenvolvimento já existentes: `pytest`, `ruff`.

**Storage**: arquivos versionados no Git. Entrada: `config.toml`. Saída: `data/atual.json` (formato da COL, inalterado) e `data/status.json` (novo, [contrato](contracts/status-json.md)).

**Testing**: pytest, com as fixtures reais da COL (`tests/fixtures/camara/`), o transporte falso de `tests/conftest.py`, retratos sintéticos e `dormir` injetável. Nenhum teste usa rede (o guarda `sem_rede` do `conftest.py` segue valendo). O workflow tem um teste textual; o disparo real é verificado manualmente depois do merge (quickstart).

**Target Platform**: GitHub Actions (`ubuntu-latest`) e desenvolvimento local em Linux.

**Project Type**: CLI / biblioteca interna (single project) mais um workflow.

**Performance Goals**: uma execução completa em até ~3 minutos por tentativa (159 s medidos na COL), com a contagem do estoque bruto somando poucos segundos. Janela máxima de ~1h40 com 4 tentativas.

**Constraints**: um agendamento por dia; sem execuções simultâneas; nenhum arquivo de dados pela metade; nenhum segredo além do `GITHUB_TOKEN` padrão; o `atual.json` byte a byte intacto em qualquer falha; job com `timeout-minutes: 240` e coleta limitada por `timeout` de 200 minutos.

**Scale/Scope**: ~1 GB baixado por tentativa (48 arquivos), ~50 itens na lista, ~1.500 itens no estoque bruto; um commit por execução bem-sucedida.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como o plano atende |
|---|---|---|
| I. Simplicidade | ✅ | Sem servidor nem banco. **Nenhuma dependência nova**, de execução ou de desenvolvimento (research.md, R1). O laço de novas tentativas é próprio, em poucas linhas, em vez de uma biblioteca. O teste do workflow é textual para não trazer um parser de YAML. |
| II. Fonte oficial e rastreável | ✅ | Nenhuma regra de inclusão muda. Cada commit do bot traz a mensagem com o resultado, e o `status.json` registra a base e a variação aceita. |
| III. Falha visível | ✅ | Toda falha deixa o workflow vermelho, o `atual.json` intacto e o `status.json` com a categoria e o motivo. O estoque bruto vazio e a variação acima de 20% bloqueiam. Lista vazia continua sendo falha. Nenhuma falha publica lista nova. |
| IV. Testes sem rede | ✅ | Plausibilidade, tentativas, status, mensagem e a restrição da confirmação manual são testados com fixtures e retratos sintéticos, com `dormir` injetável. O YAML é verificado por texto. O disparo real e o push real são conferidos à mão depois do merge (quickstart, passos 4 a 6). |
| V. Idempotência | ✅ | Mesmos dados e mesmo relógio dão arquivos idênticos byte a byte. Duas execuções no mesmo dia dão a mesma lista de itens, e só os momentos de geração e verificação mudam (decisão do mantenedor: cada execução bem-sucedida gera o seu commit). A AGE não envia mensagens, então não há aviso duplicado. Duas execuções não rodam ao mesmo tempo (`concurrency`). |
| VI. Segredos | ✅ | Nenhum segredo. O workflow usa só o `GITHUB_TOKEN` padrão com `contents: write` no job. |
| VII. Escopo controlado | ✅ | Sem Telegram, página, relatoria, comparação de eventos com o dia anterior ou `data/mudancas/`. A mitigação do risco de 60 dias é só proposta no documento. A ampliação da COL (contagem do estoque bruto e a divisão de `executar`) é necessária à checagem da linha AGE e não muda o contrato da COL. |
| Stack fixada | ✅ | Python 3.13, uv, ruff, pytest, GitHub Actions, JSON no Git. |

**Re-avaliação pós-design (Phase 1):** sem violações. O desenho final mantém a biblioteca padrão, não toca no formato do `atual.json` e não introduz tabela de complexidade.

## Pré-requisitos e bloqueios

1. **Verificação real só depois do merge.** O gatilho `schedule` só roda no último commit da branch padrão (documentação do GitHub, research.md R8). Nesta branch, o workflow existe como arquivo e é verificado por teste textual; o disparo real e o agendamento são os passos 4 a 6 do [quickstart](quickstart.md), depois do seu OK e do merge.
2. **Proteção de branch.** Se a branch padrão exigir pull request, o push do bot falha de forma visível. Ajuste é decisão do mantenedor (research.md R14).
3. **Risco de 60 dias.** Não confirmado por fonte oficial (research.md R11); o documento `docs/agendamento-60-dias.md` entrega a análise e as opções para decisão do mantenedor.

## Project Structure

### Documentation (this feature)

```text
specs/002-execucao-diaria-agendada/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── cli.md           # Comando `diaria`, opções, códigos e [execucao] do config
│   ├── status-json.md   # Formato de data/status.json
│   └── workflow.md      # Gatilhos, controles e passos do workflow
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, ainda não criado)
```

### Source Code (repository root)

```text
.github/workflows/
├── ci.yml                        # existente, sem mudança
└── coleta-diaria.yml             # NOVO: cron, disparo manual, commit do bot

config.toml                       # + tabela [execucao] (opcional, com padrões)
docs/
└── agendamento-60-dias.md        # NOVO: confirmação do risco (FR-026)
data/                             # criada pelo primeiro commit do bot
├── atual.json                    # formato da COL, inalterado
└── status.json                   # NOVO

src/monitor_comissoes/
├── erros.py                      # + ESTOQUE_IMPLAUSIVEL, INTERNA; categorias repetíveis
├── config.py                     # + campos de [execucao] com padrões e validação
├── lote.py                       # + contar_estoque_bruto (uma passada a mais)
├── coleta.py                     # `executar` dividido em `coletar` + gravar (compatível)
├── plausibilidade.py             # NOVO: regra do estoque bruto e da variação
├── status.py                     # NOVO: montar, ler, validar e gravar o status.json; gravação do par; mensagem
├── diaria.py                     # NOVO: laço de tentativas, orquestração e CLI `executar`/`mensagem`
└── (demais módulos da COL sem mudança)

tests/
├── test_plausibilidade.py        # NOVO: variação, fronteira de 20%, vazio, base
├── test_status.py                # NOVO: conteúdo, invariantes, base recomposta, mensagem
├── test_diaria.py                # NOVO: tentativas, falhas, intactos, aceitar variação, reexecução
├── test_estoque_bruto.py         # NOVO: contagem sobre as fixtures reais
├── test_workflow.py              # NOVO: verificação textual do YAML
├── test_docs.py                  # NOVO: o documento do risco de 60 dias existe e traz fonte, data e conclusão
├── test_config.py                # + casos de [execucao]
└── (testes da COL sem mudança)
```

**Structure Decision**: projeto único. A lógica nova fica em três módulos pequenos com uma responsabilidade cada (`plausibilidade.py` decide, `status.py` descreve a execução, `diaria.py` orquestra), para que a decisão seja testável sem I/O e o `diaria.py` seja o único que combina tempo, relógio e arquivos. A COL só ganha o necessário: separar `coletar` de `executar` e contar o estoque bruto. O comando da COL e o formato do `atual.json` ficam como estão.

## Complexity Tracking

Sem violações da constituição; tabela vazia.
