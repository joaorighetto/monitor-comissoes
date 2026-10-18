# Feature Specification: AGE — Execução diária agendada

**Feature Branch**: `claude/sharp-tesla-tvtc79` (sem branch própria de feature; o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido)

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "Feature AGE — Execução diária agendada (linha AGE do ROADMAP.md)", com o recorte "Inclui" e "Não inclui" da linha e os pontos em aberto levantados na situação.

## Clarifications

### Session 2026-10-18

- Q: A checagem de "variação de mais de 20% em um dia" compara o estoque bruto de PL/PLP nas comissões acompanhadas ou a lista filtrada do NOVO? → A: O estoque bruto (todos os PL/PLP nas comissões acompanhadas, antes do filtro do NOVO). O total bruto de cada execução é guardado no `status.json`; o formato do `atual.json` da COL não muda. A lista filtrada vazia continua sendo falha.
- Q: Como o mantenedor libera um dia em que a variação acima de 20% é real (por exemplo, arquivamento em massa na posse)? → A: Por disparo manual do workflow com confirmação explícita ("aceito esta variação"), válida só para aquela execução. O `status.json` e a mensagem do commit registram a variação aceita e os dois totais. O limite em configuração não é afrouxado.
- Q: O que são as "novas tentativas" da AGE? → A: Repetir a execução inteira dentro do mesmo job, com espera entre tentativas: até 4 tentativas, 30 minutos entre elas (janela de cerca de 1h30), só para falhas que podem ser passageiras. O workflow só fica vermelho se todas falharem. Não há mais de um agendamento por dia.
- Q: Uma segunda execução bem-sucedida no mesmo dia gera novo commit ou é descartada? → A: Cada execução bem-sucedida gera o seu commit. Os itens são idênticos e só mudam os momentos de geração e verificação. Nenhuma execução bem-sucedida é descartada. MUD e AVI devem tratar reexecuções do mesmo dia (requisito para elas, não implementado aqui).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Todo dia, o retrato do dia fica versionado (Priority: P1)

Sem ninguém acionar nada, o produto roda uma vez por dia, executa a coleta da COL e grava no Git o `data/atual.json` do dia e o `data/status.json`, num único commit feito pelo bot. O commit acontece mesmo quando a lista não mudou: o histórico do Git é o registro de que a execução rodou (PRODUCT.md, D8).

**Why this priority**: sem a execução diária não há histórico, e a feature MUD precisa do retrato de ontem. Sozinha, já entrega o que o ROADMAP.md pede: dados atualizados todo dia, sem servidor e sem cuidado diário (constituição, princípio I).

**Independent Test**: simular a execução sobre fixtures (coleta bem-sucedida, com e sem mudança na lista) e conferir que o resultado do dia inclui `atual.json` e `status.json` atualizados, num só commit, e que a falta de mudança na lista não impede o commit.

**Acceptance Scenarios**:

1. **Dado** uma coleta bem-sucedida e uma lista diferente da de ontem, **Quando** a execução termina, **Então** um commit do bot contém o novo `data/atual.json` e o `data/status.json` com resultado "ok".
2. **Dado** uma coleta bem-sucedida e uma lista idêntica à de ontem, **Quando** a execução termina, **Então** o commit do dia é feito mesmo assim, porque ao menos o momento da geração e o da verificação mudaram.
3. **Dado** que ainda não existe `data/` no repositório (primeiro dia), **Quando** a primeira execução bem-sucedida termina, **Então** `data/atual.json` e `data/status.json` são criados e commitados.
4. **Dado** um commit feito pelo próprio bot, **Quando** ele chega ao repositório, **Então** ele não dispara uma nova execução da coleta (sem laço).
5. **Dado** a execução bem-sucedida, **Quando** se lê o `data/status.json`, **Então** ele informa o resultado "ok", o momento da verificação, a data dos dados da Câmara e o momento em que o `atual.json` foi gerado.

---

### User Story 2 - Uma falha deixa o workflow vermelho e os dados bons intactos (Priority: P1)

Quando a coleta falha por qualquer motivo (fonte fora do ar, formato alterado, arquivos desatualizados, estoque implausível, erro inesperado), o workflow termina vermelho, o último `data/atual.json` bom continua byte a byte como estava, e o `data/status.json` registra o que aconteceu. O registro da falha vai para o Git, para que a página e o aviso futuros possam anunciá-la, e só então o workflow termina com erro.

**Why this priority**: o gabinete decide a partir da lista, e uma lista vazia ou parcial tomada por verdade é o pior erro possível (constituição, princípio III; PRODUCT.md, D10 e §7). Também é o que denuncia a falha ao mantenedor: o GitHub avisa por e-mail quando o workflow fica vermelho.

**Independent Test**: para cada categoria de falha da COL e para a falha de plausibilidade, simular a execução e conferir três coisas: o workflow termina com erro, o `atual.json` anterior está idêntico byte a byte, e o `status.json` traz o resultado "falha" com a categoria e o motivo.

**Acceptance Scenarios**:

1. **Dado** uma falha da coleta de qualquer categoria da COL, **Quando** a execução termina, **Então** o workflow fica vermelho e o `data/atual.json` é idêntico ao do commit anterior.
2. **Dado** essa mesma falha, **Quando** se lê o `data/status.json` commitado, **Então** ele informa o resultado "falha", o momento da verificação, a categoria, o motivo e a data dos últimos dados bons (a do `atual.json` mantido).
3. **Dado** uma falha inesperada (erro de programação, interrupção), **Quando** a execução termina, **Então** o resultado é o mesmo: workflow vermelho, `atual.json` intacto e `status.json` com falha de categoria "interna".
4. **Dado** que a falha acontece no primeiro dia, sem `atual.json` anterior, **Quando** a execução termina, **Então** não existe `atual.json`, o `status.json` registra a falha, e a data dos últimos dados bons consta como inexistente.
5. **Dado** que o próprio commit ou envio ao repositório falha, **Quando** a execução termina, **Então** o workflow fica vermelho e nenhum arquivo de dados fica gravado pela metade.
6. **Dado** uma falha seguida, no mesmo dia, de uma execução bem-sucedida, **Quando** se lê o `data/status.json`, **Então** ele mostra "ok", sem resto da falha anterior.

---

### User Story 3 - Estoque implausível não é publicado (Priority: P1)

Antes de substituir o `atual.json`, o sistema confere se o resultado é plausível: estoque vazio, lista vazia ou variação de mais de 20% em relação ao último retrato bom indicam, provavelmente, um arquivo truncado (PRODUCT.md, §7). Nesse caso, a execução falha como qualquer outra, e o último retrato bom é mantido.

**Why this priority**: é a defesa contra o erro que a validação do arquivo da COL não pega: uma fonte que responde sem erro, mas com dados a menos. Sem ela, a lista parcial é publicada como completa (constituição, princípio III).

**Independent Test**: com retratos sintéticos (anterior e candidato), conferir que a variação acima do limite, o estoque vazio e a lista vazia falham, e que a variação dentro do limite passa. Sem rede.

**Acceptance Scenarios**:

1. **Dado** um último retrato bom cujo estoque bruto era de 1.531 itens e um candidato com 1.100 (queda de 28%), **Quando** a execução roda, **Então** ela falha com a categoria "estoque implausível" e o motivo traz os dois totais brutos e a variação. A mesma regra vale para um aumento de mais de 20%.
2. **Dado** um candidato com variação de até 20%, **Quando** a execução roda, **Então** a checagem passa e o resultado é gravado normalmente.
3. **Dado** um estoque bruto vazio (nenhum PL/PLP nas comissões acompanhadas), **Quando** a execução roda, **Então** ela falha, mesmo sem retrato anterior para comparar.
4. **Dado** uma lista filtrada vazia, **Quando** a execução roda, **Então** ela falha (a COL já faz isso; a AGE mantém o comportamento e o registra no `status.json`).
5. **Dado** que não existe retrato anterior (primeiro dia), **Quando** a execução roda, **Então** a comparação de variação não se aplica, e só valem as checagens de estoque e lista vazios.
6. **Dado** uma lista filtrada do NOVO que encolheu mais de 20% (por exemplo, um deputado do NOVO se licenciou) com o estoque bruto estável, **Quando** a execução roda, **Então** a checagem de variação passa: a variação da lista filtrada não é critério de plausibilidade.
7. **Dado** uma falha no dia anterior, **Quando** a execução do dia compara os totais, **Então** a base de comparação é o estoque bruto do último retrato **bom**, e não o da execução que falhou.
8. **Dado** uma execução bloqueada por variação acima de 20% que o mantenedor, depois de conferir na fonte, reconhece como legítima, **Quando** ele dispara o workflow manualmente marcando a confirmação "aceito esta variação", **Então** aquela execução ignora o limite, grava o resultado e registra no `status.json` e na mensagem do commit que a variação foi aceita manualmente, com os dois totais.
9. **Dado** uma execução com a confirmação marcada, **Quando** a execução do dia seguinte roda sem confirmação, **Então** a base de comparação é o estoque bruto aceito, e o limite de 20% volta a valer normalmente.
10. **Dado** o disparo manual com a confirmação marcada, **Quando** a coleta falha por outro motivo (fonte fora do ar, formato alterado), **Então** a confirmação não libera nada: só a falha de variação é ignorada, as demais continuam sendo falha.
11. **Dado** o disparo manual sem a confirmação marcada, **Quando** a variação passa de 20%, **Então** a execução falha como no agendamento.
12. **Dado** uma variação de exatamente 20%, **Quando** a checagem roda, **Então** ela passa: só "mais de 20%" é implausível.

---

### User Story 4 - Novas tentativas diante de falha passageira (Priority: P2)

Falhas passageiras, como a Câmara ainda não ter regenerado o lote ou uma indisponibilidade curta, não devem custar um dia sem dados. O sistema repete a execução inteira, no mesmo job, com espera entre as tentativas (até 4 tentativas, 30 minutos entre elas), antes de dar a falha por definitiva. A COL já repete cada requisição HTTP, com esperas de segundos; a AGE trata a repetição da execução inteira, com esperas de minutos.

**Why this priority**: sem ela, uma falha de minutos vira um dia de atraso e um e-mail de alerta desnecessário. Não bloqueia o primeiro resultado, mas é requisito da linha ("novas tentativas").

**Independent Test**: simular uma sequência de resultados (falha passageira seguida de sucesso; falhas até esgotar as tentativas) e conferir o resultado final e o `status.json` de cada caso, sem rede e sem esperar o tempo real.

**Acceptance Scenarios**:

1. **Dado** uma tentativa que falha por causa passageira e outra, depois da espera, que funciona, **Quando** a execução do dia termina, **Então** o resultado final é "ok", o commit do dia é feito e o workflow fica verde.
2. **Dado** que as 4 tentativas permitidas falham, todas por causa repetível, **Quando** a execução do dia termina, **Então** o workflow fica vermelho e o `status.json` registra a falha da última tentativa e quantas tentativas houve.
3. **Dado** uma falha que repetir não resolve (configuração inválida, formato alterado, estoque vazio, estoque implausível), **Quando** a execução roda, **Então** o sistema não gasta novas tentativas e falha de imediato.
4. **Dado** uma falha de "arquivos desatualizados" ou "gerados em momentos diferentes" (o lote ainda estava sendo regenerado), **Quando** a execução roda, **Então** ela conta como falha que vale nova tentativa depois da espera.
5. **Dado** uma falha repetível na tentativa 1 e outra na tentativa 2, seguidas de sucesso na tentativa 3, **Quando** a execução termina, **Então** o `status.json` registra resultado "ok" com 3 tentativas, e não há falha anunciada.
6. **Dado** uma falha da API de deputados, **Quando** a execução roda, **Então** ela conta como repetível, como a indisponibilidade da fonte.
7. **Dado** que a espera entre tentativas é um valor de configuração, **Quando** os testes simulam as tentativas, **Então** eles não esperam tempo real.

---

### User Story 5 - Reexecução no mesmo dia não duplica nem corrompe (Priority: P2)

O agendamento pode coincidir com um disparo manual, e o mantenedor pode rodar de novo por conta própria. Duas execuções no mesmo dia devem terminar no mesmo conteúdo de lista, sem corrida entre elas e sem aviso duplicado (constituição, princípio V).

**Why this priority**: a idempotência é princípio da constituição, e a coleta é pesada (cerca de 1 GB), então duas execuções simultâneas seriam desperdício e risco de conflito no repositório. Não bloqueia o primeiro resultado.

**Independent Test**: simular duas execuções sobre as mesmas fixtures e conferir que a lista de itens é idêntica e que cada execução bem-sucedida gera o seu commit. A exclusão mútua se confere pela configuração do agendador, sem rede.

**Acceptance Scenarios**:

1. **Dado** duas execuções sobre os mesmos dados no mesmo dia, **Quando** ambas terminam, **Então** a lista de itens (conteúdo e ordem) é idêntica, e só os momentos de geração e verificação diferem.
2. **Dado** uma execução em andamento, **Quando** outra é disparada, **Então** as duas não rodam ao mesmo tempo: a segunda espera a primeira terminar e só então roda, e nenhuma delas deixa o repositório em conflito.
3. **Dado** uma segunda execução bem-sucedida no mesmo dia de Brasília, **Quando** ela termina, **Então** ela gera o seu próprio commit com `atual.json` e `status.json`, e nenhuma execução bem-sucedida é descartada.
4. **Dado** uma reexecução depois de uma falha no mesmo dia, **Quando** ela é bem-sucedida, **Então** ela grava e commita normalmente.

---

### User Story 6 - Risco de desativação do agendamento confirmado (Priority: P2)

O ROADMAP.md deixa em aberto se o GitHub desativa o agendamento de um repositório público depois de 60 dias sem atividade, e se os commits do próprio bot contam como atividade. A feature entrega essa confirmação documentada, com a fonte oficial e a data da consulta. Se o risco for real, o mantenedor decide a mitigação.

**Why this priority**: se o agendamento for desativado em silêncio, o produto para sem ninguém notar, o que contradiz o princípio III. A confirmação é barata e evita um dia de surpresa.

**Independent Test**: conferir que existe documento no repositório com a regra, o link oficial, a data da consulta e a conclusão ("o commit diário do bot basta" ou "o risco existe: mitigação proposta ao mantenedor").

**Acceptance Scenarios**:

1. **Dado** a documentação oficial do GitHub, **Quando** a confirmação é registrada, **Então** o documento diz se há desativação por inatividade em repositório público, depois de quantos dias, e se commits feitos por workflow contam como atividade, com o link e a data da consulta.
2. **Dado** que a confirmação conclua que o risco existe mesmo com o commit diário do bot, **Quando** o documento é entregue, **Então** ele propõe a mitigação e a deixa como decisão do mantenedor, sem implementá-la.
3. **Dado** que a confirmação conclua que o commit diário basta, **Quando** o documento é entregue, **Então** ele registra a conclusão e nenhuma mitigação é criada.

---

### Edge Cases

- **Execução atrasada pelo agendador.** O agendador do GitHub pode atrasar a execução em minutos ou até mais de uma hora. O horário escolhido deve ter folga para o atraso e para o fim da regeneração do lote, e ainda terminar bem antes do resumo diário das 7h de Brasília.
- **Lote regenerado no meio da coleta.** A COL já detecta arquivos gerados em momentos diferentes (mais de 6 horas). A AGE trata isso como falha que vale nova tentativa (User Story 4).
- **Dia sem execução nenhuma.** Se o agendador não rodar, não há commit nem `status.json` novo. O sinal é a idade do último "momento da verificação", que a feature PAG usará para a faixa de atraso (30 horas). A AGE só garante que o campo existe e é sempre o da última execução.
- **Fuso e virada de dia.** "Mesmo dia" é o dia de Brasília. O agendador conta em UTC, e uma execução atrasada pode cair no dia seguinte de Brasília.
- **Dia legitimamente atípico.** Na posse (1º/02/2027) e na recomposição anual das comissões, a variação de mais de 20% é esperada (PRODUCT.md, §5.6). O caminho de liberação é o disparo manual com confirmação (User Story 3, cenário 8); sem ele, a checagem travaria o produto justamente nesses dias. Se o mantenedor não estiver presente, o produto fica com o último retrato bom e a falha anunciada.
- **Falha logo no primeiro dia.** Sem `atual.json` anterior, não há "dados bons" a manter; o `status.json` diz isso em vez de apontar uma data inexistente.
- **Mudança de configuração entre dias.** Trocar a lista de comissões muda o estoque de forma legítima, e a comparação de variação pode acusar falso positivo no dia da troca. Isso é conhecido e cai no mesmo caminho de liberação do dia atípico (disparo manual com confirmação).
- **Conflito no envio do commit.** Se alguém empurrar para a branch principal durante a execução, o envio do bot pode ser recusado. A execução falha de forma visível, sem perder o `atual.json` bom.
- **Commit do bot e a integração contínua.** O commit do bot não precisa passar pelos testes (ele só traz dados) e não deve disparar a coleta de novo.

## Requirements *(mandatory)*

### Functional Requirements

**Execução e commit diário**

- **FR-001**: O sistema DEVE executar a coleta da COL uma vez por dia, automaticamente, sem intervenção do mantenedor e sem servidor próprio.
- **FR-002**: Em execução bem-sucedida, o sistema DEVE gravar o `data/atual.json` e o `data/status.json` no repositório, num único commit feito pelo bot, mesmo quando a lista de itens for idêntica à do dia anterior (PRODUCT.md, D8).
- **FR-003**: O commit do bot NÃO DEVE disparar uma nova execução da coleta.
- **FR-004**: O sistema DEVE permitir o disparo manual da mesma execução, com o mesmo comportamento da execução agendada, exceto pela confirmação de variação (FR-018a).
- **FR-005**: O agendamento DEVE ter horário que dê folga para o fim da regeneração do lote da Câmara e para o atraso do agendador, e termine antes das 7h de Brasília. A primeira tentativa deve começar por volta das 03h30 de Brasília, logo depois do fim esperado da regeneração (cerca de 02h21), de modo que as 4 tentativas terminem bem antes das 7h mesmo com o atraso do agendador. O horário exato em UTC é decidido no `plan.md`.

**Falha visível**

- **FR-006**: Em qualquer falha da coleta, da checagem de plausibilidade, do commit ou inesperada, o workflow DEVE terminar vermelho.
- **FR-007**: Em qualquer falha, o sistema NÃO DEVE alterar o `data/atual.json` existente, que DEVE permanecer idêntico byte a byte (constituição, princípio III; PRODUCT.md, D10).
- **FR-008**: Em falha, o sistema DEVE registrar o resultado no `data/status.json` e commitá-lo, e só então terminar o workflow com erro. Se não for possível commitar o `status.json`, o workflow DEVE terminar vermelho do mesmo jeito.
- **FR-009**: O sistema NÃO DEVE gravar nenhum arquivo de dados pela metade, em nenhuma falha, inclusive na falha do commit ou do envio.

**`data/status.json`**

- **FR-010**: O `data/status.json` DEVE trazer, no mínimo: resultado ("ok" ou "falha"); momento da verificação (o da última execução, bem-sucedida ou não); categoria e motivo da falha, quando houver; data dos dados da Câmara do último `atual.json` bom; momento da geração desse `atual.json`; total bruto do estoque do último retrato bom (base da checagem do dia seguinte, FR-015); e número de tentativas da execução. Em falha, o total bruto e as datas continuam sendo os do último retrato bom.
- **FR-011**: O `status.json` DEVE conter as informações de que as features seguintes precisam, sem que a AGE as renderize nem as envie: a linha "verificado em DD/MM às HHhMM" e a faixa de erro da página (PAG), e a mensagem de erro com "a data dos últimos dados bons" (AVI).
- **FR-012**: O `status.json` DEVE ter ordem de campos fixa e conteúdo determinístico para os mesmos dados, para que o diff diário no Git seja legível (como o `atual.json`).
- **FR-013**: Não DEVE sobrar, em um `status.json` de sucesso, nenhum resto de falha anterior.

**Plausibilidade**

- **FR-014**: Antes de substituir o `atual.json`, o sistema DEVE falhar quando o estoque bruto for vazio ou a lista filtrada for vazia, com ou sem retrato anterior.
- **FR-015**: O sistema DEVE falhar quando o **estoque bruto** variar mais de 20% em relação ao do último retrato bom, em qualquer sentido (aumento ou queda). A variação de exatamente 20% passa. A variação da lista filtrada do NOVO NÃO é critério de plausibilidade.
- **FR-015a**: O **estoque bruto** é o total de PL e PLP que estão nas comissões acompanhadas, contado antes de aplicar as etiquetas do NOVO. O critério exato de contagem (órgão do próprio último status ou da referência) é decidido no `plan.md`, desde que seja o mesmo todo dia e independa das etiquetas. O total de cada execução bem-sucedida DEVE ser gravado no `status.json` (FR-010); o formato do `atual.json` da COL NÃO muda.
- **FR-016**: Sem retrato anterior (primeiro dia), o sistema NÃO DEVE aplicar a checagem de variação.
- **FR-017**: A falha de plausibilidade DEVE ter categoria própria, e o motivo DEVE trazer os totais comparados e a variação, para que o mantenedor reconheça o caso.
- **FR-018**: O limite de 20% DEVE ser um valor de configuração, não constante no código. Trocá-lo NÃO DEVE exigir mudança de código. O limite NÃO é o caminho previsto para liberar um dia atípico.
- **FR-018a**: O disparo manual DEVE oferecer uma confirmação explícita ("aceito esta variação"), desligada por padrão. Com ela marcada, a execução DEVE ignorar **somente** a falha de variação de mais de 20%; as demais falhas e a checagem de estoque vazio continuam valendo. A confirmação vale só para aquela execução e NÃO DEVE ser possível no agendamento automático.
- **FR-018b**: Quando a variação for aceita, o `status.json` DEVE registrar que a variação foi aceita manualmente, com o estoque bruto anterior, o novo e a variação, e a mensagem do commit do bot DEVE dizer o mesmo. O estoque bruto aceito passa a ser a base do dia seguinte.

**Novas tentativas**

- **FR-019**: O sistema DEVE repetir a execução inteira, no mesmo job, quando a falha puder ser passageira: fonte indisponível, arquivos desatualizados, arquivos gerados em momentos diferentes, arquivo incompleto e erro na API de deputados. O limite é de **4 tentativas no total**, com **30 minutos de espera** entre elas (cerca de 1h30 só de espera; com o tempo das coletas, cerca de 1h40). O número de tentativas e a espera DEVEM ser valores de configuração.
- **FR-019a**: Haverá um único agendamento por dia. As novas tentativas acontecem dentro dessa execução, e o workflow só fica vermelho se todas falharem.
- **FR-020**: O sistema NÃO DEVE repetir falhas que repetir não resolve: configuração inválida, formato alterado, estoque vazio (estoque bruto ou lista filtrada), estoque implausível e falha interna (erro de programação).
- **FR-021**: Esgotadas as tentativas, o sistema DEVE tratar a execução como falha (FR-006 a FR-009), registrando o número de tentativas.

**Reexecução e concorrência**

- **FR-022**: Duas execuções sobre os mesmos dados DEVEM produzir a mesma lista de itens (conteúdo e ordem). Só o momento de geração e o da verificação podem diferir (constituição, princípio V).
- **FR-023**: Duas execuções NÃO DEVEM rodar ao mesmo tempo.
- **FR-024**: Toda execução bem-sucedida DEVE gerar o seu commit, inclusive a segunda do mesmo dia de Brasília. O sistema NÃO DEVE descartar execução bem-sucedida. Uma reexecução depois de uma falha DEVE poder sempre gravar.
- **FR-024a**: O `status.json` DEVE trazer, junto do momento da verificação, a data de Brasília a que a execução se refere, para que as features seguintes distingam o retrato de ontem de uma reexecução de hoje.
- **FR-025**: A feature NÃO DEVE gerar nenhum aviso (Telegram ou outro): a idempotência de avisos fica com a AVI.

**Risco de desativação**

- **FR-026**: A feature DEVE entregar um documento no repositório que confirme, com link oficial e data da consulta, a regra de desativação do agendamento por inatividade em repositório público e se os commits do bot contam como atividade.
- **FR-027**: Se o risco existir apesar do commit diário, o documento DEVE propor a mitigação, que só será implementada por decisão do mantenedor.

**Testes**

- **FR-028**: A lógica de decisão (plausibilidade, conteúdo do `status.json`, escolha entre tentar de novo e falhar, aceitação manual da variação) DEVE ser testável sem rede, sem agendador e sem esperar tempo real, com fixtures e retratos sintéticos (constituição, princípio IV).
- **FR-029**: Os testes DEVEM cobrir, no mínimo, cada cenário das User Stories 1, 2 e 3, os casos de tentativa da User Story 4 e a exclusão mútua da User Story 5 até onde for verificável sem rede. O agendamento em si (disparo real, commit real no GitHub) é verificado manualmente.

**Limites desta feature (não implementar)**

- **FR-030**: Esta feature NÃO DEVE implementar o envio de mensagem no Telegram, a formatação do resumo, os secrets, a página pública (HTML, GitHub Pages, faixas de erro ou atraso), a relatoria, a comparação de eventos com o dia anterior, o `data/mudancas/` nem a mitigação do risco de 60 dias sem decisão do mantenedor.
- **FR-031**: A feature NÃO DEVE usar nem exigir segredos além da permissão que o próprio agendador dá ao workflow para gravar no repositório (constituição, princípio VI).

### Key Entities *(include if feature involves data)*

- **Execução diária**: uma rodada do agendamento ou do disparo manual: coleta, checagem de plausibilidade, gravação e commit. Tem um número de tentativas e um resultado final.
- **Retrato**: o `data/atual.json` de um dia, como definido na COL. Para a AGE, "último retrato bom" é o `atual.json` do commit anterior mais recente.
- **Status da execução** (`data/status.json`): resultado da última execução: "ok" ou "falha", momento da verificação, categoria e motivo da falha, data dos últimos dados bons, momento da geração do último `atual.json` bom e tentativas (FR-010).
- **Estoque bruto**: total de PL e PLP nas comissões acompanhadas, antes do filtro do NOVO (cerca de 1.500 itens na sondagem de 17/10/2026). É a base da checagem de variação.
- **Checagem de plausibilidade**: comparação entre o estoque bruto do candidato e o do último retrato bom (e entre o candidato e zero), que decide se o candidato pode substituir o `atual.json`.
- **Categoria de falha**: as da COL (`configuracao`, `fonte_indisponivel`, `formato_alterado`, `arquivos_desatualizados`, `arquivo_incompleto`, `api_deputados`, `estoque_vazio`), mais a de plausibilidade (`estoque_implausivel`) e a "interna". A falha ao gravar no repositório (commit ou envio) não é categoria do `status.json`, porque nesse caso não há como registrá-la: aparece só como workflow vermelho.
- **Confirmação do risco de desativação**: documento com a regra do GitHub, a fonte, a data da consulta e a conclusão (FR-026).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% das execuções bem-sucedidas, o commit do bot contém `data/atual.json` e `data/status.json` no mesmo commit, inclusive quando a lista é idêntica à do dia anterior.
- **SC-002**: Em 100% dos cenários de falha das User Stories 2 e 3, o workflow termina vermelho, o `data/atual.json` anterior permanece idêntico byte a byte e o `data/status.json` traz o resultado "falha" com categoria e motivo.
- **SC-003**: Uma variação de até 20% passa e uma variação acima de 20% falha, nos dois sentidos, em todos os casos de teste com retratos sintéticos; estoque vazio e lista vazia falham sempre.
- **SC-004**: Duas execuções sobre as mesmas fixtures produzem listas de itens idênticas (conteúdo e ordem); a única diferença permitida é o momento de geração e o de verificação.
- **SC-005**: Uma falha passageira seguida de sucesso termina verde em até o número de tentativas definido, sem exigir ação do mantenedor; uma falha permanente termina vermelha depois de esgotar as tentativas, e uma falha não repetível termina vermelha sem tentativas extras.
- **SC-006**: A suíte de testes da feature passa sem acesso à internet e sem esperar tempo real.
- **SC-007**: Depois de 7 dias de operação, o histórico do Git mostra ao menos um commit de dados por dia de execução bem-sucedida (mais de um só quando houve reexecução), e a idade do "momento da verificação" do `status.json` nunca passa de 30 horas em dia normal.
- **SC-008**: O documento de confirmação do risco de 60 dias existe, com link oficial, data da consulta e conclusão explícita.
- **SC-009**: Nenhum item do que a coluna "Não inclui" da linha AGE lista (Telegram, página) nem do que pertence a REL e MUD é implementado.

## Assumptions

- A AGE roda a coleta da COL sem alterar as regras de inclusão nem o formato do `atual.json`. Como o estoque bruto não existe hoje na saída da COL, o código da coleta precisa expor essa contagem sem mudar o resultado já definido; o plano descreve essa ampliação compatível, e a COL continua tratada como dependência concluída.
- O agendador é o do GitHub Actions e o armazenamento é o Git, como a constituição fixa. O commit do bot vai direto para a branch principal. Se houver proteção de branch que o impeça, isso aparece como falha visível e o plano trata.
- O horário do agendamento é decidido no `plan.md`. A sondagem de 17/10/2026 mostrou o fim da regeneração do lote por volta de 02h21 de Brasília (05:21 UTC), o resumo diário (AVI) sai por volta das 7h de Brasília, e o agendador conta em UTC e pode atrasar.
- A coleta leva cerca de 1 GB por execução (PRODUCT.md, §8). O tempo máximo de uma execução e o custo no agendador são verificados no `plan.md`; o repositório é público, então não há cobrança de minutos.
- Em falha, o `status.json` é commitado e só depois o workflow termina vermelho (suposição: PRODUCT.md, §7, diz que "a falha é registrada em `data/status.json`", e a página e o aviso futuros dependem de ler essa falha no repositório).
- "Último retrato bom" é o `data/atual.json` do commit anterior. Como a AGE só substitui esse arquivo em sucesso, o arquivo em disco já é o último bom, e nenhum outro histórico é necessário para a checagem.
- O `status.json` não é a mesma coisa que o `meta` do `atual.json`: o `meta` descreve os dados, e o `status.json` descreve a execução. O formato exato do `status.json` é decidido no plano, como contrato em `contracts/`.
- A confirmação do risco de 60 dias é um documento e não código; sua conclusão pode virar uma decisão do mantenedor, fora desta spec.
- Reexecuções do mesmo dia geram commits adicionais com itens idênticos. É requisito para as features seguintes: a MUD compara com o retrato do dia anterior, e não com o commit imediatamente anterior; a AVI não envia duas mensagens no mesmo dia. A AGE não implementa nada disso.
- Os avisos duplicados da constituição (princípio V) não se aplicam à AGE, porque ela não envia mensagens; a idempotência aqui é a do conteúdo da lista e a do histórico no Git.
- Nenhuma dependência nova é prevista; se o plano precisar de uma, deve justificá-la por escrito (constituição, princípio I).
