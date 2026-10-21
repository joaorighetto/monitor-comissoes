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

## Notas operacionais

- **Job vermelho no push do registro, depois do envio:** a mensagem **já foi** ao grupo e o `data/envio.json` não chegou ao remoto. Confira o grupo antes de reexecutar; reexecutar sem registro duplica a mensagem.
- **Secrets não configurados:** o job fica vermelho com `variável TELEGRAM_BOT_TOKEN ausente` (ou `TELEGRAM_CHAT_ID`).
- **Aviso antes da primeira coleta com a MUD:** `FALHA [envio]: arquivo de mudanças ... não existe` (hoje `data/mudancas/` nem existe no repositório). É o comportamento correto: espere ou dispare a coleta.
- **Coleta atrasada além das 07:17:** o aviso pode mandar "a coleta de hoje não rodou" antes de a coleta terminar; isso consome o envio de erro do dia, e uma falha real posterior no mesmo dia aparece como `JÁ ENVIADO`. A margem normal é de 3h40, então é raro; se ocorrer, apague o dia do tipo `erro` no `data/envio.json` para permitir novo aviso.
- **Fila de concorrência:** o grupo `coleta-diaria` guarda uma execução em andamento e uma pendente; uma pendente mais velha é substituída pela mais nova. Se o aviso esperar uma coleta manual e outra execução entrar na fila, o aviso do dia pode ser descartado sem erro. Em caso de dúvida, dispare *Aviso diário* à mão.

## Limites a lembrar

- O resumo mostra dados do **dia anterior**: o lote da Câmara sai por volta das 2h (PRODUCT.md, §8).
- Se o próprio *Aviso diário* não rodar, não chega nada: a falta do resumo é o sinal.
- Se a conexão cair depois de o Telegram aceitar a mensagem, o envio pode duplicá-la (risco aceito, plan.md).

## Cobertura (casos de aceitação da linha AVI do ROADMAP.md)

| Caso de aceitação | Testes |
|---|---|
| Uma mensagem por dia, mesmo sem mudanças | `test_resumo_normal.py::test_dia_sem_mudancas`, `test_aviso_idempotencia.py` |
| Links oficiais em cada evento | `test_resumo_normal.py::test_todo_evento_tem_o_link_logo_abaixo`, `test_entradas.py::test_evento_sem_link_falha` |
| Até 4.096 caracteres e teto de eventos | `test_resumo_teto.py` (inclui a propriedade com 40 combinações) |
| "e mais N, veja a página" | `test_resumo_teto.py::test_n_do_e_mais_n_e_exatamente_o_numero_de_omitidos`, `::test_rodape_*` |
| Falha gera mensagem de erro com a data dos últimos dados bons | `test_resumo_erro.py`, `test_aviso.py::test_status_de_falha_do_dia_gera_erro_com_o_motivo` |
| Coleta que não rodou avisa | `test_resumo_erro.py::test_coleta_que_nao_rodou_*`, `test_aviso.py::test_status_de_outro_dia_*` |
| Reexecução no mesmo dia não duplica | `test_aviso_idempotencia.py` |
| Segredos fora do código | `test_telegram.py` (nada vaza), `test_sem_segredos.py`, `test_workflow_aviso.py::test_segredos_so_em_env_*` |
| Envio com falha visível, dados intactos | `test_aviso.py::test_falha_de_envio_nao_toca_em_nenhum_arquivo_de_dados`, `test_workflow_aviso_script.py` |
| Testes de formatação sem rede | toda a suíte (guarda `sem_rede` do `conftest.py`) |

## Verificação no Windows

A suíte completa tem falhas que **já existiam** antes da AVI e são de plataforma (fim de linha CRLF e separador `\` nos testes de `test_falhas.py`, `test_saida.py`, `test_status.py` e `test_workflow_script.py`), e um teste de SIGTERM que encerra o processo do pytest (`test_diaria.py::test_sigterm_no_meio_da_espera_grava_o_status_de_falha`). No Linux do CI nada disso ocorre. Conferido em 20/10/2026: antes da AVI, 34 falhas e 778 passes (com esse teste excluído); com a AVI, as mesmas 34 falhas e 1.063 passes.
