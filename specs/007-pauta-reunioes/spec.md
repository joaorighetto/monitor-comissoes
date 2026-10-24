# Feature Specification: PAU — Pauta das reuniões

**Feature Branch**: `docs/direcao-pauta` (branch atual, que já traz as emendas ao PRODUCT.md e ao ROADMAP.md que definem esta feature; o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido)

**Created**: 2026-10-24

**Status**: Aprovada pelo mantenedor em 24/10/2026 (com a ampliação da regra do REQ decidida no plano)

**Input**: User description: "Feature PAU — Pauta das reuniões (linha PAU do ROADMAP.md)", com o recorte "Inclui" e "Não inclui" da linha, as regras do PRODUCT.md (§5.8, §5.9, §7 e §8) e os pontos em aberto levantados na situação.

**Recorte da linha PAU (ROADMAP.md)**

- *Resultado verificável*: `data/pautas/AAAA-MM-DD.json` lista as reuniões deliberativas da CE e da CREDN convocadas para os próximos 7 dias e as realizadas nos últimos 7, inclusive as canceladas. Cada reunião traz os itens de PL, PLP, PEC, MSC e PDL, com as etiquetas do NOVO quando houver e a marca "leva apensado do NOVO" quando a proposição for a raiz de um item do inventário; a contagem dos REQ, com os de autoria do NOVO listados; e, nas realizadas, o resultado de cada item. Uma pauta alterada ou uma reunião cancelada é registrada uma única vez, mesmo com várias checagens no dia (PRODUCT.md, §5.8 e §5.9).
- *Inclui*: `/orgaos/{id}/eventos` e `/eventos/{id}/pauta`; classificação do resultado a partir de `situacaoItem`; etiquetas do NOVO nos itens (autoria pelo lote, relatoria pelo relator do item na pauta); marca "leva apensado do NOVO" pela referência dos itens do inventário; detecção de pauta alterada e de reunião cancelada; checagem mais de uma vez por dia, com as garantias do PRODUCT.md, §5.8 (horários definidos no plano); testes com pautas reais salvas.
- *Não inclui*: prazo de emendas (PRZ); envio (SEM); página (PGP); mudança no inventário; audiências públicas, seminários e outros eventos não deliberativos.
- *Dependências*: COL (concluída); AGE (concluída).

**Pontos em aberto**: resolvidos no clarify de 24/10/2026 (abaixo). Três respostas exigiram emenda ao PRODUCT.md, §5.8, feita na mesma mudança desta spec. Os horários das checagens ficam para o plano, como manda o PRODUCT.md, §5.8.

## Clarifications

### Session 2026-10-24

- Q: Quais etiquetas fazem um REQ ser listado como "do NOVO" na pauta (os demais REQ só entram na contagem)? → A: **`autoria NOVO` ou `autor hoje no NOVO`.** É a mesma noção de autoria dos demais itens. `relatoria NOVO` sozinha não faz o REQ ser listado.
- Q: Quando um REQ da pauta adita outro REQ (o item vem com o outro REQ em `proposicaoRelacionada_`), de qual REQ vêm a identificação e a autoria do item? → A: **Do próprio REQ do item** (`proposicao_`). A regra "a proposição do item é a relacionada" continua valendo para os demais casos, como o parecer (PRL → projeto). Isso exige uma emenda ao PRODUCT.md, §5.8, aprovada pelo mantenedor junto com esta spec. **Ampliada no plano (24/10/2026):** a sondagem de 12 meses de pautas mostrou 13 REQ com PL ou PEC como relacionada (por exemplo, REQ 17/2026 CE → PL 1778/2020, "Aprovado o Requerimento"); o mantenedor decidiu que **todo item cuja `proposicao_` é REQ tem o próprio REQ como proposição do item**, seja qual for a relacionada.
- Q: O que o item mostra quando a proposição do item não está no último lote bom (por exemplo, um REQ apresentado depois da geração do lote)? → A: **A marca "autoria não verificada"**, sem as etiquetas de autoria. Um REQ com essa marca é listado, e não só contado. A marca some quando o lote seguinte trouxer a proposição. Emenda ao PRODUCT.md, §5.8, aprovada pelo mantenedor junto com esta spec.
- Q: O que a checagem faz quando uma reunião convocada na checagem anterior some da consulta da janela sem aparecer como cancelada? → A: **Busca o evento pelo identificador.** Data movida para fora da janela → "data ou hora mudou"; cancelado → "reunião cancelada"; evento inexistente → alteração nova, **"reunião retirada da agenda"**. Emenda ao PRODUCT.md, §5.8 (quinto tipo de alteração), aprovada pelo mantenedor junto com esta spec.
- Q: A PAU deve registrar, em cada reunião, o momento da primeira checagem que a viu (para a SEM saber se ela foi convocada depois da mensagem de segunda)? → A: **Sim, "vista desde".** Cada reunião traz o momento da primeira checagem que a encontrou na janela, mantido de arquivo em arquivo. É só um dado: não é alteração de pauta e não muda o §5.8.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver as reuniões da semana e o que está na pauta de cada uma (Priority: P1)

O gabinete quer abrir o arquivo de pauta do dia e ver, para a CE e a CREDN, as reuniões deliberativas convocadas para os próximos 7 dias e as dos 7 dias anteriores, inclusive as canceladas, cada uma com comissão, data e hora, situação e link oficial. Em cada reunião, quer ver os PL, PLP, PEC, MSC e PDL pautados, cada um com `Tipo número/ano`, ementa, relator (nome e partido) e link oficial, e saber quantos REQ e quantos itens de outros tipos há (PRODUCT.md, §5.8 e D1).

**Why this priority**: é a pergunta central do produto ("o que vai a voto nas comissões acompanhadas", PRODUCT.md, §3). Sem a lista de reuniões e itens, nenhuma das outras histórias tem sobre o que agir.

**Independent Test**: dar à checagem eventos e pautas reais salvos da CE e da CREDN e conferir, reunião a reunião, a janela, a situação, os itens listados e as contagens contra a fonte.

**Acceptance Scenarios**:

1. **Dado** eventos da CE e da CREDN com datas de 10 dias antes a 10 dias depois do dia da checagem, **Quando** a checagem roda, **Então** o arquivo traz só as reuniões deliberativas com início entre 7 dias antes e 7 dias depois do dia da checagem, inclusive os dois extremos, qualquer que seja a situação.
2. **Dado** um evento do tipo "Audiência Pública", "Seminário", "Mesa Redonda" ou qualquer outro que não seja "Reunião Deliberativa", **Quando** a checagem roda, **Então** ele não aparece no arquivo.
3. **Dado** uma reunião deliberativa cancelada dentro da janela, **Quando** a checagem roda, **Então** ela aparece com a situação "cancelada" e com o texto original da situação.
4. **Dado** um item de pauta que é o parecer (PRL) de um PL, com o PL em `proposicaoRelacionada_`, **Quando** a checagem roda, **Então** a proposição do item é o PL, e o item aparece como `PL número/ano`.
5. **Dado** o item REQ 70/2026 CE da pauta de 28/10/2026, que vem com o REQ 63/2026 CE em `proposicaoRelacionada_`, e o item REQ 17/2026 CE da pauta de 15/04/2026, que vem com o PL 1778/2020, **Quando** a checagem roda, **Então** a proposição de cada item é o próprio REQ, e ambos são só contados (a menos que sejam do NOVO); o PL 1778/2020 não aparece como item listado.
6. **Dado** uma pauta com PL, PLP, PEC, MSC, PDL, REQ e outros tipos (por exemplo, SOR), **Quando** a checagem roda, **Então** os itens de PL, PLP, PEC, MSC e PDL são listados, os REQ são contados, e os demais tipos são contados como "outros".
7. **Dado** a pauta real da reunião da CE de 28/10/2026, salva em 24/10/2026 (20 itens: 19 PL e 1 REQ), **Quando** a checagem roda com ela, **Então** a reunião traz 19 itens listados e 1 REQ contado.
8. **Dado** qualquer reunião ou item listado, **Quando** se lê o arquivo, **Então** ele traz o link oficial da Câmara (constituição, princípio II).

---

### User Story 2 - Saber quais itens da pauta têm ligação com o NOVO (Priority: P1)

Na pauta, o deputado vota tudo, mas o gabinete precisa achar de imediato o que tem ligação com o partido. Cada item listado traz as etiquetas `autoria NOVO`, `autor hoje no NOVO` e `relatoria NOVO`, quando tiver, e a marca "leva apensado do NOVO" quando a proposição for a raiz de um item do inventário, com cada apensado identificado, com link e com as etiquetas dele. Os itens com etiqueta ou com a marca vêm primeiro. Os REQ não são listados, exceto os de autoria do NOVO (PRODUCT.md, D1, D2 e §5.8).

**Why this priority**: é o que distingue o produto de abrir a pauta no portal. Só 5 dos 287 PL/PLP pautados em 12 meses tinham ligação com o NOVO, e por isso eles não podem se perder no meio dos outros (PRODUCT.md, §1).

**Independent Test**: com pautas reais salvas, a lista de deputados do NOVO salva, os autores do lote salvos e um inventário salvo, conferir as etiquetas e a marca de cada item contra a regra.

**Acceptance Scenarios**:

1. **Dado** um item cuja proposição tem um autor que assinou como NOVO, segundo o lote, **Quando** a checagem roda, **Então** o item traz `autoria NOVO`.
2. **Dado** um item cuja proposição tem um autor que está entre os deputados em exercício do NOVO no dia, **Quando** a checagem roda, **Então** o item traz `autor hoje no NOVO`, mesmo que o autor tenha assinado por outro partido.
3. **Dado** um item cujo relator na pauta está entre os deputados em exercício do NOVO no dia, **Quando** a checagem roda, **Então** o item traz `relatoria NOVO`, mesmo que o relator atual pelas tramitações seja outro (PRODUCT.md, §8).
4. **Dado** a pauta real da CE de 15/04/2026, em que o PL 5432/2016 foi pautado, e o inventário em que o PL 3701/2020 (`autoria NOVO`, `autor hoje no NOVO`) é apensado ao PL 5432/2016, **Quando** a checagem roda, **Então** o item do PL 5432/2016 traz a marca "leva apensado do NOVO", com o PL 3701/2020, o link oficial dele e as duas etiquetas.
5. **Dado** uma pauta com itens do NOVO e itens sem ligação, **Quando** a checagem roda, **Então** os itens com etiqueta ou com a marca vêm primeiro, e, dentro de cada grupo, os itens seguem a ordem da pauta.
6. **Dado** um REQ com `autoria NOVO`, outro só com `autor hoje no NOVO` e um terceiro sem ligação com o NOVO na mesma pauta, **Quando** a checagem roda, **Então** os três são contados, e só os dois primeiros são listados, com identificação, ementa, link e etiquetas.
7. **Dado** um REQ cuja única etiqueta seria `relatoria NOVO`, **Quando** a checagem roda, **Então** ele é só contado, não listado.
8. **Dado** um item cuja proposição não está no último lote bom, **Quando** a checagem roda, **Então** ele não traz `autoria NOVO` nem `autor hoje no NOVO` e leva a marca "autoria não verificada"; se for REQ, é listado com a marca, além de contado. `relatoria NOVO` continua valendo pelo relator na pauta.
9. **Dado** um item sem nenhuma ligação com o NOVO, **Quando** a checagem roda, **Então** ele é listado normalmente, sem etiquetas. As etiquetas são só marca: nenhum item é incluído ou excluído por elas (PRODUCT.md, D2).

---

### User Story 3 - Saber o que aconteceu com cada item nas reuniões realizadas (Priority: P1)

Depois de uma reunião, o gabinete quer ver, para cada item listado, o resultado: aprovado, rejeitado, retirado de pauta, vista, não apreciado, sem registro ou outro, sempre com o texto original da Câmara ao lado, para conferir (PRODUCT.md, §5.9).

**Why this priority**: é a pergunta "o que foi decidido" (PRODUCT.md, §3), e o insumo da mensagem de quinta (SEM) e da seção da página (PGP).

**Independent Test**: com pautas reais salvas de reuniões realizadas, conferir o rótulo de cada item contra a tabela do §5.9, inclusive a ordem de precedência.

**Acceptance Scenarios**:

1. **Dado** um item com `situacaoItem` "Retirado de pauta, por acordo, a pedido do governo.", **Quando** a checagem roda, **Então** o resultado é "retirado de pauta", com o texto original.
2. **Dado** um item cujo texto menciona "Requerimento de Retirada de Pauta" e depois a aprovação do parecer, **Quando** a checagem roda, **Então** o resultado **não** é "retirado de pauta"; segue para as regras seguintes e, nesse caso, é "aprovado".
3. **Dado** um item cujo texto menciona vista e também aprovação, **Quando** a checagem roda, **Então** o resultado é "vista" (regra 2 antes da regra 3).
4. **Dado** um item com texto "Aprovado o Parecer" ou "Aprovada", **Quando** a checagem roda, **Então** o resultado é "aprovado"; com "Rejeitado" ou "Rejeitada", "rejeitado".
5. **Dado** um item com texto que diz adiado, não apreciado, não deliberado ou que a reunião foi encerrada antes do item, **Quando** a checagem roda, **Então** o resultado é "não apreciado".
6. **Dado** um item de reunião realizada com texto vazio ou ausente, **Quando** a checagem roda, **Então** o resultado é "sem registro".
7. **Dado** um item cujo texto não casa com nenhuma regra, **Quando** a checagem roda, **Então** o resultado é "outro", com o texto original.
8. **Dado** uma reunião convocada (ainda não realizada) ou cancelada, **Quando** a checagem roda, **Então** os itens não trazem resultado.
9. **Dado** o conjunto de pautas reais salvas de reuniões realizadas usado nos testes, **Quando** a classificação roda sobre os PL/PLP delas, **Então** "outro" fica restrito aos casos sem regra que case, e cada rótulo tem ao menos um caso real.

---

### User Story 4 - Saber que a pauta mudou ou a reunião caiu, uma vez só (Priority: P1)

A pauta muda até a reunião: entra item, sai item, a reunião muda de dia ou de hora, ou é cancelada. O gabinete precisa saber disso, e o resumo da véspera (SEM) e a página (PGP) precisam de um registro único de cada alteração, mesmo que a pauta seja checada várias vezes no dia (PRODUCT.md, §5.8; constituição, princípio V).

**Why this priority**: é a pergunta "a pauta mudou ou a reunião caiu depois do aviso?" (PRODUCT.md, §3) e o gatilho da mensagem de véspera.

**Independent Test**: rodar a checagem em sequência sobre pautas salvas que diferem em um aspecto por vez e conferir que cada alteração é registrada uma única vez, com o momento da checagem que a detectou.

**Acceptance Scenarios**:

1. **Dado** uma reunião convocada na checagem anterior, **Quando** uma checagem posterior encontra na pauta um item que não estava, **Então** o arquivo do dia registra a alteração "item entrou", com o item, a reunião e o momento da checagem.
2. **Dado** uma reunião convocada na checagem anterior, **Quando** uma checagem posterior não encontra mais um item que estava, **Então** registra "item saiu".
3. **Dado** uma reunião convocada cuja data ou hora de início mudou desde a checagem anterior, **Quando** a checagem roda, **Então** registra "data ou hora mudou", com o valor anterior e o novo.
4. **Dado** uma reunião convocada na checagem anterior e cancelada agora, **Quando** a checagem roda, **Então** registra "reunião cancelada".
5. **Dado** uma reunião convocada na checagem anterior que não aparece mais na consulta da janela, **Quando** a checagem a busca pelo identificador e descobre que a data foi movida para fora da janela, **Então** registra "data ou hora mudou", com a data nova; se o evento está cancelado, registra "reunião cancelada"; se o evento não existe mais, registra "reunião retirada da agenda".
6. **Dado** uma pauta cujos itens só mudaram de ordem, **Quando** a checagem roda, **Então** nenhuma alteração é registrada.
7. **Dado** uma alteração já registrada, **Quando** a checagem roda de novo no mesmo dia ou em outro dia, com a mesma pauta, **Então** a alteração **não** é registrada outra vez.
8. **Dado** uma alteração detectada pela primeira checagem de um dia, em relação à última checagem do dia anterior, **Quando** a checagem roda, **Então** a alteração fica no arquivo do dia em que foi detectada, e não no do dia anterior.
9. **Dado** que não há checagem anterior registrada (primeira execução), **Quando** a checagem roda, **Então** o arquivo do dia é uma **linha de base**: traz as reuniões e nenhuma alteração.
10. **Dado** uma reunião já realizada cujo `situacaoItem` foi preenchido entre duas checagens, **Quando** a checagem roda, **Então** isso atualiza o resultado, mas não é registrado como pauta alterada (a alteração vale só para reunião convocada).

---

### User Story 5 - Checar a pauta várias vezes ao dia, com as garantias do produto (Priority: P2)

A pauta é checada mais de uma vez por dia, em horários que dão três garantias: há uma checagem do mesmo dia antes de cada envio ao Telegram; há uma checagem depois do horário das reuniões, para o resultado aparecer no próprio dia; e há uma checagem no fim do dia, para pegar a pauta anunciada ao fim da reunião anterior (PRODUCT.md, §5.8). O arquivo do dia guarda a última checagem e as alterações registradas no dia.

**Why this priority**: sustenta a SEM e a PGP, mas a PAU entrega valor verificável (o arquivo) mesmo com uma checagem só.

**Independent Test**: conferir no agendamento que os horários cobrem as três garantias, e, com checagens simuladas, que o arquivo do dia fica com a última checagem e com todas as alterações do dia, sem repetir nenhuma.

**Acceptance Scenarios**:

1. **Dado** o agendamento da checagem, **Quando** se compara com o horário do envio diário (07:17 de Brasília, PRODUCT.md, §6.1), **Então** há uma checagem diária que termina antes dele.
2. **Dado** o agendamento, **Quando** se compara com o horário das reuniões (42 das 47 começaram entre 9h e 11h40), **Então** há uma checagem diária depois desse intervalo, com margem para a duração da reunião.
3. **Dado** o agendamento, **Então** há uma checagem diária no fim do dia.
4. **Dado** três checagens no mesmo dia, cada uma com uma alteração diferente, **Quando** a terceira termina, **Então** o arquivo do dia traz a terceira checagem como última e as três alterações, cada uma com o momento da checagem que a detectou.
5. **Dado** a checagem do dia, **Quando** ela termina sem erro, **Então** o arquivo do dia é commitado no repositório (PRODUCT.md, D8), sem afetar o commit diário da coleta.

---

### User Story 6 - Falhar de forma visível, só na pauta (Priority: P1)

Se a API de eventos ou de pauta falhar, ou devolver algo malformado, a checagem falha com o motivo. O último arquivo de pauta bom fica como está, a falha é registrada com a data e a hora da última checagem boa, e a pauta antiga nunca aparece como atual. O estoque e o inventário não são afetados (PRODUCT.md, §7; constituição, princípio III).

**Why this priority**: uma pauta parcial publicada como completa levaria o gabinete a não acompanhar uma reunião. É a mesma garantia da COL e da AGE, com o alcance limitado à pauta.

**Independent Test**: para cada falha simulada, conferir saída com erro, motivo registrado, arquivos de pauta idênticos byte a byte e `atual.json` e `status.json` da coleta intocados.

**Acceptance Scenarios**:

1. **Dado** que a API de eventos ou a de pauta falha (rede, status HTTP, tempo esgotado depois de novas tentativas), **Quando** a checagem roda, **Então** ela sai com erro, o motivo fica registrado, e a pasta `data/pautas/` fica como estava.
2. **Dado** uma resposta malformada (campo exigido ausente, tipo inesperado, JSON inválido), **Quando** a checagem roda, **Então** ela falha com "formato alterado" e o campo, e a pasta `data/pautas/` fica como estava.
3. **Dado** que a pauta de uma das reuniões da janela não pôde ser lida, **Quando** a checagem roda, **Então** a checagem inteira falha. Não há arquivo com parte das reuniões.
4. **Dado** que a lista de deputados do NOVO não pôde ser lida, ou que o inventário ou os autores do lote estão ausentes ou ilegíveis, **Quando** a checagem roda, **Então** ela falha com o motivo, sem gravar pauta sem etiquetas.
5. **Dado** uma checagem que falhou, **Quando** se lê o registro da falha, **Então** ele traz o momento da falha, o motivo e o momento da última checagem boa, para que a SEM e a PGP possam avisar sem apresentar a pauta antiga como atual.
6. **Dado** uma checagem que falhou, **Quando** se olha o `atual.json`, o `anterior.json`, a pasta `data/mudancas/` e o `status.json` da coleta, **Então** eles estão idênticos byte a byte.
7. **Dado** uma checagem que falhou, **Quando** se olha a execução agendada, **Então** ela termina em vermelho.

---

### User Story 7 - Conferível e testável sem rede (Priority: P2)

Cada reunião e cada item apontam para a fonte oficial, e o comportamento é coberto por testes com pautas reais salvas; nenhum teste depende da internet (constituição, princípios II e IV).

**Why this priority**: sustenta a confiança no arquivo e a manutenção sem cuidados diários.

**Independent Test**: rodar a suíte sem acesso à internet e conferir que cada regra das histórias acima tem ao menos um teste com fixture real salva ou sintética derivada dela.

**Acceptance Scenarios**:

1. **Dado** a suíte inteira, **Quando** ela roda sem acesso à internet, **Então** todos os testes passam.
2. **Dado** as fixtures de pauta, **Quando** se lê de onde vieram, **Então** cada uma diz o endpoint e a data em que foi salva.

---

### Edge Cases

- **Reunião de hoje.** Entra na janela pelos dois lados. Antes de acontecer, aparece com a situação que a Câmara registra (convocada); depois, encerrada e com resultados. A janela é por data de início, não pela situação.
- **Reunião passada ainda "Convocada".** Se a Câmara não atualizou a situação, a reunião aparece como a Câmara a registra, sem resultado inferido.
- **Situação de reunião desconhecida** (nem convocada, nem encerrada, nem cancelada, como "Em Andamento" ou "Suspensa"). A reunião aparece com o texto original e o rótulo "outra", sem falhar; só formato alterado falha.
- **Situações encerradas.** "Encerrada", "Encerrada (Final)" e "Encerrada (Termo)" contam como realizada (vistas em 12 meses de eventos da CE e da CREDN).
- **Reunião com pauta vazia.** Aparece com zero itens. Pauta vazia de uma reunião convocada é o que a fonte diz, e não erro.
- **Mesma proposição duas vezes na pauta da mesma reunião.** Cada ocorrência é um item; a detecção de entrada e saída compara ocorrências, sem fundir nem perder nenhuma.
- **Item sem proposição** (nem `proposicao_` nem `proposicaoRelacionada_`). É contado em "outros", com o título original.
- **REQ com proposição relacionada** (por exemplo, REQ 70/2026 CE, que inclui convidados na audiência do REQ 63/2026 CE, ou REQ 17/2026 CE, que se refere ao PL 1778/2020). A proposição do item é o próprio REQ, e a autoria e o resultado são os dele (FR-004). O PL ou a PEC relacionados não são listados por causa do REQ.
- **Proposição do item fora do inventário.** É o caso comum (só 7 dos 287 PL/PLP pautados em 12 meses estavam no inventário). As etiquetas são calculadas para ela do mesmo jeito.
- **Proposição apresentada depois do último lote.** Os autores ainda não estão no lote. O item leva a marca "autoria não verificada" (FR-008a). O mesmo vale para uma proposição anterior ao ano mínimo dos arquivos lidos.
- **Apensação feita depois do último inventário bom.** A marca "leva apensado do NOVO" usa a raiz do último `atual.json` bom, então ainda não conta (PRODUCT.md, §5.8).
- **Inventário com falha no dia.** A checagem usa o último `atual.json` bom, que é o que está no repositório. A falha da coleta não barra a pauta.
- **Relator da pauta diferente do relator atual do inventário.** Vale o da pauta para a etiqueta do item da pauta (PRODUCT.md, §8). Nada é reconciliado.
- **Reunião convocada que some da janela sem estar cancelada** (data movida para mais de 7 dias, ou evento excluído da agenda). É buscada pelo identificador (User Story 4, cenário 5). Depois de registrada, ela sai da janela e não é mais acompanhada.
- **Reunião que entra na janela porque o dia avançou.** Não é alteração de pauta: a alteração é só para reunião já vista em checagem anterior. O "vista desde" dela é o momento em que entrou na janela, que pode ser depois da convocação; como a janela é de 7 dias, a checagem de segunda já vê todas as reuniões da semana convocadas até ali.
- **Dia sem nenhuma reunião na janela** (recesso, período eleitoral: 21 das 53 semanas). O arquivo do dia existe, com zero reuniões, e diz a janela consultada. Zero reuniões não é falha.
- **Horário de verão e fuso.** A API dá a data e a hora de início sem fuso; são horas de Brasília. O dia da checagem é o dia de Brasília.
- **Reunião conjunta das duas comissões.** Um evento ligado à CE e à CREDN aparece uma vez em cada comissão, com a mesma pauta.
- **Comissão nova na configuração.** Basta a sigla estar na lista; o identificador do órgão é obtido sem mudança de código (PRODUCT.md, D1).

## Requirements *(mandatory)*

### Functional Requirements

**Reuniões e janela**

- **FR-001**: A checagem DEVE ler os eventos de cada comissão da lista de configuração e considerar **reunião** só o evento cujo tipo é "Reunião Deliberativa" (PRODUCT.md, §5.8). Audiências públicas, seminários e os demais tipos NÃO DEVEM entrar.
- **FR-002**: A **janela** DEVE ser a das reuniões com início entre 7 dias antes e 7 dias depois do dia da checagem, em Brasília, inclusive os extremos, qualquer que seja a situação. Reunião cancelada continua na janela, com a situação "cancelada".
- **FR-003**: Cada reunião DEVE trazer: identificador, comissão, data e hora de início, situação normalizada ("convocada", "realizada", "cancelada" ou "outra") com o texto original da Câmara, link oficial do evento e **"vista desde"**: o momento da primeira checagem que encontrou a reunião na janela, mantido igual nas checagens seguintes (clarify, 24/10/2026). Na linha de base, é o momento da própria checagem.

**Itens da pauta**

- **FR-004**: A **proposição do item** DEVE ser a `proposicaoRelacionada_`, quando existir, e senão a `proposicao_` (PRODUCT.md, §5.8). Exceção: quando a `proposicao_` é REQ, a proposição do item é a `proposicao_`, seja qual for a relacionada (clarify e plano, 24/10/2026; emenda ao PRODUCT.md, §5.8). Um REQ listado mostra também a proposição relacionada, quando houver, com link.
- **FR-005**: DEVEM ser **listados** os itens cuja proposição é PL, PLP, PEC, MSC ou PDL. Os REQ DEVEM ser **contados**, e os que têm `autoria NOVO` ou `autor hoje no NOVO`, ou a marca "autoria não verificada" (FR-008a), também listados (clarify, 24/10/2026); `relatoria NOVO` sozinha não faz o REQ ser listado. Os demais tipos, e os itens sem proposição, DEVEM ser contados como "outros" (PRODUCT.md, D1).
- **FR-006**: Cada item listado DEVE trazer: `Tipo número/ano` da proposição do item, ementa, link oficial da proposição, relator na pauta (nome e partido, quando houver), regime, ordem na pauta, etiquetas, a marca "leva apensado do NOVO" quando couber e, nas reuniões realizadas, o resultado (FR-011).
- **FR-007**: Os itens com etiqueta ou com a marca "leva apensado do NOVO" DEVEM vir primeiro; dentro de cada grupo, vale a ordem da pauta.

**Etiquetas e marca (só marca, nunca filtro)**

- **FR-008**: `autoria NOVO` e `autor hoje no NOVO` DEVEM seguir o §5.4, aplicados aos autores da proposição do item, com os autores e o partido na data vindos do **lote da última coleta boa** e os deputados em exercício do NOVO lidos no dia da checagem.
- **FR-008a**: Quando a proposição do item não está no lote da última coleta boa, o item NÃO DEVE receber `autoria NOVO` nem `autor hoje no NOVO` e DEVE levar a marca **"autoria não verificada"**. Um REQ com essa marca DEVE ser listado, além de contado. A marca não põe o item no grupo dos itens do NOVO (FR-007) (clarify, 24/10/2026; emenda ao PRODUCT.md, §5.8).
- **FR-009**: `relatoria NOVO` DEVE ser dada quando o relator do item na pauta está entre os deputados em exercício do NOVO no dia da checagem (PRODUCT.md, §5.8). NÃO DEVE consultar as tramitações nem o relator atual do inventário.
- **FR-010**: A marca **"leva apensado do NOVO"** DEVE ser dada quando a proposição do item é a referência (§5.2) de um ou mais itens do último `atual.json` bom que não são a própria proposição. A marca DEVE listar cada apensado com `Tipo número/ano`, link oficial e as etiquetas que ele tem no inventário.

**Resultado**

- **FR-011**: Nos itens listados de reunião realizada, o resultado DEVE ser classificado a partir de `situacaoItem` pela tabela do PRODUCT.md, §5.9, na ordem dada, valendo o primeiro rótulo que casar, e DEVE vir sempre com o texto original. Reunião convocada, cancelada ou "outra" NÃO DEVE ter resultado classificado.

**Alterações de pauta**

- **FR-012**: Para cada reunião que estava **convocada** na última checagem registrada, a checagem DEVE registrar como alteração: item que entrou, item que saiu, mudança de data ou hora de início (com o valor anterior e o novo), cancelamento e retirada da agenda. Uma reunião que some da consulta da janela DEVE ser buscada pelo identificador para decidir entre mudança de data, cancelamento e retirada da agenda; erro nessa busca falha a checagem (FR-022). A ordem dos itens NÃO DEVE contar (PRODUCT.md, §5.8).
- **FR-013**: A última checagem registrada DEVE ser a do arquivo de pauta mais recente, seja do mesmo dia ou de um dia anterior. Cada alteração DEVE ser registrada **uma única vez**, no arquivo do dia em que foi detectada, com o momento da checagem que a detectou (constituição, princípio V).
- **FR-014**: Quando não houver checagem anterior registrada, o arquivo do dia DEVE ser uma **linha de base**: as reuniões, nenhuma alteração e o motivo.
- **FR-015**: Mudanças em reunião realizada (por exemplo, `situacaoItem` preenchido depois) NÃO DEVEM ser registradas como pauta alterada; só atualizam o retrato da reunião.

**Arquivo do dia**

- **FR-016**: O arquivo `data/pautas/AAAA-MM-DD.json`, com a data da checagem em Brasília, DEVE guardar a **última checagem** do dia (momento da checagem, janela consultada, reuniões com seus itens e contagens) e **todas as alterações registradas no dia**, cumulativas entre as checagens do dia. Cada nova checagem do dia substitui a última checagem e acrescenta só as alterações novas.
- **FR-017**: Duas checagens seguidas sobre a mesma resposta da fonte DEVEM produzir o mesmo arquivo, exceto o momento da checagem, e NÃO DEVEM duplicar alteração. A ordem de reuniões, itens e alterações DEVE ser determinística, e o arquivo DEVE ter codificação, indentação e ordem de campos fixas, como os demais arquivos de dados.
- **FR-018**: O arquivo DEVE ter versão de formato.
- **FR-019**: A pauta NÃO DEVE entrar em `data/mudancas/`, e os seis tipos de evento do §5.6 NÃO DEVEM mudar (PRODUCT.md, §5.8).

**Checagem agendada**

- **FR-020**: A checagem DEVE rodar mais de uma vez por dia, num agendamento próprio, com horários (definidos no plano) que deem as três garantias do §5.8: uma checagem do mesmo dia que termina antes do envio das 07:17; uma depois do horário das reuniões; e uma no fim do dia.
- **FR-021**: Ao fim de cada checagem sem erro, o arquivo do dia DEVE ser commitado no repositório (PRODUCT.md, D8). O commit da checagem NÃO DEVE alterar nem perder o commit da coleta diária, mesmo que os dois agendamentos rodem perto um do outro.

**Falha visível**

- **FR-022**: Erro nas APIs de eventos, de pauta ou de deputados (rede, status HTTP, tempo esgotado depois de novas tentativas), resposta malformada, ou inventário e autores do lote ausentes ou ilegíveis DEVEM falhar a checagem inteira, com o motivo, sem gravar arquivo de pauta parcial (PRODUCT.md, §7; constituição, princípio III).
- **FR-023**: Em falha, a pasta `data/pautas/` DEVE ficar como estava, byte a byte, e a falha DEVE ser registrada com o momento da falha, o motivo e o momento da última checagem boa, de forma que a SEM e a PGP possam anunciá-la. A execução agendada DEVE terminar com erro.
- **FR-024**: A falha da checagem da pauta NÃO DEVE alterar o `atual.json`, o `anterior.json`, a pasta `data/mudancas/` nem o registro de status da coleta, e a falha da coleta NÃO DEVE impedir a checagem da pauta (PRODUCT.md, §7).

**Testes**

- **FR-025**: O comportamento DEVE ser coberto por testes com **pautas e eventos reais salvos** da CE e da CREDN, mais variações sintéticas derivadas deles para as alterações e as falhas, e NENHUM teste DEVE depender da internet (constituição, princípio IV). Os testes DEVEM cobrir, no mínimo: a janela e o filtro de tipo; a proposição do item; a separação entre listados, REQ e outros; cada etiqueta e a marca, com o caso real do PL 5432/2016 e do PL 3701/2020; cada rótulo do §5.9 e a exceção do "Requerimento de Retirada de Pauta"; cada tipo de alteração, a ordem que não conta e o registro único; a linha de base; e cada falha da User Story 6.

**Limites desta feature (não implementar)**

- **FR-026**: Esta feature NÃO DEVE implementar prazo de emendas (PRZ), envio ao Telegram nem formatação de mensagem (SEM), seção ou publicação da página (PGP), mudança no inventário (filtro, etiquetas, `atual.json`, `data/mudancas/`), nem audiências públicas, seminários e outros eventos não deliberativos. Os workflows do aviso e da página não mudam. O da coleta ganha só o passo que guarda o índice de autoria para a checagem (plano, research R8; ajuste levado ao mantenedor no OK do plano).

### Key Entities *(include if feature involves data)*

- **Reunião**: evento "Reunião Deliberativa" de uma comissão da lista, na janela. Atributos: identificador, comissão, início, situação (normalizada e original), link oficial, vista desde, itens listados, contagem de REQ, REQ do NOVO listados, contagem de outros.
- **Item da pauta**: uma entrada da pauta de uma reunião. Atributos: ordem, regime, título original, proposição do item, relator na pauta, etiquetas, marcas "leva apensado do NOVO" e "autoria não verificada", resultado (só em realizada).
- **Proposição do item**: a proposição relacionada, quando existe, ou a própria do item; quando a própria é REQ, é sempre ela (FR-004). Atributos: tipo, número, ano, ementa, link oficial.
- **Apensado do NOVO**: item do inventário cuja referência é a proposição de um item da pauta. Atributos: `Tipo número/ano`, link oficial, etiquetas.
- **Resultado**: rótulo do §5.9 e texto original de `situacaoItem`.
- **Checagem**: uma leitura da janela. Atributos: momento, janela consultada, reuniões.
- **Alteração de pauta**: mudança numa reunião convocada desde a última checagem registrada. Tipos: item entrou, item saiu, data ou hora mudou, reunião cancelada, reunião retirada da agenda. Atributos: reunião, detalhe, momento da checagem que a detectou.
- **Arquivo de pauta do dia**: `data/pautas/AAAA-MM-DD.json`, com a versão de formato, a última checagem e as alterações do dia (ou a marca de linha de base).
- **Registro de falha da pauta**: momento da falha, motivo e momento da última checagem boa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com eventos reais salvos, 100% das reuniões deliberativas da CE e da CREDN com início na janela estão no arquivo, e nenhum evento de outro tipo ou de fora da janela está.
- **SC-002**: Com a pauta real da CE de 28/10/2026, salva em 24/10/2026, o arquivo traz 19 PL listados e 1 REQ contado, cada um com link oficial.
- **SC-003**: Com a pauta real da CE de 15/04/2026 e o inventário de 24/10/2026, o PL 5432/2016 traz a marca "leva apensado do NOVO" com o PL 3701/2020 e as etiquetas `autoria NOVO` e `autor hoje no NOVO`, e vem antes dos itens sem ligação com o NOVO.
- **SC-004**: Em 100% dos itens de reuniões realizadas das fixtures, o resultado tem um rótulo do §5.9 e o texto original; cada um dos sete rótulos tem ao menos um caso de teste.
- **SC-005**: Em sequências simuladas de checagens, cada alteração (item entrou, item saiu, data ou hora mudou, cancelada, retirada da agenda) aparece exatamente uma vez no conjunto dos arquivos de pauta, e uma checagem repetida sobre a mesma fonte não acrescenta nenhuma.
- **SC-006**: Em 100% dos cenários de falha da User Story 6, a checagem termina com erro, o motivo fica registrado com o momento da última checagem boa, e a pasta `data/pautas/`, o `atual.json`, o `anterior.json`, a pasta `data/mudancas/` e o status da coleta ficam idênticos byte a byte.
- **SC-007**: O agendamento tem ao menos três checagens diárias, que cumprem as três garantias do §5.8.
- **SC-008**: A suíte inteira (ruff e pytest) passa sem acesso à internet.
- **SC-009**: Nada da fronteira "Não inclui" é implementado, e nenhum item da pauta é incluído ou excluído por etiqueta (constituição, princípios II e VII; PRODUCT.md, D2).

## Assumptions

- **COL, AGE, REL, MUD, AVI e PAG preservadas.** A PAU lê o último `atual.json` bom e não altera o inventário, o `status.json` da coleta, o aviso diário nem a página.
- **Autores do lote fora da checagem.** A coleta diária já baixa o lote. A checagem, que roda várias vezes por dia, não deve baixar o lote de novo; os autores necessários vêm do lote da última coleta boa. Como isso é guardado e lido é decisão do plano, com o custo no Git avaliado lá. (Plano: índice de autoria gravado pela coleta fora do Git e levado à checagem pelo cache do GitHub Actions.)
- **Deputados do NOVO lidos na checagem.** A lista de deputados em exercício do NOVO é lida a cada checagem, como a coleta faz no dia (PRODUCT.md, §5.4).
- **Janela por data de início.** "Convocadas para os próximos 7 dias e realizadas nos últimos 7" é lido como "todas as reuniões deliberativas com início entre D−7 e D+7, inclusive", com a situação que a Câmara registra. Assim a reunião do próprio dia nunca fica fora, e uma reunião passada ainda "Convocada" não some.
- **Situações.** "Convocada" é convocada; "Encerrada", "Encerrada (Final)" e "Encerrada (Termo)" são realizada; "Cancelada" é cancelada; qualquer outra é "outra", com o texto original. Situação nova não é formato alterado.
- **Identidade do item para alteração.** Um item é identificado na reunião pela proposição do item (ou, sem proposição, pelo título), contando ocorrências repetidas. O detalhe fica no plano.
- **Idempotência e o momento da checagem.** Reexecutar sobre a mesma fonte dá o mesmo conteúdo; só o momento da checagem muda, como o `gerado_em` do `atual.json` e o `verificado_em` do `status.json` (constituição, princípio V).
- **Registro da falha.** O registro de falha da pauta é separado do `status.json` da coleta, para que uma falha não apague a outra. Onde ele fica é decisão do plano. (Plano: `data/status-pauta.json`.)
- **Link oficial do evento.** A página do evento no portal da Câmara, montada a partir do identificador do evento; a forma exata fica no `research.md`.
- **Commit concorrente.** A checagem e a coleta commitam no mesmo branch; o plano define como evitar que um commit perca o do outro.
- **Dependência nova só com justificativa escrita no `plan.md`** (constituição, princípio I). A PAU não deve precisar de nenhuma.
- **Requisito para SEM e PGP (não implementado aqui).** O resumo semanal, o de quinta, o de véspera e a seção da página consomem este arquivo e o registro de falha.
