# Research: AGE — Execução diária agendada

Decisões técnicas do plano. R11 foi pesquisado em fontes públicas em 18/10/2026; as demais decorrem da spec, do código da COL (já mergeado) e da documentação do GitHub Actions citada em cada item.

## R1. Sem dependência nova

- **Decision**: nenhuma dependência de execução nova. Python usa só biblioteca padrão (`json`, `argparse`, `datetime`, `time`, `pathlib`). O workflow usa o `git` que já vem no runner, o `actions/checkout` e o `astral-sh/setup-uv` que o `ci.yml` já usa (mesmos pins).
- **Rationale**: constituição, princípio I. Tudo que a feature precisa (comparar inteiros, gravar JSON, repetir com espera, chamar `git`) cabe na biblioteca padrão e no shell.
- **Alternatives considered**: PyYAML para testar o workflow (rejeitado: dependência só para teste; o teste do workflow é textual, ver R12). `tenacity` para as novas tentativas (rejeitado: um laço de 15 linhas com `dormir` injetável é mais simples e testável).

## R2. A lógica fica em Python; o YAML só chama

- **Decision**: plausibilidade, escolha entre repetir e falhar, conteúdo do `status.json` e mensagem do commit ficam em módulos Python testáveis. O workflow só instala, chama `python -m monitor_comissoes.diaria`, faz `git add/commit/push` e propaga o código de saída.
- **Rationale**: FR-028 e princípio IV exigem testes sem rede, sem agendador e sem esperar tempo real. YAML não se testa em unidade; shell dentro do YAML também não. Quanto menos decisão no YAML, menos coisa só verificável em produção.
- **Alternatives considered**: lógica em shell no YAML com `jq` (rejeitado: intestável localmente, e a lógica de comparação de totais ficaria escondida).

## R3. Estoque bruto: PL e PLP pelo órgão do próprio último status

- **Decision**: o estoque bruto é o número de linhas dos arquivos `proposicoes-{ano}.csv` lidos com `siglaTipo` em `PL`/`PLP` e `ultimoStatus_siglaOrgao` em uma das comissões configuradas. Conta o **próprio** status de cada proposição, não o da referência, e ignora as etiquetas do NOVO. Entra na coleta como uma passada a mais sobre os arquivos já baixados.
- **Rationale**: o estoque bruto é um indicador de saúde do lote (PRODUCT.md §7: "provavelmente o arquivo veio truncado"), não um número do produto. O critério mais simples e que não depende da lógica de apensação é o que reproduz o número da sondagem: 1.356 PL + 12 PLP na CE e 159 PL + 4 PLP na CREDN = **1.531** (docs/fontes.md §3), que é o exemplo da spec. Contar pela referência exigiria resolver a cadeia de ~1.500 itens para um número que só serve de termômetro, e acoplaria o alarme a uma regra que pode ter bug.
- **Custo**: uma leitura a mais dos arquivos de proposições (a leitura do maior arquivo, 90 MB, levou 0,6 s; a passada inteira deve somar de 10 a 20 s, dentro de 159 s da execução completa medida na COL, R7 da COL).
- **Alternatives considered**: contar pela referência (rejeitado, acima). Contar todos os tipos (rejeitado: REQ e outros tipos mudam de órgão com muito mais volume e ruído, e não fazem parte do produto, D1).

## R4. A COL ganha `coletar`; `executar` continua igual por fora

- **Decision**: em `coleta.py`, o corpo de `executar` passa para uma função `coletar(config, transporte, agora)` que devolve o documento (`meta` + `itens`), o estoque bruto e a data dos dados da Câmara, **sem gravar**. `executar` vira `coletar` + `gravar_atomico`, com o mesmo comportamento, a mesma mensagem e o mesmo contrato de linha de comando. O `atual.json` **não muda de formato**.
- **Rationale**: a AGE precisa comparar o estoque bruto candidato com o do último retrato bom **antes** de substituir o `atual.json` (FR-007, FR-014/015). Hoje `executar` grava no fim; sem esta divisão, a AGE teria de gravar num caminho temporário e trocar depois, ou aceitar gravar antes de checar. É uma ampliação compatível: os testes existentes da COL seguem valendo sem mudança.
- **Alternatives considered**: gravar o candidato em arquivo temporário e comparar depois (rejeitado: mais I/O e mais um arquivo a limpar em cada falha). Pôr o total bruto no `meta` do `atual.json` (rejeitado pela decisão do mantenedor em 18/10/2026: o formato da COL não muda).

## R5. Regra de plausibilidade

- **Decision**:
  1. Estoque bruto igual a zero → falha `estoque_vazio` (mesma categoria da COL), com ou sem retrato anterior. A lista filtrada vazia continua falhando dentro da COL, com a mesma categoria.
  2. Com base anterior válida: falha `estoque_implausivel` quando `|novo − anterior| × 100 > limite × anterior`, com aritmética de inteiros. Exatamente 20% passa (FR-015). Vale para queda e para alta.
  3. Sem base anterior: a variação não se aplica (FR-016).
  4. Com `--aceitar-variacao`, **só** a falha do item 2 é ignorada e registrada (FR-018a/b). O item 1 e todas as outras falhas continuam valendo.
- **Base anterior**: o `estoque_bruto` do campo `ultimo_retrato_bom` do `status.json` do commit anterior. Ele só vale se o `gerado_em` desse campo for igual ao `meta.gerado_em` do `atual.json` em disco. Se não for (arquivo editado à mão, ou `atual.json` da COL de antes da AGE, sem status), não há base: a variação não se aplica, e a execução imprime em `stderr` "sem base para comparar a variação". Assim, o total bruto nunca é comparado com um retrato que não é o que ele descreve.
- **Decisão registrada (revisão de 18/10/2026, I2)**: com `atual.json` presente e base ausente (status apagado ou corrompido, `gerado_em` diferente, `atual.json` de antes da AGE), a variação **não é checada**, como este plano e a spec (FR-016) previram. O aviso vai ao log e, no Actions, vira anotação `::warning::` na execução; o workflow segue verde. Uma alternativa mais estrita, **não adotada e dependente de decisão do mantenedor**: falhar nesse caso, liberável por `--aceitar-variacao`. Custo dela: o primeiro dia depois de um `atual.json` commitado à mão e qualquer status perdido exigiriam um disparo manual com confirmação.
- **Rationale**: aritmética de inteiros evita erro de ponto flutuante na fronteira de exatamente 20%. Ligar a base ao `gerado_em` mantém a integridade (prioridade 1: nada em silêncio, nada comparado com o dado errado).
- **Alternatives considered**: comparar com o `total_itens` do `atual.json` (rejeitado pela pergunta 1 da clarificação). Guardar o histórico de totais (rejeitado: o Git já tem o histórico e só o último importa).

## R6. Novas tentativas: laço em Python, janela de cerca de 1h40

- **Decision**: o laço fica em `diaria.py`. Até `tentativas` (4) execuções da coleta, com `espera_minutos` (30) entre elas, só quando a categoria da falha for repetível: `fonte_indisponivel`, `arquivos_desatualizados`, `arquivo_incompleto` e `api_deputados`. Não repetem: `configuracao`, `formato_alterado`, `estoque_vazio`, `estoque_implausivel` e `interna`. `dormir` e o relógio são injetáveis, e os testes não esperam tempo real (FR-019, FR-020, FR-028).
- **Lacuna da spec, a registrar**: a spec lista as categorias repetíveis (FR-019) e as não repetíveis (FR-020), mas **não cita `estoque_vazio`** (lista filtrada vazia ou estoque bruto vazio). O plano a trata como **não repetível**, igual ao estoque implausível: é problema de conteúdo do dado, e repetir 30 minutos depois só atrasaria a falha. O `/speckit-analyze` deve acrescentar `estoque_vazio` ao FR-020.
- **Orçamento de tempo**: uma coleta completa levou ~159 s (COL, R7). Quatro tentativas com três esperas de 30 min somam ~1h40 (4 × 3 min + 90 min). O `timeout` interno é de 200 min e o job leva `timeout-minutes: 240` (R15).
- **Rationale**: decidido pelo mantenedor na pergunta 3. Um único job só fica vermelho, e só manda e-mail, se todas as tentativas falharem. Em repositório público os minutos do Actions não são cobrados.
- **Alternatives considered**: vários agendamentos por dia (rejeitado pelo mantenedor: ruído de e-mail a cada tentativa que falha).

## R7. `status.json`: uma fotografia da última execução, com a base do dia seguinte

- **Decision**: formato em [contracts/status-json.md](contracts/status-json.md). Ordem de campos fixa, mesma serialização do `atual.json` (reaproveita `gravar_atomico`). Em sucesso, `ultimo_retrato_bom` descreve o retrato recém-gravado (inclusive o `estoque_bruto`). Em falha, ele é **recomposto**: `gerado_em`, `dados_camara_em` e `total_itens` vêm do `meta` do `atual.json` em disco (a verdade sobre o arquivo mantido), e o `estoque_bruto` vem do `status.json` anterior, quando passar na checagem de R5. Sem `atual.json`, é `null`.
- **Rationale**: FR-010 e FR-011 pedem que as features seguintes (PAG e AVI) leiam o status sem precisar abrir o `atual.json` para saber a "data dos últimos dados bons". Recompor a partir do `atual.json` evita que o status e o arquivo discordem.
- **Alternatives considered**: um `status.json` que acumula histórico (rejeitado: o Git já guarda e PRODUCT.md D8 diz que o histórico fica no Git). Guardar só a falha (rejeitado: PAG precisa do "verificado em" também em sucesso).

## R8. O workflow

- **Decision**: arquivo `.github/workflows/coleta-diaria.yml`, descrito em [contracts/workflow.md](contracts/workflow.md):
  - Gatilhos: `schedule` (um cron diário) e `workflow_dispatch` com a entrada booleana `aceitar_variacao` (padrão `false`). Não há gatilho `push`, então o commit do bot não pode disparar a coleta (FR-003).
  - `concurrency` com grupo fixo e `cancel-in-progress: false` (FR-023).
  - `permissions: contents: write` só nesse job; nenhum segredo além do token padrão (FR-031).
  - `timeout-minutes: 240`, com a coleta limitada a 200 min por `timeout` interno (R15).
- **Fatos da documentação do GitHub** (consultados em 18/10/2026, [eventos que disparam workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) e [concorrência](https://docs.github.com/en/actions/using-jobs/using-concurrency)):
  - "Scheduled workflows run on the latest commit on the default branch." Portanto o agendamento só passa a existir depois do merge na branch principal, e a verificação real do workflow é depois do merge.
  - "The `schedule` event can be delayed during periods of high loads of GitHub Actions workflow runs." Por isso o cron não usa minuto 0.
  - Eventos disparados com o `GITHUB_TOKEN` não criam novas execuções de workflow, com a exceção de `workflow_dispatch` e `repository_dispatch`. Logo, o push do bot não dispara o `ci.yml` (que escuta `push` em `main`), e isso é aceitável: o commit só traz dados.
  - "At most one running job or workflow in a concurrency group at any time" e, por padrão, no máximo uma execução pendente: uma nova execução pendente **cancela a pendente anterior**. Como a execução pendente cancelada nunca começou, nenhuma execução bem-sucedida é descartada (FR-024).
- **Rationale**: o gatilho `schedule` e o `workflow_dispatch` com a mesma tarefa atendem FR-001 e FR-004 sem duplicar passos.

## R9. Sequência de commit e a garantia de `atual.json` intacto

- **Decision**: o passo do workflow roda a coleta com `set +e`, guarda o código de saída e continua:
  1. Se o código for diferente de zero: `git checkout -- data/atual.json` (cinto e suspensórios: o Python já não o altera em falha; isso garante FR-007 mesmo se o processo morrer entre duas gravações). Em falha, só o `data/status.json` é adicionado.
  2. Se for zero: adiciona `data/atual.json` e `data/status.json`.
  3. Commit com a mensagem de `python -m monitor_comissoes.diaria mensagem`, `git pull --rebase origin <branch>` e `git push` (com uma nova tentativa de pull e push se o primeiro push for recusado).
  4. O passo termina com o código de saída da coleta. Se o próprio commit ou o push falhar, o passo falha por `set -e` a partir daí (FR-006, FR-008).
- **Gravação do par em sucesso**: o Python **prepara os dois arquivos como temporários** (com `fsync`) e só então troca os dois com `os.replace`, o `atual.json` primeiro. Assim, uma falha ao preparar qualquer um deles (disco cheio, permissão) não troca nenhum dos dois, e o `atual.json` anterior continua intacto já no nível do processo. Se a troca do segundo falhar depois da do primeiro (erro, não morte do processo), `gravar_par` restaura o `atual.json` ao conteúdo anterior (ou o remove, se não existia) antes de propagar o erro; o status de falha gravado em seguida descreve, então, o retrato que está de fato em disco. O que sobra é a morte do processo entre os dois `os.replace`: o código de saída é diferente de zero e o passo do workflow restaura o `atual.json` do Git antes de commitar só o status de falha (revisão de 18/10/2026, M1).
- **Rationale**: FR-007, FR-008 e FR-009.
- **Conflito no push**: o bot só toca em `data/`. O `git pull --rebase` imediatamente antes do push cobre alguém ter empurrado para a branch principal durante a janela de até 1h40. Uma segunda recusa falha o job de forma visível (caso de borda da spec). Um disparo manual numa branch que não é a padrão grava os dados nessa branch; é intencional, para o teste do quickstart (passo 5). O disparo manual só vale em **branch**: a partir de uma tag, `GITHUB_REF_NAME` é o nome da tag e o push falha de forma visível, sem dano.

## R10. Aceitar a variação

- **Decision**: a entrada `aceitar_variacao` só existe no `workflow_dispatch`. O passo passa `--aceitar-variacao` à coleta somente quando `github.event_name == 'workflow_dispatch'` e a entrada é verdadeira. Com a variação aceita, o `status.json` traz o campo `variacao_aceita` (estoque anterior, novo, variação em %) e a mensagem do commit diz "variação aceita manualmente" (FR-018a/b).
- **Rationale**: decidido pelo mantenedor na pergunta 2. A confirmação não existe no agendamento, e vale só para aquela execução. No dia seguinte, a base é o estoque aceito, e o limite volta ao normal.
- **Alternatives considered**: subir o limite em `config.toml` (rejeitado pelo mantenedor: fica frouxo depois).

## R11. Risco de desativação do agendamento após 60 dias (consultado em 18/10/2026)

- **O que a fonte oficial diz**: "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." (GitHub Docs, [eventos que disparam workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) e [desativar e reativar um workflow](https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow)). Para reativar: botão "Enable workflow" na aba Actions, ou `gh workflow enable`.
- **O que a fonte oficial NÃO diz**: o que conta como "repository activity". As duas páginas não definem o termo, e não afirmam nem negam que commits feitos pelo `GITHUB_TOKEN` contam.
- **Fontes não oficiais**: guias e discussões descrevem a regra, e um deles diz que qualquer commit reinicia a contagem. O projeto [efrecon/gh-action-keepalive](https://github.com/efrecon/gh-action-keepalive) existe para evitar a desativação e funciona gerando um commit na branch principal, o que sugere que commits automáticos contam, mas não é afirmação oficial sobre commits do `GITHUB_TOKEN`. O mesmo projeto avisa que um método anterior de simular atividade deixou de contornar o prazo.
- **Conclusão**: **o risco não pôde ser confirmado nem afastado por fonte oficial.** É plausível que o commit diário do bot já seja atividade suficiente, mas isso é hipótese. Um agendamento desativado não roda de novo sozinho, e nenhum outro workflow do repositório se salvaria, porque todos os agendados seriam desativados. A única detecção automática é a ausência do commit diário e a faixa de "dados atrasados" depois de 30 horas, que é da feature PAG.
- **Mitigações possíveis, para decisão do mantenedor, nenhuma implementada** (FR-027):
  1. **Não fazer nada** e confiar no commit diário. Custo zero. Se a hipótese estiver errada, o produto para em silêncio, com o sinal descrito acima.
  2. **Teste empírico**: o primeiro sinal real só aparece depois de 60 dias de operação. Registrar a data de início da operação e, em torno do dia 55, conferir na aba Actions que o workflow segue ativo.
  3. **Atividade humana periódica**: o mantenedor faz um commit próprio (por exemplo, uma linha no changelog) a cada 50 dias. Manual, mas independente de hipótese.
  4. **Gatilho externo**: `workflow_dispatch` chamado por um agendador de fora do GitHub. Exige token em segredo, o que a constituição permite (princípio VI) mas que aumenta a superfície. Não recomendado antes de se saber se há risco.
- **Entregável**: `docs/agendamento-60-dias.md`, com este conteúdo, os links e a data da consulta (FR-026, SC-008).

## R12. Estratégia de testes, sem rede

- **Decision**:
  - As fixtures da COL (`tests/fixtures/camara/`, 48 arquivos reais) e o `TransporteFalso` de `tests/conftest.py` são reaproveitados. O guarda de rede (`sem_rede`) segue valendo para todos os testes.
  - Retratos sintéticos (dicionários e arquivos temporários em `tmp_path`) para a plausibilidade e para a base do `status.json`.
  - `dormir` injetável registra as esperas pedidas sem esperar.
  - O workflow tem um teste **textual** (`tests/test_workflow.py`): lê o arquivo como texto e confere o cron, o `concurrency`, as permissões, o `timeout-minutes`, a ausência de gatilho `push`, a ausência de `secrets.` além do `GITHUB_TOKEN` padrão e a restrição do `--aceitar-variacao` ao `workflow_dispatch`. Não substitui a verificação real no GitHub (quickstart).
- **Rationale**: princípio IV e FR-028/029. O disparo real do agendamento e o push real só podem ser verificados no GitHub, depois do merge.

## R13. Horário do agendamento

- **Decision**: `cron: "37 6 * * *"`, ou seja, 06:37 UTC = 03:37 de Brasília.
- **Rationale**: a sondagem de 17/10/2026 mostrou a regeneração do lote entre 04:31 e 05:21 UTC (01h31 a 02h21 de Brasília), então 06:37 UTC dá cerca de 1h15 de folga. As 4 tentativas terminam em até ~1h40, por volta das 05h20 de Brasília no pior caso, mais o atraso do agendador (que a documentação diz poder ocorrer em carga alta). O resumo diário (AVI) sai por volta das 7h de Brasília, ainda com margem. O minuto 37 evita o topo da hora, quando o agendador costuma atrasar mais.
- **Alternatives considered**: 06:00 UTC (rejeitado: topo da hora). Horário mais cedo (rejeitado: corre o risco de pegar a regeneração no meio, o que a COL trata como falha repetível, mas gasta tentativa).

## R14. Proteção de branch e primeiro commit

- **Decision**: o plano assume push direto na branch padrão com o `GITHUB_TOKEN` (spec, Assumptions). Se houver proteção de branch exigindo pull request, o push falha de forma visível, e o ajuste é decisão do mantenedor (por exemplo, liberar o `github-actions[bot]` na proteção). A pasta `data/` ainda não existe no repositório: o primeiro commit do bot cria `data/atual.json` e `data/status.json` (FR-002, cenário 3 da US1).
- **Rationale**: simplicidade. Abrir pull request automático a cada dia seria muito mais código e ruído.

## R15. Tempo limite: o `timeout` interno grava o status antes de o job ser morto

- **Problema** (revisão independente de 18/10/2026, I1): se o job estourar o `timeout-minutes`, o GitHub mata o processo; o Python não passa por nenhum `except`, o bash não chega ao commit, e fica um workflow vermelho **sem** `status.json` de falha (contra FR-008 e FR-021).
- **Decision**: a coleta roda sob `timeout --signal=TERM 200m`, e o Python instala um tratador de `SIGTERM` que levanta `InterrupcaoPorSinal`. A exceção cai no `except Exception`, o status de falha `interna` ("recebeu SIGTERM …") é gravado e o código de saída é 1; o bash então commita o status e termina vermelho. O job tem `timeout-minutes: 240` como rede de segurança, com 40 minutos para o commit. O tratador é instalado só no comando `executar` e restaurado ao sair.
- **Conferido**: `uv run` **não** repassa o `SIGTERM` ao Python (testado em 18/10/2026: o `timeout` mata o `uv` e o tratador do Python nem roda). Por isso o workflow chama `.venv/bin/python -m monitor_comissoes.diaria` direto, depois do `uv sync --locked`.
- **Orçamento**: 4 coletas e 3 esperas de 30 min somam ~1h40 com coletas de ~3 min. As 200 min permitem coletas de até ~27 min cada antes de estourar.
- **`--kill-after=10m`**: se o Python não sair em 10 minutos depois do TERM (travado onde o tratador não roda), o `timeout` manda KILL; 200 + 10 cabem nos 240 do job (revisão de 18/10/2026, rodada 2).
- **Limite aceito**: um SIGTERM que chegue depois de `gravar_par` terminar e antes do `return` (microssegundos, só no minuto 200) deixa o status de sucesso gravado e o `atual.json` restaurado do Git pelo workflow; no dia seguinte a base não confere e a variação não é checada, com aviso. Teórico, sem perda de dados.
- **Alternatives considered**: só aumentar o `timeout-minutes` (rejeitado: não grava status se estourar mesmo assim). Gravar um status provisório antes de começar (rejeitado: mudaria o contrato e o `status.json` de "sucesso" intermediário seria uma mentira).
