# Feature Specification: COL — Coleta e estoque filtrado

**Feature Branch**: `main-ibd849` (sem branch própria de feature; o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido)

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "Feature COL — Coleta e estoque filtrado (linha COL do ROADMAP.md)", com o recorte "Inclui" e "Não inclui" da linha.

## Clarifications

### Session 2026-10-18

- Q: Quando a principal de um apensado não é encontrada (ou a cadeia tem ciclo), o item usa o próprio status ou entra sempre? → A: Usa o próprio status. Só entra se o órgão do próprio último status estiver na lista de comissões, e leva a marca "principal não localizada".
- Q: Como o sistema decide que um arquivo baixado está cortado? → A: O arquivo está cortado se o tamanho recebido for menor que o informado pelo servidor, ou se a última linha estiver incompleta (faltam colunas). Não há mínimo de linhas por ano nesta feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar o estoque filtrado do NOVO nas comissões (Priority: P1)

O mantenedor roda um único comando e obtém um arquivo de dados (`data/atual.json`) com os PL e PLP que estão hoje na CE e na CREDN e que têm ligação de **autoria** com o NOVO. Cada item diz por que está na lista (as etiquetas `autoria NOVO` e/ou `autor hoje no NOVO`), traz a situação atual e um link para a página oficial da Câmara. É a base de dados de todas as features seguintes (relatoria, mudanças, aviso, página).

**Why this priority**: sem esse arquivo nada mais existe. Sozinha, já entrega uma lista conferível do que é de interesse do NOVO nas comissões, e responde à pergunta central do produto (PRODUCT.md, §3).

**Independent Test**: rodar o comando sobre fixtures salvas de uma coleta real e conferir que o arquivo contém exatamente os itens esperados nos três casos de aceitação abaixo, cada um com as etiquetas certas e o link oficial.

**Acceptance Scenarios**:

1. **Dado** o PL 1843/2022, de autoria de Lucas Gonzalez (assinou como NOVO) e na CE, **Quando** o estoque é gerado, **Então** o item aparece com a etiqueta `autoria NOVO`.
2. **Dado** o PL 3871/2024, de Luiz Lima, assinado quando ele era do PL e hoje deputado em exercício do NOVO, **Quando** o estoque é gerado, **Então** o item aparece com a etiqueta `autor hoje no NOVO` e sem `autoria NOVO`.
3. **Dado** o PL 4047/2019, apensado a um PL cujo último status está na CFT, **Quando** o estoque é gerado, **Então** o item **não** aparece, ainda que tenha ligação com o NOVO.
4. **Dado** um item cujo autor assinou como NOVO **e** hoje é deputado do NOVO, **Quando** o estoque é gerado, **Então** o item mostra as duas etiquetas.
5. **Dado** uma proposição que não é PL nem PLP (por exemplo REQ, PDL ou PEC), **Quando** o estoque é gerado, **Então** ela não entra na lista, mesmo estando na CE ou na CREDN.

---

### User Story 2 - Apensados seguem a proposição principal (Priority: P1)

Metade do estoque é de proposições apensadas, e o último status delas fica congelado (às vezes desde 2013). O gabinete precisa ver o apensado com a comissão, a situação e o "parado há" da proposição principal, e saber a qual proposição ele está apensado. Quando a principal não pode ser determinada, o item aparece com uma marca explícita, e não some.

**Why this priority**: sem isso, a lista erra a comissão de cerca de metade dos itens (PRODUCT.md, D4 e §5.2). É regra de domínio, não detalhe.

**Independent Test**: com fixtures que contêm uma cadeia de apensação de dois ou mais níveis, uma principal fora dos arquivos lidos e um ciclo, conferir a comissão, a situação, a referência e a marca de cada item.

**Acceptance Scenarios**:

1. **Dado** um apensado A cuja principal B está na CE e é a raiz da cadeia, **Quando** o estoque é gerado, **Então** A é avaliado pela comissão, pela situação e pelo "parado há" de B, e mostra "apensado ao PL B".
2. **Dado** uma cadeia A → B → C em que C é a raiz, **Quando** o estoque é gerado, **Então** a referência de A é C, e não B.
3. **Dado** um apensado cuja principal está em outra comissão (fora da lista), **Quando** o estoque é gerado, **Então** o apensado não entra, ainda que o próprio último status dele seja da CE ou da CREDN.
4. **Dado** um apensado com etiqueta do NOVO cuja raiz não é encontrada nos arquivos lidos e cujo próprio último status é de uma comissão da lista, **Quando** o estoque é gerado, **Então** o item aparece avaliado pelo próprio status e com a marca "principal não localizada".
5. **Dado** um apensado com etiqueta do NOVO cuja raiz não é encontrada e cujo próprio último status é de órgão fora da lista, **Quando** o estoque é gerado, **Então** o item não aparece.
6. **Dado** uma cadeia de apensação com ciclo, **Quando** o estoque é gerado, **Então** o item é tratado como "principal não localizada" (mesma regra dos cenários 4 e 5) e a execução termina normalmente.
7. **Dado** um apensado de autoria do NOVO cuja principal é de outro autor, **Quando** o estoque é gerado, **Então** as etiquetas são calculadas pelos autores do próprio apensado, e a comissão e a situação vêm da principal.

---

### User Story 3 - Falhar de forma visível, sem gravar dado ruim (Priority: P1)

Quando a fonte está fora do ar, mudou de formato, está desatualizada, veio vazia ou traz um estoque vazio, o comando termina com erro e uma mensagem que diz o motivo. O último `data/atual.json` bom continua exatamente como estava. Uma lista vazia ou parcial nunca é gravada como se fosse completa.

**Why this priority**: o gabinete decide a partir da lista. Uma lista vazia ou parcial tomada por verdade é o pior erro possível (Constituição, princípio III; PRODUCT.md, D10).

**Independent Test**: para cada tipo de falha, alimentar o comando com uma fonte simulada defeituosa e conferir três coisas: saída com erro, mensagem com o motivo e arquivo anterior intacto.

**Acceptance Scenarios**:

1. **Dado** que a fonte não responde ou responde com erro depois das novas tentativas, **Quando** o comando roda, **Então** ele sai com erro dizendo que a fonte falhou, e o `atual.json` anterior não muda.
2. **Dado** um arquivo da fonte sem uma coluna que a coleta usa, ou com tipo de dado inesperado, **Quando** o comando roda, **Então** ele sai com erro "formato alterado: coluna X", e o `atual.json` anterior não muda.
3. **Dado** arquivos cuja data de modificação tem mais de 36 horas, **Quando** o comando roda, **Então** ele sai com erro "a Câmara não atualizou os arquivos", e o `atual.json` anterior não muda.
4. **Dado** arquivos cuja data de modificação mais recente passa em mais de 6 horas a mais antiga (por exemplo, parte dos anos já regenerada pela Câmara e parte não), **Quando** o comando roda, **Então** ele sai com erro "os arquivos da Câmara foram gerados em momentos diferentes", e o `atual.json` anterior não muda.
5. **Dado** um arquivo de ano vazio ou ausente dentro do intervalo configurado, **Quando** o comando roda, **Então** ele sai com erro, e o `atual.json` anterior não muda.
6. **Dado** um arquivo cujo tamanho recebido é menor que o informado pelo servidor, **Quando** o comando roda, **Então** ele sai com erro de arquivo incompleto, e o `atual.json` anterior não muda.
7. **Dado** um arquivo cuja última linha está incompleta (faltam colunas), **Quando** o comando roda, **Então** ele sai com erro de arquivo incompleto, e o `atual.json` anterior não muda.
8. **Dado** que a lista de deputados do NOVO não pôde ser obtida, **Quando** o comando roda, **Então** a execução inteira falha: não há publicação parcial só com `autoria NOVO`.
9. **Dado** que, depois de aplicar os filtros, a lista de itens ficou vazia, **Quando** o comando roda, **Então** ele sai com erro, e o `atual.json` anterior não muda.
10. **Dado** que o comando falhou no meio da gravação, **Quando** se examina `data/atual.json`, **Então** ele é o arquivo bom anterior ou o novo completo, nunca um arquivo pela metade.

---

### User Story 4 - Comissões e ano mínimo configuráveis (Priority: P2)

Quem mantém o produto troca as comissões acompanhadas (hoje CE e CREDN) e o ano mínimo de leitura (hoje 2003) editando um arquivo de configuração, sem alterar código. Isso prepara a troca de comissão em 2027.

**Why this priority**: a decisão D1 pede configuração, não tela nem código. Não bloqueia o primeiro resultado, mas é requisito da linha.

**Independent Test**: alterar a lista de comissões na configuração, rodar sobre as mesmas fixtures e conferir que passam a entrar itens da outra comissão e a sair os da antiga.

**Acceptance Scenarios**:

1. **Dado** a configuração com `["CE", "CREDN"]` e ano mínimo 2003, **Quando** o comando roda, **Então** só entram itens dessas comissões e só são lidos os anos de 2003 em diante.
2. **Dado** a lista alterada para outra sigla de comissão, **Quando** o comando roda sobre as mesmas fixtures, **Então** o resultado muda sem nenhuma alteração de código.
3. **Dado** um valor de configuração inválido (lista vazia, ano mínimo no futuro ou não numérico), **Quando** o comando roda, **Então** ele sai com erro dizendo qual valor é inválido, sem baixar nada.

---

### User Story 5 - Resultado repetível e auditável (Priority: P2)

Rodar o comando duas vezes sobre os mesmos dados de origem produz a mesma lista, na mesma ordem. O bloco `meta` do arquivo registra de onde vieram os dados e com quais parâmetros, para que qualquer pessoa confira cada linha na fonte.

**Why this priority**: sustenta a idempotência (princípio V) e a rastreabilidade (princípio II), e o histórico diário no Git depende de diffs limpos (PRODUCT.md, D8).

**Independent Test**: rodar duas vezes sobre as mesmas fixtures e comparar os arquivos; os itens devem ser idênticos, e só o momento de geração pode diferir.

**Acceptance Scenarios**:

1. **Dado** as mesmas fixtures, **Quando** o comando roda duas vezes, **Então** a lista de itens (conteúdo e ordem) é idêntica nas duas execuções.
2. **Dado** um `atual.json` gerado, **Quando** se lê o bloco `meta`, **Então** ele informa a data dos dados da Câmara, o momento da geração, as comissões e o ano mínimo usados, o total de itens e o total por comissão.
3. **Dado** um `atual.json` gerado, **Quando** se lê o bloco `meta`, **Então** ele traz a lista de deputados do NOVO em exercício que foi usada, para que a etiqueta `autor hoje no NOVO` possa ser conferida depois.

---

### Edge Cases

- **Apensado a proposição de outro tipo.** A raiz da cadeia pode ser de tipo diferente de PL/PLP (por exemplo, um PLP apensado a um PL). A busca da raiz considera todos os tipos presentes nos arquivos lidos.
- **Raiz apresentada antes do ano mínimo.** A raiz está fora dos arquivos lidos, então vale "principal não localizada". Um apensado cujo próprio status esteja congelado em órgão fora da lista não entra, mesmo que a raiz desconhecida estivesse na CE ou na CREDN; é limite conhecido da regra.
- **Autor que não é deputado** (Senado, Executivo): `autoria NOVO` ainda vale se o partido registrado na autoria for NOVO. `autor hoje no NOVO` não se aplica a ele.
- **Vários autores.** Basta um autor satisfazer a regra de uma etiqueta para o item recebê-la. O item mostra todos os autores, cada um com o partido na data.
- **Deputado do NOVO licenciado ou afastado** não aparece na lista de em exercício. Os itens dele perdem `autor hoje no NOVO` enquanto ele estiver fora (PRODUCT.md, §8). A COL só aplica a regra, e a mudança será registrada pela feature MUD.
- **Dados do dia anterior.** A fonte é gerada de madrugada, e o estoque reflete o dia anterior. Isso é limite conhecido, não erro.
- **A coluna `ano` nem sempre coincide com o ano de apresentação.** A identificação do item é `tipo número/ano` como a Câmara exibe, e o link oficial permite conferir.
- **Primeira execução (sem `atual.json` anterior).** A falha não pode deixar um arquivo parcial; sem arquivo anterior, simplesmente não há `atual.json`.
- **Ano corrente recém-iniciado** (por exemplo, em janeiro, antes de a fonte publicar o arquivo do ano). Arquivo ausente dentro do intervalo configurado é falha, não omissão silenciosa.

## Requirements *(mandatory)*

### Functional Requirements

**Coleta e validação da fonte**

- **FR-001**: O sistema DEVE obter, da fonte oficial da Câmara, os arquivos em lote de proposições e de autores de cada ano, do ano mínimo configurado até o ano corrente.
- **FR-002**: O sistema DEVE validar cada arquivo obtido: resposta bem-sucedida, presença e tipo das colunas que a coleta usa, conteúdo não vazio e arquivo completo. O arquivo é considerado incompleto quando o tamanho recebido é menor que o informado pelo servidor ou quando a última linha tem colunas faltando. A feature NÃO exige número mínimo de linhas por ano.
- **FR-003**: O sistema DEVE tentar de novo, um número limitado de vezes, as falhas temporárias de rede antes de declarar a fonte indisponível.
- **FR-004**: O sistema DEVE verificar a data de modificação dos arquivos e falhar com "a Câmara não atualizou os arquivos" quando a mais antiga tiver mais de 36 horas. DEVE também falhar, com "os arquivos da Câmara foram gerados em momentos diferentes", quando a diferença entre a data de modificação mais antiga e a mais recente passar de 6 horas, para que a lista nunca misture arquivos de dias diferentes.
- **FR-005**: O sistema DEVE obter a lista de deputados do NOVO em exercício no dia, pela API da Câmara. Falha nessa obtenção DEVE falhar a execução inteira, sem resultado parcial. Também é falha da execução inteira: resposta sem o total anunciado (`X-Total-Count`), total entregue diferente do anunciado, lista vazia e link de paginação fora da API da Câmara.

**Regras de inclusão (PRODUCT.md §5.1 a §5.5)**

- **FR-006**: O sistema DEVE considerar apenas proposições dos tipos PL e PLP como candidatas.
- **FR-007**: O sistema DEVE determinar a referência de cada candidata: a própria proposição quando não há principal; caso contrário, a raiz da cadeia de apensação.
- **FR-008**: Quando a raiz não for encontrada nos arquivos lidos, ou a cadeia tiver ciclo, o sistema DEVE usar o próprio status do item no lugar do da referência e marcar o item como "principal não localizada". O item entra na lista somente se o órgão do próprio último status estiver na lista de comissões (FR-009) e ele tiver etiqueta (FR-012).
- **FR-009**: O sistema DEVE considerar a candidata "na comissão" somente quando o órgão do último status da referência fizer parte da lista de comissões configurada.
- **FR-010**: O sistema DEVE atribuir `autoria NOVO` quando algum autor da própria candidata constar com o partido NOVO na data da autoria.
- **FR-011**: O sistema DEVE atribuir `autor hoje no NOVO` quando algum autor da própria candidata, identificado como deputado, estiver entre os deputados em exercício do NOVO no dia.
- **FR-012**: O sistema DEVE incluir na lista apenas as candidatas "na comissão" que tenham ao menos uma das duas etiquetas. Nenhuma outra regra DEVE incluir ou excluir item.
- **FR-013**: A situação, a comissão e a data e hora do último status de cada item DEVEM vir da referência. O "parado há" (dias desde a data e hora do último status da referência) DEVE ser informado.

**Conteúdo do resultado**

- **FR-014**: Cada item DEVE trazer: identificação `tipo número/ano`, ementa, autores com o partido na data, etiquetas, comissão, situação, referência (e "apensado ao X", quando for o caso), "parado há" e o link para a página oficial da proposição na Câmara.
- **FR-015**: O resultado DEVE trazer um bloco `meta` com: data dos dados da Câmara, momento da geração, comissões e ano mínimo usados, total de itens, total por comissão e lista de deputados do NOVO em exercício usada.
- **FR-016**: A lista de itens DEVE ter ordem determinística, e duas execuções sobre os mesmos dados DEVEM produzir itens idênticos.

**Falha visível e integridade**

- **FR-017**: O sistema DEVE terminar com saída de erro e uma mensagem que diga o motivo em cada uma destas situações: fonte indisponível, formato alterado (indicando a coluna), arquivos desatualizados, arquivo vazio, incompleto ou ausente, falha na obtenção dos deputados, estoque filtrado vazio e configuração inválida.
- **FR-018**: Em qualquer falha, o sistema NÃO DEVE alterar o `data/atual.json` existente. A gravação DEVE ser tudo ou nada: o arquivo nunca fica pela metade.
- **FR-019**: Uma lista filtrada vazia DEVE ser sempre tratada como falha, nunca publicada como resultado válido.

**Configuração e testes**

- **FR-020**: A lista de comissões e o ano mínimo DEVEM ser lidos de um arquivo de configuração. Mudar esses valores NÃO DEVE exigir mudança de código. Valores inválidos DEVEM falhar a execução antes de qualquer download, inclusive sigla de comissão com espaço no começo ou no fim, que nunca casaria com a fonte.
- **FR-021**: O comportamento DEVE ser coberto por testes que usam fixtures reais salvas e NÃO DEVEM depender de rede.
- **FR-022**: Os testes DEVEM cobrir, no mínimo, os três casos de aceitação da User Story 1, a cadeia de apensação (dois níveis, principal não localizada, ciclo) e cada tipo de falha da User Story 3.

**Limites desta feature (não implementar)**

- **FR-023**: Esta feature NÃO DEVE implementar a etiqueta `relatoria NOVO`, o relator atual, a leitura de tramitações, a comparação com o dia anterior, os eventos de mudança, o agendamento, o `data/status.json`, o Telegram, os avisos nem a página pública. A checagem de variação do estoque entre dias (mais de 20%) depende do retrato anterior e pertence à feature AGE.

### Key Entities *(include if feature involves data)*

- **Proposição**: PL, PLP ou outro tipo presente nos arquivos. Atributos usados: identificador, tipo, número, ano, ementa, data de apresentação, indicação de proposição principal e último status (data e hora, órgão, situação).
- **Referência**: a proposição que determina a comissão, a situação e o "parado há" de um item. É a própria proposição ou a raiz da cadeia de apensação. Pode ser "não localizada".
- **Autor**: pessoa ou órgão que assina a proposição. Atributos: identificador do deputado (quando houver), nome, partido na data da autoria, ordem de assinatura.
- **Deputado do NOVO em exercício**: deputado que a API lista como do NOVO no dia da execução. É a base da etiqueta `autor hoje no NOVO`.
- **Etiqueta**: motivo pelo qual o item está na lista. Nesta feature: `autoria NOVO` e `autor hoje no NOVO`.
- **Item do estoque**: proposição candidata que está na comissão e tem ao menos uma etiqueta, com os atributos da FR-014.
- **Configuração**: lista de comissões acompanhadas e ano mínimo de leitura.
- **Meta**: bloco do resultado com a origem e os parâmetros dos dados (FR-015).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os três casos de aceitação da User Story 1 (PL 1843/2022, PL 3871/2024 e PL 4047/2019) passam, com as etiquetas esperadas, nas fixtures reais.
- **SC-002**: 100% dos itens do resultado têm link para a página oficial da proposição na Câmara, e 100% têm ao menos uma etiqueta.
- **SC-003**: Em 100% dos cenários de falha da User Story 3, o comando termina com erro, a mensagem diz o motivo e o `data/atual.json` anterior permanece idêntico byte a byte.
- **SC-004**: Duas execuções sobre as mesmas fixtures, no mesmo dia (ou com o relógio fixado), produzem listas de itens idênticas (conteúdo e ordem); a única diferença permitida é o momento de geração no `meta`. Em dias diferentes, o "parado há" muda porque depende da data.
- **SC-005**: Trocar a lista de comissões ou o ano mínimo muda o resultado sem alterar nenhuma linha de código.
- **SC-006**: A suíte de testes inteira passa sem acesso à internet.
- **SC-007**: Nenhum item é incluído ou excluído por regra que o `PRODUCT.md` não descreva, e nenhum item deixa de aparecer em silêncio por falha na cadeia de apensação (todo item que entra com raiz não resolvida leva a marca "principal não localizada").
- **SC-008**: Na conferência manual contra a ordem de grandeza da sondagem (cerca de 50 itens com `autoria NOVO` ou `autor hoje no NOVO`, sem contar os de relatoria), o total gerado fica na mesma ordem de grandeza e a diferença é explicável item a item.

## Assumptions

- A fonte é o lote completo da Câmara, baixado inteiro todo dia; o download condicional não reduz volume (PRODUCT.md, D7 e §8). O volume é de cerca de 1 GB por execução, e a viabilidade em tempo e memória é decidida no `plan.md`.
- O limite de 36 horas para "arquivos desatualizados" vem do PRODUCT.md (§7, "cerca de 36 horas") e é o valor adotado nesta spec.
- "Contagem" na validação do lote significa: nenhum ano do intervalo configurado pode estar ausente, vazio ou incompleto (conforme definido em FR-002), e o estoque filtrado não pode ser vazio. Não há comparação com o dia anterior (isso é da AGE).
- A raiz da cadeia de apensação é buscada entre todas as proposições dos arquivos lidos, de qualquer tipo.
- As etiquetas de autoria são calculadas pelos autores da própria candidata, e a comissão, a situação e o "parado há" vêm da referência (PRODUCT.md, §5.2 e §5.4).
- O "parado há" é calculado em dias inteiros, em relação à data da geração registrada no `meta`.
- O link oficial é o da página da proposição no portal da Câmara; o formato exato da URL é decidido no plano.
- As fixtures são recortes reais dos arquivos da Câmara, com o mesmo formato, salvos no repositório. A forma de obtê-las (a sondagem de 17/10/2026 não deixou os arquivos no repositório) é decidida no plano.
- O ano corrente é o ano da execução. Em janeiro, se o arquivo do ano ainda não existir, a execução falha (FR-017); isso é aceito como comportamento seguro.
- O comando roda manualmente nesta feature. O agendamento diário é da feature AGE.
- Relatoria é tratada pela feature REL: nenhum item da COL traz relator, e os casos de aceitação que dependem dele (PL 4501/2023, PL 937/2022, PL 3514/2023) ficam fora desta spec.
- A idempotência de que trata esta spec é a do conteúdo da lista. Avisos duplicados não se aplicam, porque a COL não envia mensagens.
