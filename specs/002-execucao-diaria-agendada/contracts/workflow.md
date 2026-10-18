# Contrato: workflow `coleta-diaria`

Arquivo: `.github/workflows/coleta-diaria.yml`. O `ci.yml` existente não muda.

## Gatilhos

| Gatilho | Configuração | Observação |
|---|---|---|
| `schedule` | `cron: "37 6 * * *"` (06:37 UTC = 03:37 de Brasília) | Um agendamento por dia. Roda no último commit da branch padrão |
| `workflow_dispatch` | entrada booleana `aceitar_variacao`, padrão `false` | Disparo manual. Mesma execução do agendamento |

Não há gatilho `push` nem `pull_request`: o commit do bot não pode disparar a coleta (FR-003).

## Controles

| Item | Valor |
|---|---|
| `concurrency` | grupo fixo `coleta-diaria`, `cancel-in-progress: false` (FR-023) |
| `permissions` | `contents: write`, só no job. Nenhum outro escopo |
| `timeout-minutes` | 150 (4 coletas de ~3 min com 3 esperas de 30 min, mais folga) |
| Segredos | nenhum além do `GITHUB_TOKEN` padrão (FR-031) |

## Passos

1. `actions/checkout` e `astral-sh/setup-uv`, com os mesmos pins do `ci.yml`.
2. `uv sync --locked`.
3. Configurar a identidade do bot no Git (`github-actions[bot]`).
4. **Coleta e commit** (um passo, em `bash`):

```text
set +e
uv run python -m monitor_comissoes.diaria executar [--aceitar-variacao se dispatch e entrada verdadeira]
codigo=$?
set -e
se codigo ≠ 0: git checkout -- data/atual.json   (ignora se o arquivo não existir)
git add data/status.json
se codigo = 0: git add data/atual.json
git commit -m "$(uv run python -m monitor_comissoes.diaria mensagem)"
git pull --rebase
git push
exit $codigo
```

5. O passo termina com o código da coleta. Falha da coleta, do commit ou do push deixa o workflow vermelho.

## Comportamento

| Situação | Resultado do workflow | Commit |
|---|---|---|
| Sucesso | verde | `atual.json` + `status.json` |
| Falha da coleta (qualquer categoria) | vermelho | só `status.json` |
| Falha do commit ou do push | vermelho | nenhum |
| Execução já em andamento quando outra é disparada | a nova espera; se já havia uma pendente, a pendente antiga é cancelada (nunca começou) | — |

A confirmação `aceitar_variacao` só chega à coleta quando o evento é `workflow_dispatch`. No agendamento ela não existe.

## O que não está neste contrato

Telegram, secrets, GitHub Pages e qualquer publicação: são das features AVI e PAG. O commit do bot, feito com o `GITHUB_TOKEN`, não dispara o `ci.yml`; quando o PAG precisar publicar a página depois do commit, ele deve chamar o próprio deploy (decisão da PAG).
