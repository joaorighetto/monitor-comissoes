# Implementation Plan: AVI — Resumo diário no Telegram

**Branch**: `main` (sem branch própria; o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido) | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-resumo-telegram/spec.md`

## Summary

Um workflow novo, agendado para ~7h de Brasília, lê os dados que a coleta das 03:37 já commitou (`data/mudancas/AAAA-MM-DD.json`, `data/atual.json`, `data/status.json`), monta **uma mensagem de texto** (normal, de erro da coleta ou "a coleta de hoje não rodou") e a envia ao grupo pela Bot API do Telegram. Um registro versionado, `data/envio.json`, impede a segunda mensagem do mesmo tipo no mesmo dia. A coleta (AGE), as regras da COL/REL e o formato da MUD não mudam.

Abordagem (detalhes em [research.md](research.md)): só biblioteca padrão e **nenhuma dependência nova**.
- **Formatação pura** (`resumo.py`): dicionários entram, texto sai, sem relógio nem rede. É o núcleo dos testes de formatação.
- **Texto puro, sem `parse_mode`**: nenhum caractere vindo da Câmara pode ser rejeitado por escape (FR-018). Os links viram links no Telegram sozinhos, e a pré-visualização de links é desligada.
- **Teto de 4.096 contado em unidades UTF-16** (conservador), com seleção dos eventos **alternando entre as comissões** e o "e mais N" exato.
- **Cliente da Bot API com `urllib`** (`telegram.py`), com transporte injetável como o `TransporteHttp` da AGE. O token vai na URL da Bot API; por isso nenhuma mensagem de erro é montada a partir da URL, e todo texto de erro passa por um filtro que remove o token.
- **Registro de envio em `data/envio.json`**: dia e tipo (normal ou erro) do último envio. Só é gravado depois de o Telegram aceitar a mensagem.
- **Workflow próprio, no mesmo grupo de concorrência da coleta**: o envio nunca lê dados no meio de uma coleta.

## Technical Context

**Language/Version**: Python 3.13 (constitution).

**Primary Dependencies**: nenhuma nova. Biblioteca padrão (`json`, `urllib`, `datetime`, `dataclasses`, `os`). Desenvolvimento: `pytest`, `ruff` (já existentes).

**Storage**: arquivos JSON versionados no Git. Novo: `data/envio.json`. `config.toml` ganha a tabela opcional `[aviso]`.

**Testing**: pytest com respostas da Bot API simuladas (`abrir` falso, como na AGE), entradas salvas em `tests/fixtures/aviso/` (arquivo de mudanças, `atual.json` e `status.json` sintéticos) e a guarda `sem_rede` do `conftest.py`. Nenhum teste usa rede nem credencial real.

**Target Platform**: Linux (GitHub Actions) e desenvolvimento local.

**Project Type**: CLI / biblioteca interna (projeto único).

**Performance Goals**: execução em segundos (só lê três arquivos pequenos e faz uma requisição).

**Constraints**: mensagem em até 4.096 caracteres; token e chat_id só em variáveis de ambiente; execução idempotente no dia; sem rede nos testes.

**Scale/Scope**: uma mensagem por dia para um grupo; dias de posse podem ter centenas de eventos (o teto os limita).

## Constitution Check

*GATE: avaliado antes da pesquisa e reavaliado depois do desenho.*

| Princípio | Avaliação |
|---|---|
| I. Simplicidade | **Passa.** Sem servidor, sem banco, sem dependência nova (`urllib` da biblioteca padrão). O estado do envio é um JSON no Git. Nenhuma justificativa de dependência é necessária. |
| II. Fonte oficial e rastreável | **Passa.** Todo evento na mensagem traz o link oficial que o arquivo de mudanças já traz; evento sem link falha o envio (FR-022). O código não cria regra de inclusão: só formata o que a MUD registrou. |
| III. Falha visível | **Passa.** Arquivo de mudanças ausente, de versão desconhecida, incoerente com o `status.json` ou sem link falha o envio (workflow vermelho), nunca vira "sem mudanças". Falha da coleta e coleta que não rodou viram mensagem de erro. |
| IV. Testes sem rede | **Passa.** Bot API simulada por transporte falso; entradas salvas; guarda de rede ativa. As tarefas começam pelos testes. |
| V. Idempotência | **Passa.** `data/envio.json` guarda dia e tipo; reexecução no mesmo dia não reenvia; mensagem não aceita pelo Telegram não é registrada. Ressalva conhecida: ver "Riscos" abaixo. |
| VI. Segredos fora do código | **Passa.** `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` só em variáveis de ambiente (secrets do GitHub no workflow). O token nunca entra em log, mensagem de erro, `status.json`, `envio.json` nem fixture. |
| VII. Escopo controlado | **Passa.** Só o recorte da linha AVI. Sem comandos no bot, sem vários destinatários, sem página, sem mudança nas regras de coleta, relatoria ou comparação, e sem mudança no `status.json`. |

**Stack fixada**: Python 3.13, uv, ruff, pytest, GitHub Actions, JSON no Git. Nada trocado: não há emenda à constituição.

**Reavaliação depois do desenho:** continua passando. A tabela de complexidade fica vazia.

### Conferência com o PRODUCT.md

O desenho segue D5, §6.1, §7 e §10. Duas decisões do mantenedor (clarify de 20/10/2026) vão além do texto atual do PRODUCT.md e **pedem emenda, na mesma mudança da implementação**, sem conflito material: (1) a mensagem "a coleta de hoje não rodou", enviada pelo workflow das ~7h (hoje o §7 trata a falta do resumo como o sinal; ela continua sendo, para o caso de o próprio envio não rodar); (2) `data/envio.json` entre os arquivos de histórico (D8).

### Riscos aceitos

- **Duplicata em resposta ambígua.** Se a conexão cai depois de o Telegram aceitar a mensagem, a nova tentativa pode duplicá-la. Entre duplicar e não avisar, escolhe-se avisar (spec, Edge Cases).
- **Registro não commitado.** Se o envio teve sucesso e o commit/push de `data/envio.json` falhar, uma reexecução manual enviaria de novo. O workflow tenta o push duas vezes, como a AGE, e fica vermelho se não conseguir.
- **Fila de concorrência.** O GitHub mantém uma execução em andamento e uma pendente por grupo; uma pendente mais velha é substituída pela mais nova. Só ocorre com três execuções do grupo ao mesmo tempo (coleta em andamento, coleta manual pendente, envio), o que não é o caso normal.
- **Primeiro dia depois do merge.** O envio das ~7h falha, visivelmente, se a coleta com a MUD ainda não tiver gravado `data/mudancas/AAAA-MM-DD.json` do dia. É o comportamento correto (FR-022), e a ordem de ativação está no quickstart.

## Project Structure

### Documentation (this feature)

```text
specs/005-resumo-telegram/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── mensagem.md      # Conteúdo, layout e teto da mensagem
│   ├── envio-json.md    # Registro de envio
│   └── aviso-cli.md     # CLI, variáveis de ambiente, config e workflow
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
.github/workflows/
└── aviso-diario.yml          # novo: envio às ~7h, mesmo grupo de concorrência da coleta

config.toml                    # + tabela opcional [aviso]
data/
└── envio.json                 # novo: registro de envio (criado no primeiro envio)

src/monitor_comissoes/
├── config.py                  # + campos pagina_url e repositorio (tabela [aviso])
├── erros.py                   # + FalhaDeEnvio (sem categoria; CATEGORIAS e REPETIVEIS não mudam)
├── entradas.py                # novo: lê e valida mudancas, atual e status do dia
├── resumo.py                  # novo: formatação pura (normal, erro, coleta não rodou, teto)
├── telegram.py                # novo: cliente da Bot API (urllib), tentativas, filtro do token
├── envio.py                   # novo: registro data/envio.json (ler, validar, gravar)
└── aviso.py                   # novo: CLI `enviar` e `texto`, orquestração e códigos de saída

tests/
├── fixtures/aviso/            # novo: uma pasta por cenário (atual, status, mudancas/) e telegram/
├── test_resumo.py             # formatação: tipos de evento, teto, avisos, erro
├── test_entradas.py           # leitura, versão de formato, incoerências
├── test_telegram.py           # Bot API simulada: sucesso, 429, 5xx, recusa, sem vazar token
├── test_envio.py              # registro: idempotência, falha antes do registro
├── test_aviso.py              # orquestração e CLI ponta a ponta com transporte falso
├── test_config.py             # + [aviso]
└── test_workflow_aviso.py     # verificação textual do novo workflow
```

**Structure Decision**: projeto único, como nas features anteriores. A formatação é pura e separada do envio e do relógio para ser testada só com dicionários e texto; o único módulo com efeito colateral externo é `telegram.py`, com o transporte injetável.

## Complexity Tracking

Sem violações do Constitution Check. Nada a justificar.
