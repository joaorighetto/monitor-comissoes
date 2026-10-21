# Monitor de comissões — produto

Documento de referência do produto. As specs do Spec Kit partem daqui e do [ROADMAP.md](ROADMAP.md). As fontes e os números que embasam as decisões estão em [docs/fontes.md](docs/fontes.md), com a sondagem de 17/10/2026.

## 1. Problema

Um gabinete parlamentar precisa saber, todo dia, o que é de interesse do partido nas comissões em que atua. Hoje isso exige abrir a ficha de cada proposição no portal da Câmara. Não há uma lista por comissão e partido, e a API pública não filtra por órgão. Também não basta olhar o "último relator" ou o partido registrado na autoria, porque ambos enganam: o relator pode já ter devolvido a matéria, e o autor pode ter mudado de partido.

## 2. Público

- **Principal:** o gabinete de um deputado federal do NOVO que toma posse em 1º/02/2027, especialmente o chefe de gabinete e a assessoria legislativa. Leem o resumo diário no Telegram, quase sempre no celular.
- **Secundário:** quem visita o portfólio do autor (joaorighetto.github.io). Lá, a página pública aparece incorporada como peça de trabalho, e quem avalia o trabalho é sobretudo chefe de gabinete e deputado, também no celular.
- **Até a posse:** o produto roda com a bancada atual do NOVO, como protótipo funcional.

## 3. Perguntas que o produto responde

Todo dia: **o que de interesse do NOVO está nas comissões acompanhadas, com quem está, há quanto tempo está parado e o que mudou desde ontem?**

- Quais PL e PLP estão hoje na Comissão de Educação (CE) e na Comissão de Relações Exteriores e de Defesa Nacional (CREDN) e têm ligação com o NOVO?
- Por que cada um está na lista: autoria, autor que hoje é do NOVO, ou relatoria do NOVO?
- Em que situação está e há quantos dias?
- Quem é o relator atual e de que partido é hoje?
- O que entrou, o que saiu e por quê, o que mudou de situação ou de relator e onde houve parecer desde o último retrato?
- Os dados são de quando, e a última atualização deu certo?

## 4. Decisões tomadas

| # | Decisão | Por quê |
|---|---|---|
| D1 | **Tipos PL e PLP.** As comissões ficam numa lista de configuração, hoje `["CE", "CREDN"]`, sem tela para editar | O PLP tem o mesmo fluxo e não custa nada a mais. Trocar de comissão em 2027 não exige código. PDL e PEC trariam ruído: os PDL da CREDN são em geral acordos internacionais de autoria do Executivo |
| D2 | **"Do NOVO" é a união de três etiquetas**: `autoria NOVO`, `autor hoje no NOVO` e `relatoria NOVO`. O item mostra quais etiquetas tem | O partido da autoria e o atual divergem: 4 itens são de deputados que entraram depois no NOVO, e 6 de quem saiu do partido. Com as etiquetas, o gabinete vê o motivo e pode filtrar por ele. Na posse, a nova bancada passa a contar sem mudança de código |
| D3 | **Na relatoria vale o relator atual**: designado na comissão em que a proposição está e que não devolveu a matéria. Conta o partido de hoje | `uriUltimoRelator` continua apontando para o relator que devolveu sem manifestação (PL 937/2022) e para o relator de uma comissão anterior (PL 3514/2023). Para o gabinete, importa quem está com a matéria agora |
| D4 | **"Estar na comissão" é ter o órgão do último status na comissão. Os apensados seguem a proposição principal** (raiz da cadeia) | Metade do estoque são apensados, e o status deles congela, às vezes desde 2013. O parecer sobre a principal vale para eles. Em 8 casos, a principal já saiu da comissão |
| D5 | **Um resumo diário único no Telegram, enviado sempre**, mesmo sem mudanças. Cobre entrada, saída, situação, relator, parecer e etiquetas | Assim, o silêncio nunca quer dizer "parou de funcionar". Uma mensagem por dia não vira ruído |
| D6 | **O arquivamento não é feature.** Vira regra de domínio e motivo de saída ("arquivado, art. 105") | Desde a Resolução 33/2022, só cerca de 2 dos 54 itens estariam em risco, e o prazo de 31/01/2027 vence antes da posse. A forma de contar as legislaturas não foi confirmada |
| D7 | **A fonte do estoque é o lote completo da Câmara, baixado todo dia** desde o ano mínimo configurável (2003). A API entra só para detalhar | A API sem datas devolve só os últimos 30 dias, limita intervalos a 3 meses e não filtra por órgão. O lote tem o último status e o partido do autor. Uma fonte única é mais fácil de conferir do que duas reconciliadas |
| D8 | **O histórico fica no Git:** commit diário de `data/atual.json`, mesmo sem mudanças, de `data/mudancas/AAAA-MM-DD.json`, da cópia `data/anterior.json` (§5.6) e do registro de envio `data/envio.json` (§6.1) | Não precisa de banco nem de servidor. O diff de cada dia é conferível, e a falta de commit denuncia que a execução não rodou |
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
  - o resumo diário avisa. Nenhum item some em silêncio.

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

## 6. Comportamento das saídas

### 6.1 Resumo diário (Telegram)

- Uma mensagem por dia, por volta das 7h de Brasília (07:17), para um grupo do gabinete. É enviada por um workflow próprio, depois da coleta (03:37) e da publicação da página, e só uma vez por dia: o registro `data/envio.json` guarda o último dia de cada tipo (normal ou erro).
- **Sempre enviada.** Sem mudanças: "sem mudanças · N itens · dados de DD/MM".
- Os eventos vêm agrupados por comissão, cada um com o link oficial da proposição.
- Cabe em uma única mensagem (4.096 caracteres). O excedente é resumido como "e mais N, veja a página"; enquanto não houver página, "veja o arquivo do dia", com o link do `data/mudancas/AAAA-MM-DD.json`. Sob o teto, os eventos entram alternando entre as comissões.
- Em caso de falha, vai uma mensagem de erro com o motivo e a data dos últimos dados bons. Se a coleta do dia não rodou, a mensagem é "a coleta de hoje não rodou", com a data dos últimos dados bons.

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
7. **Bloco "Limites"**, com o conteúdo da seção 8.
8. **Baixar dados**: `atual.json` e CSV.

A página funciona sem JavaScript: os chips só filtram, e sem JS todos os itens aparecem. Usa o DS do portfólio: tokens azuis, FilterChips e as regras de acessibilidade, foco e área de toque.

**Publicação.** A página é gerada em Python dos arquivos versionados e publicada no GitHub Pages por um workflow próprio, disparado ao fim de toda execução da coleta (com sucesso ou falha), para a faixa de erro aparecer no mesmo dia. Nada gerado é commitado. Se a geração falhar, a página anterior continua publicada e o workflow fica vermelho.

## 7. Falhar de forma visível

**Regra geral:** nenhuma falha publica uma lista nova. O último `atual.json` bom fica como está, a falha é registrada em `data/status.json`, e a página e o Telegram a anunciam.

| Falha | Tratamento |
|---|---|
| Fonte fora do ar ou lenta, depois de novas tentativas | Falha anunciada, com o motivo |
| Formato alterado (coluna ausente, tipo inesperado) | Falha com "formato alterado: coluna X" |
| Arquivos desatualizados (`Last-Modified` com mais de cerca de 36 horas) | Falha com "a Câmara não atualizou os arquivos" |
| Arquivos gerados em momentos diferentes (mais de 6 horas entre o `Last-Modified` mais antigo e o mais novo) | Falha com "os arquivos da Câmara foram gerados em momentos diferentes". A Câmara regenera todos os arquivos todo dia; uma diferença grande indica que a coleta pegou a regeneração no meio |
| Estoque implausível: variação de mais de 20% em um dia ou estoque vazio | Falha. Provavelmente o arquivo veio truncado |
| Lista filtrada vazia | Sempre tratada como falha |
| Erro na API (deputados ou tramitações) | A execução inteira falha. Não há publicação parcial |
| Falha no envio ao Telegram | A página já foi atualizada. O workflow fica vermelho e o GitHub manda e-mail ao dono |
| A execução não roda | A página mostra "dados atrasados" depois de 30 horas, e o resumo das 7h avisa "a coleta de hoje não rodou". Se o próprio envio não rodar, a falta do resumo diário é o sinal |

## 8. Limites conhecidos

- **Dados do dia anterior.** O lote é gerado por volta das 2h de Brasília, então o que acontece num dia aparece no resumo do dia seguinte.
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
- **PAU, pauta:** inclusão em pauta de reunião deliberativa.
- **GAB, etiqueta do gabinete:** autoria ou relatoria do deputado do gabinete, depois da posse.

**Não planejado:**

- **Previsão de votação ou de chance de aprovação.** Não dá para conferir com fonte oficial.
- **Chatbot, bot do Telegram com comandos, resumo de ementa por IA.** O bot só envia mensagens. Sem servidor, e todo texto vem da fonte.
- **Login, vários gabinetes, preferências por usuário.**
- **Senado Federal, REQ, PDL, PEC e outros tipos.**
- **Novas comissões como feature.** Basta editar a lista de configuração.
- **Selo, alerta ou lista de risco de arquivamento** (decisão D6).
- **Histórico de mais de 7 dias na página.** O Git guarda tudo.
- **Conteúdo dos pareceres.** O resumo informa que houve parecer e dá o link.

## 10. Restrições técnicas

- Python 3.13 com uv.
- Arquivos JSON versionados no Git como histórico. Sem servidor nem banco.
- GitHub Actions como agendador e GitHub Pages para a página, publicada por workflow próprio ao fim da coleta (§6.2).
- Segredos (token do bot e chat_id do Telegram) só em variáveis de ambiente e secrets do GitHub. O `.env` local fica fora do Git.
- Todo item conferível, com link para a página oficial da proposição.
- Visual: o Design System do portfólio (`../Portfolio/design-system`), com tokens azuis e os componentes FilterChips e, do lado do portfólio, EmbedFrame. Os ativos do DS (tokens, CSS dos chips e fontes) são copiados para `src/monitor_comissoes/pagina/estatico/`, porque a geração roda no GitHub Actions, onde o repositório do portfólio não existe.
