# Feature Specification: PAG — Página pública

**Feature Branch**: nenhuma criada. O `CLAUDE.md` proíbe criar ou trocar de branch sem pedido do mantenedor; a spec foi escrita em `main`, e a branch fica para o mantenedor decidir antes do `/speckit-implement`.

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Feature PAG — Página pública (linha PAG do ROADMAP.md)", com o recorte "Inclui" e "Não inclui" da linha, as regras do PRODUCT.md que se aplicam (§6.2, §7, §8, D9, D10) e os pontos em aberto levantados na situação.

**Recorte da linha PAG (ROADMAP.md)**

- *Resultado verificável*: o GitHub Pages mostra a linha de atualização, a faixa de erro ou de atraso, os números, as mudanças de 7 dias e a lista com chips de comissão e de motivo, ordenada por "parado há". Tem bloco de limites e download em JSON e CSV. Funciona sem JS.
- *Inclui*: HTML estático gerado em Python; tokens azuis e FilterChips do DS; aviso de dados atrasados no navegador; acessibilidade do DS.
- *Não inclui*: busca; paginação; histórico de mais de 7 dias; a página de projeto no portfólio (fica no repositório Portfolio, com EmbedFrame).
- *Dependências*: COL, AGE e MUD (todas concluídas).

**Fora desta feature, por consequência do recorte e das outras linhas do ROADMAP.md**: o envio no Telegram (AVI, concluída); a pauta das reuniões (PAU); os itens "a caminho" (CAM); a etiqueta do gabinete (GAB); as movimentações relevantes (MOV); qualquer mudança nas regras de coleta, de relatoria ou de comparação. A página só **exibe** o que `data/atual.json`, `data/status.json` e `data/mudancas/AAAA-MM-DD.json` já trazem: não inclui, não exclui nem reclassifica item por regra própria (constitution, princípio II).

## Clarifications

### Session 2026-10-20

- Q: Como a página é publicada no GitHub Pages? → A: **Workflow próprio**, disparado ao fim de toda execução da "Coleta diária" (com sucesso ou falha) e também manualmente. Gera a página dos arquivos já commitados e publica pelo GitHub Pages; nada gerado é commitado no Git. Uma falha da geração não altera o resultado da coleta. Ao publicar, esta feature preenche `aviso.pagina_url` no `config.toml` com o endereço da página.
- Q: Qual o formato do CSV de download? → A: **";" como separador, UTF-8 com BOM, uma linha por item**, com as colunas que a página exibe (identificação, link oficial, ementa, comissão, situação, parado há, etiquetas, autores com partido na data, relator atual com partido de hoje, apensado a, marcas). Listas numa célula, unidas por " | ".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver, no celular, a lista de hoje e de quando ela é (Priority: P1)

O chefe de gabinete abre o endereço da página no celular e vê, no topo, de quando são os dados ("Dados da Câmara de DD/MM (arquivo gerado às HHhMM) · verificado em DD/MM às HHhMM"), os números (total de itens, total por comissão, mudanças desde o retrato anterior) e a lista dos PL/PLP de interesse do NOVO, com o que mais importa primeiro: o que está parado há mais tempo. Cada item mostra o que o gabinete precisa para decidir e traz o link para a ficha oficial da Câmara (PRODUCT.md, §6.2 e §3).

**Why this priority**: é a razão de a feature existir. Sem lista e sem a data dos dados, o resumo do Telegram ("veja a página") não leva a lugar nenhum.

**Independent Test**: gerar a página a partir de um `atual.json` e um `status.json` salvos e conferir, no HTML, a linha de atualização, os números, a ordem dos itens e os campos de cada item.

**Acceptance Scenarios**:

1. **Dado** um retrato bom e um `status.json` de sucesso, **Quando** a página é gerada, **Então** a primeira linha diz "Dados da Câmara de DD/MM (arquivo gerado às HHhMM) · verificado em DD/MM às HHhMM", com datas e horas no horário de Brasília.
2. **Dado** o mesmo retrato, **Então** os números mostram o total de itens, o total de cada comissão acompanhada e quantas mudanças houve desde o retrato anterior, e os valores batem com o `meta` do `atual.json` e com o arquivo de mudanças do dia.
3. **Dado** o mesmo retrato, **Então** cada item da lista mostra: `Tipo número/ano` como link para a página oficial da Câmara; a ementa; os autores, cada um com o partido na data da autoria (só o nome, quando o autor não tem partido); as etiquetas; a situação; o relator atual com o partido de hoje; "nesta situação há N dias"; e "apensado ao PL X" (com link) quando for o caso.
4. **Dado** um item cuja principal não foi localizada, **Então** o item mostra a marca "principal não localizada". **Dado** um item de relator indeterminado, **Então** mostra a marca "relator indeterminado". Nenhuma das duas marcas some em silêncio (PRODUCT.md, §5.2 e §5.4).
5. **Dado** um item sem relator atual, **Então** o campo diz que não há relator atual, em vez de ficar em branco.
6. **Dado** itens com valores diferentes de "parado há", **Então** a lista vem do mais tempo parado para o menos, e itens com o mesmo valor aparecem sempre na mesma ordem.
7. **Dado** a mesma entrada, **Quando** a página é gerada duas vezes, **Então** o arquivo resultante é idêntico byte a byte (constitution, princípio V).

---

### User Story 2 - Nunca confundir dado velho ou falha com lista nova (Priority: P1)

Quando a última execução falha, a página continua mostrando o último retrato bom, mas diz de forma inequívoca que a atualização falhou: "A atualização de DD/MM falhou (motivo). Dados de DD/MM." E quando ninguém verificou os dados há mais de 30 horas (a execução nem rodou), uma faixa de atraso aparece, calculada no navegador, porque a página estática não sabe que está velha. O leitor nunca toma uma lista antiga ou parcial como a de hoje (PRODUCT.md, §7, D10; constitution, princípio III).

**Why this priority**: uma lista vazia, parcial ou velha publicada como verdade é "o pior erro possível" (PRODUCT.md, D10). A página é a única saída que o gabinete consulta por conta própria.

**Independent Test**: gerar a página com um `status.json` de falha e conferir a faixa de erro; gerar com um `status.json` de sucesso e simular o relógio do navegador 31 horas depois de `verificado_em` e conferir a faixa de atraso.

**Acceptance Scenarios**:

1. **Dado** um `status.json` com `resultado = "falha"`, **Quando** a página é gerada, **Então** ela traz a faixa de erro "A atualização de DD/MM falhou (motivo). Dados de DD/MM.", com o motivo registrado no status e a data dos dados do último retrato bom, e a lista continua sendo a do último retrato bom.
2. **Dado** um `status.json` de sucesso, **Então** a página não traz a faixa de erro.
3. **Dado** que a verificação (`verificado_em`) tem mais de 30 horas no momento em que o leitor abre a página, **Então** o navegador mostra a faixa de atraso ("dados atrasados"), e com 30 horas ou menos a faixa não aparece.
4. **Dado** que o navegador não executa JavaScript, **Então** a página continua legível e correta: as faixas calculadas no navegador não aparecem, e o aviso de falha, que não depende de JS, continua visível.
5. **Dado** que o significado das faixas não pode depender de cor (o DS não tem cores de status), **Então** cada faixa diz o que aconteceu em texto, e é identificável por quem usa leitor de tela.
6. **Dado** que a geração da página falha (por exemplo, `atual.json` ilegível ou fora do contrato), **Então** nenhuma página nova é publicada: a anterior permanece como está, o erro é anunciado pela falha visível da execução, e a página nunca sai vazia ou parcial.

---

### User Story 3 - Filtrar por comissão e por motivo, e funcionar sem JavaScript (Priority: P2)

O gabinete quer ver só a CE, ou só o que tem relatoria do NOVO. A lista tem dois grupos de chips (FilterChips do DS): **Comissão** (Todas · CE · CREDN) e **Motivo** (Todos · Autoria NOVO · Autor hoje no NOVO · Relatoria NOVO). Os chips só filtram a lista que já está na página; sem JavaScript, todos os itens aparecem (PRODUCT.md, §6.2).

**Why this priority**: aumenta muito a utilidade da lista, mas a lista inteira, ordenada, já resolve o dia sem filtro.

**Independent Test**: com a página gerada, conferir no HTML que cada item carrega a comissão e as etiquetas que os chips usam, e, num navegador com JS, que escolher um chip mostra só os itens dele. Num navegador sem JS, que todos os itens estão visíveis.

**Acceptance Scenarios**:

1. **Dado** a página com JS, **Quando** o leitor escolhe a comissão CE, **Então** só os itens da CE ficam visíveis. Escolher "Todas" volta a mostrar todos.
2. **Dado** a página com JS, **Quando** o leitor escolhe um chip de motivo, **Então** ficam visíveis só os itens que têm aquela etiqueta (um item com duas etiquetas aparece sob as duas).
3. **Dado** um chip de comissão e um de motivo escolhidos ao mesmo tempo, **Então** a lista mostra os itens que atendem aos dois.
4. **Dado** que o filtro muda o que está na tela, **Então** o resultado é anunciado em texto ("Mostrando N de M itens"), de forma que leitores de tela percebam.
5. **Dado** a página sem JavaScript, **Então** todos os itens aparecem, na mesma ordem, e nenhum controle que dependa de JS aparece como se funcionasse.
6. **Dado** o DS, **Então** os chips são botões com área de toque de 44 px, foco visível, seleção marcada de forma acessível, e a linha de chips rola na horizontal dentro do próprio contêiner no celular, sem fazer a página rolar de lado.

---

### User Story 4 - Ver o que mudou nos últimos 7 dias (Priority: P2)

Numa seção "Mudou nos últimos 7 dias", o gabinete vê os eventos dos arquivos de mudanças (entrou, saiu com motivo e destino, situação, relator, parecer, etiquetas) agrupados por dia, cada um com o link oficial. É o lugar para o qual o resumo do Telegram manda quando há mais eventos do que cabem na mensagem ("e mais N, veja a página") (PRODUCT.md, §6.2 e §5.6).

**Why this priority**: responde "o que mudou" além do dia, mas a lista atual já responde "o que há".

**Independent Test**: gerar a página com arquivos de mudanças salvos de 8 dias e conferir que só os 7 mais recentes aparecem, agrupados por dia, com todos os tipos de evento e os links.

**Acceptance Scenarios**:

1. **Dado** arquivos de mudanças de vários dias, **Quando** a página é gerada, **Então** a seção mostra apenas os dias dos últimos 7 dias, com o mais recente primeiro, e cada dia lista os seus eventos.
2. **Dado** um evento de qualquer um dos seis tipos, **Então** ele aparece com a identificação da proposição, o link oficial e o conteúdo do tipo (motivo e destino em "saiu"; "de → para" e comissão anterior em "situação"; quem saiu e quem entrou em "relator"; etiqueta ganha ou perdida em "etiquetas"; informe de parecer com o link, sem o conteúdo do parecer).
3. **Dado** um dia com arquivo de mudanças e zero eventos, **Então** o dia aparece como "sem mudanças". **Dado** um dia com linha de base, **Então** aparece "linha de base criada com N itens" e o motivo. **Dado** um arquivo que cobre mais de um dia, **Então** a página diz as duas datas do intervalo.
4. **Dado** que a coleta de um dia falhou e não há arquivo dele, **Então** a página não inventa eventos nem diz "sem mudanças" para esse dia. Se um arquivo posterior cobre esse dia (o intervalo vai do retrato anterior ao dele), a página diz em qual arquivo estão as mudanças.
5. **Dado** um dia com muitos eventos (posse, recomposição das comissões), **Então** nenhum evento se perde: todos continuam acessíveis na página, mesmo que a parte além de um teto por dia fique recolhida (PRODUCT.md, §5.6).
6. **Dado** que ainda não existe nenhum arquivo de mudanças (antes da primeira execução com a MUD), **Então** a seção diz que ainda não há mudanças registradas, e o resto da página funciona normalmente.

---

### User Story 5 - Baixar os dados e conhecer os limites (Priority: P3)

Quem quer conferir ou reaproveitar os dados baixa o JSON (`atual.json`) e o CSV da lista. No fim da página, o bloco "Limites" repete o que o produto não garante (PRODUCT.md, §8): dados do dia anterior, janela de um dia no motivo de entrada, "hoje no NOVO" quer dizer em exercício, partido na autoria como a Câmara registra, e que a página não é publicação oficial (o link oficial é onde vale conferir) (PRODUCT.md, §6.2).

**Why this priority**: dá rastreabilidade e honestidade à página, mas não bloqueia a leitura da lista.

**Independent Test**: gerar a página e conferir que os dois links de download apontam para arquivos publicados, que o CSV tem uma linha por item da lista com os campos acordados, e que o bloco "Limites" cobre os limites do PRODUCT.md, §8.

**Acceptance Scenarios**:

1. **Dado** a página publicada, **Então** há um link para baixar o `atual.json` e um para baixar o CSV, cada um com um nome estável.
2. **Dado** o CSV, **Então** ele tem exatamente uma linha por item da lista, com o mesmo conteúdo do `atual.json` nas colunas definidas em FR-017, separado por ";", em UTF-8 com BOM, abrindo corretamente no Excel em português com acentos preservados.
3. **Dado** o bloco "Limites", **Então** ele traz os limites conhecidos do PRODUCT.md, §8, em linguagem do leitor, sem prometer o que o produto não faz.
4. **Dado** a falha da última execução, **Então** os arquivos para baixar são os do último retrato bom, e a linha de atualização diz de quando eles são.

---

### Edge Cases

- **Retrato bom sem nenhum item.** A coleta já trata lista vazia como falha (PRODUCT.md, §7), então o `atual.json` não chega vazio à página. Se chegar (arquivo adulterado ou fora do contrato), a geração falha e a página anterior é mantida, em vez de publicar uma lista vazia (US2, cenário 6).
- **`status.json` ausente, ilegível ou incoerente com o `atual.json`.** A geração falha, com o nome do arquivo; nunca há página com a linha de atualização inventada.
- **Versão de formato desconhecida** em `atual.json`, `status.json` ou no arquivo de mudanças: a geração falha, com a versão encontrada, em vez de exibir campos que a página não entende.
- **Dia do meio de um arquivo que cobre vários dias** (o arquivo do dia seguinte a uma coleta que falhou cobre o intervalo inteiro, PRODUCT.md §5.6): o dia sem arquivo próprio, entre o retrato anterior e o do arquivo, diz "Sem arquivo próprio: as mudanças deste dia estão no arquivo de DD/MM", e não "sem arquivo".
- **Autor que não é deputado** (por exemplo, uma comissão especial, como no retrato real de 20/10/2026): `partido_na_data` vem vazio, e a página e o CSV mostram só o nome do autor, sem parênteses.
- **Arquivo de mudanças do dia do retrato ausente** (antes da primeira execução com a MUD): "mudanças desde o retrato anterior" diz "sem comparação ainda", nunca zero.
- **Item sem etiqueta** (candidato com relator indeterminado): aparece em "Todos" e nunca sob um chip de motivo que ele não tem.
- **Comissão sem item** no dia: o chip dela não é mostrado, como pede o DS ("esconda o chip"); o total dela continua nos números.
- **Muitos autores ou ementa muito longa**: o texto quebra dentro da largura da tela, sem rolar de lado, sem cortar informação.
- **Texto da Câmara com caracteres especiais** (`&`, `<`, aspas): aparece como texto, nunca interpretado como HTML.
- **Ementa ou nome com acentos**: preservados em todos os arquivos da página, inclusive no CSV.
- **Navegador com relógio errado**: a faixa de atraso depende do relógio do aparelho; o limite disso entra em "Limites".
- **Tela de 360 px**: nada exige rolagem horizontal da página.
- **Tema claro e escuro do DS**: a página respeita a preferência do sistema, e os dois temas mantêm contraste e foco legíveis.
- **Página dentro de um quadro incorporado** (EmbedFrame do portfólio): continua legível na largura do quadro, e não impede ser exibida em quadro.

## Requirements *(mandatory)*

### Functional Requirements

**Conteúdo (PRODUCT.md, §6.2)**

- **FR-001**: A página MUST ser HTML estático, gerado a partir dos dados versionados (`data/atual.json`, `data/status.json` e `data/mudancas/AAAA-MM-DD.json`), sem consultar a rede na geração.
- **FR-002**: A página MUST ter, de cima para baixo: a linha de atualização; a faixa de erro e a de atraso, quando couberem; os números; "Mudou nos últimos 7 dias"; a lista com os chips; o bloco "Limites"; "Baixar dados".
- **FR-003**: A linha de atualização MUST dizer a data dos dados da Câmara, a hora em que o arquivo foi gerado e a data e hora da última verificação, no horário de Brasília, no formato "Dados da Câmara de DD/MM (arquivo gerado às HHhMM) · verificado em DD/MM às HHhMM".
- **FR-004**: Os números MUST mostrar o total de itens, o total por comissão acompanhada e a quantidade de mudanças desde o retrato anterior, todos vindos dos arquivos de dados, sem recontagem por regra própria.
- **FR-005**: Cada item da lista MUST mostrar `Tipo número/ano` com link para a página oficial da Câmara, a ementa, os autores com o partido na data, as etiquetas, a situação, o relator atual com o partido de hoje, "nesta situação há N dias" e, quando houver, "apensado ao PL X" com link. Todo item MUST ter o link oficial (constitution, princípio II).
- **FR-006**: Itens com "principal não localizada" ou "relator indeterminado" MUST exibir essas marcas. Um item sem relator atual MUST dizer isso.
- **FR-007**: A lista MUST ser ordenada por "parado há", do maior para o menor, com desempate determinístico.
- **FR-008**: A página MUST NOT incluir, excluir ou reclassificar nenhum item por regra própria: a lista é exatamente a do `atual.json` (constitution, princípio II).
- **FR-009**: O bloco "Limites" MUST trazer os limites conhecidos do PRODUCT.md, §8, aplicáveis ao leitor da página, incluindo que a página não é publicação oficial.

**Falha visível (PRODUCT.md, §7 e D10; constitution, princípio III)**

- **FR-010**: Quando o `status.json` registra falha, a página MUST mostrar a faixa de erro "A atualização de DD/MM falhou (motivo). Dados de DD/MM.", com o dia da execução que falhou (`data_referencia`), o motivo do status e a data dos dados do último retrato bom, e MUST manter a lista do último retrato bom.
- **FR-011**: A página MUST mostrar, no navegador, a faixa de atraso quando a última verificação tiver mais de 30 horas. A faixa depende do relógio do leitor e dos dados da página; sem JavaScript ela não aparece, e isso é um limite declarado, não uma falha.
- **FR-012**: As faixas MUST comunicar o significado por texto, não por cor, e MUST ser percebidas por leitores de tela.
- **FR-013**: Se `atual.json`, `status.json` ou o arquivo de mudanças estiver ilegível, fora do contrato ou numa versão de formato desconhecida, a geração MUST falhar com o nome do arquivo e o motivo. Nenhuma falha de geração pode substituir a página publicada por uma vazia ou parcial.

**Filtros e funcionamento sem JS**

- **FR-014**: A lista MUST ter dois grupos de chips: Comissão (Todas e uma por comissão acompanhada, vindas dos dados) e Motivo (Todos · Autoria NOVO · Autor hoje no NOVO · Relatoria NOVO), com seleção única em cada grupo, combinados por "e". O resultado do filtro MUST ser anunciado em texto.
- **FR-015**: A página MUST funcionar sem JavaScript: todos os itens visíveis e na mesma ordem, e nenhum controle que dependa de JS parecendo funcional. O JS MUST ser usado só para filtrar e para a faixa de atraso.

**Mudanças de 7 dias**

- **FR-016**: A seção "Mudou nos últimos 7 dias" MUST agrupar por dia, do mais recente para o mais antigo, todos os eventos dos arquivos de mudanças dos 7 dias que terminam no dia do retrato, cada um com o link oficial e o conteúdo do tipo. MUST tratar dia sem eventos, linha de base, arquivo que cobre mais de um dia e dia sem arquivo, sem inventar eventos nem dizer "sem mudanças" onde não há arquivo. Nenhum evento pode se perder; um teto por dia só recolhe o excedente, não o remove.

**Download**

- **FR-017**: A página MUST oferecer o download do `atual.json` e de um CSV com uma linha por item da lista, em endereços estáveis. O CSV MUST usar ";" como separador, UTF-8 com marca de ordem de bytes (para abrir direto, com acentos, no Excel em português) e as colunas que a página exibe, na ordem: identificação, link oficial, ementa, comissão, situação, parado há (dias), etiquetas, autores (com o partido na data), relator atual (com o partido de hoje), apensado a, marcas ("principal não localizada", "relator indeterminado"). Listas (etiquetas, autores) MUST ir numa única célula, unidas por " | ". O CSV MUST NOT trazer dado que a página não mostra, e o conteúdo de cada campo MUST ser o do `atual.json`.

**Publicação**

- **FR-018**: A página, o `atual.json` e o CSV MUST ser publicados no GitHub Pages, com endereço estável que o portfólio possa incorporar. Repetir a publicação no mesmo dia, com os mesmos dados, MUST produzir a mesma página.
- **FR-018a**: A publicação MUST ser feita por um workflow próprio, disparado ao fim de toda execução da "Coleta diária", com sucesso ou falha, e também manualmente. Ele lê os arquivos já commitados e MUST NOT commitar nada gerado. Uma falha dele MUST NOT alterar o resultado da coleta nem da página já publicada, e MUST deixar o próprio workflow vermelho (constitution, princípio III).
- **FR-018b**: Ao publicar, esta feature MUST preencher `aviso.pagina_url` no `config.toml` com o endereço da página, para o "veja a página" do Telegram (AVI) apontar para ela.

**Qualidade da página (DS do portfólio, §6.2)**

- **FR-019**: A página MUST usar o Design System do portfólio com os tokens azuis e os FilterChips, e seguir as regras de acessibilidade, foco e área de toque do DS (alvo de toque de 44 px, foco visível, contraste, tema claro e escuro, sem rolagem lateral em 360 px). Textos em português do Brasil.
- **FR-020**: Todo texto vindo da Câmara MUST ser exibido como texto, sem ser interpretado como HTML.
- **FR-021**: A geração MUST ser coberta por testes com fixtures salvas e MUST NOT depender da rede (constitution, princípio IV). Segredos MUST NOT aparecer na página nem nos arquivos publicados (constitution, princípio VI).

### Key Entities *(include if feature involves data)*

- **Retrato**: o conteúdo do `atual.json` (`meta` e itens) de um dia. A página exibe o último retrato bom.
- **Status da execução**: o conteúdo do `status.json`: resultado, instante da verificação, data de referência, falha e o último retrato bom. Alimenta a linha de atualização e as faixas.
- **Item da lista**: uma proposição do retrato, com identificação, link oficial, ementa, autores, etiquetas, comissão, situação, "parado há", apensamento e relator atual.
- **Arquivo de mudanças do dia**: o conteúdo de `data/mudancas/AAAA-MM-DD.json`: eventos, ressalvas e linha de base. Alimenta os números e a seção dos 7 dias.
- **Evento**: uma mudança de um dos seis tipos (entrou, saiu, situação, relator, parecer, etiquetas), com link oficial.
- **Faixa**: aviso em texto no topo da página, de erro (quando a última execução falhou) ou de atraso (verificação com mais de 30 horas).
- **Chip**: filtro de comissão ou de motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% das páginas geradas dos retratos de teste, o número de itens listados é igual ao `total_itens` do retrato, cada item tem link oficial, e a ordem é a de "parado há" decrescente.
- **SC-002**: Com a última execução em falha, 100% das páginas geradas trazem a faixa de erro com o motivo e a data dos dados bons, e nenhuma traz lista diferente da do último retrato bom.
- **SC-003**: O leitor consegue dizer, olhando só o topo da página, de que dia são os dados e se a última atualização deu certo, sem rolar mais do que uma tela de celular.
- **SC-004**: Com JavaScript desligado, 100% dos itens aparecem e a página não mostra nenhum controle que não funcione.
- **SC-005**: Com JavaScript ligado, escolher qualquer combinação de chips mostra exatamente os itens que atendem à combinação, e a contagem anunciada é igual à de itens visíveis.
- **SC-006**: Todos os eventos dos arquivos de mudanças dos últimos 7 dias estão acessíveis na página; nenhum é perdido, mesmo num dia com centenas de eventos.
- **SC-007**: A página, em tela de 360 px, não exige rolagem horizontal, tem alvos de toque de pelo menos 44 px e mantém contraste legível nos temas claro e escuro.
- **SC-008**: Gerar a página duas vezes com a mesma entrada produz arquivos idênticos byte a byte.
- **SC-009**: Qualquer entrada inválida (arquivo ilegível, formato desconhecido) faz a geração falhar sem alterar a página já publicada.
- **SC-010**: Os testes da feature passam sem rede e a verificação completa do projeto (ruff e pytest) passa.

## Assumptions

- **O que a página lê.** Os três arquivos de dados já existem e têm contrato fixo (COL, AGE, MUD): `data/atual.json`, `data/status.json` e `data/mudancas/AAAA-MM-DD.json`. A página não recalcula nada: "parado há", etiquetas, relator e totais vêm como estão.
- **"Parado há" é o do retrato.** O número vem de `parado_ha_dias` do `atual.json`, calculado na coleta, e não é recalculado pela página. Combina com a linha de atualização, que diz de quando são os dados.
- **Últimos 7 dias** contam a partir do dia do último retrato bom, em dias de calendário de Brasília, usando os arquivos de mudanças que existirem. Dia sem arquivo não é preenchido.
- **Chips vêm dos dados.** Os chips de comissão saem da lista de comissões do `meta` do retrato (D1: trocar a configuração não exige código). Os chips de motivo são os três rótulos de etiqueta do PRODUCT.md. Chip de categoria sem item é ocultado, como pede o DS.
- **Desempate de ordem.** Itens com o mesmo "parado há" ficam em ordem estável por identificador da proposição.
- **Teto por dia nos eventos.** O valor do teto que recolhe o excedente de um dia com muitos eventos é definido no plano, sem remover nenhum evento.
- **Faixa de atraso.** O limite de 30 horas é o do PRODUCT.md, §6.2, e conta a partir de `verificado_em`. Sem JS, a faixa não aparece, o que o bloco "Limites" admite.
- **Onde fica o DS.** O DS do portfólio (`../Portfolio/design-system`) é a referência visual; como a página usa os tokens e o FilterChips sem depender do repositório Portfolio em tempo de execução é decisão do plano.
- **Link "Ir para a lista".** O primeiro elemento da página é um atalho, visível só com o foco, que leva da entrada direto à lista, sem passar pelo cabeçalho e pelas faixas. A spec não o pede; entra por FR-019 (acessibilidade e foco) e custa uma linha de HTML.
- **Tema.** A página segue a preferência de tema do sistema do leitor; a opção azul é a do produto (D9).
- **Fora desta feature.** A página de projeto no portfólio, com o EmbedFrame, é feita no repositório Portfolio. Esta feature só garante que a página tem endereço estável, é legível numa moldura incorporada e tem os links de download que o EmbedFrame pede.
- **Dependências.** Requer COL, AGE e MUD concluídas, o que já ocorre. Não depende da AVI; ela é quem passa a apontar para a página depois que `aviso.pagina_url` for preenchido.
