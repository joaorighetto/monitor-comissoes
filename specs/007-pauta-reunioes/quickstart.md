# Quickstart: PAU — Pauta das reuniões

## 1. Verificação completa (sem rede)

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Esperado: tudo passa. A guarda `sem_rede` do `conftest.py` derruba qualquer teste que tente abrir
conexão.

## 2. Casos de aceitação da linha PAU (com fixtures)

| Caso | Teste | Esperado |
|---|---|---|
| Janela e só reuniões deliberativas | `tests/test_pauta_checagem.py` | eventos de fora de D±7 e de outros tipos ficam fora |
| Pauta de 28/10/2026 (CE 83091) | `tests/test_pauta_aceitacao.py` | 19 PL listados, 1 REQ contado, REQ 70/2026 como proposição do item |
| PL 5432/2016 leva o PL 3701/2020 (CE 81555) | `tests/test_pauta_aceitacao.py` | marca com o apensado e as duas etiquetas; item no grupo do NOVO |
| REQ 17/2026 → PL 1778/2020 | `tests/test_pauta_aceitacao.py` | só o REQ conta; o PL não é listado |
| Resultado (§5.9) | `tests/test_pauta_resultado.py` | os sete rótulos, a exceção do "Requerimento de Retirada de Pauta" |
| Alterações e registro único | `tests/test_pauta_alteracoes.py` | cinco tipos, ordem não conta, nada repetido |
| Falhas | `tests/test_pauta_falhas.py` | saída 1, `data/pautas/` intocada, status gravado |

## 3. Execução real, local (com rede)

Pré-requisito: um índice de autoria. Ele sai de uma coleta diária completa (cerca de 1 GB de
download):

```bash
uv run python -m monitor_comissoes.diaria executar
```

Esperado: além dos arquivos de sempre, `cache/indice-autoria.json` (dezenas de MB, fora do Git).

Depois, a checagem:

```bash
uv run python -m monitor_comissoes.pauta checar
```

Esperado na primeira vez: `OK: N reuniões (CE: n, CREDN: n) · linha de base · pauta checada em
DD/MM às HHhMM`, e os arquivos `data/pautas/AAAA-MM-DD.json` e `data/status-pauta.json`.

Conferência manual:

1. Abra `data/pautas/AAAA-MM-DD.json` e escolha uma reunião `convocada`.
2. Abra o `link` dela (`https://www.camara.leg.br/evento-legislativo/{id}`) e confira data, hora e
   itens.
3. Para um item com etiqueta, abra o `link` da proposição e confira autor ou relator.

Rodar a checagem de novo em seguida:

```bash
uv run python -m monitor_comissoes.pauta checar
```

Esperado: `0 alterações novas`, e o diff do arquivo do dia só em `checada_em`.

Simular falha (sem índice):

```bash
uv run python -m monitor_comissoes.pauta checar --indice nao-existe.json
```

Esperado: `FALHA [entrada_invalida]: …`, saída 1, `data/pautas/` igual, `data/status-pauta.json`
com `resultado: falha`.

## 4. Ativação no GitHub (depois do merge)

1. A primeira coleta agendada depois do merge grava o índice e o salva no cache.
2. Até lá, a checagem falha com `entrada_invalida` (visível, workflow vermelho). Para não esperar,
   dispare a "Coleta diária" manualmente e, depois, a "Checagem da pauta".
3. Confira no Actions que o passo de restauração do cache achou `indice-autoria-…` e que o commit
   `pauta: … · ok · … · linha de base` entrou no branch padrão.
