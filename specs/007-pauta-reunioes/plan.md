# Implementation Plan: PAU — Pauta das reuniões

**Branch**: `docs/direcao-pauta` (branch atual; nenhuma branch criada ou trocada) | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-pauta-reunioes/spec.md`

## Summary

Um workflow novo checa a pauta três vezes por dia (05:47, 15:17 e 22:47 de Brasília). Cada checagem:

- lê na API os eventos deliberativos da CE e da CREDN de D−7 a D+7 e a pauta de cada um;
- marca os itens com as etiquetas do NOVO e com "leva apensado do NOVO";
- classifica o resultado das reuniões realizadas;
- compara com a última checagem gravada para registrar, uma vez só, as alterações de pauta;
- grava `data/pautas/AAAA-MM-DD.json` e `data/status-pauta.json`.

A falha de qualquer leitura falha só a checagem da pauta. O inventário não muda.

Abordagem (detalhes em [research.md](research.md)): só biblioteca padrão, **nenhuma dependência
Python nova**.

- **Pacote `monitor_comissoes/pauta/`**, separado como o da página. As regras (janela, proposição
  do item, etiquetas, resultado, alterações) são funções puras sobre dicionários; a rede fica num
  módulo só, com o `Transporte` injetável que já existe.
- **Autoria pelo lote, sem baixar o lote** (R8): a coleta diária passa a gravar um índice de
  autoria dos seis tipos da pauta, em `cache/` (fora do Git). O workflow da coleta o salva no cache
  do GitHub Actions, e o da pauta o restaura.
- **Registro único por comparação com a última checagem gravada** (R6): o arquivo do dia guarda a
  última checagem e as alterações acumuladas do dia; a busca pelo id resolve a reunião que sumiu.
- **404 como dado só onde é dado** (R7): `RecursoInexistente`, subclasse de `FalhaDeColeta`, para
  a busca de evento sumido.

## Technical Context

**Language/Version**: Python 3.13 (constituição).

**Primary Dependencies**: nenhuma nova. Biblioteca padrão (`json`, `urllib`, `re`, `datetime`,
`dataclasses`). Desenvolvimento: `pytest`, `ruff` (já existentes). Nova peça de CI: a ação
`actions/cache` v6.1.0 (save na coleta, restore na pauta), fixada por SHA.

**Storage**: JSON versionado no Git: `data/pautas/AAAA-MM-DD.json` e `data/status-pauta.json`
(novos). Fora do Git: `cache/indice-autoria.json`, levado pelo cache do Actions.

**Testing**: pytest com respostas reais salvas da API em `tests/fixtures/pauta/` (capturadas por
`tests/capturar_pautas.py`, ferramenta com rede fora da suíte), variações sintéticas derivadas delas
e a guarda `sem_rede`. Nenhum teste usa rede.

**Target Platform**: Linux (GitHub Actions) e desenvolvimento local.

**Project Type**: CLI / biblioteca interna (projeto único).

**Performance Goals**: uma checagem em menos de 1 minuto. São cerca de 2 + 2 + N_reuniões
chamadas: deputados, órgãos, eventos e uma pauta por reunião (tipicamente de 2 a 6), mais uma por
reunião que sumiu. O índice da coleta acrescenta uma passada pelos arquivos do lote (minutos, dentro
do teto de 200 da coleta).

**Constraints**: falha só da pauta (§7); registro único (princípio V); sem rede nos testes; nenhuma
gravação parcial; o índice de autoria nunca vai para o Git.

**Scale/Scope**: 2 comissões, cerca de 4 reuniões por janela, até ~40 itens por pauta; índice de
~480 mil proposições.

## Constitution Check

*GATE: avaliado antes da pesquisa e reavaliado depois do desenho.*

| Princípio | Avaliação |
|---|---|
| I. Simplicidade | **Passa, com uma justificativa.** Sem servidor nem banco, sem dependência Python nova. A ação `actions/cache` é uma peça nova de CI, justificada abaixo e na tabela de complexidade: sem ela, cada checagem baixaria ~1 GB, ou um índice de ~15 MB entraria no Git todo dia. |
| II. Fonte oficial e rastreável | **Passa.** Toda reunião, item, apensado e alteração tem link oficial (R12). Toda regra de listagem e marca está no PRODUCT.md, §5.8 e §5.9, inclusive as emendas de 24/10/2026 (REQ como proposição do item, "autoria não verificada", "retirada da agenda"). Etiqueta é marca, nunca filtro (D2). |
| III. Falha visível | **Passa.** Erro de rede, resposta malformada, paginação incompleta, índice, inventário ou checagem anterior inválidos falham a checagem inteira, sem arquivo parcial; o motivo vai para `status-pauta.json`, e o workflow fica vermelho. A pauta antiga nunca é regravada como atual. |
| IV. Testes sem rede | **Passa.** Fixtures reais salvas, sintéticas derivadas, transporte falso e guarda `sem_rede`. As tarefas começam pelos testes. |
| V. Idempotência | **Passa.** Cada alteração é detectada contra a última checagem gravada e registrada uma vez; duas checagens sobre a mesma fonte dão o mesmo arquivo, exceto o momento da checagem (como o `gerado_em` do `atual.json`). |
| VI. Segredos fora do código | **Passa.** A checagem não usa credencial: a API da Câmara é pública, e o cache do Actions usa o token implícito do workflow. |
| VII. Escopo controlado | **Passa.** Sem prazo de emendas (PRZ), envio (SEM), página (PGP), mudança no inventário nem eventos não deliberativos. As mudanças fora do pacote da pauta são só a infraestrutura que ela exige: o índice gravado pela coleta e salvo no cache (R8), e a subclasse de 404 no transporte (R7). Nenhuma muda o `atual.json`, o `status.json` nem as mensagens da AVI. |

**Stack fixada**: Python 3.13, uv, ruff, pytest, GitHub Actions, GitHub Pages, JSON no Git. Nada
trocado. O cache do Actions é parte do GitHub Actions; não há emenda à constituição.

**Reavaliação depois do desenho:** continua passando.

### Conferência com o PRODUCT.md e o ROADMAP.md

- O desenho segue D1, D2, D7, D8, §5.2, §5.4, §5.8, §5.9, §7 e §8.
- **Emendas ao §5.8 nesta mudança** (aprovadas pelo mantenedor em 24/10/2026): (1) item cuja
  `proposicao_` é REQ tem o próprio REQ como proposição do item (ampliada no plano, research R4);
  (2) marca "autoria não verificada"; (3) quinto tipo de alteração, "retirada da agenda".
- **D8:** a lista de arquivos de histórico ganha `data/status-pauta.json`. É emenda de redação, já
  feita no PRODUCT.md junto com este plano, sem conflito material (a PAU já tinha os arquivos de
  pauta em D8).
- **Spec, FR-026, ajustado no plano:** o texto aprovado dizia que o workflow da coleta não mudava.
  O índice de autoria (premissa "Autores do lote fora da checagem", que deixou o "como" para o
  plano) exige um passo de cache nele. O FR-026 passa a admitir só esse passo, e o ponto é levado ao
  mantenedor no OK do plano.

### Riscos aceitos

- **Despejo do cache.** O GitHub despeja um cache sem uso há 7 dias. A checagem o usa três vezes
  por dia; se mesmo assim ele sumir, a checagem falha de forma visível até a próxima coleta.
- **Primeiro dia depois do merge.** Até a primeira coleta com o índice, a checagem falha com
  `entrada_invalida` (quickstart, §4).
- **Índice e inventário de coletas diferentes.** Se a checagem roda entre o commit da coleta e o
  `cache/save`, ela usa o índice de ontem com o inventário de hoje. As datas dos dois vão no arquivo
  (`checagem.lote` e `checagem.inventario`), e a checagem seguinte corrige.
- **Hora real versus hora convocada** (R2). A comparação de hora só vale entre duas checagens com a
  reunião ainda convocada; a mudança para o início real durante a reunião não vira alteração.
- **Atraso do agendador.** A checagem das 05:47 tem 90 min de folga até o envio das 07:17. A
  garantia de "checagem do mesmo dia antes do envio" é conferida pela SEM no momento do envio.

## Project Structure

### Documentation (this feature)

```text
specs/007-pauta-reunioes/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── pauta-json.md          # data/pautas/AAAA-MM-DD.json
│   ├── status-pauta-json.md   # data/status-pauta.json
│   ├── indice-autoria.md      # cache/indice-autoria.json
│   └── pauta-cli.md           # CLI, workflow novo e acréscimo à coleta
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
.github/workflows/
├── checagem-pauta.yml        # novo: três checagens por dia, grupo "pauta", cache restore
└── coleta-diaria.yml         # + passo actions/cache/save do índice, só em sucesso

.gitignore                     # + cache/
PRODUCT.md                     # emendas do §5.8 e da D8 (já feitas)
data/
├── pautas/                    # novo: um arquivo por dia
└── status-pauta.json          # novo

src/monitor_comissoes/
├── erros.py                   # + ENTRADA_INVALIDA (fora de CATEGORIAS da coleta)
├── transporte.py              # + RecursoInexistente (404)
├── indice.py                  # novo: construir o índice de autoria a partir do lote; ler e validar
├── coleta.py                  # + índice no Coletado
├── diaria.py                  # + --indice; grava o índice no mesmo gravar_todos
└── pauta/
    ├── __init__.py
    ├── __main__.py
    ├── api.py                 # órgãos, eventos (paginação), evento, pauta; validação das respostas
    ├── regras.py              # puro: situação, proposição do item, grupos, resultado, chaves
    ├── etiquetas.py           # puro: etiquetas, "autoria não verificada", apensados do inventário
    ├── checagem.py            # puro: montar reuniões, comparar com a anterior, montar o arquivo
    ├── arquivos.py            # ler/validar a última checagem, status-pauta, gravar tudo ou nada
    └── cli.py                 # checar e mensagem; orquestração e códigos de saída

tests/
├── capturar_pautas.py         # ferramenta com rede (não é teste)
├── fixtures/pauta/            # respostas reais salvas + manifesto.json
├── pauta_sinteticos.py        # variações das respostas reais e transporte falso da pauta
├── test_pauta_sinteticos.py   # fixtures carregam; construtores no formato real
├── test_pauta_api.py          # órgãos, eventos, paginação, evento (404), pauta; validação
├── test_pauta_arquivos.py     # última checagem, status-pauta, gravação tudo ou nada
├── test_indice.py             # índice: construção pelo lote de fixtures, leitura, falhas
├── test_pauta_regras.py       # situação, proposição do item (R4), grupos, chaves
├── test_pauta_resultado.py    # §5.9 com textos reais
├── test_pauta_etiquetas.py    # etiquetas, autoria não verificada, apensados
├── test_pauta_checagem.py     # janela, montagem, ordem, vista desde
├── test_pauta_alteracoes.py   # cinco tipos, sumiço, registro único, linha de base
├── test_pauta_falhas.py       # cada falha da User Story 6
├── test_pauta_cli.py          # ponta a ponta com transporte falso; mensagem de commit
├── test_pauta_aceitacao.py    # casos reais da spec (83091, 81555)
├── test_workflow_pauta.py     # verificação textual do workflow novo
├── test_transporte.py         # + 404 → RecursoInexistente
├── test_diaria.py             # + índice gravado em sucesso, intocado em falha
└── test_workflow.py           # + passo de cache da coleta
```

**Structure Decision**: projeto único, como nas features anteriores, com um pacote próprio para a
pauta, como o da página. A orquestração com rede (`cli.py` e `api.py`) fica separada das regras
puras, que os testes exercitam só com dicionários vindos das fixtures.

## Complexity Tracking

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Ação `actions/cache` (save na coleta, restore na pauta) | A autoria vem do lote (ROADMAP), e a checagem roda três vezes por dia | Baixar o lote em cada checagem: ~1 GB, três vezes por dia. Commitar o índice: ~15 MB mudando todo dia no repositório público, sem valor de histórico. Consultar autores na API: sem partido na data, o que muda a fonte fixada no ROADMAP |
