# Contrato: CLI, configuração e workflow do aviso

## CLI

`python -m monitor_comissoes.aviso <enviar|texto>`

| Subcomando | O que faz | Precisa de credencial |
|---|---|---|
| `texto` | Monta a mensagem do dia e a **imprime**, sem enviar e sem tocar em `data/envio.json`. Antes do texto, uma linha `TIPO: normal` ou `TIPO: erro` | Não |
| `enviar` | Monta a mensagem, confere o registro, envia, grava `data/envio.json` | Sim: `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` |
| `mensagem` | Imprime a mensagem de uma linha do commit do registro (`aviso: AAAA-MM-DD · normal\|erro`), comparando `--envio` com o registro de antes (`--antes`, ausente = vazio). Falha se mais de um tipo, ou nenhum, mudou | Não |

Opções comuns (todas com padrão):

| Opção | Padrão |
|---|---|
| `--config` | `config.toml` |
| `--atual` | `data/atual.json` |
| `--status` | `data/status.json` |
| `--mudancas` | pasta `mudancas` ao lado do `--atual` |
| `--envio` | `envio.json` ao lado do `--atual` (só `enviar`) |
| `--hoje AAAA-MM-DD` | data de Brasília do relógio. **Só em `texto`**: serve para ver uma mensagem de um dia salvo (as fixtures). `enviar` não aceita a opção: o dia do envio é sempre o do relógio |

Os padrões ficam ao lado do `--atual`, como na MUD, para uma execução de teste nunca gravar em `data/` do repositório.

### Variáveis de ambiente

| Variável | Uso |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token do bot (secret do GitHub no workflow; `.env` local fora do Git) |
| `TELEGRAM_CHAT_ID` | Identificador do grupo (secret do GitHub) |

Variável ausente ou vazia em `enviar`: falha `FALHA [envio]: variável TELEGRAM_BOT_TOKEN ausente`, citando o **nome** e nunca o valor. Espaços e quebras de linha nas pontas são removidos (um segredo colado com `Enter` no fim funciona); espaço ou caractere de controle no meio do valor é recusado sem mostrá-lo. O CLI não lê `.env`; quem quiser usar um `.env` local o carrega no shell.

### Saída e código de saída

| Resultado | Saída | Código |
|---|---|---|
| Enviada | `OK: mensagem normal|de erro de DD/MM enviada (N caracteres)` | 0 |
| Já enviada hoje | `JÁ ENVIADO: mensagem normal|de erro de DD/MM` | 0 |
| `texto` | `TIPO: ...` e o texto | 0 |
| Qualquer falha | `FALHA [envio]: <motivo>` em `stderr` | 1 |

Falhas (sempre em `stderr`, sem segredo): credencial ausente; `data/envio.json` inválido; arquivo de mudanças ou `atual.json` ausente, ilegível, de versão desconhecida ou incoerente com o `status.json`; evento sem link; Bot API recusou (com o código HTTP e a descrição do Telegram) ou ficou fora do ar depois das tentativas; gravação do registro falhou depois de um envio aceito (a mensagem diz que **foi** enviada).

### Chamada à Bot API

`POST https://api.telegram.org/bot<TOKEN>/sendMessage`, `Content-Type: application/json`, corpo:

```json
{"chat_id": "<TELEGRAM_CHAT_ID>", "text": "<mensagem>", "link_preview_options": {"is_disabled": true}}
```

Sucesso = HTTP 200 e `ok: true` no corpo. Tentativas: ver R9 do [research.md](../research.md).

## Configuração (`config.toml`)

Tabela opcional; sem ela valem os padrões.

```toml
[aviso]
# Endereço da página pública (feature PAG). Vazio até a PAG existir: enquanto estiver vazio,
# o "e mais N" aponta para o arquivo do dia no repositório.
pagina_url = ""
# Repositório, no formato dono/nome, usado no link do arquivo do dia.
repositorio = "joaorighetto/monitor-comissoes"
```

Validação (falha `configuracao`): `pagina_url` texto, vazio ou começando com `https://`; `repositorio` texto no formato `dono/nome` (letras, números, `_`, `.` e `-`); campo desconhecido em `[aviso]` falha, como em `[execucao]`.

**A tabela só é lida pelo aviso** (`carregar_config_do_aviso`). `carregar_config`, usado pela coleta, a ignora: um erro de digitação em `[aviso]` falha o envio, nunca a coleta (FR-016, FR-026; revisão de 20/10/2026).

## Workflow `.github/workflows/aviso-diario.yml`

- `on.schedule`: `cron: "17 10 * * *"` (07:17 de Brasília) e `workflow_dispatch` (sem entradas).
- `concurrency: {group: coleta-diaria, cancel-in-progress: false}`: o mesmo grupo da coleta.
- `permissions: contents: write`.
- Mesmos pins de `actions/checkout` e `astral-sh/setup-uv` do `coleta-diaria.yml`; `uv sync --locked`.
- Segredos em `env` do passo de envio: `TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}` e `TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}`. Nunca interpolados no script.
- Passo "Enviar e registrar": guarda o `data/envio.json` de antes em `$RUNNER_TEMP`; `set +e`; roda `.venv/bin/python -m monitor_comissoes.aviso enviar`; guarda o código; se `data/envio.json` mudou, `git add` + `git commit -m "$(... aviso mensagem --antes ...)"` (`aviso: AAAA-MM-DD · normal|erro`); `git pull --rebase` e `git push` com uma segunda tentativa; sai com o código guardado (workflow vermelho em falha de envio).
- Em falha de envio, `data/envio.json` volta ao que o Git tem (`git checkout --` com `|| true`), e nada é commitado.
- O workflow **não** toca em `data/atual.json`, `status.json`, `anterior.json` nem `mudancas/`.

Verificação (textual, em `tests/test_workflow_aviso.py`): cron, `workflow_dispatch`, grupo de concorrência igual ao da coleta e sem cancelamento, permissões, pins iguais aos do `coleta-diaria.yml`, segredos só em `env` e vindos de `secrets.*`, nenhum valor de segredo no arquivo, e que o passo não faz `git add` de nada além de `data/envio.json`.

## Compatibilidade

- A coleta (AGE) não muda: nem o cron, nem os passos, nem os arquivos que grava.
- `CI` (`ci.yml`) não muda.
- PRODUCT.md: emenda de `data/envio.json` em D8 e da mensagem "a coleta de hoje não rodou" em §6.1/§7, na mesma mudança da implementação.
