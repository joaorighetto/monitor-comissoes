# Contrato: execução diária com a MUD (diferenças da AGE)

Vale tudo o que está em [`specs/002-execucao-diaria-agendada/contracts/`](../../002-execucao-diaria-agendada/contracts/) (CLI, `status.json`, workflow), com as mudanças abaixo. O comando da COL (`python -m monitor_comissoes`) **não muda**: continua gravando só o `atual.json`.

## CLI

`python -m monitor_comissoes.diaria executar` ganha duas opções, ambas com padrão:

| Opção | Padrão | Descrição |
|---|---|---|
| `--anterior` | `data/anterior.json` | Cópia rotativa do retrato anterior |
| `--mudancas` | `data/mudancas` | Pasta dos arquivos de mudanças |

`--config`, `--atual`, `--status` e `--aceitar-variacao` continuam como estão. O subcomando `mensagem` não muda.

**Saída e código de saída:** como na AGE (0 em sucesso, 1 em qualquer falha). A linha `OK:` ganha o resumo da comparação, por exemplo `mudanças: 3 eventos (1 entrou, 1 saiu, 1 situação)` ou `mudanças: linha de base (primeiro retrato)`.

## Arquivos gravados

Em sucesso, os quatro de uma vez, tudo ou nada:

| Arquivo | Quando muda |
|---|---|
| `data/atual.json` | sempre (versão de formato 3) |
| `data/status.json` | sempre |
| `data/anterior.json` | só quando o `atual.json` existente era de um dia anterior ao da execução |
| `data/mudancas/AAAA-MM-DD.json` | sempre (substituído numa reexecução no mesmo dia) |

Em falha, só o `status.json` é gravado, como na AGE. `atual.json`, `anterior.json` e `data/mudancas/` ficam como estavam, byte a byte.

## Falhas novas

Sem categoria nova (research R9). A mensagem sempre diz o arquivo ou a proposição e o motivo.

| Situação | Categoria | Exemplo de motivo |
|---|---|---|
| Retrato anterior ilegível, fora do contrato ou com id repetido | `interna` | `retrato anterior inválido (data/atual.json): campo itens` |
| Retrato com data posterior à da execução | `interna` | `retrato anterior de data futura (2026-10-20)` |
| Rede ou HTTP nas tramitações | `fonte_indisponivel` | como na REL |
| Tramitações sem a sequência de hoje, ou sequência de hoje menor que a anterior | `formato_alterado` | `tramitações da proposição 2267727: a sequência 43 do lote não existe` |

## Workflow (`.github/workflows/coleta-diaria.yml`)

Mudanças no passo "Coleta e commit":

- **Em falha** (código diferente de zero), além de `git checkout -- data/atual.json`, restaurar `data/anterior.json` e `data/mudancas` com um `git checkout --` **por caminho**, cada um com `|| true` (um caminho inexistente no Git aborta o comando inteiro), e remover o arquivo de mudanças novo, não rastreado, com `git clean -fdq -- data/mudancas`.
- **Em sucesso**, além de `git add data/atual.json`, adicionar `data/mudancas` e, se existir, `data/anterior.json` (`[ -e data/anterior.json ] && git add data/anterior.json`).
- `git add data/status.json` continua incondicional. O restante (identidade do bot, `timeout`, `pull --rebase`, `push`, saída com o código da coleta) não muda.

## Compatibilidade

- Nenhuma mudança no contrato do `status.json`.
- O commit diário passa a poder conter até quatro arquivos de dados; a mensagem do commit não muda.
- Primeira execução depois da MUD: o `atual.json` commitado é de dia anterior e de versão 1 ou 2. Ele vira `anterior.json`, o arquivo do dia é linha de base com o motivo "formato anterior incompatível", e a comparação começa no dia seguinte.
