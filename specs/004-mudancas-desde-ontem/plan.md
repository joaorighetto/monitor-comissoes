# Implementation Plan: MUD — Mudanças desde ontem

**Branch**: `claude/stoic-brown-accrz2` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-mudancas-desde-ontem/spec.md`

## Summary

A execução diária passa a comparar o retrato de hoje com o **retrato anterior** (o último de um dia anterior) e a gravar `data/mudancas/AAAA-MM-DD.json` com os eventos entrou, saiu (motivo e destino), situação, relator, parecer e etiquetas, cada um com as tramitações do intervalo. No primeiro dia, ou quando o retrato anterior está num formato antigo, o arquivo é uma **linha de base** sem eventos e com o motivo explícito.

Abordagem (detalhes em [research.md](research.md)): só biblioteca padrão e nenhuma dependência nova.
- **Retrato anterior em arquivo, não no Git.** Uma cópia rotativa `data/anterior.json` é atualizada só quando o `atual.json` existente é de um dia anterior. Assim a reexecução no mesmo dia compara com o mesmo retrato anterior e dá o mesmo arquivo.
- **Estado de quem saiu vem do lote do dia.** O lote traz órgão, situação e apensação de qualquer proposição; os ids do retrato anterior entram no conjunto de linhas lidas.
- **Tramitações do intervalo vêm da API**, limitadas pela sequência do último status do lote de hoje, o que torna o resultado repetível.
- **O `atual.json` ganha `ultimo_status_sequencia`** (`versao_formato: 3`), necessário para saber de onde ler.
- **Quatro arquivos, tudo ou nada:** `atual.json`, `status.json`, `anterior.json` e o arquivo de mudanças. O `gravar_par` da AGE vira um `gravar_todos` geral.

## Technical Context

**Language/Version**: Python 3.13 (constitution).

**Primary Dependencies**: nenhuma nova. Biblioteca padrão (`json`, `re`, `datetime`, `dataclasses`). Desenvolvimento: `pytest`, `ruff` (já existentes).

**Storage**: arquivos JSON versionados no Git. Novos: `data/anterior.json` (cópia rotativa) e `data/mudancas/AAAA-MM-DD.json` (um por dia). `config.toml` sem chave nova.

**Testing**: pytest com transporte falso, retratos sintéticos derivados do `atual.json` real e tramitações reais salvas em `tests/fixtures/camara/tramitacoes/`. Nenhum teste usa rede.

**Target Platform**: Linux (GitHub Actions) e desenvolvimento local.

**Project Type**: CLI / biblioteca interna (projeto único).

**Performance Goals**: acrescentar menos de 2 minutos à execução diária em dia comum. Estimativa: de 0 a 10 pedidos de tramitações; em dia de posse, algumas dezenas, sequenciais, cada um com menos de 1 s. O job tem folga (240 min).

**Constraints**: nenhuma escrita parcial entre os quatro arquivos; nenhum segredo; a API de tramitações não pagina (REL, R1), então a completude é validada pelo formato e pela presença da sequência de hoje.

**Scale/Scope**: dezenas de itens por retrato; poucas dezenas de eventos por dia comum, algumas centenas na posse.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Como o plano atende |
|---|---|---|
| I. Simplicidade | ✅ | Sem servidor, banco ou **dependência nova** (research R11). Sem chave de configuração nova. Sem paralelismo nem cache em disco: pedidos sequenciais, e um cache por referência dentro da execução. O retrato anterior é um arquivo, sem depender do `git` (decisão do clarify). |
| II. Fonte oficial e rastreável | ✅ | Todo evento traz o link oficial da ficha e as tramitações de que decorre. Motivo e destino são fatos do lote e das tramitações. A tabela de situações finais e a precedência dos motivos são classificação de **motivo**, não de inclusão, e ficam registradas no `PRODUCT.md` §5.6 (decisão D6 abaixo). |
| III. Falha visível | ✅ | API de tramitações, tramitações incoerentes com os retratos e retrato anterior inválido falham a execução inteira. Linha de base é sempre declarada com motivo; um retrato corrompido nunca vira linha de base em silêncio. |
| IV. Testes sem rede | ✅ | Comparação como função pura; tramitações injetadas por função; tramitações reais salvas; retratos sintéticos. Guarda de rede já existente (`conftest.py`) continua valendo. |
| V. Idempotência | ✅ | Retrato anterior definido por data (R5), tramitações limitadas pela sequência de hoje (R6), nenhum horário de execução no arquivo (só `dados_camara_em` do lote), ordem determinística. Teste de reexecução no mesmo dia depois de o `atual.json` ter sido gravado. |
| VI. Segredos | ✅ | As APIs são públicas; nenhum segredo. |
| VII. Escopo controlado | ✅ | Sem envio, página, teto de eventos, texto de resumo ou tipo de evento além dos seis. As mudanças no contrato da COL/REL (campo novo) e no commit da AGE (arquivos novos) são as que o clarify aprovou. |
| Stack fixada | ✅ | Python 3.13, uv, ruff, pytest, GitHub Actions, JSON no Git. |

**Re-avaliação pós-design (Phase 1):** sem violações, tabela de complexidade vazia. As decisões que dependem do mantenedor estão abaixo.

## Decisões do mantenedor (18/10/2026)

A spec e o clarify fixaram o comportamento. As decisões abaixo são de classificação e de contrato que o `PRODUCT.md` não cobre. **Todas aprovadas em 18/10/2026**, uma por uma: D1 com os quatro grupos; D2 e D3 na opção A (sem categoria nova; retrato anterior corrompido falha); D4 e D5 como propostas; D6 no fim da feature.

1. **Tabela de situações finais** (research R2), usada só para o *motivo* "situação final" de uma saída. Proposta, sobre a lista oficial da Câmara de 18/10/2026:
   - arquivado: `Arquivada`;
   - transformado em norma jurídica: `Transformado em Norma Jurídica`;
   - aprovado pela Câmara, segue ao Senado: `Aguardando Apreciação pelo Senado Federal`, `Aguardando Envio ao Senado Federal`, `Enviada ao Senado Federal`;
   - encerrada sem aprovação: `Vetado totalmente`, `Recusado`, `Retirado pelo(a) Autor(a)`, `Devolvida ao(à) Autor(a)`, `Transformado em nova proposição`, `Perdeu a Eficácia`, `Tramitação Finalizada`.

   Situação fora da tabela não é erro: o motivo cai em "foi para outro órgão" e a situação aparece no destino. **Decidido: os quatro grupos ficam na tabela.**
2. **Sem categoria de falha nova.** Retrato anterior inválido → `interna`; tramitações incoerentes → `formato_alterado`; rede e HTTP → categorias existentes. O contrato do `status.json` da AGE não muda (research R9).
3. **`atual.json` corrompido deixa de se autorrecuperar quando é o retrato anterior.** Hoje a AGE o trata como "primeiro dia" e o sobrescreve com um aviso. Com a MUD, um arquivo de dia anterior ilegível falha a execução (spec FR-003), com instrução de reparo no `quickstart.md`. Um `atual.json` corrompido **do próprio dia** não falha: ele é sobrescrito, pois o retrato anterior vem de `anterior.json`.
4. **Parecer = tramitação de código `322` ("Parecer do(a) Relator(a)") no órgão da comissão do item** (research R4). A aprovação do parecer (`336`) e a leitura (`330`) não geram evento.
5. **Janela de um dia para "chegou à comissão"** (research R7): a chegada conta como posterior ao retrato anterior se a data dela for igual ou maior que a data de `dados_camara_em` do retrato anterior. Limite conhecido: um item que chegou na madrugada do dia do lote anterior, antes da geração dele, pode sair como "chegou à comissão" em vez de "ganhou etiqueta".
6. **Registrar no `PRODUCT.md` §5.6** as regras que só existem na spec: linha de base com motivo, retrato anterior por data, precedência dos motivos de saída, tabela de situações finais e a regra de intervalo das tramitações. Commit próprio (tarefa dedicada, T039), para o mantenedor revisar o diff. **Decidido: no fim da feature**, com a tabela já testada.

## Project Structure

### Documentation (this feature)

```text
specs/004-mudancas-desde-ontem/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── mudancas-json.md     # data/mudancas/AAAA-MM-DD.json (versao_formato 1)
│   ├── atual-json.md        # diferenças do data/atual.json (versao_formato 3)
│   └── execucao-diaria.md   # CLI, arquivos gravados, rotação e workflow da AGE
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, ainda não criado)
```

### Source Code (repository root)

```text
src/monitor_comissoes/
├── lote.py              # + coluna ultimoStatus_sequencia em Proposicao
├── tramitacoes.py       # + campo despacho em Tramitacao (art. 105)
├── estoque.py           # + ultimo_status_sequencia no item; estado_de_saida(...) de quem saiu
├── coleta.py            # VERSAO_FORMATO = 3; coletar(..., comparacao) devolve também o arquivo de mudanças
├── retratos.py          # NOVO: ler e validar o retrato; decidir retrato anterior, rotação e linha de base
├── mudancas.py          # NOVO: comparação (eventos, motivos, tramitações do intervalo); sem I/O de rede próprio
├── saida.py             # + gravar_todos(escritas): N arquivos, tudo ou nada
├── status.py            # gravar_par passa a chamar gravar_todos
├── diaria.py            # prepara a comparação, grava os quatro arquivos; opções --anterior e --mudancas
└── cli.py               # sem mudança (a COL continua gravando só o atual.json)

.github/workflows/coleta-diaria.yml   # adiciona anterior.json e data/mudancas ao commit e à restauração em falha

data/
├── atual.json           # versao_formato 3 (a partir da primeira execução da MUD)
├── anterior.json        # NOVO: cópia rotativa
└── mudancas/            # NOVO: um arquivo por dia

tests/
├── fixtures/camara/tramitacoes/{id}.json   # só se o inventário (T001) achar falta de um caso real
├── capturar_fixtures.py                    # estendido apenas se houver captura (T002)
├── test_retratos.py       # NOVO: validação, versão, dia, rotação, linha de base, reexecução
├── test_mudancas.py       # NOVO: cada evento e cada motivo, com retratos sintéticos
├── test_mudancas_falhas.py# NOVO: API, incoerência, retrato inválido, atomicidade
├── test_tramitacoes.py    # + despacho
├── test_lote.py           # + sequência
├── test_estoque.py        # + ultimo_status_sequencia e estado_de_saida
├── test_saida.py          # + gravar_todos
├── test_diaria.py         # + quatro arquivos, reexecução, dia sem retrato
├── test_workflow.py       # + commit de anterior.json e data/mudancas e restauração em falha
└── (ajustes de formato 2 → 3 em test_aceitacao, test_falhas, test_status e docs)
```

**Structure Decision**: projeto único, um módulo por responsabilidade, como na COL e na REL. `retratos.py` decide **qual** retrato é o anterior (arquivos e datas); `mudancas.py` decide **o que mudou** (função pura sobre dois retratos, o estado de quem saiu e uma função que devolve tramitações); `coleta.py` só liga as peças dentro da execução, de modo que a falha de rede da comparação entra no mesmo laço de novas tentativas da coleta.

## Fluxo da execução diária (acréscimos)

1. **Preparar a comparação** (`retratos.preparar`), com a data de hoje em Brasília:
   - sem `atual.json`: linha de base "primeiro retrato", sem rotação;
   - `atual.json` de dia anterior: ele é o retrato anterior e será a nova cópia. Formato diferente de 3 → linha de base "formato anterior incompatível"; ilegível ou fora do contrato → falha `interna` (FR-003);
   - `atual.json` do próprio dia: o retrato anterior é `anterior.json`, sem rotação; ausente → linha de base "primeiro retrato";
   - `atual.json` de data futura: falha `interna`.
2. **Coletar** como hoje (lote, deputados, relatoria), com os ids do retrato anterior acrescentados às linhas lidas do lote.
3. **Comparar** (`mudancas.comparar`) o documento novo com o retrato anterior. As tramitações são lidas por referência, uma vez, e só até a sequência de hoje.
4. **Gravar tudo ou nada** (`saida.gravar_todos`): `atual.json`, `status.json`, `anterior.json` (só se houve rotação) e `data/mudancas/AAAA-MM-DD.json`.
5. O workflow adiciona os arquivos novos ao commit diário (contrato em [execucao-diaria.md](contracts/execucao-diaria.md)).

## Complexity Tracking

Sem violações da constituição; tabela vazia.
