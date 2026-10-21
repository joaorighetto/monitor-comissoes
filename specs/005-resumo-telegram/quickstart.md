# Quickstart: AVI — Resumo diário no Telegram

Como conferir a feature, do mais barato ao mais real. Contratos em [contracts/](contracts/); modelo em [data-model.md](data-model.md).

## 1. Verificação completa (sem rede, sem credencial)

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Esperado: tudo verde. Os testes de formatação, do cliente da Bot API (respostas simuladas), do registro de envio, da orquestração e do workflow cobrem os casos da spec; nenhum usa a internet.

## 2. Ver a mensagem de hoje, sem enviar

```bash
uv run python -m monitor_comissoes.aviso texto
```

Esperado: `TIPO: normal` (ou `erro`) e o texto da mensagem do dia, construído com `data/mudancas/AAAA-MM-DD.json`, `data/atual.json` e `data/status.json` do repositório. Não precisa de credencial e não altera nenhum arquivo.

- Dia com `status.json` de falha: `TIPO: erro`, começando com `⚠ ERRO`.
- `data_referencia` de outro dia: `TIPO: erro`, "A coleta de hoje (DD/MM) não rodou".
- Sem o arquivo de mudanças do dia: `FALHA [envio]: ...` e código de saída 1.

Para ver a mensagem de um dia salvo, use as fixtures (cada pasta é um cenário) e a data do cenário:

```bash
uv run python -m monitor_comissoes.aviso texto --atual tests/fixtures/aviso/completo/atual.json --hoje 2026-10-20
```

Outros cenários: `sem-eventos`, `linha-base-primeiro`, `linha-base-formato`, `intervalo`, `falha`, `sem-retrato`. Esperado: `TIPO: normal` e o texto de `contracts/mensagem.md` (ou `TIPO: erro` em `falha` e `sem-retrato`).

## 3. Preparar o bot (uma vez, pelo mantenedor)

1. No Telegram, criar o bot com o @BotFather e copiar o token.
2. Adicionar o bot ao grupo do gabinete e descobrir o `chat_id` do grupo.
3. No GitHub: *Settings → Secrets and variables → Actions → New repository secret*, com os nomes `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.

O token e o `chat_id` nunca entram no repositório, no chat nem em log.

## 4. Primeiro envio de verdade

Ordem de ativação (a coleta com a MUD precisa ter gravado o arquivo de mudanças do dia antes do envio):

1. Fazer o merge da AVI.
2. Esperar (ou disparar à mão) uma coleta: o `data/mudancas/AAAA-MM-DD.json` do dia aparece no commit do bot.
3. Disparar *Aviso diário* em *Actions → Aviso diário → Run workflow*.

Esperado: o grupo recebe **uma** mensagem; o workflow fica verde; o commit do bot `aviso: AAAA-MM-DD · normal` inclui só `data/envio.json`.

## 5. Idempotência

Disparar *Aviso diário* de novo no mesmo dia.

Esperado: nenhuma segunda mensagem; o log mostra `JÁ ENVIADO: mensagem normal de DD/MM`; o workflow fica verde; nenhum commit novo.

## 6. Falha visível

- **Token errado:** trocar o secret `TELEGRAM_BOT_TOKEN` por um inválido e disparar. Esperado: workflow vermelho, `FALHA [envio]: ... 401 ...`, nada commitado, e o token **não** aparece no log. Restaurar o secret.
- **Coleta que não rodou:** disparar *Aviso diário* depois da meia-noite, antes da coleta. Esperado: mensagem `⚠ ERRO ... A coleta de hoje (DD/MM) não rodou`.

## 7. Reenviar de propósito

Em um commit, remover do `data/envio.json` o dia do tipo que se quer reenviar e disparar o workflow.

## Limites a lembrar

- O resumo mostra dados do **dia anterior**: o lote da Câmara sai por volta das 2h (PRODUCT.md, §8).
- Se o próprio *Aviso diário* não rodar, não chega nada: a falta do resumo é o sinal.
- Se a conexão cair depois de o Telegram aceitar a mensagem, o envio pode duplicá-la (risco aceito, plan.md).
