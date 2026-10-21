# Feature Specification: AVI — Resumo diário no Telegram

**Feature Branch**: `feat/avi-resumo-telegram` (criada a pedido do mantenedor em 20/10/2026; o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido)

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Feature AVI — Resumo diário no Telegram (linha AVI do ROADMAP.md)", com o recorte "Inclui" e "Não inclui" da linha, as regras do PRODUCT.md que se aplicam e os pontos em aberto levantados na situação.

**Recorte da linha AVI (ROADMAP.md)**

- *Resultado verificável*: um grupo recebe uma mensagem por dia, mesmo sem mudanças, com links oficiais, em até 4.096 caracteres e com teto de eventos. Uma falha gera mensagem de erro com a data dos últimos dados bons.
- *Inclui*: formatação; envio pela Bot API; secrets; "e mais N, veja a página"; testes de formatação.
- *Não inclui*: comandos no bot; vários destinatários.
- *Dependências*: MUD (concluída); AGE (concluída).

**Fora desta feature, por consequência do recorte e das outras linhas do ROADMAP.md**: a página pública, HTML e CSV (PAG); a pauta das reuniões (PAU); as movimentações relevantes (MOV); qualquer mudança nas regras de coleta, de relatoria ou de comparação. Os eventos chegam prontos em `data/mudancas/AAAA-MM-DD.json` (MUD); esta feature só os lê e os conta ao leitor.

## Clarifications

### Session 2026-10-20

- Q: A coleta roda às 03:37 de Brasília e o PRODUCT.md pede o resumo por volta das 7h. Como o envio se encaixa no agendamento? → A: **Segundo agendamento, às ~7h de Brasília**, em workflow próprio que só lê os dados já commitados e envia. A coleta (AGE) não muda. Se o `status.json` não é do dia (a coleta não rodou), o envio manda a mensagem de erro "a coleta de hoje não rodou", em vez de ficar em silêncio.
- Q: Como o sistema lembra que a mensagem do dia já foi enviada? → A: **`data/envio.json`**, versionado no Git e commitado pelo workflow de envio, com chave dia + tipo (normal ou erro): no máximo uma mensagem normal e uma de erro por dia. Reexecução com dados novos no mesmo dia **não** reenvia (o dia seguinte cobre). O `status.json` não muda.
- Q: Num dia com mais eventos do que cabem, quais aparecem e quais viram "e mais N"? → A: **Alternar entre comissões**: entra um evento de cada comissão por vez, na ordem do arquivo (tipo, id) dentro de cada uma, até encher. A mensagem continua agrupada por comissão, e todas as comissões com eventos aparecem.
- Q: Enquanto a PAG não existe, para onde aponta o "veja a página"? → A: **Um endereço da página em `config.toml`**. Enquanto estiver vazio, o texto vira "veja o arquivo do dia" e o link leva ao `data/mudancas/AAAA-MM-DD.json` no repositório. Quando a PAG existir, basta preencher a configuração.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ler, todo dia, o que mudou nas comissões (Priority: P1)

O chefe de gabinete abre o Telegram, quase sempre no celular, e encontra uma única mensagem do dia com o que mudou desde o retrato anterior: o que **entrou**, o que **saiu** (com o motivo), as mudanças de **situação**, de **relator**, os **pareceres** e as mudanças de **etiquetas**. Os eventos vêm agrupados por comissão e cada um traz o link oficial da proposição, para conferir na fonte (PRODUCT.md, D5 e §6.1).

**Why this priority**: é a razão de a feature existir: responder "o que mudou desde ontem" sem abrir nenhuma página (PRODUCT.md, §3).

**Independent Test**: dar à formatação um arquivo de mudanças salvo com um evento de cada tipo, em duas comissões, e conferir a mensagem: agrupamento por comissão, o conteúdo de cada tipo e o link de cada evento.

**Acceptance Scenarios**:

1. **Dado** um arquivo de mudanças do dia com eventos nas duas comissões, **Quando** a mensagem é formatada, **Então** ela traz um grupo por comissão acompanhada, e cada evento aparece no grupo da comissão dele.
2. **Dado** um evento **entrou**, **Quando** a mensagem é formatada, **Então** o evento traz a identificação da proposição (por exemplo, "PL 4501/2023"), o motivo da entrada e o link oficial.
3. **Dado** um evento **saiu**, **Quando** a mensagem é formatada, **Então** o evento traz a identificação, o motivo principal ("arquivado, art. 105", "foi para outro órgão" etc.), o destino quando houver e o link oficial.
4. **Dado** um evento de **situação**, **Então** a mensagem diz "de → para" e, se o item mudou de comissão, qual era a comissão anterior.
5. **Dado** um evento de **relator**, **Então** a mensagem diz se foi designado, devolveu ou foi substituído, com o nome e o partido de hoje de quem entra e de quem sai.
6. **Dado** um evento de **parecer**, **Então** a mensagem informa que houve parecer do relator e dá o link para a ficha oficial. O conteúdo do parecer não é reproduzido (PRODUCT.md, §9).
7. **Dado** um evento de **etiquetas**, **Então** a mensagem diz qual etiqueta foi ganha ou perdida.
8. **Dado** um item com mais de um evento no dia, **Quando** a mensagem é formatada, **Então** nenhum dos eventos é fundido nem omitido, quando cabem na mensagem.
9. **Dado** a mesma entrada, **Quando** a mensagem é formatada duas vezes, **Então** o texto é idêntico, com ordem determinística.

---

### User Story 2 - Receber a mensagem mesmo quando nada mudou (Priority: P1)

Num dia sem mudanças, o gabinete ainda recebe a mensagem: "sem mudanças · N itens · dados de DD/MM". Assim, o silêncio nunca quer dizer "parou de funcionar" (PRODUCT.md, D5). O mesmo vale para o primeiro retrato e para quando o retrato anterior era de formato incompatível: a mensagem diz "linha de base criada com N itens" e o motivo, sem nenhum evento falso.

**Why this priority**: é o ponto de D5. Sem a mensagem diária garantida, a ausência dela não prova nada.

**Independent Test**: formatar um arquivo de mudanças com zero eventos, um com linha de base "primeiro retrato", um com linha de base "formato anterior incompatível" e um que cobre mais de um dia, e conferir cada texto.

**Acceptance Scenarios**:

1. **Dado** um arquivo de mudanças sem eventos e sem linha de base, **Quando** a mensagem é formatada, **Então** ela diz "sem mudanças · N itens · dados de DD/MM", com o total de itens do retrato de hoje e a data dos dados da Câmara.
2. **Dado** um arquivo com linha de base por "primeiro retrato", **Então** a mensagem diz "linha de base criada com N itens" e que ainda não há comparação.
3. **Dado** um arquivo com linha de base por "formato anterior incompatível", **Então** a mensagem diz "linha de base criada com N itens" e o motivo, para não parecer um dia sem mudanças.
4. **Dado** um arquivo cujo retrato anterior é de mais de um dia antes (um dia ficou sem retrato), **Então** a mensagem diz as duas datas do intervalo coberto, para o leitor não achar que são só as mudanças de ontem.
5. **Dado** qualquer dia com execução bem-sucedida, **Quando** a execução termina, **Então** exatamente uma mensagem do dia é enviada ao grupo, tenha havido eventos ou não.

---

### User Story 3 - Dia de muitas mudanças cabe em uma mensagem (Priority: P1)

Na posse (1º/02/2027) e na recomposição anual das comissões, o número de eventos passa do que cabe em uma mensagem. O resumo mostra os eventos até um teto e termina com "e mais N, veja a página", sem passar de 4.096 caracteres, sem cortar um evento ao meio e sem perder a linha de totais. O arquivo de mudanças continua com todos os eventos; o teto é só do resumo (PRODUCT.md, §5.6 e §6.1).

**Why this priority**: o limite do Telegram é rígido: uma mensagem maior é recusada, e o gabinete ficaria sem resumo justo no dia em que mais precisa.

**Independent Test**: formatar um arquivo salvo com centenas de eventos e conferir o tamanho, o "e mais N" e que N bate com o número de eventos omitidos.

**Acceptance Scenarios**:

1. **Dado** um arquivo com mais eventos do que cabem, **Quando** a mensagem é formatada, **Então** o texto tem no máximo 4.096 caracteres e termina com "e mais N, veja a página", em que N é o número exato de eventos omitidos.
2. **Dado** o mesmo caso, **Então** nenhum evento aparece cortado: cada um está inteiro, com o link, ou foi omitido e contado em N.
3. **Dado** o mesmo caso, **Então** a linha de totais (quantos eventos por tipo, mesmo os omitidos) e os avisos de User Story 6 continuam inteiros na mensagem.
4. **Dado** um arquivo em que todos os eventos cabem, **Então** não há "e mais N".
5. **Dado** eventos com textos longos (nomes, situações, links), **Então** o limite vale para o texto final que o leitor recebe, e não para o texto antes da formatação.
6. **Dado** um arquivo com mais eventos do que cabem e eventos nas duas comissões, **Quando** a mensagem é formatada, **Então** os eventos são escolhidos alternando entre as comissões (um de cada por vez, na ordem do arquivo dentro de cada uma), de modo que as duas comissões com eventos aparecem, e a mensagem mostra cada grupo na ordem da configuração.
7. **Dado** que o endereço da página não está configurado, **Então** o fim da mensagem diz "e mais N, veja o arquivo do dia" com o link do `data/mudancas/AAAA-MM-DD.json` do dia no repositório; **dado** que está configurado, diz "e mais N, veja a página" com o link da página.

---

### User Story 4 - Saber, no Telegram, que a atualização falhou (Priority: P1)

Quando a execução do dia falha (fonte fora do ar, formato alterado, arquivos desatualizados, estoque implausível, lista vazia, erro nas APIs), o gabinete recebe uma mensagem de erro, claramente distinta da mensagem normal, com o motivo e a data dos últimos dados bons. Nenhuma lista nova foi publicada, e a mensagem diz isso. Se o **envio** ao Telegram é que falha, a coleta e o commit do dia já aconteceram e continuam valendo; a execução termina com erro, o workflow fica vermelho e o GitHub avisa o dono (PRODUCT.md, §6.1, §7 e D10).

**Why this priority**: uma lista antiga lida como atual é o pior erro possível para quem decide a partir dela (constituição, III; PRODUCT.md, D10).

**Independent Test**: dar à formatação um `status.json` salvo de falha, com cada categoria de falha, e conferir a mensagem; simular o Telegram recusando o envio e conferir o código de saída e que os dados do dia continuam.

**Acceptance Scenarios**:

1. **Dado** um `status.json` com falha, **Quando** a mensagem é formatada, **Então** ela começa com um marcador de erro inequívoco, diz o motivo da falha e a data dos últimos dados bons (do último retrato bom), e diz que a lista publicada é a da data anterior.
2. **Dado** cada categoria de falha prevista em PRODUCT.md, §7, **Então** o motivo aparece com as palavras do próprio `status.json`, sem ser reescrito nem omitido.
3. **Dado** uma falha em que nunca houve um retrato bom, **Então** a mensagem diz que ainda não há dados bons, em vez de uma data vazia.
4. **Dado** que a Bot API recusa ou não responde, **Quando** a execução tenta enviar, **Então** ela termina com código de erro e uma mensagem que diz o motivo, depois de poucas novas tentativas em falhas passageiras, e **sem** desfazer a coleta e o commit do dia (PRODUCT.md, §7).
5. **Dado** que o token ou o chat_id não existem no ambiente, **Quando** a execução tenta enviar, **Então** ela falha com mensagem que diz qual variável falta, sem mostrar valor algum.
6. **Dado** que o `status.json` não é do dia (a coleta de hoje não rodou), **Quando** o envio das ~7h roda, **Então** ele manda a mensagem de erro "a coleta de hoje não rodou", com a data dos últimos dados bons, e não fica em silêncio.
7. **Dado** que o próprio workflow de envio não rodou, **Então** nenhuma mensagem chega: a falta do resumo é o sinal (PRODUCT.md, §7). Isso é um limite conhecido, não um defeito.

---

### User Story 5 - Reexecutar no mesmo dia não duplica o aviso (Priority: P1)

Novas tentativas e execuções manuais acontecem. Reexecutar o processo no mesmo dia não pode repetir a mensagem para quem lê (constituição, V). O gabinete recebe uma mensagem por dia, e a mensagem de um dia com dados novos ou com falha seguida de recuperação não pode ser confundida com uma repetição.

**Why this priority**: mensagem duplicada ensina o gabinete a ignorar o canal.

**Independent Test**: executar o envio duas vezes com os mesmos dados, no mesmo dia, e conferir que o segundo não envia; depois, mudar a situação do dia (falha seguida de sucesso) e conferir o que é enviado.

**Acceptance Scenarios**:

1. **Dado** que a mensagem do dia já foi enviada, **Quando** a execução roda de novo no mesmo dia sobre os mesmos dados, **Então** nenhuma segunda mensagem é enviada, e a execução termina com sucesso, dizendo que já enviou.
2. **Dado** que a mensagem de erro do dia foi enviada e uma reexecução do mesmo dia tem sucesso, **Então** o gabinete recebe a mensagem normal do dia (a falha foi superada).
3. **Dado** que o envio falhou antes de a mensagem chegar, **Quando** a execução roda de novo, **Então** a mensagem é enviada, e não é tratada como já enviada.
4. **Dado** que a mensagem normal do dia já foi enviada e o lote da Câmara foi regenerado e coletado de novo no mesmo dia, **Quando** o envio roda outra vez, **Então** nenhuma segunda mensagem normal é enviada (uma por dia).
5. **Dado** que o envio do dia terminou com sucesso, **Então** o registro de envio (`data/envio.json`) diz o dia e o tipo da mensagem enviada, e é commitado; **dado** que o envio falhou, **Então** o registro não diz que foi enviada.

---

### User Story 6 - Nada que o produto sabe pode sumir em silêncio (Priority: P2)

O PRODUCT.md manda que o resumo avise de dois tipos de ressalva: itens com "principal não localizada" (§5.2) e itens com "relator indeterminado", para os quais a comparação de relator não foi possível (§5.4, §5.6). Esses avisos aparecem na mensagem sempre que valem no dia, com a contagem e a identificação dos itens, mesmo em dias sem eventos.

**Why this priority**: é o que impede que uma lacuna da fonte pareça um dia tranquilo. Fica em P2 porque a mensagem de eventos já entrega o essencial sem ela.

**Independent Test**: formatar um arquivo com ressalvas e um retrato com um item "principal não localizada", e conferir os avisos, também num dia sem eventos.

**Acceptance Scenarios**:

1. **Dado** um arquivo de mudanças com ressalvas de relator indeterminado, **Quando** a mensagem é formatada, **Então** ela avisa quantos itens estão nessa situação e quais são, com o link oficial.
2. **Dado** um retrato com itens marcados "principal não localizada", **Então** a mensagem avisa quantos e quais são, com o link oficial.
3. **Dado** um dia sem eventos mas com ressalvas, **Então** a mensagem é "sem mudanças · N itens · dados de DD/MM" **mais** os avisos, e não apenas a frase de "sem mudanças".
4. **Dado** um dia sem ressalvas, **Então** a mensagem não traz bloco de avisos.

---

### User Story 7 - Conferir e testar sem enviar nada (Priority: P2)

O mantenedor precisa ver como ficou a mensagem antes de ela ir ao grupo e poder testar tudo sem internet e sem credencial. O texto da mensagem do dia pode ser gerado e mostrado sem enviar, e os testes usam apenas arquivos salvos (constituição, IV e VI).

**Why this priority**: é o que permite conferir a feature item a item e proteger contra regressão sem tocar no grupo real.

**Independent Test**: rodar a geração do texto sem credenciais e sem rede sobre os dados do repositório e ler a mensagem; rodar a suíte sem rede.

**Acceptance Scenarios**:

1. **Dado** os dados do repositório e nenhuma credencial no ambiente, **Quando** o mantenedor pede só o texto, **Então** a mensagem do dia é mostrada e nada é enviado.
2. **Dado** a suíte de testes, **Quando** ela roda sem rede, **Então** todos os testes de formatação e de envio passam, com as respostas da Bot API simuladas por arquivos salvos.
3. **Dado** qualquer teste, execução ou mensagem de erro, **Então** o token do bot nunca aparece em saída, em log, em `status.json`, em fixture ou em arquivo versionado.

---

### Edge Cases

- **Caracteres especiais** na mensagem (nomes, situações e identificações vêm da Câmara e podem trazer símbolos que o formato do Telegram interpreta): a mensagem precisa ser aceita e legível, sem erro de formatação e sem links quebrados.
- **Link oficial ausente** em um evento: é defeito do arquivo de mudanças (o contrato exige link em todo evento). O envio falha com mensagem que diz qual evento, em vez de publicar evento sem fonte (constituição, II).
- **Arquivo de mudanças ausente, ilegível ou de versão de formato desconhecida** num dia de sucesso da coleta: o envio falha de forma visível. Nunca vira "sem mudanças" em silêncio (constituição, III).
- **Dados do dia e `status.json` incoerentes** (por exemplo, `status.json` de sucesso de um dia, mas arquivo de mudanças de outro): o envio falha com mensagem que diz as datas, sem enviar mensagem enganosa.
- **Evento sozinho maior que a mensagem**: não existe com os campos do contrato, mas, se ocorrer, o envio não corta o evento ao meio nem passa de 4.096 caracteres.
- **Resposta ambígua da Bot API** (a conexão cai depois de o Telegram aceitar): uma nova tentativa pode duplicar a mensagem. Entre duplicar e não avisar, prefere-se avisar; o plano registra a escolha.
- **Primeiro envio de todos**: sem registro de "já enviei", a mensagem do dia é enviada normalmente.
- **Dia com mensagem já enviada e dados novos** (reexecução manual com o lote regenerado): não reenvia; o dia seguinte cobre (User Story 5, cenário 4).
- **Coleta ainda em andamento às ~7h** (a coleta pode levar até 200 minutos mais esperas): o envio espera pela concorrência compartilhada e só então lê os dados (FR-017a).
- **Registro de envio ilegível ou de formato desconhecido**: o envio falha de forma visível; não envia nem finge que enviou.

## Requirements *(mandatory)*

### Functional Requirements

**Conteúdo da mensagem**

- **FR-001**: O sistema DEVE formatar **uma única mensagem de texto por dia**, em português, a partir de `data/mudancas/AAAA-MM-DD.json` (MUD), de `data/atual.json` (total de itens e marcas dos itens) e de `data/status.json` (resultado da execução e último retrato bom), sem consultar a Câmara nem outra fonte (PRODUCT.md, D5 e §6.1).
- **FR-002**: Os eventos DEVEM aparecer **agrupados por comissão**, na ordem da configuração, e cada evento DEVE trazer a identificação da proposição, o essencial do seu tipo (User Story 1) e o **link oficial** da proposição (constituição, II). A mensagem NÃO DEVE reproduzir as tramitações do intervalo nem o conteúdo de pareceres: o link leva a elas.
- **FR-003**: A mensagem DEVE cobrir os seis tipos de evento do arquivo de mudanças: entrou, saiu, situação, relator, parecer e etiquetas, e DEVE mostrar a data dos dados da Câmara (DD/MM) e o total de itens da lista.
- **FR-004**: Num dia sem eventos e sem linha de base, a mensagem DEVE ser enviada e dizer "sem mudanças · N itens · dados de DD/MM" (PRODUCT.md, §6.1).
- **FR-005**: Num dia de linha de base, a mensagem DEVE dizer "linha de base criada com N itens" e, quando o motivo for "formato anterior incompatível", dizer isso, sem nenhum evento (PRODUCT.md, §5.6).
- **FR-006**: Quando o retrato anterior é de mais de um dia antes, a mensagem DEVE trazer a data dele e a de hoje (PRODUCT.md, §5.6).
- **FR-007**: A mensagem DEVE avisar dos itens com **"principal não localizada"** (PRODUCT.md, §5.2) e dos itens com **relator indeterminado** (as ressalvas do arquivo de mudanças), com contagem, identificação e link, em todos os dias em que valem, e DEVE manter o aviso mesmo quando o teto de eventos corta a lista. A **contagem** de cada aviso fica sempre inteira; a lista de itens de cada aviso tem um limite fixo de tamanho, e o excedente vira "e mais M", para o aviso nunca estourar o teto de 4.096 caracteres (acréscimo do plano, 20/10/2026).

**Teto e tamanho**

- **FR-008**: O texto final enviado NÃO DEVE passar de **4.096 caracteres**, medidos como o Telegram os conta na mensagem recebida (PRODUCT.md, §6.1; ROADMAP.md, linha AVI).
- **FR-009**: Quando os eventos não cabem, o sistema DEVE mostrar os que cabem inteiros e terminar com **"e mais N, veja a página"**, em que N é exatamente o número de eventos omitidos. NÃO DEVE cortar um evento ao meio. A linha de totais e os avisos de FR-007 DEVEM caber sempre. Sob o teto, os eventos são escolhidos **alternando entre as comissões** (um de cada por vez, na ordem do arquivo dentro de cada uma), e a mensagem mostra cada grupo na ordem da configuração.
- **FR-010**: O arquivo de mudanças NÃO DEVE ser alterado nem truncado: o teto é só do resumo (PRODUCT.md, §5.6).
- **FR-011**: O destino do "veja a página" DEVE ser um endereço real e conferível. O endereço da página fica em `config.toml`, sem tela para editar. Enquanto ele estiver vazio (a PAG ainda não existe), o texto é "e mais N, veja o arquivo do dia" e o link é o do `data/mudancas/AAAA-MM-DD.json` do dia no repositório. Com o endereço preenchido, o texto é "e mais N, veja a página" e o link é o da página. A AVI NÃO DEVE criar a página.

**Mensagem de erro**

- **FR-012**: Quando o `status.json` do dia registra falha, o sistema DEVE enviar uma **mensagem de erro** que se distingue da mensagem normal já na primeira linha, com o motivo da falha como o `status.json` o registra, a data dos últimos dados bons e a informação de que a lista publicada continua a anterior (PRODUCT.md, §6.1, §7 e D10).
- **FR-013**: Na falha, a mensagem NÃO DEVE conter eventos nem totais do dia: não houve retrato novo. Se nunca houve retrato bom, DEVE dizer isso.
- **FR-013a**: Quando o `status.json` não é do dia da execução (a coleta de hoje não rodou), o sistema DEVE enviar a mensagem de erro "a coleta de hoje não rodou", com a data dos últimos dados bons. O dia é o de Brasília.

**Envio**

- **FR-014**: O sistema DEVE enviar a mensagem pela Bot API do Telegram a **um único grupo**, usando o token do bot e o chat_id lidos de variáveis de ambiente (em produção, secrets do GitHub). NÃO DEVE haver mais de um destinatário nem processamento de comandos, mensagens recebidas ou atualizações do bot: o bot só envia (PRODUCT.md, §9).
- **FR-015**: Token e chat_id NÃO DEVEM existir no código, nos dados, no `status.json`, nos logs, nas mensagens de erro, nas fixtures nem em qualquer arquivo versionado. O `.env` local fica fora do Git (constituição, VI; PRODUCT.md, §10). Variável ausente DEVE falhar o envio, dizendo o **nome** da variável, nunca o valor.
- **FR-016**: Falha de envio (rede, HTTP, recusa da Bot API, resposta malformada) DEVE terminar a execução com código de erro e mensagem que diga o motivo. Falhas passageiras (rede, 5xx, limite de taxa) DEVEM ter um número pequeno e fixo de novas tentativas, respeitando a espera que a Bot API indicar. A falha de envio NÃO DEVE desfazer nem impedir o que a coleta e o commit do dia já gravaram (PRODUCT.md, §7).
- **FR-017**: O envio DEVE acontecer **depois** de os dados do dia estarem gravados e commitados, e o workflow DEVE ficar vermelho quando o envio falhar, para o GitHub avisar o dono por e-mail (PRODUCT.md, §7).
- **FR-017a**: O envio roda num **workflow próprio, agendado para ~7h de Brasília**, que só lê os dados já commitados e envia (PRODUCT.md, §6.1). O agendamento e o workflow da coleta (AGE) NÃO DEVEM mudar. Os dois workflows DEVEM compartilhar o controle de concorrência da coleta, para o envio nunca ler dados no meio de uma coleta em andamento. O envio também pode ser disparado à mão.
- **FR-018**: A mensagem DEVE ser aceita pelo Telegram sem erro de formatação, seja qual for o texto vindo da Câmara (nomes, situações, símbolos), e os links DEVEM continuar utilizáveis.

**Quando enviar e não duplicar**

- **FR-019**: O sistema DEVE enviar a mensagem **todos os dias em que o workflow de envio roda**, com ou sem eventos, com sucesso, com falha da coleta ou com a coleta que não rodou (PRODUCT.md, D5).
- **FR-020**: Reexecutar no mesmo dia sobre os mesmos dados NÃO DEVE enviar uma segunda mensagem (constituição, V). A execução repetida termina com sucesso e diz que já enviou. Uma mensagem que não chegou ao grupo NÃO DEVE contar como enviada. O registro de envio é o arquivo versionado `data/envio.json`, com o dia e o tipo (normal ou erro) da mensagem enviada, commitado pelo workflow de envio; no máximo uma mensagem normal e uma de erro por dia. Reexecução com dados novos no mesmo dia NÃO reenvia. O `status.json` NÃO muda.
- **FR-021**: A mensagem de erro e a mensagem normal do mesmo dia NÃO DEVEM se anular: depois de uma falha seguida de uma execução bem-sucedida no mesmo dia, o gabinete recebe a mensagem normal.

**Integridade, conferência e testes**

- **FR-022**: O sistema DEVE falhar de forma visível, sem enviar mensagem enganosa, quando o arquivo de mudanças do dia estiver ausente, ilegível, de versão de formato desconhecida, com evento sem link ou incoerente com o `status.json` do dia (constituição, III). Nunca converter esses casos em "sem mudanças".
- **FR-023**: O texto da mensagem do dia DEVE poder ser gerado e mostrado **sem enviar** e sem credenciais, para o mantenedor conferi-lo.
- **FR-024**: O comportamento DEVE ser coberto por testes com **arquivos salvos** (arquivos de mudanças, retratos e `status.json` sintéticos, e respostas da Bot API simuladas), e NENHUM teste DEVE depender da internet nem de credencial real (constituição, IV). Os testes DEVEM cobrir, no mínimo: cada um dos seis tipos de evento; o dia sem mudanças; a linha de base nos dois motivos; o intervalo de vários dias; o teto de 4.096 caracteres com "e mais N" exato; cada categoria de falha na mensagem de erro; a falha de envio; a variável de ambiente ausente; os avisos de FR-007; os caracteres especiais; e a não duplicação no mesmo dia.
- **FR-025**: A mensagem DEVE ser idêntica, byte a byte, quando formatada duas vezes a partir dos mesmos arquivos.

**Limites desta feature (não implementar)**

- **FR-026**: Esta feature NÃO DEVE implementar comandos no bot, resposta a mensagens, vários destinatários ou preferências por usuário; página, HTML ou CSV; pauta das reuniões; movimentações relevantes; resumo de ementa por IA; nem mudar as regras de coleta, de relatoria, de comparação ou o conteúdo do `atual.json` e do arquivo de mudanças. Só lê esses arquivos.

### Key Entities *(include if feature involves data)*

- **Mensagem do dia**: o texto único enviado ao grupo. Dois tipos: normal (com eventos, sem mudanças ou linha de base) e de erro. Sempre em até 4.096 caracteres.
- **Resumo do dia**: o que a mensagem normal conta: a data dos dados, o total de itens, os totais por tipo, os eventos por comissão, os avisos e, se houver excedente, o "e mais N".
- **Evento**: a mudança de um item, como o arquivo de mudanças a registra, com o link oficial. A mensagem mostra uma versão curta dele.
- **Aviso**: ressalva que a mensagem repete todo dia em que vale: "principal não localizada" e relator indeterminado.
- **Mensagem de erro**: aviso de que a execução do dia falhou, com o motivo e a data dos últimos dados bons.
- **Registro de envio**: `data/envio.json`, o que permite saber que a mensagem do dia já foi enviada e não repeti-la. Chave: dia + tipo (normal ou erro).
- **Credenciais do bot**: token e chat_id, só em variáveis de ambiente e secrets do GitHub.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos dias em que o envio roda, com mudanças, sem mudanças, com falha da coleta ou com a coleta que não rodou, o grupo recebe exatamente uma mensagem do dia.
- **SC-002**: Nenhuma mensagem passa de 4.096 caracteres, nem em um arquivo salvo com centenas de eventos, e o N do "e mais N" bate com o número de eventos omitidos em 100% dos casos testados.
- **SC-003**: Todo evento mostrado na mensagem tem link oficial que o gabinete consegue abrir, e nenhum evento aparece cortado.
- **SC-004**: Numa falha da coleta, o gabinete lê, na primeira linha da mensagem, que é um erro, e encontra o motivo e a data dos últimos dados bons sem abrir nenhum outro lugar.
- **SC-005**: Reexecutar duas vezes no mesmo dia sobre os mesmos dados gera uma única mensagem no grupo, em 100% dos casos testados.
- **SC-006**: Uma falha de envio deixa o workflow vermelho e os dados do dia intactos, em 100% dos casos testados.
- **SC-007**: A suíte de testes completa passa sem rede e sem credencial, e nenhum arquivo versionado contém o token do bot.
- **SC-008**: O mantenedor lê no celular, em menos de 1 minuto, o resumo de um dia com mudanças e identifica o que entrou, o que saiu e por quê.

## Assumptions

- A mensagem normal usa só o arquivo de mudanças, o `atual.json` e o `status.json`. A MUD já registra todos os eventos, e a AVI não recalcula nenhuma regra de domínio.
- Não há destinatário além do grupo do gabinete, e o chat_id é um só (ROADMAP.md, "Não inclui": vários destinatários).
- O contrato `data/mudancas/AAAA-MM-DD.json` está em `versao_formato` 1 e **congela com a AVI**: a MUD previu que, antes de a AVI ou a PAG lerem o arquivo, o contrato fica fechado, e que depois disso campo novo, removido ou com outro sentido sobe a versão. A AVI se recusa a formatar uma versão que não conhece.
- "Dados de DD/MM" é a data dos dados da Câmara (`dados_camara_em`), em Brasília. A mensagem usa datas no formato DD/MM.
- A mensagem de erro usa o motivo e a data do último retrato bom que o `status.json` já registra (AGE). A AVI não cria categoria nova de falha da coleta.
- O texto da mensagem não reproduz as tramitações do intervalo: a mensagem mostra uma linha curta por evento e o link oficial.
- O endereço da página pública é um valor de `config.toml`, vazio até a PAG existir.
- O workflow de envio faz commit só de `data/envio.json`.
- O texto exato da mensagem é detalhe do plano, desde que cumpra os conteúdos obrigatórios de FR-002 a FR-013.
- Por falta de um servidor, nada recebe resposta do grupo: a mensagem não tem botões nem comandos (PRODUCT.md, §9).

### Exemplo ilustrativo (conteúdo, não layout final)

> (nomes e números fictícios)
>
> **Monitor de comissões · dados de 20/10 · 105 itens**
> 3 eventos: 1 entrou · 1 situação · 1 relator
>
> **CE**
> ▸ Entrou: PL AAA/AAAA — chegou à comissão · link
> ▸ Relator: PL BBB/BBBB — designado: Fulano (NOVO) · link
>
> **CREDN**
> ▸ Situação: PL CCC/CCCC — Aguardando Parecer → Pronta para Pauta · link
>
> ⚠ 1 item com relator indeterminado: PL DDD/DDDD · link
