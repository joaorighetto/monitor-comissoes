# Feature Specification: REL — Relatoria NOVO atual

**Feature Branch**: `claude/feature-rel-spec-kit-k2esac` (branch já designada para o trabalho; o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido)

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "Feature REL — Relatoria NOVO atual (linha REL do ROADMAP.md)", com o recorte "Inclui" e "Não inclui" da linha e os pontos em aberto levantados na situação.

**Recorte da linha REL (ROADMAP.md)**

- *Resultado verificável*: `relatoria NOVO` só aparece quando o relator foi designado na comissão atual e não devolveu a matéria. PL 937/2022 e PL 3514/2023 ficam fora, PL 4501/2023 fica dentro. Apensados herdam o relator da principal.
- *Inclui*: leitura das tramitações dos candidatos; regra do relator atual; partido atual do relator; testes dos casos da sondagem.
- *Não inclui*: histórico de relatores; relatores de outras comissões.
- *Dependências*: COL (concluída).

## Clarifications

### Session 2026-10-18

- Q: O relator atual (nome e partido de hoje) deve ser calculado e gravado para todos os itens da lista ou só para os candidatos à relatoria NOVO? → A: Para **todos** os itens da lista. As tramitações são lidas para a referência de cada item com ao menos uma etiqueta e para os candidatos à relatoria NOVO.
- Q: Quando as tramitações de um item não permitirem saber quem é o relator atual, o sistema falha a execução ou marca o item? → A: **Marca o item** com "relator indeterminado", sem dar nem negar `relatoria NOVO`. Erro de rede, de formato ou de paginação continua falhando a execução inteira (FR-012). Para que nada suma em silêncio, um candidato à relatoria NOVO com relator indeterminado entra na lista com a marca, mesmo sem outra etiqueta.
- Q: Se a proposição saiu da comissão atual e voltou, uma designação feita na passagem anterior por essa mesma comissão ainda vale? → A: **Não vale.** Só conta designação feita depois da última entrada da referência na comissão atual; sem redesignação, o item fica sem relator atual.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enxergar a relatoria do NOVO que vale hoje (Priority: P1)

O gabinete quer ver, na lista, os PL e PLP da CE e da CREDN cujo **relator atual** é deputado do NOVO. O item ganha a etiqueta `relatoria NOVO` e mostra quem é o relator. "Relator atual" é o deputado designado na comissão em que a proposição está e que não devolveu a matéria depois disso (PRODUCT.md, D3 e §5.4). Um item pode entrar na lista **somente** por essa etiqueta, como o PL 4501/2023 (autoria de Duarte Jr., do PSB; relator na CE: Luiz Lima).

**Why this priority**: é o recorte da linha REL. A relatoria é, para o gabinete, o sinal mais forte de que o NOVO está com a matéria na mão, e hoje a lista não a mostra (a COL só cobre autoria).

**Independent Test**: rodar a coleta sobre fixtures reais (lote e tramitações) e conferir os três casos da sondagem, mais o PL 1843/2022 com as etiquetas `autoria NOVO` e `relatoria NOVO`.

**Acceptance Scenarios**:

1. **Dado** o PL 4501/2023 (autor Duarte Jr., PSB), na CE, cujo relator atual na CE é Luiz Lima (deputado em exercício do NOVO), **Quando** a lista é gerada, **Então** o item **aparece**, só com a etiqueta `relatoria NOVO`, mostrando Luiz Lima como relator atual.
2. **Dado** o PL 937/2022, na CE em "Aguardando Designação de Relator(a)", cujo relator do NOVO (Luiz Lima) devolveu a matéria sem manifestação em 20/05/2026, **Quando** a lista é gerada, **Então** o item **não** ganha `relatoria NOVO` (e, sem outra etiqueta, não aparece).
3. **Dado** o PL 3514/2023, na CREDN em "Aguardando Designação de Relator(a)", cujo relator do NOVO (Luiz Lima) foi designado na Comissão do Esporte (CESPO), **Quando** a lista é gerada, **Então** o item **não** ganha `relatoria NOVO` (e, sem outra etiqueta, não aparece).
4. **Dado** o PL 1843/2022 (autoria de Lucas Gonzalez, que assinou como NOVO), na CE, cuja relatora é Adriana Ventura (NOVO), **Quando** a lista é gerada, **Então** o item mostra `autoria NOVO` **e** `relatoria NOVO` (PRODUCT.md, §5.4).
5. **Dado** um item cujo relator atual não é do NOVO e que tem `autoria NOVO`, **Quando** a lista é gerada, **Então** o item permanece com `autoria NOVO`, sem `relatoria NOVO`.
6. **Dado** um relator do NOVO designado que foi substituído por um relator de outro partido na mesma comissão, **Quando** a lista é gerada, **Então** o item não tem `relatoria NOVO`.
7. **Dado** um relator de outro partido substituído por um relator do NOVO na mesma comissão, **Quando** a lista é gerada, **Então** o item tem `relatoria NOVO`.

---

### User Story 2 - Apensados herdam o relator da principal (Priority: P1)

Como a comissão, a situação e o "parado há" de um apensado vêm da proposição principal (PRODUCT.md, D4 e §5.2), o relator também vem dela. Um apensado cuja principal tem relator atual do NOVO ganha `relatoria NOVO`, mesmo que seja de autoria de outro partido; um apensado cuja principal não tem relator do NOVO não ganha a etiqueta, ainda que ele próprio tenha tido relator do NOVO no passado.

**Why this priority**: metade do estoque é de apensados (PRODUCT.md, D4). Sem a herança, a etiqueta erraria justamente o grupo mais numeroso.

**Independent Test**: com fixtures que contêm uma cadeia de apensação cuja raiz tem relator do NOVO, conferir que o apensado herda a etiqueta e mostra o relator da raiz.

**Acceptance Scenarios**:

1. **Dado** um apensado A cuja principal B (raiz) está na CE com relator atual do NOVO, **Quando** a lista é gerada, **Então** A tem `relatoria NOVO`, mostra o relator de B e continua mostrando "apensado ao PL B".
2. **Dado** uma cadeia A → B → C em que C é a raiz, **Quando** a lista é gerada, **Então** o relator considerado é o de C.
3. **Dado** um apensado A cujo último relator do NOVO foi designado para o próprio A, mas cuja raiz B não tem relator do NOVO, **Quando** a lista é gerada, **Então** A não ganha `relatoria NOVO`.
4. **Dado** um apensado cuja principal está fora da lista de comissões, **Quando** a lista é gerada, **Então** o apensado continua fora (REL não altera a regra de "estar na comissão", PRODUCT.md, §5.3).
5. **Dado** um apensado com "principal não localizada" (PRODUCT.md, §5.2), **Quando** a lista é gerada, **Então** o relator considerado é o do próprio status do item, e a marca "principal não localizada" permanece.

---

### User Story 3 - Saber quem é o relator e de que partido é hoje (Priority: P2)

Cada item da lista mostra o relator atual e o **partido dele hoje** (não o da data da designação), ou diz explicitamente que não há relator designado. Assim, o gabinete responde à pergunta "quem é o relator atual e de que partido é hoje?" (PRODUCT.md, §3) sem abrir a ficha.

**Why this priority**: sustenta a etiqueta (o gabinete confere o motivo) e prepara a página e o resumo diário, mas a etiqueta já entrega valor sozinha.

**Independent Test**: conferir, nas fixtures, o relator e o partido de hoje de um item com relator do NOVO, de um com relator de outro partido, de um sem relator e de um cujo relator mudou de partido depois de ser designado.

**Acceptance Scenarios**:

1. **Dado** um item com relator atual de outro partido, **Quando** a lista é gerada, **Então** o item mostra o nome e o partido atual desse relator, e não tem `relatoria NOVO`.
2. **Dado** um relator designado quando era do PL e hoje do NOVO (por exemplo, Luiz Lima, designado em 09/04/2025 como "PL-RJ"), **Quando** a lista é gerada, **Então** o item tem `relatoria NOVO` e mostra o partido de hoje (NOVO), não o da designação.
3. **Dado** um item cuja matéria aguarda designação de relator ou cujo relator devolveu a matéria, **Quando** a lista é gerada, **Então** o item indica que não há relator atual.
4. **Dado** um item de autoria do NOVO, **Quando** a lista é gerada, **Então** o item mostra o relator atual e o partido de hoje **mesmo sem** `relatoria NOVO`.

---

### User Story 4 - Falhar de forma visível quando as tramitações falham (Priority: P1)

Se as tramitações não puderem ser obtidas ou interpretadas, a execução inteira falha, com o motivo, e o último `atual.json` bom fica intacto. Uma lista sem `relatoria NOVO` porque a leitura falhou nunca é publicada como se fosse completa (PRODUCT.md, §7 e D10; constituição, princípio III).

**Why this priority**: é a mesma garantia da COL e da AGE; sem ela, a ausência de `relatoria NOVO` seria indistinguível de "não há relatoria do NOVO".

**Independent Test**: para cada falha simulada, conferir saída com erro, mensagem com o motivo e `atual.json` anterior idêntico byte a byte.

**Acceptance Scenarios**:

1. **Dado** que a API de tramitações não responde ou responde com erro depois das novas tentativas, **Quando** o comando roda, **Então** ele sai com erro dizendo que a leitura das tramitações falhou, e o `atual.json` anterior não muda.
2. **Dado** uma resposta de tramitações com formato inesperado (campo ausente, tipo errado, sequência repetida, lista vazia, paginação inesperada), **Quando** o comando roda, **Então** ele sai com erro "formato alterado", e o `atual.json` anterior não muda.
3. **Dado** que não foi possível obter o partido atual de um relator, **Quando** o comando roda, **Então** a execução inteira falha: não há publicação parcial.
4. **Dado** que as tramitações de um item não permitem determinar o relator atual com segurança (sequência incoerente ou tipo de tramitação de relatoria desconhecido), **Quando** o comando roda, **Então** a execução **termina normalmente**, o item fica na lista com a marca "relator indeterminado" e sem `relatoria NOVO`, e os demais itens não são afetados.
5. **Dado** um candidato à relatoria NOVO, sem etiqueta de autoria, cujo relator atual é indeterminado, **Quando** a lista é gerada, **Então** o item **aparece** com a marca "relator indeterminado" (nada some em silêncio).

---

### User Story 5 - Resultado repetível, auditável e testável sem rede (Priority: P2)

Duas execuções sobre os mesmos dados dão a mesma lista, na mesma ordem. Cada item registra o relator considerado e a tramitação de que ele vem, para que se confira a regra na fonte oficial. Os testes usam fixtures reais salvas de tramitações e nenhum teste depende da internet.

**Why this priority**: constituição, princípios II, IV e V. O produto só é confiável se a etiqueta puder ser conferida linha a linha.

**Independent Test**: rodar duas vezes sobre as mesmas fixtures e comparar; conferir, num item com `relatoria NOVO`, o relator, a data da designação e o link oficial.

**Acceptance Scenarios**:

1. **Dado** as mesmas fixtures, **Quando** o comando roda duas vezes, **Então** a lista de itens é idêntica (conteúdo e ordem).
2. **Dado** um item com `relatoria NOVO`, **Quando** se lê o item, **Então** ele traz o relator (nome e identificação), a data da designação e o link oficial da ficha da proposição de que o relator foi lido.
3. **Dado** a suíte de testes inteira, **Quando** ela roda sem acesso à internet, **Então** todos os testes passam.

---

### Edge Cases

- **Relator que deixou o exercício.** Um deputado do NOVO licenciado ou afastado não está na lista de em exercício (PRODUCT.md, §8). Enquanto isso, os itens dele perdem `relatoria NOVO`. A REL só aplica a regra; o evento de perda será registrado pela MUD.
- **Relator que não é mais deputado** (mandato encerrado). Ele não está na lista do NOVO, então não gera `relatoria NOVO`. O partido atual dele, se a Câmara ainda o informar, é o último registrado.
- **Matéria que voltou à mesma comissão.** Só vale designação feita na passagem mais recente da referência pela comissão atual. Designação de uma passagem anterior pela mesma comissão não vale (ver Assumptions).
- **Vários relatores no histórico.** Vale o mais recente que ainda não devolveu a matéria. Os anteriores são histórico e **não** são registrados (fora do recorte).
- **Designação e devolução no mesmo dia.** Vale a ordem das tramitações pela sequência registrada, e não só pela data.
- **Mesmo relator designado de novo depois de devolver.** Vale a nova designação.
- **Relator suplente ou designação "ad hoc".** Se a tramitação o registrar como designação de relator, segue a regra comum; se a Câmara usar um tipo de tramitação que a regra não reconhece, vale o comportamento decidido em FR-011.
- **Matéria em "Pronta para Pauta" ou "Aguardando Parecer" após parecer do relator.** O relator continua o atual até devolver a matéria ou ser substituído (PRODUCT.md, D3). Parecer não encerra a relatoria.
- **Dados do dia anterior.** O lote é de madrugada e as tramitações vêm ao vivo. Se as duas fontes divergirem (por exemplo, a matéria mudou de comissão entre o lote e a consulta), a última passagem pelas tramitações fica em outro órgão que o do lote e o item leva a marca "relator indeterminado" (FR-011), sem dar nem negar `relatoria NOVO`. Amanhã o lote alcança a API e a marca some.
- **Primeira execução depois da REL.** Itens que passam a existir só por `relatoria NOVO` aparecem de uma vez na lista. A comparação com o dia anterior é da MUD; a REL não gera evento.
- **Item sem etiqueta de autoria e sem relator do NOVO.** Continua fora da lista (PRODUCT.md, §5.4).

## Requirements *(mandatory)*

### Functional Requirements

**Etiqueta e inclusão**

- **FR-001**: O sistema DEVE atribuir a etiqueta `relatoria NOVO` ao item cujo **relator atual** esteja entre os deputados do NOVO em exercício no dia (PRODUCT.md, §5.4). O partido considerado é o de hoje, não o da data da designação.
- **FR-002**: O sistema DEVE definir **relator atual** como o deputado designado relator **na comissão em que a referência do item está** que **não devolveu a matéria** depois da designação (devolução sem manifestação, substituição ou saída do relator da comissão, esta última uma interpretação de PRODUCT.md, D3, aprovada pelo mantenedor em 18/10/2026: ver plan.md, "Decisões do mantenedor"). O campo de "último relator" da fonte em lote é apenas um candidato e só vale depois de confirmado pelas tramitações (PRODUCT.md, D3).
- **FR-003**: Um item DEVE entrar na lista quando tiver ao menos uma etiqueta, **inclusive** quando a única etiqueta for `relatoria NOVO` (PRODUCT.md, §5.4). A única exceção é o candidato à relatoria NOVO com relator indeterminado (FR-011), que entra sem etiqueta e com a marca. A inclusão continua sujeita a "estar na comissão" (PRODUCT.md, §5.3); nenhuma regra nova inclui ou exclui item.
- **FR-004**: O relator DEVE ser avaliado na **referência** do item: a própria proposição quando não há principal; a raiz da cadeia de apensação quando há. Apensados herdam o relator da principal (PRODUCT.md, D4 e §5.2). Quando a referência é "principal não localizada", vale o status do próprio item.
- **FR-005**: Os PL 937/2022 e PL 3514/2023 DEVEM ficar sem `relatoria NOVO`, e o PL 4501/2023 DEVE tê-la, nas fixtures reais da sondagem.

**Leitura das tramitações**

- **FR-006**: O sistema DEVE ler as tramitações da referência (a) de todo item que já tem etiqueta de autoria e (b) dos **candidatos à relatoria NOVO**: as referências na comissão cujo último relator registrado na fonte em lote é deputado do NOVO em exercício. Só o relator atual confirmado pelas tramitações gera a etiqueta; ela não é inferida do campo em lote. A referência compartilhada por vários itens (apensados e a principal) é lida uma vez.
- **FR-007**: Quando uma designação de relator, uma devolução ou uma substituição é lida das tramitações, o sistema DEVE respeitar a **ordem** das tramitações (sequência registrada) para decidir qual vale.
- **FR-008**: O sistema DEVE informar, em **todo** item da lista (inclusive os só de autoria, como o PL 5594/2020), o relator atual (nome e identificação) e o partido atual dele, ou indicar que não há relator atual (PRODUCT.md, §3 e §6.2).
- **FR-009**: O partido atual do relator DEVE ser obtido de fonte oficial, no dia da execução, e não do texto da designação (que registra o partido na data dela).
- **FR-010**: O sistema NÃO DEVE registrar o histórico de relatores nem considerar relatores designados em outras comissões (limites da linha REL).

**Falha visível e integridade**

- **FR-011**: Quando as tramitações de um item **não permitirem determinar o relator atual** com segurança (sequência de tramitações incoerente ou tipo de tramitação de relatoria que a regra não reconhece), o sistema DEVE manter o item avaliado, marcá-lo como "relator indeterminado" e **não** atribuir nem negar `relatoria NOVO`. Um candidato à relatoria NOVO com relator indeterminado DEVE entrar na lista com a marca, mesmo sem outra etiqueta. Isso vale só para a indeterminação do conteúdo; resposta ausente, malformada ou incompleta da API continua sendo FR-012.
- **FR-012**: Erro na API de tramitações ou de partido do relator (rede, status HTTP, JSON inesperado ou sem os campos exigidos, lista de tramitações vazia ou com sequência repetida, paginação ou link fora da API da Câmara; a API de tramitações não anuncia total nem pagina, então a completude é validada pelo formato) DEVE falhar a execução inteira, com mensagem que diga o motivo, sem publicação parcial (PRODUCT.md, §7). O `atual.json` anterior DEVE permanecer intacto, byte a byte, e a gravação continua sendo tudo ou nada.
- **FR-013**: A etiqueta `relatoria NOVO` NÃO DEVE ser omitida em silêncio por falha de leitura: ou a leitura foi completa, ou a execução falha (FR-012), ou o item leva a marca "relator indeterminado" (FR-011).
- **FR-014**: Reexecutar no mesmo dia, sobre os mesmos dados, DEVE produzir itens idênticos, na mesma ordem (constituição, princípio V). A ordem dos itens continua sendo "parado há mais tempo primeiro", com desempate estável.

**Conteúdo do resultado**

- **FR-015**: Cada item DEVE trazer, além do que a COL já traz: o relator atual (nome, identificação, partido de hoje e data da designação), ou a indicação de que não há; a marca "relator indeterminado", quando for o caso; e, sempre que houver relator, o link oficial da ficha da proposição de onde o relator foi lido (a referência), para conferência.
- **FR-016**: A ordem das etiquetas de um item DEVE ser determinística: `autoria NOVO`, `autor hoje no NOVO`, `relatoria NOVO`.
- **FR-017**: O `meta` do `atual.json` DEVE continuar descrevendo o resultado (total de itens e total por comissão passam a incluir os itens só de `relatoria NOVO`). O formato do `atual.json` DEVE ter a versão de formato incrementada se campos forem acrescentados, para quem lê o arquivo detectar a mudança.

**Configuração e testes**

- **FR-018**: A lista de comissões e o ano mínimo continuam vindo da configuração. A REL NÃO DEVE exigir configuração nova para o caso comum.
- **FR-019**: O comportamento DEVE ser coberto por testes com **fixtures reais salvas** (lote e tramitações dos casos da sondagem) e NENHUM teste DEVE depender da internet (constituição, princípio IV). Os testes DEVEM cobrir, no mínimo: os casos PL 937/2022, PL 3514/2023, PL 4501/2023 e PL 1843/2022; a herança de relator por apensação (um e dois níveis); designação, devolução e substituição; relator que mudou de partido; matéria sem relator; e cada tipo de falha da User Story 4.

**Limites desta feature (não implementar)**

- **FR-020**: Esta feature NÃO DEVE implementar histórico de relatores, relatores de outras comissões, comparação com o dia anterior, eventos de mudança (entrou, saiu, relator, parecer), o resumo no Telegram, avisos nem a página pública. As regras da COL e da AGE não mudam, exceto na medida exigida por FR-003 e FR-017.

### Key Entities *(include if feature involves data)*

- **Referência**: a proposição de que vêm a comissão, a situação e o relator do item (a própria, a raiz da cadeia de apensação, ou a própria quando "principal não localizada"). Já existe na COL.
- **Tramitação**: registro de andamento da proposição. Atributos usados: sequência, data e hora, órgão, tipo de tramitação e despacho. É a fonte para saber quem foi designado, quem devolveu e quem substituiu.
- **Relator atual**: deputado designado relator na comissão atual da referência que não devolveu a matéria. Atributos: identificação, nome, partido de hoje, data da designação. Pode não existir.
- **Candidato à relatoria NOVO**: referência na comissão cujo último relator registrado na fonte em lote é deputado do NOVO em exercício; é o conjunto cujas tramitações são lidas para confirmar a etiqueta.
- **Marca "relator indeterminado"**: sinal no item de que as tramitações não permitiram determinar o relator atual (análoga a "principal não localizada").
- **Etiqueta `relatoria NOVO`**: terceiro motivo pelo qual um item está na lista (PRODUCT.md, D2).
- **Item do estoque**: o item da COL, acrescido do relator atual e, quando for o caso, da etiqueta `relatoria NOVO`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nas fixtures reais, PL 937/2022 e PL 3514/2023 ficam sem `relatoria NOVO`, PL 4501/2023 aparece com `relatoria NOVO`, e PL 1843/2022 mostra `autoria NOVO` e `relatoria NOVO`.
- **SC-002**: 100% dos itens com `relatoria NOVO` trazem o relator atual, o partido de hoje, a data da designação e o link oficial para conferir; nenhum item tem a etiqueta sem relator.
- **SC-003**: Nenhum item tem `relatoria NOVO` por relator que devolveu a matéria, por relator de outra comissão ou por relator só do apensado (e não da principal), em todos os casos cobertos pelos testes.
- **SC-004**: Em 100% dos cenários de falha de leitura da User Story 4 (cenários 1 a 3), o comando termina com erro, a mensagem diz o motivo, e o `atual.json` anterior permanece idêntico byte a byte. Nos cenários 4 e 5 (relator indeterminado), 100% dos itens afetados levam a marca e nenhum deixa de aparecer.
- **SC-005**: Duas execuções sobre as mesmas fixtures produzem itens idênticos, na mesma ordem.
- **SC-006**: A suíte inteira (ruff e pytest) passa sem acesso à internet.
- **SC-007**: Na conferência manual contra a sondagem de 17/10/2026 (34 PL/PLP nas comissões com o "último relator" do NOVO, vários só por relator histórico), os candidatos confirmados pelas tramitações, contados **por referência**, são no máximo esses 34, e cada diferença é explicável item a item pelas tramitações. Os apensados que herdam o relator da principal (D4) são itens à parte e não entram nessa conta. *(Redação ajustada em 18/10/2026, com o OK do mantenedor: a original media o total de itens e ignorava a herança, que a própria REL introduz.)*
- **SC-008**: Nenhum item entra ou sai por regra que o `PRODUCT.md` não descreva (constituição, princípio II).

## Assumptions

- **COL e AGE estão concluídas e seu comportamento é preservado.** A etiqueta de autoria, a referência, a plausibilidade e o `status.json` não mudam. Os testes da COL e da AGE que dependem do total de itens ou do conjunto de itens podem precisar de ajuste, porque entram itens só de relatoria; essa mudança deve ficar explícita nos testes.
- **O candidato é lido do campo de último relator da fonte em lote**, e a etiqueta só é dada depois de confirmada pelas tramitações (PRODUCT.md, D3). A suposição de que o relator atual, quando existe, coincide com o último relator designado foi conferida em research.md (R1 e R3) em 25 histórias reais.
- **Passagem mais recente pela comissão (decidido no clarify).** Se a proposição saiu da comissão atual e voltou, só vale designação feita depois da última entrada. É a leitura de "designado na comissão em que a proposição está" (PRODUCT.md, D3) que não mantém relator de passagem antiga.
- **Relator atual vem das tramitações; o partido de hoje vem da Câmara, no dia.** A lista de deputados do NOVO em exercício, já obtida pela COL, decide a etiqueta; o partido exibido de relatores fora do NOVO exige consulta própria.
- **A fonte das tramitações é a API da Câmara, ao vivo**, enquanto o estoque vem do lote do dia anterior. Pode haver divergência de um dia entre as duas; a divergência de órgão vira "relator indeterminado" (FR-011); o resto é limite conhecido (PRODUCT.md, §8).
- **Volume.** O universo de leitura de tramitações é pequeno (dezenas de referências: os itens da lista mais os candidatos, FR-006), além das consultas de partido dos relatores. O custo em tempo e em chamadas é avaliado no `plan.md`.
- **Requisito para AVI e PAG (não implementado aqui).** O resumo diário e a página devem avisar quantos itens estão com "relator indeterminado", como farão com "principal não localizada". Decidido pelo mantenedor em 18/10/2026.
- **O formato do `atual.json` muda** (relator atual por item e marca de indeterminação). Os consumidores existentes (AGE) leem `meta` e o total; a compatibilidade é verificada no plano.
- **Dependência nova só com justificativa escrita no `plan.md`** (constituição, princípio I). A REL não deve precisar de nenhuma.
