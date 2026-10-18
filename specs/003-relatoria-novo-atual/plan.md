# Implementation Plan: REL — Relatoria NOVO atual

**Branch**: `claude/feature-rel-spec-kit-k2esac` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-relatoria-novo-atual/spec.md`

## Summary

A coleta passa a ler as tramitações das referências relevantes, determinar o **relator atual** de cada uma (designado na comissão atual, na passagem mais recente, e que não devolveu a matéria), obter o partido de hoje dos relatores e atribuir a etiqueta `relatoria NOVO`. Todo item da lista ganha o relator atual; itens podem passar a existir só por `relatoria NOVO`; quando as tramitações não permitem decidir, o item leva a marca "relator indeterminado". Erro de rede, de formato ou de paginação nas APIs falha a execução inteira, sem tocar no `atual.json`.

Abordagem (detalhes em [research.md](research.md)): só biblioteca padrão. Uma passagem a mais sobre os arquivos em lote reúne os **candidatos** pela coluna `ultimoStatus_uriRelator`; as tramitações (API ao vivo) **confirmam**. A regra do relator é uma função pura sobre a lista de tramitações, testada com respostas reais salvas. O formato do `atual.json` vai a `versao_formato: 2`.

## Technical Context

**Language/Version**: Python 3.13 (constitution).

**Primary Dependencies**: nenhuma nova. Biblioteca padrão (`urllib.request`, `json`, `csv`). Desenvolvimento: `pytest`, `ruff` (já existentes).

**Storage**: arquivos. `data/atual.json` (JSON versionado), `config.toml` sem chave nova. Fixtures em `tests/fixtures/camara/`.

**Testing**: pytest com transporte falso e fixtures reais salvas (lote, tramitações, deputados). Nenhum teste usa rede.

**Target Platform**: Linux (GitHub Actions) e desenvolvimento local.

**Project Type**: CLI / biblioteca interna (projeto único).

**Performance Goals**: acrescentar menos de 2 minutos à execução diária (hoje bem abaixo do limite de 20 minutos da COL; o job tem folga de 240 min). Estimativa: de 40 a 70 pedidos sequenciais de menos de 1 s cada.

**Constraints**: nenhuma escrita parcial; nenhum segredo; a API de tramitações não tem total anunciado nem paginação (research R1), então a completude é validada pelo formato.

**Scale/Scope**: dezenas de referências (itens da lista + candidatos) e algumas dezenas de relatores distintos por dia.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como o plano atende |
|---|---|---|
| I. Simplicidade | ✅ | Sem servidor, banco ou **dependência nova** (research R8). Nenhuma chave de configuração nova: órgãos de apoio e tabela de tipos são regra de domínio fixa. Sem paralelismo nem cache: pedidos sequenciais, que bastam para o volume. |
| II. Fonte oficial e rastreável | ✅ | Cada `relatoria NOVO` traz relator, data da designação e link oficial da ficha de onde foi lido. A inclusão segue só `PRODUCT.md` §5.4 e D3. A regra de `1250`/`1255` como fim da relatoria é interpretação de D3 e está **registrada em research.md R2 para OK do mantenedor**. |
| III. Falha visível | ✅ | Rede, HTTP, JSON, campos, sequência repetida, lista vazia e paginação inesperada falham a execução inteira (categorias existentes `fonte_indisponivel`, `formato_alterado` e `api_deputados`). Indeterminação de conteúdo nunca some: o item leva a marca e o candidato entra na lista. |
| IV. Testes sem rede | ✅ | Transporte injetável; tramitações e deputados reais salvos; casos que não existem nos dados reais derivados dentro do teste a partir de respostas reais. |
| V. Idempotência | ✅ | Função pura sobre os mesmos dados; ordem de etiquetas e de itens determinística; ordenação das tramitações por `sequencia`. Sem mensagens, logo sem aviso duplicado. |
| VI. Segredos | ✅ | As APIs são públicas; nenhum segredo. |
| VII. Escopo controlado | ✅ | Sem histórico de relatores, relatores de outras comissões, comparação com ontem, eventos, Telegram ou página. Nenhuma mudança no contrato da AGE: as falhas usam categorias existentes (R5). |
| Stack fixada | ✅ | Python 3.13, uv, ruff, pytest, GitHub Actions, JSON no Git. |

**Re-avaliação pós-design (Phase 1):** sem violações, tabela de complexidade vazia. As cinco decisões do mantenedor estão registradas abaixo.

## Decisões do mantenedor (18/10/2026)

Todas aprovadas na revisão do plano, uma por uma.

1. **A saída do relator da comissão (`1250` e `1255`) encerra a relatoria** (research R2). Hoje não muda nenhum item: nas 25 histórias reais as duas leituras dão o mesmo resultado.
2. **Sem categoria de falha nova.** Rede e 5xx → `fonte_indisponivel`; formato inesperado → `formato_alterado`; partido do relator → `api_deputados` (research R5). O contrato da AGE não muda.
3. **Recaptura completa das fixtures** (research R7): uma fotografia consistente de 18/10, com ajustes justificados nos testes da COL e da AGE (T003).
4. **Registrar no `PRODUCT.md` §5.4** as três regras que só existiam na spec: saída do relator da comissão, designação de passagem anterior que não vale e marca "relator indeterminado" (com o candidato indeterminado na lista). Commit próprio, tarefa T028; o mantenedor revisa o diff.
5. **Tipo de tramitação de relatoria desconhecido só marca o item** (constitution III lida como "fonte quebrou" = resposta malformada ou incompleta). Consequência registrada: AVI e PAG devem avisar a contagem de itens com "relator indeterminado".

## Project Structure

### Documentation (this feature)

```text
specs/003-relatoria-novo-atual/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── atual-json.md    # Diferenças de data/atual.json (versao_formato 2)
│   └── api-camara.md    # O que a coleta exige das respostas de tramitações e deputados
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, ainda não criado)
```

### Source Code (repository root)

```text
src/monitor_comissoes/
├── lote.py              # + coluna ultimoStatus_uriRelator em Proposicao; ler_ids_relator_novo(...)
├── deputados.py         # + obter_deputado(transporte, url_base, id) -> partido de hoje e nome
├── tramitacoes.py       # NOVO: obter e validar as tramitações de uma proposição (API)
├── relatoria.py         # NOVO: regra pura do relator atual (R2); sem I/O
├── estoque.py           # + etiqueta "relatoria NOVO"; item com relator e marca; candidatos
├── coleta.py            # orquestra: candidatos, tramitações, partidos; VERSAO_FORMATO = 2
└── saida.py             # sem mudança

tests/
├── fixtures/camara/
│   ├── proposicoes-*.csv, proposicoesAutores-*.csv   # recapturados com os casos novos
│   ├── tramitacoes/{id}.json                         # respostas reais (NOVO)
│   └── deputados/{id}.json                           # respostas reais de /deputados/{id} (NOVO)
├── capturar_fixtures.py   # estendido
├── test_relatoria.py      # NOVO: regra pura (reais + derivados)
├── test_tramitacoes.py    # NOVO: validação do formato e falhas
├── test_deputados.py      # + obter_deputado
├── test_lote.py           # + coluna e candidatos
├── test_estoque.py        # + etiqueta, herança por apensação, indeterminado
├── test_aceitacao.py      # + PL 937/2022, PL 3514/2023, PL 4501/2023, PL 1843/2022
└── test_falhas.py         # + falhas de tramitações e de partido; arquivo anterior intacto
```

**Structure Decision**: projeto único, um módulo por responsabilidade, como na COL. `relatoria.py` é função pura sobre dados já lidos (testável sem I/O); `tramitacoes.py` e `deputados.py` concentram o I/O de API; `estoque.py` monta os itens; `coleta.py` só orquestra.

## Fluxo da coleta (acréscimos)

1. Como hoje: deputados do NOVO, download e validação do lote, frescor, etiquetas de autoria, cadeias.
2. **Candidatos por relatoria:** em cada arquivo de proposições, ids das linhas com órgão em `comissoes` e `ultimoStatus_uriRelator` de deputado do NOVO; candidatos = essas linhas e os apensados cuja raiz está no conjunto.
3. As linhas necessárias passam a incluir os candidatos; autores completos dos que estão na comissão.
4. Referência de cada candidato e de cada item com etiqueta; **tramitações lidas uma vez por referência** na comissão.
5. Regra do relator (`relatoria.py`); partido de hoje dos relatores fora do NOVO (`/deputados/{id}`, um pedido por id).
6. Itens = (autoria, autor hoje) ∪ (relatoria NOVO confirmada) ∪ (candidato indeterminado). Lista vazia continua sendo falha.

## Complexity Tracking

Sem violações da constituição; tabela vazia.
