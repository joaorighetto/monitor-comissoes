# Feature Specification: MUD — Mudanças desde ontem

**Feature Branch**: `claude/stoic-brown-accrz2` (branch já designada para o trabalho; o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido)

**Created**: 2026-10-18

**Status**: Aprovada pelo mantenedor em 18/10/2026

**Input**: User description: "Feature MUD — Mudanças desde ontem (linha MUD do ROADMAP.md)", com o recorte "Inclui" e "Não inclui" da linha e os pontos em aberto levantados na situação.

**Recorte da linha MUD (ROADMAP.md)**

- *Resultado verificável*: `data/mudancas/AAAA-MM-DD.json` lista os eventos entrou, saiu (com motivo e destino), situação, relator, parecer e etiquetas, com todas as tramitações desde o retrato anterior. O primeiro dia registra "linha de base".
- *Inclui*: comparação por id; tramitações dos itens cuja sequência mudou; motivo "arquivado, art. 105"; testes com retratos sintéticos.
- *Não inclui*: envio; página.
- *Dependências*: COL (concluída); REL (desejável, concluída).

## Clarifications

### Session 2026-10-18

- Q: O `atual.json` commitado está no formato antigo (sem relator e sem a sequência do último status). Ele deve ser tratado como não comparável, e o primeiro arquivo da MUD gravado como linha de base? → A: **Sim.** O primeiro arquivo é uma linha de base com o motivo "formato anterior incompatível", sem eventos. A comparação começa no dia seguinte. Perde-se um dia de eventos, dito explicitamente no arquivo.
- Q: O `atual.json` deve passar a guardar o número de sequência do último status de cada item, subindo a versão de formato? → A: **Sim.** O retrato registra a sequência do último status da referência de cada item, a versão de formato sobe, e os testes que dependem do formato são ajustados de forma explícita. Comparar por data e hora foi rejeitado: um mesmo dia pode ter várias tramitações.
- Q: A `versao_formato` do arquivo de mudanças sobe com o campo novo `comissao_de`? → A: **Não.** Fica em 1 enquanto nada publicado a lê; o contrato congela antes de a AVI ou a PAG consumirem o arquivo, e dali em diante mudança de campo sobe a versão (mantenedor, na revisão, 18/10/2026). A linha `MOV` (futura) do ROADMAP.md foi confirmada pelo mantenedor na mesma data.
- Q: Uma mudança de sequência que não altera situação, relator, parecer nem etiquetas (por exemplo, pedido de vista ou retirada de pauta) deve aparecer no arquivo? → A: **Não.** Sem um dos seis tipos de evento do PRODUCT.md §5.6, não há registro, e as tramitações acompanham só os eventos. Um sétimo tipo restrito a uma lista fechada de tramitações relevantes (vista, retirada de pauta) fica como **candidata futura**, registrada na linha `MOV` do ROADMAP.md (status `futura`): exigiria definir a lista e emendar o PRODUCT.md §5.6. Não é desta feature.
- Q: Quando um item sai da lista por mais de um motivo ao mesmo tempo, qual motivo o evento registra como principal? → A: Na ordem: **situação final** (aprovada, transformada em norma, arquivada), **apensado a proposição fora da lista**, **foi para outro órgão**, **perdeu as etiquetas**. O evento traz o motivo principal e, no detalhe, os demais fatos que também valiam, para nada se perder em silêncio.
- Q: Como a execução obtém o retrato anterior: pelo histórico do Git ou por uma cópia guardada em `data/`? → A: **Cópia rotativa `data/anterior.json`**, só com arquivos, sem o código depender do Git. Antes de gravar o `atual.json` novo, a execução guarda em `anterior.json` o `atual.json` de um dia anterior ao da execução; numa reexecução no mesmo dia, o `anterior.json` não é tocado. O arquivo entra no commit diário da AGE.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber o que entrou e o que saiu da lista, e por quê (Priority: P1)

O gabinete quer abrir o arquivo do dia e ver, de um lado, os itens que **entraram** na lista desde o retrato anterior e, de outro, os que **saíram**, cada um com o motivo e, quando houver, o destino. Quem decide a partir da lista precisa saber que um item sumiu e por quê: foi para outro órgão, chegou a uma situação final (aprovado, transformado em norma, arquivado), foi apensado a uma proposição de fora da lista ou deixou de ter etiqueta (PRODUCT.md, §5.6).

**Why this priority**: é o núcleo da pergunta "o que entrou, o que saiu e por quê" (PRODUCT.md, §3). Sem isso, um item que some da lista é indistinguível de uma falha da coleta.

**Independent Test**: dar à comparação dois retratos sintéticos com um item que só existe no de hoje e outro que só existe no anterior, e conferir os dois eventos, com motivo e destino.

**Acceptance Scenarios**:

1. **Dado** um item presente no retrato de hoje e ausente do anterior, cuja referência chegou à comissão depois do retrato anterior, **Quando** a comparação roda, **Então** o arquivo traz o evento **entrou** com o motivo "chegou à comissão".
2. **Dado** um item presente nos dois retratos de dias diferentes que já estava na comissão, mas ausente da lista anterior por não ter etiqueta e que hoje tem uma, **Quando** a comparação roda, **Então** o evento **entrou** traz o motivo "ganhou etiqueta" e diz qual.
3. **Dado** um item do retrato anterior cuja referência está hoje em outro órgão, **Quando** a comparação roda, **Então** o evento **saiu** traz o motivo "foi para outro órgão" e o órgão de destino.
4. **Dado** um item do retrato anterior cuja referência chegou a uma situação final (aprovada, transformada em norma jurídica ou arquivada), **Quando** a comparação roda, **Então** o evento **saiu** traz o motivo "situação final" e diz qual.
5. **Dado** um item cuja situação final é o arquivamento por tramitação que cita o art. 105 do Regimento Interno, **Quando** a comparação roda, **Então** o evento **saiu** traz o motivo **"arquivado, art. 105"** (PRODUCT.md, §5.7 e D6). Arquivamento que não cita o art. 105 traz "arquivado", sem a menção.
6. **Dado** um item do retrato anterior que hoje é apensado a uma proposição fora da lista, **Quando** a comparação roda, **Então** o evento **saiu** traz o motivo "apensado a uma proposição fora da lista" e a identificação dela.
7. **Dado** um item cuja referência continua na comissão, mas que perdeu todas as etiquetas (por exemplo, o deputado ficou licenciado), **Quando** a comparação roda, **Então** o evento **saiu** traz o motivo "perdeu as etiquetas" e quais perdeu (PRODUCT.md, §8).
8. **Dado** qualquer evento **entrou** ou **saiu**, **Quando** se lê o arquivo, **Então** o evento traz a identificação da proposição, a comissão e o link oficial da ficha, e o motivo nunca está vazio: se os fatos não permitirem decidir, o motivo é "não determinado", com o link para conferência.

---

### User Story 2 - Saber o que mudou nos itens que continuam na lista (Priority: P1)

Para o item que está nos dois retratos, o gabinete quer saber se a **situação** da referência mudou (de → para), se o **relator** atual mudou (designado, devolveu ou substituído), se houve **parecer** do relator e se o item **ganhou ou perdeu etiqueta** sem sair da lista. Quando o número de sequência do último status mudou, o evento traz **todas as tramitações desde o retrato anterior**, não só a última, porque o lote guarda só a última e um mesmo dia pode ter várias (PRODUCT.md, §5.6 e §8).

**Why this priority**: é o restante do resultado verificável da linha MUD, e a razão de a comparação existir.

**Independent Test**: com retratos sintéticos que diferem em um campo por vez (situação, relator, etiqueta) e tramitações sintéticas de parecer, conferir um evento por tipo, com as tramitações do intervalo.

**Acceptance Scenarios**:

1. **Dado** um item cuja situação passou de "Aguardando Parecer" para "Pronta para Pauta", **Quando** a comparação roda, **Então** o arquivo traz o evento **situação** com "de → para".
2. **Dado** um item sem relator atual que hoje tem relator, **Quando** a comparação roda, **Então** o evento **relator** traz "designado" e o relator (nome e partido de hoje).
3. **Dado** um item com relator atual que hoje não tem (devolveu a matéria), **Quando** a comparação roda, **Então** o evento **relator** traz "devolveu" e quem era o relator.
4. **Dado** um item cujo relator atual passou de uma pessoa a outra, **Quando** a comparação roda, **Então** o evento **relator** traz "substituído", com o anterior e o novo.
5. **Dado** um item em que as tramitações do intervalo incluem um parecer do relator, **Quando** a comparação roda, **Então** o arquivo traz o evento **parecer** com o link para a ficha oficial.
6. **Dado** um item que continua na lista e ganhou ou perdeu uma etiqueta (por exemplo, `relatoria NOVO` ganha porque o relator designado é do NOVO), **Quando** a comparação roda, **Então** o evento **etiquetas** diz qual.
7. **Dado** um item cujo número de sequência do último status mudou entre os retratos, **Quando** a comparação roda, **Então** os eventos desse item trazem **todas** as tramitações cuja sequência é maior que a do retrato anterior e vai até a do retrato de hoje, em ordem de sequência, e não só a última.
8. **Dado** um item cuja sequência **não** mudou e que não teve nenhuma outra diferença, **Quando** a comparação roda, **Então** o item não aparece no arquivo de mudanças.
9. **Dado** um item com mais de um tipo de mudança no mesmo dia (por exemplo, nova situação e novo relator), **Quando** a comparação roda, **Então** o arquivo traz um evento para cada tipo, sem fundi-los nem omitir algum.

---

### User Story 3 - O primeiro dia registra a linha de base (Priority: P1)

No primeiro dia, ou sempre que não existir retrato anterior comparável, não há o que comparar. O arquivo do dia diz isso explicitamente: "linha de base criada com N itens", sem nenhum evento. Assim, a ausência de eventos nunca é confundida com "nada mudou", e uma lista toda de uma vez não vira centenas de "entrou" falsos.

**Why this priority**: é parte do resultado verificável da linha MUD (PRODUCT.md, §5.6: "No primeiro retrato não há eventos").

**Independent Test**: rodar a comparação sem retrato anterior e conferir o arquivo de linha de base; rodar com um retrato anterior de formato antigo e conferir que não há eventos falsos.

**Acceptance Scenarios**:

1. **Dado** que não existe retrato anterior (primeiro dia), **Quando** a comparação roda, **Então** o arquivo do dia é gravado como **linha de base**, com o total de itens, sem nenhum evento.
2. **Dado** que o retrato anterior está num formato antigo que não traz o que a comparação exige (por exemplo, sem o relator ou sem a sequência do último status), **Quando** a comparação roda, **Então** o arquivo do dia é uma **linha de base** que diz o motivo ("formato anterior incompatível"), sem nenhum evento de relator, de etiqueta ou de entrada falsos.
3. **Dado** uma linha de base gravada, **Quando** o dia seguinte roda, **Então** a comparação usa o retrato da linha de base como retrato anterior e gera eventos normalmente.

---

### User Story 4 - Resultado repetível e que cobre os dias sem retrato (Priority: P1)

Rodar de novo no mesmo dia, sobre os mesmos dados, dá o **mesmo arquivo**, sem comparar o retrato de hoje com ele mesmo. Se um dia não gerou retrato (a coleta falhou), o dia seguinte compara com o último retrato bom, e o arquivo diz de que dia a que dia ele cobre, com todas as tramitações do intervalo inteiro (constituição, princípio V; PRODUCT.md, D8 e §7).

**Why this priority**: novas tentativas e execuções manuais acontecem (AGE). Se a segunda execução do dia comparasse o retrato novo com o `atual.json` que a primeira já gravou, o arquivo do dia sairia vazio e esconderia as mudanças.

**Independent Test**: executar a comparação duas vezes no mesmo dia, depois de a primeira ter gravado o `atual.json`, e comparar os arquivos byte a byte; simular um dia sem retrato e conferir o intervalo coberto.

**Acceptance Scenarios**:

1. **Dado** as mesmas entradas, **Quando** a comparação roda duas vezes no mesmo dia, **Então** os dois arquivos são idênticos, byte a byte, inclusive quando o `atual.json` do dia já foi gravado pela primeira execução.
2. **Dado** uma segunda execução no mesmo dia com dados mais novos que os da primeira, **Quando** a comparação roda, **Então** o arquivo reflete a diferença entre o retrato novo e o retrato **de um dia anterior** (o mesmo da primeira execução), e não a diferença entre as duas execuções do dia.
3. **Dado** que o último retrato bom é de dois ou mais dias antes, **Quando** a comparação roda, **Então** o arquivo cobre o intervalo inteiro, traz as datas dos dois retratos e todas as tramitações desde o retrato anterior.
4. **Dado** uma execução que termina sem erro, **Quando** se lê o arquivo, **Então** ele traz as datas do retrato de hoje e do retrato anterior (ou o motivo de não haver), para que se saiba o que foi comparado.
5. **Dado** tramitações lançadas na Câmara depois da geração do lote do dia, **Quando** a comparação roda, **Então** elas **não** entram no arquivo de hoje: só as tramitações até a sequência do retrato de hoje, o que mantém o resultado repetível. Elas aparecem no dia seguinte.

---

### User Story 5 - Falhar de forma visível (Priority: P1)

Se a comparação não puder ser feita com segurança, a execução inteira falha, com o motivo, e nada é publicado pela metade: nem `atual.json` novo, nem arquivo de mudanças. Um arquivo de mudanças vazio porque a leitura falhou nunca pode se passar por "nada mudou" (constituição, princípio III; PRODUCT.md, §7 e D10).

**Why this priority**: é a mesma garantia da COL, da AGE e da REL. Sem ela, "sem mudanças" seria indistinguível de "a comparação quebrou".

**Independent Test**: para cada falha simulada, conferir saída com erro, mensagem com o motivo e, byte a byte, o `atual.json`, o `anterior.json` e a pasta `data/mudancas/` como estavam.

**Acceptance Scenarios**:

1. **Dado** que a API de tramitações falha (rede, status HTTP, resposta malformada ou incompleta) ao buscar as tramitações do intervalo, **Quando** o comando roda, **Então** ele sai com erro dizendo o motivo, e o `atual.json`, o `anterior.json` e a pasta `data/mudancas/` ficam como estavam.
2. **Dado** que o retrato anterior existe, mas está corrompido ou fora do contrato (JSON inválido, campos exigidos ausentes, tipos errados), **Quando** o comando roda, **Então** ele sai com erro dizendo qual retrato e por quê. Um retrato corrompido **não** vira linha de base em silêncio.
3. **Dado** que as tramitações do intervalo não trazem a sequência esperada (a sequência do retrato de hoje não existe, ou a do retrato anterior é maior que a de hoje), **Quando** o comando roda, **Então** ele sai com erro dizendo a incoerência.
4. **Dado** que a coleta falha antes da comparação, **Quando** o comando roda, **Então** nenhum arquivo de mudanças é gravado e o último bom permanece (PRODUCT.md, D10).
5. **Dado** uma execução que grava o `atual.json` novo, **Quando** ela termina sem erro, **Então** o arquivo de mudanças do dia também foi gravado. Não existe `atual.json` novo sem o arquivo de mudanças correspondente, nem o contrário.

---

### User Story 6 - Conferível item a item e testável sem rede (Priority: P2)

Cada evento aponta para a ficha oficial da proposição, e cada regra de comparação é coberta por testes com **retratos sintéticos** e tramitações salvas; nenhum teste depende da internet (constituição, princípios II e IV).

**Why this priority**: sustenta a confiança no arquivo e a manutenção sem cuidados diários.

**Independent Test**: rodar a suíte sem acesso à internet e conferir que cada tipo de evento e cada motivo de saída têm ao menos um teste.

**Acceptance Scenarios**:

1. **Dado** qualquer evento do arquivo, **Quando** se lê o evento, **Então** ele traz o link oficial da ficha da proposição.
2. **Dado** a suíte de testes inteira, **Quando** ela roda sem acesso à internet, **Então** todos os testes passam.

---

### Edge Cases

- **Item que sai e volta.** Se um item saiu num dia e voltou em outro, cada passagem gera o seu evento, sem apagar o histórico. Cada arquivo diário só descreve a comparação do seu intervalo.
- **Referência diferente.** O item passou a ser apensado a outra principal, ou deixou de ser apensado. Situação e relator são comparados pelos valores atuais da referência. A sequência de outra proposição não é comparável com a anterior, então nesse caso as tramitações listadas são as da **nova** referência posteriores à data do retrato anterior.
- **Principal arquivada ou saída da principal.** Quando a principal sai da comissão, todos os apensados saem junto, e cada um tem o seu evento **saiu** com o mesmo motivo (PRODUCT.md, D4).
- **Vários motivos de saída.** Um item pode sair, por exemplo, por ter ido a outro órgão e por ter perdido as etiquetas. O evento traz **um** motivo principal (ordem de precedência na Assumption correspondente), e os fatos adicionais ficam no detalhe, sem se perderem.
- **Relator indeterminado em um dos retratos** (PRODUCT.md, §5.4). Sem relator conhecido não se pode afirmar "designado" ou "devolveu". Nesse caso não há evento de relator, e o arquivo registra que a comparação de relator não foi possível para o item. A marca em si não é evento.
- **Licença ou afastamento de deputado.** O item perde `autor hoje no NOVO` ou `relatoria NOVO` enquanto o deputado estiver fora; isso aparece como evento de **etiquetas** (ou de saída, se não restar etiqueta) (PRODUCT.md, §8). Quando ele volta, o inverso.
- **Item que muda de comissão e continua na lista** (CE → CREDN). Gera o evento **situação** com `comissao_de`, mesmo que o texto da situação seja o mesmo (revisão, 18/10/2026).
- **Relator e sequência do lote.** O relator da lista vale até a sequência do último status do lote, como a situação; o que a Câmara lançou depois entra no dia seguinte (revisão, 18/10/2026).
- **Item que muda de etiqueta e de situação no mesmo dia.** Um evento por tipo (Story 2, cenário 9).
- **Dias de muitas mudanças** (posse em 1º/02/2027, recomposição anual das comissões). O arquivo registra **todos** os eventos, sem teto. O teto e o "e mais N" são do resumo (AVI) e da página (PAG).
- **Dados do dia anterior.** O lote é gerado de madrugada (PRODUCT.md, §8). "Ontem" é o retrato anterior, e "hoje" é o último lote disponível.
- **Mudança de formato do `atual.json` no futuro.** Um retrato anterior em formato mais antigo vira linha de base com o motivo explícito (Story 3, cenário 2), a menos que a feature que mudou o formato inclua migração.
- **Arquivo do dia já existe e a execução roda de novo.** O arquivo é substituído pelo resultado recalculado, nunca duplicado nem acumulado (Story 4).

## Requirements *(mandatory)*

### Functional Requirements

**Retrato anterior e linha de base**

- **FR-001**: O sistema DEVE comparar o retrato de hoje com o **retrato anterior**, que é o último retrato bom **de um dia anterior ao da execução**, pela chave `id` da proposição (PRODUCT.md, §5.6). O retrato do próprio dia, se já tiver sido gravado por uma execução anterior, NÃO DEVE servir de retrato anterior. O retrato anterior é guardado numa cópia rotativa, `data/anterior.json`: quando o `atual.json` existente é de um dia anterior ao da execução, ele é o retrato anterior e passa a ser a cópia; quando é do próprio dia, a cópia existente é o retrato anterior e não é alterada. O dia de um retrato é a data de `meta.gerado_em`, em Brasília.
- **FR-002**: Quando não existir retrato anterior, ou ele estiver num formato antigo que não traz o que a comparação exige, o sistema DEVE gravar o arquivo do dia como **linha de base**: o total de itens, o motivo ("primeiro retrato" ou "formato anterior incompatível") e nenhum evento. O texto do resumo ("linha de base criada com N itens") é do AVI.
- **FR-003**: Um retrato anterior que exista, mas esteja corrompido ou fora do contrato, DEVE falhar a execução, com mensagem que diga qual retrato e por quê. NÃO DEVE virar linha de base em silêncio (constituição, princípio III).
- **FR-004**: O arquivo do dia DEVE trazer a data do retrato de hoje e a do retrato anterior (ou o motivo de não haver), de modo que, quando houver dias sem retrato, se saiba o intervalo coberto. O intervalo coberto vai do retrato anterior ao de hoje, ainda que sejam mais de 24 horas.

**Eventos**

- **FR-005**: O sistema DEVE registrar o evento **entrou** para o item cujo `id` está no retrato de hoje e não estava no anterior, com o motivo "chegou à comissão" ou "ganhou etiqueta" (qual). Quando os fatos não permitirem decidir, o motivo é "não determinado" (PRODUCT.md, §5.6).
- **FR-006**: O sistema DEVE registrar o evento **saiu** para o item cujo `id` estava no retrato anterior e não está no de hoje, com **um** destes motivos: foi para outro órgão (e qual); chegou a uma situação final (aprovada, transformada em norma, arquivada), com a menção "art. 105" quando a tramitação de arquivamento a fizer; foi apensado a uma proposição fora da lista (e qual); ou perdeu as etiquetas (e quais). Quando os fatos não permitirem decidir, o motivo é "não determinado" (PRODUCT.md, §5.6 e §5.7).
- **FR-007**: O motivo "arquivado, art. 105" DEVE ser registrado como motivo de saída. O arquivamento NÃO DEVE ser tratado como feature nem gerar alerta, selo ou lista de risco (PRODUCT.md, D6; ROADMAP.md, linha ARQ).
- **FR-008**: O sistema DEVE registrar o evento **situação** (de → para, com a comissão anterior) quando a situação da referência do item, presente nos dois retratos, mudou, ou quando o item mudou de comissão sem sair da lista (decidido pelo mantenedor em 18/10/2026, na revisão).
- **FR-009**: O sistema DEVE registrar o evento **relator** quando o relator atual do item, presente nos dois retratos, mudou: "designado" (não havia, passou a haver), "devolveu" (havia, deixou de haver) ou "substituído" (de uma pessoa a outra). Quando o relator é indeterminado em qualquer dos retratos, NÃO DEVE gerar evento de relator, e o arquivo DEVE registrar que a comparação de relator não foi possível para o item.
- **FR-010**: O sistema DEVE registrar o evento **parecer**, com o link para a ficha, quando as tramitações do intervalo incluírem parecer do relator da referência (na comissão do item de hoje ou, se o item mudou de comissão no intervalo, na comissão anterior). NÃO DEVE registrar o conteúdo do parecer (PRODUCT.md, §9).
- **FR-011**: O sistema DEVE registrar o evento **etiquetas** quando o item, presente nos dois retratos, ganhou ou perdeu uma etiqueta e continua na lista, dizendo qual.
- **FR-012**: Um item com mais de um tipo de mudança DEVE ter um evento por tipo. Um item sem nenhuma mudança NÃO DEVE aparecer.
- **FR-013**: Todo evento DEVE trazer a identificação da proposição, a comissão e o link oficial da ficha (constituição, princípio II). Nenhum motivo pode ficar vazio.

**Tramitações do intervalo**

- **FR-014**: Quando o número de sequência do último status da referência do item mudou entre os retratos, os eventos do item DEVEM trazer **todas as tramitações** com sequência maior que a do retrato anterior e até a do retrato de hoje, em ordem de sequência (PRODUCT.md, §5.6). Cada tramitação traz sequência, data e hora, órgão e descrição. Para o item que **entrou**, ou cuja referência mudou (sequências de proposições diferentes não se comparam), o evento traz as tramitações da referência de hoje lançadas **desde a data do retrato anterior**, também até a sequência do retrato de hoje (FR-017).
- **FR-015**: O retrato (`atual.json`) DEVE passar a registrar o número de sequência do último status da referência de cada item, porque o PRODUCT.md manda disparar a leitura das tramitações quando ele muda e o retrato atual não o guarda. Isso é um acréscimo ao formato do `atual.json` e DEVE incrementar a versão de formato (ver Assumptions).
- **FR-016**: As tramitações DEVEM ser lidas só para os itens que delas precisam (sequência mudou, ou item que entrou ou saiu e cujo motivo depende delas). Uma referência compartilhada por vários itens (a principal e seus apensados) é lida uma vez.
- **FR-017**: As tramitações lançadas na Câmara depois da geração do lote do dia NÃO DEVEM entrar no arquivo de hoje: o limite superior é a sequência do retrato de hoje. Assim, reexecutar no mesmo dia sobre os mesmos dados dá o mesmo arquivo.

**Falha visível, integridade e repetibilidade**

- **FR-018**: Erro na API de tramitações (rede, status HTTP, resposta malformada ou incompleta), tramitações incoerentes com os retratos (FR-014) ou retrato anterior inválido (FR-003) DEVEM falhar a execução inteira, com mensagem que diga o motivo, sem publicação parcial (PRODUCT.md, §7 e D10).
- **FR-019**: O `atual.json` novo, o `anterior.json` e o arquivo de mudanças do dia DEVEM ser gravados juntos, tudo ou nada. Em falha, o `atual.json`, o `anterior.json` e a pasta `data/mudancas/` ficam como estavam, byte a byte.
- **FR-020**: Reexecutar no mesmo dia, sobre os mesmos dados, DEVE produzir o mesmo arquivo, byte a byte, com a ordem dos eventos determinística, e NÃO DEVE gerar evento duplicado (constituição, princípio V). Uma reexecução com dados novos substitui o arquivo do dia pelo resultado recalculado contra o mesmo retrato anterior.
- **FR-021**: O arquivo do dia DEVE ser o histórico das mudanças no Git (PRODUCT.md, D8): `data/mudancas/AAAA-MM-DD.json`, com a data da execução em Brasília, a mesma que o `status.json` usa. O commit diário da AGE DEVE incluí-lo e incluir o `data/anterior.json`, sem mudar mais nada do fluxo da AGE.

**Conteúdo e ordem do arquivo**

- **FR-022**: Os eventos DEVEM ter ordem determinística: por comissão, depois por tipo de evento, depois por `id` da proposição. O arquivo DEVE ter codificação, indentação e ordem de campos fixas, como os demais arquivos de dados.
- **FR-023**: O arquivo DEVE ter versão de formato, para quem o lê detectar mudança.

**Testes**

- **FR-024**: O comportamento DEVE ser coberto por testes com **retratos sintéticos** e tramitações salvas, e NENHUM teste DEVE depender da internet (constituição, princípio IV). Os testes DEVEM cobrir, no mínimo: cada tipo de evento; cada motivo de saída, inclusive "arquivado, art. 105" e "arquivado" sem a menção; cada motivo de entrada; a linha de base nos dois casos (sem retrato anterior e formato antigo); a repetibilidade no mesmo dia depois de o `atual.json` ter sido gravado; o intervalo de vários dias; e cada falha da User Story 5.

**Limites desta feature (não implementar)**

- **FR-025**: Esta feature NÃO DEVE implementar envio ao Telegram, formatação de mensagem, teto de eventos para texto, textos do resumo, página, HTML, avisos nem histórico de mais de um retrato dentro do arquivo (cada dia tem o seu arquivo). As regras da COL, da AGE e da REL não mudam, exceto o acréscimo de FR-015 e o que FR-021 exige do commit.

### Key Entities *(include if feature involves data)*

- **Retrato**: o `atual.json` de um dia, ou seja, a lista filtrada com o `meta`. Atributos usados na comparação: `id`, comissão, situação, relator, etiquetas, referência (`apensado_a`) e número de sequência do último status.
- **Retrato anterior**: o último retrato bom de um dia anterior ao da execução, guardado em `data/anterior.json`.
- **Evento**: uma mudança de um item entre dois retratos. Tipos: entrou, saiu, situação, relator, parecer, etiquetas. Traz a proposição, o motivo e o link oficial.
- **Motivo**: a razão registrada num evento de entrada ou de saída (PRODUCT.md, §5.6). Nunca vazio.
- **Tramitação do intervalo**: tramitação da referência com sequência maior que a do retrato anterior e até a do retrato de hoje.
- **Arquivo de mudanças do dia**: `data/mudancas/AAAA-MM-DD.json`, com as datas dos dois retratos, os eventos (ou a marca de linha de base) e a versão de formato.
- **Linha de base**: arquivo do dia sem eventos, gravado quando não há retrato anterior comparável, com o total de itens e o motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com retratos sintéticos, 100% dos tipos de evento (entrou, saiu, situação, relator, parecer, etiquetas) e 100% dos motivos de saída e de entrada listados em FR-005 e FR-006 são registrados com o tipo e o motivo corretos, incluindo "arquivado, art. 105".
- **SC-002**: Sem retrato anterior, o arquivo do dia é uma linha de base com o total de itens e **zero** eventos. Com retrato anterior em formato antigo, também há zero eventos e o motivo é explícito.
- **SC-003**: Duas execuções no mesmo dia, sobre os mesmos dados, dão arquivos idênticos byte a byte, inclusive quando a segunda já encontra o `atual.json` do dia gravado pela primeira. Em nenhum caso o retrato de hoje é comparado com ele mesmo.
- **SC-004**: Em 100% dos cenários de falha da User Story 5, o comando termina com erro, a mensagem diz o motivo, e o `atual.json`, o `anterior.json` e a pasta `data/mudancas/` permanecem idênticos byte a byte.
- **SC-005**: 100% dos eventos trazem o link oficial da ficha, e nenhum tem motivo vazio.
- **SC-006**: Para todo item cuja sequência mudou, o arquivo traz 100% das tramitações do intervalo (anterior, hoje], sem repetir nem perder nenhuma, nos casos de um dia e de vários dias sem retrato.
- **SC-007**: A suíte inteira (ruff e pytest) passa sem acesso à internet.
- **SC-008**: Nenhum item é incluído ou excluído por regra que o `PRODUCT.md` não descreva, e nada da fronteira "Não inclui" (envio, página) é implementado (constituição, princípios II e VII).
- **SC-009**: Quando houver retratos reais de dois dias diferentes, a conferência manual de cada evento contra a ficha oficial da Câmara não encontra divergência. Esta conferência não impede a entrega: a validação das regras é feita com retratos sintéticos, como diz a linha MUD.

## Assumptions

- **COL, AGE e REL estão concluídas e seu comportamento é preservado.** A etiqueta de autoria, a referência, a plausibilidade, o `status.json` e a relatoria não mudam. Os acréscimos são só o de FR-015, no formato do `atual.json`, e o commit dos arquivos novos (`data/mudancas/` e `data/anterior.json`) pelo workflow da AGE (FR-021).
- **Retrato anterior = último retrato bom de um dia anterior**, guardado numa cópia rotativa `data/anterior.json` (FR-001). Decidido no clarify (18/10/2026): o histórico do Git foi rejeitado porque faria o código depender do `git` e do checkout raso do Actions, e uma cópia por dia foi rejeitada porque duplica o que o Git já guarda (D8). No primeiro dia não há `anterior.json`, e o `atual.json` do próprio dia não serve de retrato anterior; o resultado é a linha de base com o motivo "primeiro retrato".
- **Ampliação do `atual.json` (FR-015).** O PRODUCT.md, §5.6, manda disparar a leitura das tramitações quando o número de sequência do último status muda, e o retrato atual guarda só a data e hora. Comparar pela data e hora seria menos seguro, porque um mesmo dia pode ter várias tramitações (PRODUCT.md, §5.6). Por isso, o formato ganha o campo e a versão de formato sobe. Como isso altera um contrato da COL e da REL, o plano deve registrá-lo e ajustar os testes que dependem do formato. Decidido no clarify (18/10/2026).
- **Transição do formato.** O `atual.json` commitado hoje está na versão de formato 1, sem relator e sem a sequência, de antes da REL. Comparar um retrato nesse formato com um novo geraria eventos falsos de relator e de etiqueta, e itens que só existem pela relatoria apareceriam como "entrou". Decidido no clarify (18/10/2026): ele é tratado como não comparável, o primeiro arquivo da MUD é uma linha de base com o motivo "formato anterior incompatível" (FR-002), e a comparação só começa no dia seguinte. Perde-se um dia de eventos, mas o arquivo diz isso explicitamente.
- **Tramitações sem evento.** O PRODUCT.md, §5.6, lista seis tipos de evento. Uma mudança de sequência que não altere situação, relator, parecer nem etiquetas (por exemplo, só um despacho) não gera evento, e portanto as tramitações dela não aparecem. As tramitações acompanham os eventos do item. Decidido no clarify (18/10/2026); a movimentação sem evento, como pedido de vista ou retirada de pauta, é candidata a uma feature futura (ver Clarifications).
- **Precedência do motivo de saída.** Quando mais de um motivo vale, o evento registra um motivo principal, na ordem: situação final, apensado a proposição fora da lista, outro órgão, perdeu as etiquetas. Os fatos adicionais ficam no detalhe. O PRODUCT.md não define a precedência; decidido no clarify (18/10/2026).
- **De onde vêm o motivo e o destino.** O `atual.json` guarda só os itens da lista, então o estado de um item que saiu (órgão, situação, apensação) vem do lote do dia e das tramitações, e não da comparação dos dois arquivos. Isso é decisão do `plan.md`; a spec exige apenas que o motivo e o destino sejam os fatos da fonte oficial.
- **A data do arquivo é a da execução, em Brasília**, pelo mesmo critério do `data_referencia` do `status.json`. O arquivo cobre o intervalo entre os dois retratos.
- **O volume é pequeno.** A leitura de tramitações cobre dezenas de referências por dia, e em dias de muitas mudanças (posse), poucas centenas. O custo em chamadas é avaliado no `plan.md`.
- **Parecer.** O tipo de tramitação que representa parecer do relator é levantado no `research.md`, com tramitações reais salvas.
- **Dependência nova só com justificativa escrita no `plan.md`** (constituição, princípio I). A MUD não deve precisar de nenhuma.
- **Requisito para AVI e PAG (não implementado aqui).** O resumo e a página devem consumir este arquivo, com o teto de eventos e o "e mais N, veja a página" do lado deles.
