# Quickstart: validar a AGE

Guia para provar que a feature funciona de ponta a ponta. Contratos em [contracts/](contracts/), modelo em [data-model.md](data-model.md).

## Pré-requisitos

- `uv` instalado; Python 3.13 (o `uv` resolve pelo `.python-version`).
- Os passos 1 a 3 não precisam de rede.
- Os passos 4 a 6 precisam do repositório no GitHub, com a feature já na branch padrão (o agendamento só roda no último commit da branch padrão) e com acesso de escrita do `GITHUB_TOKEN` ao repositório.

## 1. Verificação completa (sem rede)

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

**Esperado:** os três comandos terminam com código 0, e todos os testes passam, inclusive os da COL (que não mudaram) e os novos: plausibilidade, tentativas, `status.json`, mensagem do commit e verificação textual do workflow.

## 2. Falha deixa `atual.json` intacto e registra o status (sem rede)

Coberto por testes. Conferência manual, com configuração inválida (falha antes de qualquer rede):

```bash
mkdir -p /tmp/age && echo '{"sentinela": true}' > /tmp/age/atual.json
printf 'comissoes = []\nano_minimo = 2003\n' > /tmp/age/config-invalida.toml
uv run python -m monitor_comissoes.diaria executar --config /tmp/age/config-invalida.toml \
  --atual /tmp/age/atual.json --status /tmp/age/status.json
echo "codigo=$?"; cat /tmp/age/atual.json; cat /tmp/age/status.json
uv run python -m monitor_comissoes.diaria mensagem --status /tmp/age/status.json
```

**Esperado:** `FALHA [configuracao]: …` em `stderr`, `codigo=1`; `/tmp/age/atual.json` ainda com `{"sentinela": true}`; `status.json` com `"resultado": "falha"`, categoria `configuracao`, `tentativas: 0` e `ultimo_retrato_bom: null` (o `atual.json` de exemplo não é um retrato da COL); e a mensagem `dados: AAAA-MM-DD · falha [configuracao]`.

## 3. Variação acima de 20% bloqueia, e a confirmação libera só ela (sem rede)

Coberto por `tests/test_plausibilidade.py` e `tests/test_diaria.py`, com retratos sintéticos: queda de 28% falha com `estoque_implausivel`; exatamente 20% passa; com `--aceitar-variacao` o mesmo caso grava e registra `variacao_aceita`; estoque bruto zero falha mesmo com a confirmação.

**Esperado:** todos passam na verificação do passo 1.

## 4. Verificação real do workflow (com rede, depois do merge)

No GitHub, aba Actions → "Coleta diária" → "Run workflow" (sem marcar a confirmação).

**Esperado:**
- O workflow termina verde em poucos minutos (a coleta completa levou ~159 s na COL).
- Um commit de `github-actions[bot]` com a mensagem `dados: AAAA-MM-DD · ok · N itens · estoque bruto B`, contendo `data/atual.json` e `data/status.json`.
- N da mesma ordem de grandeza do resultado da COL (23 itens em 18/10/2026) e `estoque_bruto` perto de 1.500.
- O `ci.yml` **não** dispara por causa desse commit (o push com `GITHUB_TOKEN` não cria execuções).

Repita o disparo: **Esperado:** um segundo commit no mesmo dia, com os mesmos itens (só `gerado_em` e `verificado_em` mudam).

## 5. Falha real deixa o workflow vermelho e os dados intactos

Com o passo 4 já feito, provoque uma falha controlada sem tocar no código: dispare o workflow numa branch de teste cujo `config.toml` tenha `ano_minimo = 2999` (configuração inválida, sem rede).

**Esperado:**
- Workflow vermelho; o GitHub manda e-mail ao dono.
- Um commit só com `data/status.json` (`resultado: falha`, categoria `configuracao`).
- `data/atual.json` idêntico ao do commit anterior (`git diff HEAD~1 -- data/atual.json` vazio).

## 6. Agendamento real e as 60 dias

- No dia seguinte ao merge, conferir na aba Actions que o workflow rodou sozinho por volta das 03h37 de Brasília (pode atrasar em carga alta) e que há um commit do bot.
- Depois de 7 dias de operação, conferir no histórico do Git que há ao menos um commit de dados do bot por dia e que o `verificado_em` do `status.json` nunca passou de 30 horas (SC-007).
- Conferir que `docs/agendamento-60-dias.md` existe, com os links oficiais, a data da consulta e a conclusão.
- Lembrete a cada 45 dias (decisão do mantenedor): conferir na aba Actions que a "Coleta diária" segue ativa. Datas a partir de 18/10/2026: dia 45 = 02/12/2026 e dia 55 = 12/12/2026 (R11 do [research.md](research.md)).
