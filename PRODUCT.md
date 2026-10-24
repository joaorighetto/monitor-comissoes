# Monitor de comissões — produto

Documento de referência do produto. As specs do Spec Kit partem daqui e do [ROADMAP.md](ROADMAP.md). As fontes e os números que embasam as decisões estão em [docs/fontes.md](docs/fontes.md), com a sondagem de 17/10/2026 e a de pautas e prazos de 23/10/2026.

## 1. Problema

Um gabinete parlamentar precisa saber, toda semana, o que vai a voto nas comissões em que atua e o que nelas é de interesse do partido. Hoje isso exige abrir a ficha de cada proposição no portal da Câmara. Não há uma lista por comissão e partido, e a API pública não filtra por órgão. Também não basta olhar o "último relator" ou o partido registrado na autoria, porque ambos enganam: o relator pode já ter devolvido a matéria, e o autor pode ter mudado de partido.

O estoque do partido, porém, quase não se move: em 12 meses, metade dos processos do NOVO na CE e na CREDN não teve nenhuma tramitação. O que muda a semana de um gabinete é o que vai a voto: a pauta das reuniões deliberativas, quase sempre às quartas, e os prazos de emendas, que antecedem a pauta em semanas. Na pauta, o deputado vota tudo, não só o que tem ligação com o partido: dos 287 PL/PLP pautados na CE e na CREDN em 12 meses, só 5 tinham autor ou relator do NOVO.

## 2. Público

- **Principal:** o gabinete de um deputado federal do NOVO que toma posse em 1º/02/2027, especialmente o chefe de gabinete e a assessoria legislativa. Leem o resumo semanal no Telegram, quase sempre no celular.
- **Secundário:** quem visita o portfólio do autor (joaorighetto.github.io). Lá, a página pública aparece incorporada como peça de trabalho, e quem avalia o trabalho é sobretudo chefe de gabinete e deputado, também no celular.
- **Até a posse:** o produto roda com a bancada atual do NOVO, como protótipo funcional.

## 3. Perguntas que o produto responde

Toda semana: **o que vai a voto nas comissões acompanhadas, o que está perto de ir e o que foi decidido?**

- Quais reuniões deliberativas estão convocadas na semana, e o que está na pauta de cada uma? Quais itens têm ligação com o NOVO?
- Quais prazos de emendas estão abertos, e quais são ao substitutivo (o parecer já foi apresentado)?
- O que aconteceu com cada item pautado: aprovado, retirado de pauta, vista ou não apreciado?
- A pauta mudou ou a reunião caiu depois do aviso?

No inventário: **o que de interesse do NOVO está nas comissões acompanhadas, com quem está, há quanto tempo está parado e o que mudou?**

- Quais PL e PLP estão hoje na Comissão de Educação (CE) e na Comissão de Relações Exteriores e de Defesa Nacional (CREDN) e têm ligação com o NOVO?
- Por que cada um está na lista: autoria, autor que hoje é do NOVO, ou relatoria do NOVO?
- Em que situação está e há quantos dias?
- Quem é o relator atual e de que partido é hoje?
- O que entrou, o que saiu e por quê, o que mudou de situação ou de relator e onde houve parecer desde o último retrato?
- Os dados são de quando, e a última atualização deu certo?

## 4. Decisões tomadas

| # | Decisão | Por quê |
|---|---|---|
| D1 | **No inventário, tipos PL e PLP. Na pauta e nos prazos, PL, PLP, PEC, MSC e PDL são listados, e os REQ são contados** (os de autoria do NOVO são listados). As comissões ficam numa lista de configuração, hoje `["CE", "CREDN"]`, sem tela para editar | O PLP tem o mesmo fluxo e não custa nada a mais. Trocar de comissão em 2027 não exige código. No inventário, PDL e PEC trariam ruído: os PDL da CREDN são em geral acordos internacionais de autoria do Executivo, sem ligação com o partido. Na pauta é diferente: o deputado vota tudo, e as MSC (tratados) são a matéria própria da CREDN (38 em pauta em 12 meses). Os REQ (210 em pauta) são quase sempre aprovados em bloco (90%) e só pesam pela contagem |
| D2 | **"Do NOVO" é a união de três etiquetas**: `autoria NOVO`, `autor hoje no NOVO` e `relatoria NOVO`. O item mostra quais etiquetas tem. **No inventário, as etiquetas são o filtro de entrada. Na pauta e nos prazos, são só marca:** todos os itens aparecem, e os do NOVO vêm primeiro | O partido da autoria e o atual divergem: 4 itens são de deputados que entraram depois no NOVO, e 6 de quem saiu do partido. Com as etiquetas, o gabinete vê o motivo e pode filtrar por ele. Na posse, a nova bancada passa a contar sem mudança de código. Como filtro, a pauta ficaria quase vazia: só 5 dos 287 PL/PLP pautados em 12 meses tinham ligação com o NOVO |
| D3 | **Na relatoria vale o relator atual**: designado na comissão em que a proposição está e que não devolveu a matéria. Conta o partido de hoje | `uriUltimoRelator` continua apontando para o relator que devolveu sem manifestação (PL 937/2022) e para o relator de uma comissão anterior (PL 3514/2023). Para o gabinete, importa quem está com a matéria agora |
| D4 | **"Estar na comissão" é ter o órgão do último status na comissão. Os apensados seguem a proposição principal** (raiz da cadeia) | Metade do estoque são apensados, e o status deles congela, às vezes desde 2013. O parecer sobre a principal vale para eles. Em 8 casos, a principal já saiu da comissão |
| D5 | **O Telegram segue o ritmo das reuniões.** Toda segunda, sempre (também em semana sem reunião), vai a semana: reuniões convocadas, prazos abertos e mudanças do inventário. Na quinta, em semana com reunião realizada, vai o resultado. Na véspera de uma reunião, só se a pauta mudou, se ela foi convocada depois da segunda ou se foi cancelada. O erro vai no dia em que acontece | 37 das 42 reuniões deliberativas em 12 meses foram numa quarta, e houve reunião em só 19 (CE) e 20 (CREDN) das 52 semanas. Um resumo diário repetiria a mesma pauta e só teria novidade em 21% dos dias. O menor prazo de emendas medido durou 7 dias, então a mensagem de segunda pega todos os prazos ainda abertos. A mensagem fixa de segunda mantém o sinal de vida semanal; o envio continua rodando todo dia para avisar erro e coleta que não rodou |
| D6 | **O arquivamento não é feature.** Vira regra de domínio e motivo de saída ("arquivado, art. 105") | Desde a Resolução 33/2022, só cerca de 2 dos 54 itens estariam em risco, e o prazo de 31/01/2027 vence antes da posse. A forma de contar as legislaturas não foi confirmada |
| D7 | **A fonte do estoque e dos prazos é o lote completo da Câmara, baixado todo dia** desde o ano mínimo configurável (2003). A API entra para detalhar e é a **fonte da pauta**: `/orgaos/{id}/eventos` e `/eventos/{id}/pauta` | A API de proposições sem datas devolve só os últimos 30 dias, limita intervalos a 3 meses e não filtra por órgão. O lote tem o último status e o partido do autor. Uma fonte única é mais fácil de conferir do que duas reconciliadas. O lote não tem pauta; os eventos da API são filtrados por órgão e trazem a pauta inteira de cada reunião |
| D8 | **O histórico fica no Git:** commit diário de `data/atual.json`, mesmo sem mudanças, de `data/mudancas/AAAA-MM-DD.json`, da cópia `data/anterior.json` (§5.6), de `data/pautas/AAAA-MM-DD.json` (§5.8) e do registro da checagem da pauta `data/status-pauta.json` (§7), de `data/prazos/AAAA-MM-DD.json` (§5.10) e do registro de envio `data/envio.json` (§6.1) | Não precisa de banco nem de servidor. O diff de cada dia é conferível, e a falta de commit denuncia que a execução não rodou |
| D9 | **A página pública é HTML estático gerado em Python, com o Design System do portfólio** (tokens azuis, FilterChips). O portfólio a incorpora por EmbedFrame | A página funciona sem JS, como o DS exige. O EmbedFrame pede uma URL, a fonte com a data de coleta e um link de download |
| D10 | **Nenhuma falha publica uma lista nova.** O último retrato bom é mantido e o erro é anunciado na página e no Telegram | Uma lista vazia ou parcial publicada como verdade é o pior erro possível para quem decide a partir dela |

## 5. Regras de domínio

### 5.1 Universo

- Proposições com `siglaTipo` igual a `PL` ou `PLP`.
- Comissões da lista de configuração, comparadas pela sigla do órgão.
- Arquivos em lote lidos a partir do ano mínimo configurável, 2003 por padrão.
  - Justificativa: o art. 3º da Resolução 33/2022 arquivou em definitivo, ao fim da 56ª legislatura, o que tramitava havia 5 legislaturas completas.
  - Na sondagem, não havia PL anterior a 2003 na CE nem na CREDN.

### 5.2 Proposição de referência e apensados

- Se a proposição tem `uriPropPrincipal`, sobe-se a cadeia de apensação até a raiz. A **referência** é a raiz.
- Se não tem, a referência é a própria proposição.
- **Da referência vêm a comissão, a situação, o relator e o "parado há"** do item. O item mostra "apensado ao PL X".
- Se a raiz não for encontrada nos arquivos, ou se a cadeia tiver um ciclo:
  - o item aparece com o próprio status e a marca "principal não localizada";
  - o resumo semanal avisa. Nenhum item some em silêncio.

### 5.3 Estar na comissão

O item está na comissão quando o órgão do último status da referência (`ultimoStatus_siglaOrgao`) faz parte da lista.

Uma proposição distribuída a várias comissões passa por elas em sequência, e só conta como "na CE" quando chega a vez da CE. Os PL distribuídos que ainda não chegaram ficam para a feature futura CAM.

### 5.4 "Do NOVO": etiquetas

O item entra na lista se tiver ao menos uma etiqueta, ou se for candidato à relatoria NOVO com relator indeterminado (abaixo).

| Etiqueta | Regra | Fonte |
|---|---|---|
| `autoria NOVO` | Algum autor assinou como NOVO (`siglaPartidoAutor = NOVO`, que é o partido **na data da autoria**) | `proposicoesAutores-{ano}` |
| `autor hoje no NOVO` | Algum autor (`idDeputadoAutor`) está entre os deputados em exercício do NOVO no dia | `/api/v2/deputados?siglaPartido=NOVO` |
| `relatoria NOVO` | O **relator atual** da referência está entre os deputados em exercício do NOVO no dia | Tramitações da referência e a mesma lista de deputados |

**Relator atual** é o deputado designado relator na comissão em que a referência está, na passagem mais recente dela por essa comissão, e que não deixou de sê-lo depois disso. Deixam de ser relator a devolução da matéria sem manifestação, a substituição por nova designação e a saída do relator da comissão. Designação feita em passagem anterior da matéria por essa comissão não vale. Como a situação, o relator vale até a sequência do último status do lote: uma designação ou devolução lançada depois entra no dia seguinte (decidido pelo mantenedor em 18/10/2026). O campo `uriUltimoRelator` aponta para um candidato, que só é confirmado pelas tramitações. O partido considerado é o de hoje, não o da data da designação.

Quando as tramitações não permitem decidir quem é o relator atual (designação sem relator identificado, tipo de tramitação de relatoria desconhecido, ou a matéria já estar em outro órgão no instante do lote), o item leva a marca **"relator indeterminado"** e não ganha nem perde `relatoria NOVO`. Um candidato à relatoria NOVO (o relator registrado no último status é do NOVO) nessa situação entra na lista com a marca, para que nada suma em silêncio. Erro de rede, resposta malformada ou incompleta das APIs continua falhando a execução inteira (§7).

Exemplos verificados na sondagem:

| Item | Resultado | Por quê |
|---|---|---|
| PL 1843/2022 (Lucas Gonzalez) | dentro: `autoria NOVO` + `relatoria NOVO` | Assinou como NOVO; a relatora é Adriana Ventura |
| PL 3871/2024 (Luiz Lima) | dentro: `autor hoje no NOVO` | Assinado quando ele era do PL |
| PL 4501/2023 (Duarte Jr., PSB) | dentro: `relatoria NOVO` | O relator na CE é Luiz Lima |
| PL 937/2022 | fora | O relator do NOVO devolveu sem manifestação |
| PL 3514/2023 | fora | O relator do NOVO era da Comissão do Esporte, não da CREDN |
| PL 4047/2019 | fora | É apensado a um PL que já está na Comissão de Finanças e Tributação (CFT) |

### 5.5 Parado há

É o número de dias desde a data e hora do último status da referência (`ultimoStatus_dataHora`). É a ordem padrão da página: parado há mais tempo primeiro.

### 5.6 Mudança

O retrato de hoje é comparado com o anterior pela chave `id` da proposição.

| Evento | Quando | Motivo registrado |
|---|---|---|
| Entrou | O id não estava no retrato anterior | Chegou à comissão, ou ganhou uma etiqueta |
| Saiu | O id não está no retrato de hoje | Foi para outro órgão (qual); chegou a uma situação final (aprovado, transformado em norma, arquivado, com menção ao art. 105 quando for o caso); foi apensado a uma proposição fora da lista; ou perdeu as etiquetas |
| Situação | A situação da referência mudou, ou o item mudou de comissão sem sair da lista | De → para, e a comissão anterior |
| Relator | O relator atual mudou | Designado, devolveu ou foi substituído |
| Parecer | Houve tramitação de parecer do relator no período | Link para a ficha |
| Etiquetas | O item ganhou ou perdeu uma etiqueta e continua na lista | Qual etiqueta |

- Quando o número de sequência do último status muda, o evento traz **todas as tramitações desde o retrato anterior**, não só a última. O lote guarda só a última tramitação, e um mesmo dia pode ter várias.
- No primeiro retrato não há eventos: o resumo diz "linha de base criada com N itens".
- **Dias de muitas mudanças** são esperados na posse, em 1º/02/2027, e na recomposição anual das comissões. Nesses dias, o resumo detalha os eventos até um teto e termina com "e mais N, veja a página".

**Como o arquivo do dia é montado** (feature MUD; regras decididas pelo mantenedor em 18/10/2026):

- **Retrato anterior** é o último retrato bom de um dia anterior ao da execução. Como o `atual.json` é sobrescrito a cada execução, o produto guarda uma cópia rotativa, `data/anterior.json`. Reexecutar no mesmo dia compara com o mesmo retrato anterior e dá o mesmo arquivo. Se um dia ficou sem retrato (a coleta falhou), o arquivo do dia seguinte cobre o intervalo inteiro e diz as duas datas.
- **Linha de base** é o arquivo do dia sem eventos, com o total de itens e o motivo: "primeiro retrato" ou "formato anterior incompatível" (o retrato anterior está numa versão de formato que a comparação não entende). Um retrato anterior ilegível ou fora do contrato **não** vira linha de base: a execução falha, com o nome do arquivo.
- **Tramitações do evento:** vão da primeira depois da sequência do retrato anterior até a do último status de hoje. Quando a referência do item mudou, ou o item entrou, as sequências de proposições diferentes não se comparam, e valem as tramitações da referência de hoje desde o dia do lote anterior. Nunca passam da sequência do lote de hoje: o que a Câmara lançou depois aparece no dia seguinte.
- **Motivo de saída, quando mais de um vale:** o principal segue esta ordem: situação final, apensado a uma proposição fora da lista, foi para outro órgão, perdeu as etiquetas. Os demais ficam no detalhe do evento.
- **Situações finais** (só rotulam o motivo da saída, nunca incluem ou excluem item):

  | Rótulo | Situação da Câmara |
  |---|---|
  | arquivado (com "art. 105" se a tramitação de arquivamento do período cita o artigo) | Arquivada |
  | transformado em norma jurídica | Transformado em Norma Jurídica |
  | aprovado, segue ao Senado | Aguardando Apreciação pelo Senado Federal; Aguardando Envio ao Senado Federal; Enviada ao Senado Federal |
  | encerrado | Vetado totalmente; Recusado; Retirado pelo(a) Autor(a); Devolvida ao(à) Autor(a); Transformado em nova proposição; Perdeu a Eficácia; Tramitação Finalizada |

  Uma situação fora da tabela não é erro: o motivo vira "foi para outro órgão", e o destino traz a situação.
- **Entrou:** "chegou à comissão" se a passagem mais recente da referência pela comissão começou no dia do lote anterior ou depois; senão "ganhou etiqueta", dizendo qual; se o item não tem etiqueta (candidato com relator indeterminado), "não determinado". Passagem tem a definição da relatoria (§5.4): a Mesa, a CCP e o Plenário nunca iniciam passagem, então uma ida e volta pela Mesa não é chegada nova.
- **Parecer** é a tramitação "Parecer do(a) Relator(a)" no órgão da comissão do item. Se o item mudou de comissão no intervalo, vale também o parecer dado na comissão anterior (decidido pelo mantenedor em 18/10/2026). A leitura e a aprovação do parecer não geram evento.
- **Item que muda de comissão e continua na lista** (por exemplo, da CE para a CREDN) gera um evento de **situação**, que traz a comissão anterior mesmo quando o texto da situação não mudou (decidido pelo mantenedor em 18/10/2026).
- **Relator indeterminado** em um dos retratos não gera evento de relator. O arquivo registra que a comparação de relator não foi possível para o item.
- **Sem teto:** o arquivo registra todos os eventos. O teto e o "e mais N" são do resumo e da página.
- Uma mudança de sequência que não altera situação, relator, parecer nem etiquetas não gera evento (as tramitações só acompanham os eventos). Registrar, por exemplo, pedido de vista e retirada de pauta é a feature futura MOV.

### 5.7 Arquivamento (RICD, art. 105)

Texto vigente e links oficiais em [docs/fontes.md](docs/fontes.md#4-arquivamento-ao-fim-da-legislatura-ricd-art-105).

- Ao fim da legislatura, os PL e PLP são arquivados **apenas se já tramitaram por 3 legislaturas completas** (art. 105, VI, conforme a Resolução 33/2022, em vigor desde 1º/02/2023). Há outras exceções, como as proposições de iniciativa popular, os projetos de código e as aprovadas pela Câmara e revisadas pelo Senado.
- O desarquivamento a pedido do autor foi revogado.
- A 57ª legislatura termina em 31/01/2027.
- O produto não prevê arquivamento. Quando ele acontece, o item sai da lista com o motivo "arquivado, art. 105".
- **Dúvida aberta:** não foi confirmado como a Câmara conta as "3 legislaturas completas", nem se conta a legislatura de apresentação e os períodos em que a proposição ficou arquivada.

### 5.8 Pauta (feature PAU)

- **Reunião:** evento de uma comissão da lista com `descricaoTipo` igual a "Reunião Deliberativa". Audiências públicas, seminários e outros eventos não entram.
- **Janela:** as reuniões convocadas para os 7 dias seguintes ao dia da checagem e as realizadas nos 7 dias anteriores. Reunião cancelada continua na janela, com a situação "cancelada".
- **Item e proposição do item:** cada item da pauta do evento. A proposição do item é `proposicaoRelacionada_`, quando existe (o item pode ser o parecer, PRL, e a relacionada, o projeto). Quando não existe, é `proposicao_`. Exceção: quando a `proposicao_` é REQ, a proposição do item é ela, inclusive para a autoria e o resultado, seja qual for a relacionada. Isso cobre o requerimento que adita outro (o REQ 70/2026 CE inclui convidados na audiência pedida pelo REQ 63/2026 CE) e o que se refere a um projeto (o REQ 17/2026 CE, aprovado em 15/04/2026, vem com o PL 1778/2020 como relacionada, e o PL não foi votado). Em 12 meses, 28 itens de REQ tinham relacionada: 15 com outro REQ, 10 com PL e 3 com PEC (decidido pelo mantenedor em 24/10/2026).
- **O que é listado (D1):** os itens cuja proposição é PL, PLP, PEC, MSC ou PDL. Os REQ são contados, e os de autoria do NOVO são listados. Os demais tipos (SOR, por exemplo) são contados como "outros".
- **Etiquetas (D2), só como marca:**
  - `autoria NOVO` e `autor hoje no NOVO`: como no §5.4, pelos autores da proposição do item.
  - `autoria não verificada`: a proposição do item não está no último lote bom (por exemplo, um REQ apresentado depois da geração do lote). O item fica sem as duas etiquetas de autoria e leva essa marca. Um REQ com essa marca é listado, e não só contado, para que um REQ do NOVO não suma na contagem. Com o lote seguinte, a marca some (decidido pelo mantenedor em 24/10/2026).
  - `relatoria NOVO`: o relator do item na pauta (`relator.id`) está entre os deputados em exercício do NOVO no dia.
  - `leva apensado do NOVO`: a proposição do item é a referência (§5.2) de um ou mais itens do inventário. O apensado não aparece sozinho na pauta, porque vai junto com a principal (RICD, art. 143, III). A marca lista cada apensado, com `Tipo número/ano`, link oficial e as etiquetas dele. A raiz é a do último `atual.json` bom, então uma apensação feita depois do lote ainda não conta. Em 12 meses, isso aconteceu uma vez: o PL 5432/2016, pautado na CE em 15/04/2026, levava o PL 3701/2020.
  - Os itens com etiqueta ou com essa marca vêm primeiro.
- **Pauta alterada:** a pauta de uma reunião convocada mudou quando, em relação à última checagem registrada:
  - um item entrou ou saiu;
  - a data ou a hora mudou;
  - a reunião foi cancelada;
  - a reunião foi retirada da agenda (o evento deixou de existir na fonte sem ter sido cancelado).

  Uma reunião que some da consulta da janela é buscada pelo identificador: se a data mudou para fora da janela, vale "a data ou a hora mudou"; se foi cancelada, "cancelada"; se o evento não existe mais, "retirada da agenda" (decidido pelo mantenedor em 24/10/2026). A ordem dos itens não conta. Cada alteração é registrada uma única vez, mesmo com várias checagens no dia (constituição, princípio V).
- **Checagem:** mais de uma vez por dia, com três garantias:
  - toda mensagem do Telegram (§6.1) usa uma checagem do mesmo dia, feita antes do envio;
  - o resultado de uma reunião (§5.9) aparece na página no próprio dia, por uma checagem depois do horário das reuniões (em 12 meses, 42 das 47 reuniões deliberativas começaram entre 9h e 11h40);
  - uma checagem no fim do dia pega a pauta anunciada ao fim da reunião anterior (RICD, art. 47, parágrafo único).

  Os horários ficam no plano da PAU. O arquivo do dia, `data/pautas/AAAA-MM-DD.json`, guarda a última checagem e as alterações registradas no dia.
- **Arquivo próprio:** a pauta não entra em `data/mudancas/`. Os seis tipos de evento do §5.6 não mudam.

### 5.9 Resultado da reunião (feature PAU)

O resultado de um item de reunião realizada vem do texto livre `situacaoItem`. O texto original sempre acompanha o rótulo, para que o resultado possa ser conferido. Em 12 meses, a regra abaixo deu rótulo a 509 dos 511 PL/PLP pautados; os 2 restantes caíram em "outro".

O primeiro rótulo que casar vale:

| Ordem | Rótulo | Quando |
|---|---|---|
| 1 | retirado de pauta | O texto diz "Retirado de pauta" ou "Retirada de pauta", **exceto** em "Requerimento de Retirada de Pauta" |
| 2 | vista | O texto menciona vista |
| 3 | aprovado | "Aprovado" ou "Aprovada" |
| 4 | rejeitado | "Rejeitado" ou "Rejeitada" |
| 5 | não apreciado | Adiado, não apreciado, não deliberado, ou a reunião foi encerrada antes do item |
| 6 | sem registro | Texto vazio |
| 7 | outro | Nenhum dos anteriores |

### 5.10 Prazo de emendas (feature PRZ)

- **Abertura:** tramitação `350` ("Abertura de Prazo") num órgão da lista, com despacho que menciona emendas. É "ao substitutivo" quando o despacho menciona substitutivo; senão, "ao projeto". O prazo ao substitutivo é aberto depois do parecer. Em 12 meses, a primeira pauta veio uma mediana de 26 dias depois dele.
- **Encerramento:** a primeira tramitação `600` ("Encerramento de Prazo") no mesmo órgão, depois da abertura, com despacho que menciona emendas. A `600` também encerra prazo de vista, que não conta. "Com emenda" quando o despacho diz "Foi apresentada" ou "Foram apresentadas".
- **Detecção:**
  - A abertura é vista no lote quando é o último status da proposição (`ultimoStatus_idTipoTramitacao` = `350`) e é confirmada pelas tramitações.
  - Cada prazo aberto é acompanhado pelas tramitações até o encerramento.
  - Os tipos são os da pauta (D1), e as etiquetas são marca (D2), como no §5.8.
- **Fim do prazo:** o prazo é contado em sessões ("5 sessões a partir de DD/MM"), e o produto não prevê quando ele acaba. Mostra só a data de abertura e, quando houver, a de encerramento.
- **Arquivo:** `data/prazos/AAAA-MM-DD.json`, com os prazos abertos no dia e os encerrados desde o arquivo anterior.

## 6. Comportamento das saídas

### 6.1 Resumo no Telegram (feature SEM; substitui o resumo diário da AVI)

- O envio roda todo dia, por volta das 7h de Brasília (07:17), num workflow próprio, depois da coleta (03:37) e da publicação da página. Só manda mensagem nos casos abaixo. O registro `data/envio.json` guarda o último dia de cada tipo (semanal, resultado, véspera, erro), para que nenhum tipo saia duas vezes no mesmo dia.
- **Semanal: toda segunda, sempre.** Tem três partes:
  - as reuniões convocadas da semana, por comissão, com dia, hora e número de itens; os itens do NOVO primeiro (com etiqueta ou com a marca "leva apensado do NOVO", §5.8), com as etiquetas e os apensados; os demais itens listados em linha compacta (`Tipo número/ano · relator Nome (PARTIDO)`); e os REQ contados;
  - os prazos de emendas abertos, os ao substitutivo primeiro, cada um com "desde DD/MM";
  - as mudanças do inventário dos últimos 7 dias, agrupadas por tipo (§5.6).

  Em semana sem reunião e sem prazo: "sem reunião convocada · N prazos abertos · inventário: N itens, sem mudanças".
- **Resultado: na quinta, só em semana com reunião realizada.** Cada PL, PLP, PEC, MSC ou PDL pautado com o rótulo do §5.9 (aprovado, retirado de pauta, vista, não apreciado), os do NOVO primeiro.
- **Véspera: só quando há o que avisar.** Na manhã anterior a uma reunião convocada, se a pauta foi alterada (§5.8) desde a mensagem de segunda, se a reunião foi convocada depois dela ou se foi cancelada. Diz o que entrou, o que saiu e o que mudou de data ou hora.
- Cada mensagem tem o link oficial de cada item e cabe em 4.096 caracteres. O excedente é resumido como "e mais N, veja a página".
- **Erro: no dia.** Em caso de falha, vai uma mensagem de erro com o motivo e a data dos últimos dados bons. Se a coleta do dia não rodou, a mensagem é "a coleta de hoje não rodou", com a data dos últimos dados bons.

### 6.2 Página pública

De cima para baixo:

1. **Linha de atualização**: "Dados da Câmara de DD/MM (arquivo gerado às HHhMM) · verificado em DD/MM às HHhMM".
2. **Faixa de erro**, quando a última execução falhou ("A atualização de DD/MM falhou (motivo). Dados de DD/MM.": o primeiro DD/MM é o dia da execução que falhou; o segundo, a data dos últimos dados bons). **Faixa de atraso**, calculada no navegador quando a verificação tem mais de 30 horas. O significado vem do texto, porque o DS não tem cores de status.
3. **Números**: total de itens, total por comissão e mudanças desde o retrato anterior. Se o arquivo de mudanças do dia do retrato não existe (antes da primeira execução com a MUD), "mudanças desde o retrato anterior" diz "sem comparação ainda", nunca zero.
4. **"Mudou nos últimos 7 dias"**: os eventos agrupados por dia, com link oficial. São os 7 dias de calendário que terminam no dia do retrato. Dia sem arquivo diz "Sem arquivo de mudanças neste dia". Os 20 primeiros eventos de cada dia ficam abertos e o resto fica recolhido, sem perder nenhum.
5. **Lista** com dois grupos de FilterChips:
   - Comissão: Todas · CE · CREDN.
   - Motivo: Todos · Autoria NOVO · Autor hoje no NOVO · Relatoria NOVO.
6. **Cada item** mostra:
   - `Tipo número/ano` com link para a página oficial;
   - ementa;
   - autores com o partido na data (só o nome, quando o autor não tem partido, como uma comissão especial);
   - etiquetas;
   - situação;
   - relator atual com o partido de hoje;
   - "nesta situação há N dias";
   - "apensado ao PL X", quando for o caso.
7. **Bloco "Limites"**, com os limites da seção 8 que valem para quem lê a lista: os dados são do dia anterior; o motivo de entrada tem janela de um dia; só a última tramitação de cada retrato vem do lote; "hoje no NOVO" quer dizer em exercício; o partido na autoria é o que a Câmara registra; a página não é publicação oficial. Acrescenta-se o limite da faixa de atraso, que é calculada no navegador, com o relógio do aparelho, e não aparece sem JavaScript. Ficam fora o arquivamento e o volume da coleta, que não afetam a leitura da lista.
8. **Baixar dados**: `atual.json` e CSV.

A página funciona sem JavaScript: os chips só filtram, e sem JS todos os itens aparecem. Usa o DS do portfólio: tokens azuis, FilterChips e as regras de acessibilidade, foco e área de toque.

**Publicação.** A página é gerada em Python dos arquivos versionados e publicada no GitHub Pages por um workflow próprio, disparado ao fim de toda execução da coleta (com sucesso ou falha), para a faixa de erro aparecer no mesmo dia. Nada gerado é commitado. Se a geração falhar, a página anterior continua publicada e o workflow fica vermelho.

### 6.3 Pauta e prazos na página (feature PGP)

Duas seções entram entre os **Números** (item 3 do §6.2) e **"Mudou nos últimos 7 dias"** (item 4):

1. **"Próximas reuniões"**:
   - as reuniões da janela do §5.8, por dia, com comissão, hora e situação (convocada ou cancelada);
   - em cada reunião, os itens listados (D1), os do NOVO primeiro (§5.8) e com as etiquetas ou a marca "leva apensado do NOVO", cada um com link oficial e relator;
   - os REQ e os outros tipos contados;
   - as realizadas nos últimos 7 dias, com o resultado de cada item (§5.9);
   - uma linha que diz quando a pauta foi checada pela última vez ("pauta verificada em DD/MM às HHhMM"). Ela é separada da linha de atualização do estoque, porque as duas fontes têm horários diferentes.
2. **"Prazos de emendas abertos"**: cada prazo do §5.10, ao substitutivo primeiro, com "aberto em DD/MM", etiquetas e link oficial.

A página é publicada de novo ao fim de cada checagem da pauta, além do fim da coleta (§6.2), para o resultado aparecer no dia da reunião. Ninguém prevê data de votação nem fim de prazo (§9). As duas seções funcionam sem JavaScript, e "Baixar dados" passa a oferecer também os arquivos de pauta e de prazos do dia.

## 7. Falhar de forma visível

**Regra geral:** nenhuma falha publica uma lista nova. O último `atual.json` bom fica como está, a falha é registrada em `data/status.json`, e a página e o Telegram a anunciam. A pauta tem fonte própria (D7), então a falha dela só barra a pauta.

| Falha | Tratamento |
|---|---|
| Fonte fora do ar ou lenta, depois de novas tentativas | Falha anunciada, com o motivo |
| Formato alterado (coluna ausente, tipo inesperado) | Falha com "formato alterado: coluna X" |
| Arquivos desatualizados (`Last-Modified` com mais de cerca de 36 horas) | Falha com "a Câmara não atualizou os arquivos" |
| Arquivos gerados em momentos diferentes (mais de 6 horas entre o `Last-Modified` mais antigo e o mais novo) | Falha com "os arquivos da Câmara foram gerados em momentos diferentes". A Câmara regenera todos os arquivos todo dia; uma diferença grande indica que a coleta pegou a regeneração no meio |
| Estoque implausível: variação de mais de 20% em um dia ou estoque vazio | Falha. Provavelmente o arquivo veio truncado |
| Lista filtrada vazia | Sempre tratada como falha |
| Erro na API (deputados ou tramitações) | A execução inteira falha. Não há publicação parcial |
| Erro na API de eventos ou de pauta, ou pauta malformada | Falha só a checagem da pauta. O último arquivo de pauta bom fica como está, a falha é avisada no Telegram no mesmo dia, e a seção da pauta na página diz que não foi atualizada desde a última checagem boa, com data e hora. A pauta antiga nunca aparece como atual (constituição, princípio III). O estoque e o inventário não são afetados |
| Falha no envio ao Telegram | A página já foi atualizada. O workflow fica vermelho e o GitHub manda e-mail ao dono |
| A execução não roda | A página mostra "dados atrasados" depois de 30 horas, e o envio das 7h, que roda todo dia, avisa "a coleta de hoje não rodou". Se o próprio envio não rodar, a falta da mensagem de segunda é o sinal. Num outro dia da semana, nada avisa até a segunda seguinte |

## 8. Limites conhecidos

- **Dados do dia anterior.** O lote é gerado por volta das 2h de Brasília, então o que acontece num dia só aparece nos dados do dia seguinte. A pauta é a exceção: vem da API e tem o horário da própria checagem.
- **A pauta muda até a reunião.** Itens "sobre a mesa" entram na própria reunião, e a pauta pode mudar depois da última checagem. Os avulsos saem até 24 horas antes da reunião (RICD, art. 47), então numa reunião às 10h a pauta pode fechar depois da mensagem de véspera das 7h. A pauta de uma reunião cancelada pode ter sido substituída por outra reunião.
- **O resultado vem de texto livre.** O rótulo do §5.9 é uma classificação do produto; o texto original acompanha o rótulo.
- **Relator na pauta e relator atual.** Na pauta, `relatoria NOVO` vem do relator do item na pauta (§5.8). No inventário, vem do relator atual pelas tramitações (§5.4). Os dois podem divergir, por exemplo, se a designação mudou depois da pauta.
- **O prazo de emendas é contado em sessões.** O produto não diz quando ele acaba.
- **O lote só mostra a abertura de prazo que for o último status.** Se outra tramitação for lançada antes da geração do lote, a abertura não aparece nele. Em 12 meses, isso foi possível em 10 dos 170 prazos medidos.
- **O aviso de prazo é semanal.** Um prazo aberto numa terça aparece na segunda seguinte. O menor prazo medido em 12 meses durou 7 dias, então ainda estava aberto.
- **O motivo de entrada tem janela de um dia.** O produto não guarda o estado de ontem de quem estava fora da lista, então "chegou à comissão" compara datas, e muitas tramitações só trazem a data. Um item que chegou à comissão na madrugada do dia do lote anterior, antes da geração dele, pode sair como "chegou à comissão" em vez de "ganhou etiqueta".
- **A última tramitação de cada retrato.** O lote só guarda o último status. As tramitações intermediárias são recuperadas pela API, mas apenas para os itens da lista.
- **"Hoje no NOVO" quer dizer em exercício.** Um deputado licenciado ou afastado some da lista de deputados em exercício do NOVO, e os itens dele perdem as etiquetas `autor hoje no NOVO` e `relatoria NOVO` enquanto ele estiver fora. Essa perda aparece no resumo como evento.
- **O partido na autoria é o que a Câmara registra.** Há sobreposições curtas entre partidos na troca, como Luiz Lima entre março e abril de 2025.
- **Sobre o arquivamento, a contagem das legislaturas não foi confirmada.** Por isso o produto não prevê arquivamentos.
- **Não é publicação oficial.** Todo item tem link para a página oficial da Câmara, que é onde vale conferir.
- **Volume da coleta.** Cerca de 1 GB por dia, em 48 arquivos: 24 anos (2003 a 2026) vezes 2 tipos. A Câmara regenera todos diariamente, por isso o download condicional não ajuda.

## 9. Fora de escopo

**Futuro** (no [ROADMAP.md](ROADMAP.md), depois do núcleo):

- **CAM, "a caminho":** PL/PLP distribuídos à CE ou à CREDN que ainda estão em outra comissão.
- **GAB, etiqueta do gabinete:** autoria ou relatoria do deputado do gabinete, depois da posse.

A pauta (PAU), os prazos de emendas (PRZ), o resumo semanal (SEM) e a pauta na página (PGP) deixaram de ser futuro e fazem parte do núcleo (§5.8 a §5.10, §6.1 e §6.3).

**Não planejado:**

- **Previsão de votação, de chance de aprovação ou do fim de um prazo.** Não dá para conferir com fonte oficial. O produto informa que o prazo ao substitutivo foi aberto, mas não diz "vai a voto em N dias".
- **Apresentar emendas ou acompanhar o conteúdo delas.** O produto informa o prazo e se houve emenda.
- **Chatbot, bot do Telegram com comandos, resumo de ementa por IA.** O bot só envia mensagens. Sem servidor, e todo texto vem da fonte.
- **Login, vários gabinetes, preferências por usuário.**
- **Senado Federal. REQ, PDL, PEC e outros tipos no inventário.** Na pauta e nos prazos, eles entram como manda a D1.
- **Novas comissões como feature.** Basta editar a lista de configuração.
- **Selo, alerta ou lista de risco de arquivamento** (decisão D6).
- **Histórico de mais de 7 dias na página.** O Git guarda tudo.
- **Conteúdo dos pareceres.** O resumo informa que houve parecer e dá o link.

## 10. Restrições técnicas

- Python 3.13 com uv.
- Arquivos JSON versionados no Git como histórico. Sem servidor nem banco.
- GitHub Actions como agendador e GitHub Pages para a página, publicada por workflow próprio ao fim da coleta (§6.2). A pauta é checada mais de uma vez por dia, com as garantias do §5.8; os horários ficam no plano da PAU, e a página é publicada de novo depois de cada checagem (§6.3).
- Segredos (token do bot e chat_id do Telegram) só em variáveis de ambiente e secrets do GitHub. O `.env` local fica fora do Git.
- Todo item conferível, com link para a página oficial da proposição.
- Visual: o Design System do portfólio (`../Portfolio/design-system`), com tokens azuis e os componentes FilterChips e, do lado do portfólio, EmbedFrame. Os ativos do DS (tokens, CSS dos chips e fontes) são copiados para `src/monitor_comissoes/pagina/estatico/`, porque a geração roda no GitHub Actions, onde o repositório do portfólio não existe.
