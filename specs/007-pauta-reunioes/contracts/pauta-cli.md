# Contrato: linha de comando e workflows da pauta

## `python -m monitor_comissoes.pauta checar`

| Opção | Padrão |
|---|---|
| `--config` | `config.toml` |
| `--pautas` | `data/pautas` |
| `--status` | `data/status-pauta.json` |
| `--atual` | `data/atual.json` |
| `--indice` | `cache/indice-autoria.json` |

- Sucesso: grava `data/pautas/AAAA-MM-DD.json` e `data/status-pauta.json` (tudo ou nada), imprime
  uma linha `OK: N reuniões (CE: n, CREDN: n) · M alterações novas · pauta checada em DD/MM às
  HHhMM` e sai com 0. Na linha de base, o trecho das alterações diz `linha de base`.
- Falha: não toca em `data/pautas/`, grava `data/status-pauta.json` com `resultado: falha`, imprime
  `FALHA [categoria]: motivo` no `stderr` e sai com 1. Uma exceção inesperada vira categoria
  `interna`, sem traceback parcial gravado.
- Nunca lê nem grava `data/atual.json` (só lê), `data/anterior.json`, `data/mudancas/`,
  `data/status.json` nem `data/envio.json`.
- O relógio e o transporte HTTP são injetáveis (`main(argv, transporte=None, agora=None)`), como
  nas outras CLIs.

## `python -m monitor_comissoes.pauta mensagem`

Imprime a mensagem do commit a partir de `data/status-pauta.json` e do arquivo de pauta do dia:

- `pauta: 2026-10-24 05:49 · ok · 3 reuniões · 1 alteração`
- `pauta: 2026-10-24 05:49 · ok · 3 reuniões · linha de base`
- `pauta: 2026-10-24 15:18 · falha · fonte_indisponivel`

Sai com 1 se o status não existir ou for inválido.

## `python -m monitor_comissoes.diaria executar` (AGE, acréscimo)

Ganha `--indice` (padrão `cache/indice-autoria.json`). Em sucesso, grava o índice junto com os
demais arquivos (contrato [indice-autoria.md](indice-autoria.md)). Nada mais muda na saída, nos
códigos nem no `status.json`.

## Workflow novo: `.github/workflows/checagem-pauta.yml`

- Gatilhos: `schedule` com `47 8 * * *`, `17 18 * * *` e `47 1 * * *` (05:47, 15:17 e 22:47 de
  Brasília, research R9) e `workflow_dispatch` sem entradas. Sem `push` nem `pull_request`.
- `concurrency: {group: pauta, cancel-in-progress: false}`.
- `permissions: {contents: write}`; `timeout-minutes: 20`.
- Passos: checkout; setup-uv (o mesmo SHA dos outros workflows); `uv sync --locked`;
  `actions/cache/restore` (SHA de v6.1.0) com `path: cache/indice-autoria.json`,
  `key: indice-autoria-` e `restore-keys: indice-autoria-` (restaura o mais recente); identidade
  do bot; passo "Checar e registrar":
  1. roda `.venv/bin/python -m monitor_comissoes.pauta checar` guardando o código;
  2. em falha, `git checkout -- data/pautas` e `git clean -fdq -- data/pautas` (defesa: a CLI já
     não grava);
  3. `git add data/status-pauta.json` e, em sucesso, `git add data/pautas`;
  4. commit com a mensagem de `pauta mensagem`; `git pull --rebase`; push com uma nova tentativa;
  5. devolve o código (workflow vermelho em falha).
- Índice ausente no cache: a CLI falha com `entrada_invalida` (workflow vermelho e status gravado).

## Workflow da coleta (acréscimo)

Depois do passo "Coleta e commit", um passo `actions/cache/save` (SHA de v6.1.0), só quando ele
termina com sucesso (`if: success()`), com `path: cache/indice-autoria.json` e
`key: indice-autoria-${{ github.run_id }}-${{ github.run_attempt }}`. Nada mais muda na coleta.
