# Implementation Plan: COL — Coleta e estoque filtrado

**Branch**: `main-ibd849` (sem branch própria de feature) | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-coleta-estoque-filtrado/spec.md`

## Summary

Um comando (`uv run python -m monitor_comissoes`) baixa os arquivos em lote da Câmara (proposições e autores, do ano mínimo ao ano corrente), consulta os deputados do NOVO em exercício na API, resolve a proposição de referência de cada apensado, atribui as etiquetas `autoria NOVO` e `autor hoje no NOVO` e grava `data/atual.json`. Qualquer falha de fonte, de formato, de frescor, de completude ou de resultado vazio interrompe a execução com erro e deixa o arquivo anterior intacto (gravação atômica).

Abordagem técnica (detalhes em [research.md](research.md)): Python puro, só biblioteca padrão. Os arquivos são baixados um a um para um diretório temporário e lidos em fluxo, em poucas passadas, para que o uso de memória não dependa do volume de ~1 GB. O acesso HTTP passa por uma função injetável, e por isso a suíte roda inteira com fixtures salvas e sem rede.

## Technical Context

**Language/Version**: Python 3.13 (fixado na constituição e em `.python-version`)

**Primary Dependencies**: nenhuma nova. Apenas biblioteca padrão (`urllib.request`, `csv`, `json`, `tomllib`, `tempfile`, `email.utils`, `datetime`, `os`). Dependências de desenvolvimento já existentes: `pytest`, `ruff`.

**Storage**: arquivos. Entrada: `config.toml` (versionado). Saída: `data/atual.json` (JSON versionado no Git). Temporários: diretório temporário apagado ao fim.

**Testing**: pytest, com fixtures reais salvas em `tests/fixtures/camara/` e transporte HTTP falso. Nenhum teste usa rede.

**Target Platform**: Linux (GitHub Actions, futuramente na AGE) e desenvolvimento local. Sem dependência de fuso horário do sistema (Brasília = UTC−3 fixo).

**Project Type**: CLI / biblioteca interna (single project).

**Performance Goals**: caber folgadamente em uma execução diária do Actions. Meta interna: menos de 20 minutos por execução. Medição parcial com o maior arquivo (90 MB: 7 s de download, 0,6 s de leitura, 12 MB de memória) indica folga grande; confirmar na primeira execução completa (research.md, R7).

**Constraints**: memória limitada (a leitura não pode carregar os ~2 milhões de linhas em memória); disco temporário de cerca de 1 GB; nenhuma escrita parcial; nenhum segredo (a API de deputados é pública e não usa token).

**Scale/Scope**: 48 arquivos (24 anos × 2 tipos) e ~1 GB por execução; resultado esperado de ~50 itens (dado da sondagem de 17/10/2026).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como o plano atende |
|---|---|---|
| I. Simplicidade | ✅ | Sem servidor nem banco. **Nenhuma dependência de execução nova**: tudo com biblioteca padrão (research.md, R1). **Justificativa escrita da única ferramenta nova, o `uv_build`** (sistema de build do próprio `uv`, só para instalar o pacote local): com `package = false` o `src/` não entra no caminho do Python no `uv run`, e o comando da feature falharia. Alternativa rejeitada: `PYTHONPATH=src` em todo comando (frágil e herdado pela AGE). Decidido pelo mantenedor em 18/10/2026. |
| II. Fonte oficial e rastreável | ✅ | Todo item leva link oficial. A inclusão segue só o `PRODUCT.md` §5.1 a §5.5. O `meta` registra a origem dos dados e os deputados usados. |
| III. Falha visível | ✅ | Sete categorias de falha terminam com saída de erro e motivo. Lista vazia é falha. Gravação atômica (arquivo temporário + `os.replace`). Nada é gravado antes de tudo ter sido validado. |
| IV. Testes sem rede | ✅ | Transporte HTTP injetável e fixtures salvas. A captura (única, com rede) é ferramenta de desenvolvimento; a suíte nunca a executa. Ver "Pré-requisitos". |
| V. Idempotência | ✅ | Ordem determinística dos itens; relógio injetável; duas execuções no mesmo dia com os mesmos dados geram itens idênticos (só `gerado_em` muda). Sem mensagens, então não há aviso duplicado. |
| VI. Segredos | ✅ | Nenhum segredo é usado nesta feature. |
| VII. Escopo controlado | ✅ | Nada de relatoria, comparação com o dia anterior, agendamento, `status.json`, avisos ou página. A checagem de variação de 20% fica com a AGE. |
| Stack fixada | ✅ | Python 3.13, uv, ruff, pytest, JSON no Git. O arquivo de configuração é TOML lido pela biblioteca padrão; ele não é "armazenamento" de dados (ver research.md, R8). |

**Re-avaliação pós-design (Phase 1):** sem violações. O desenho final continua usando só biblioteca padrão e não introduz tabela de complexidade. O único item de infraestrutura extra é o script de captura de fixtures, que é ferramenta de teste e não código do produto.

## Pré-requisitos e bloqueios

1. **Rede para a Câmara: resolvido.** O domínio `dadosabertos.camara.leg.br` estava bloqueado neste ambiente e foi liberado pelo mantenedor em 18/10/2026. O acesso foi testado (arquivos, API e link oficial). O comando e a captura de fixtures dependem dele; o CI e os testes não.
2. **Captura das fixtures reais** (primeira tarefa): uma execução única de `tests/capturar_fixtures.py`, com acesso à Câmara, grava os recortes reais e comita. As conferências pontuais já feitas (research.md, R2 a R4, R7 e R10) não substituem a captura completa. Se a captura mostrar algo diferente do que o plano assume, o plano é corrigido antes de seguir.

## Project Structure

### Documentation (this feature)

```text
specs/001-coleta-estoque-filtrado/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── cli.md           # Comando, códigos de saída e mensagens de falha
│   └── atual-json.md    # Formato de data/atual.json
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, ainda não criado)
```

### Source Code (repository root)

```text
config.toml                       # comissões e ano mínimo (NOVO)
data/
└── atual.json                    # saída (o comando a cria; o primeiro commit dela é da feature AGE)

src/monitor_comissoes/
├── __init__.py
├── __main__.py                   # ponto de entrada: python -m monitor_comissoes
├── erros.py                      # FalhaDeColeta + categorias
├── config.py                     # ler e validar config.toml
├── transporte.py                 # HTTP com novas tentativas; função injetável
├── deputados.py                  # deputados do NOVO em exercício (API)
├── lote.py                       # baixar, validar e ler em fluxo os arquivos em lote
├── estoque.py                    # referência, etiquetas e filtros (regra de domínio)
├── saida.py                      # montar o JSON e gravar de forma atômica
└── coleta.py                     # orquestração e passadas

tests/
├── fixtures/camara/              # recortes reais + README de origem
├── capturar_fixtures.py          # ferramenta de captura (não é teste)
├── test_config.py
├── test_transporte.py
├── test_deputados.py
├── test_lote.py
├── test_estoque.py
├── test_saida.py
├── test_aceitacao.py             # os três casos de aceitação e a repetibilidade
└── test_falhas.py                # cada categoria de falha, arquivo anterior intacto
```

**Structure Decision**: projeto único em `src/monitor_comissoes/`. Cada módulo corresponde a uma responsabilidade da spec: `estoque.py` concentra as regras de §5.2 a §5.4 sem I/O, o que permite testá-las com dados pequenos; `lote.py` e `transporte.py` concentram o I/O. O `tests/test_ambiente.py` provisório é removido quando chegar o primeiro teste real.

## Complexity Tracking

Sem violações da constituição; tabela vazia.
