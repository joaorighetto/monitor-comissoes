# Pesquisa (Phase 0): MUD — Mudanças desde ontem

Fatos conferidos em 18/10/2026 nas fixtures salvas (`tests/fixtures/camara/`) e na API pública da Câmara. A spec não deixou nenhum `[NEEDS CLARIFICATION]`; este documento fixa as escolhas técnicas e registra o que cada uma troca.

## R1. De onde vem o estado de quem saiu

**Decisão:** do lote do dia, que a coleta já baixa. Os ids do retrato anterior entram no conjunto de linhas lidas (junto com as raízes das cadeias de apensação), e a proposição de cada um é avaliada com `resolver_referencia`, como qualquer item.

**Por quê:** o `atual.json` guarda só os itens da lista, então não diz para onde um item foi. O lote tem, por proposição, `ultimoStatus_siglaOrgao`, `ultimoStatus_descricaoSituacao`, `uriPropPrincipal`, `ultimoStatus_dataHora` e `ultimoStatus_sequencia` (docs/fontes.md, lista de colunas). Uma fonte só para o estado de hoje é mais simples de conferir do que lote mais API (PRODUCT.md, D7).

**Custo:** a coluna `ultimoStatus_sequencia` passa a ser exigida em `proposicoes-*.csv` (falta de coluna = "formato alterado", como as demais) e entra em `Proposicao`. A leitura já filtra por `ids`, então o custo é nulo para as linhas fora do conjunto.

**Descartado:** consultar `/proposicoes/{id}` na API para cada item que saiu. Daria um segundo estado de "hoje", ao vivo, que poderia divergir do lote do dia usado no resto da coleta.

**Proposição ausente do lote:** o motivo é "não determinado", com a ficha e o texto "proposição ausente do lote". Não é falha: o lote vale para o dia, e nada some em silêncio.

## R2. Situações finais (motivo "situação final")

**Fato:** a Câmara publica a lista de situações em `/api/v2/referencias/proposicoes/codSituacao` (consultada em 18/10/2026; 99 entradas). Nas linhas PL/PLP das fixtures aparecem apenas 7 situações (Tramitando em Conjunto, Aguardando Parecer, Aguardando Apreciação pelo Senado Federal, Pronta para Pauta, Aguardando Designação de Relator(a), Transformado em Norma Jurídica, Aguardando Despacho do Presidente da Câmara dos Deputados (Chancela)). "Arquivada" não aparece nas fixtures do lote, mas existe na lista oficial (cod 923).

**Decisão (proposta ao mantenedor, plan.md D1):** tabela fechada, em código, sobre o texto exato de `ultimoStatus_descricaoSituacao`:

| Código do motivo | Situações |
|---|---|
| `arquivado` (ou `arquivado_art_105`, ver R3) | Arquivada |
| `transformado_em_norma` | Transformado em Norma Jurídica |
| `aprovado_segue_ao_senado` | Aguardando Apreciação pelo Senado Federal; Aguardando Envio ao Senado Federal; Enviada ao Senado Federal |
| `encerrado` | Vetado totalmente; Recusado; Retirado pelo(a) Autor(a); Devolvida ao(à) Autor(a); Transformado em nova proposição; Perdeu a Eficácia; Tramitação Finalizada |

**Por quê:** o PRODUCT.md §5.6 cita "aprovado, transformado em norma, arquivado" como exemplos de situação final, mas não lista os textos da Câmara. Sem uma lista, o código teria de adivinhar. A lista é só de *motivo*: não inclui nem exclui item (constituição, II).

**Efeito de uma situação fora da tabela:** o motivo cai para "foi para outro órgão" (ou "perdeu as etiquetas"), e o destino sempre traz a situação em texto. Nenhuma informação se perde, só a rotulagem.

**Descartado:** classificar por padrão de texto (por exemplo, "Arquiv"). Textos como "Aguardando Remessa ao Arquivo" (931) e "Aguardando Despacho de Arquivamento" (940) não são arquivamento concluído.

## R3. "Arquivado, art. 105"

**Fato:** nas respostas reais de tramitações salvas, as 9 tramitações de código `502` ("Arquivamento") trazem no `despacho` "Arquivado nos termos do Artigo 105 do Regimento Interno da Câmara dos Deputados." (por exemplo, proposição 2086175, sequência 42, 31/01/2019; 495615, sequências 36 e 59). O tipo `640` (desarquivamento) e `194` (requerimento) também citam o artigo, mas não são arquivamento.

**Decisão:** o motivo é `arquivado_art_105` se, entre as tramitações do intervalo da referência, houver uma de código `502` cujo `despacho` casa com `art(igo|.)? 105` (sem diferenciar maiúsculas). Se a situação é "Arquivada" e nenhuma tramitação do intervalo casa, o motivo é `arquivado`, sem a menção. `Tramitacao` ganha o campo `despacho` (texto, pode ser vazio).

**Por quê:** o lote só guarda o último status, que pode não ser o arquivamento; as tramitações do intervalo já são lidas para o evento (R6) e dizem exatamente o que foi lançado.

**Limite conhecido:** a Câmara pode redigir outro despacho para outro tipo de arquivamento. Ele sai como `arquivado`, sem a menção, e a ficha oficial resolve a dúvida. Isso casa com o PRODUCT.md, §5.7: a menção só é feita quando for o caso, e a contagem das legislaturas continua em aberto.

## R4. Parecer

**Fato:** o tipo `322` ("Parecer do(a) Relator(a)") aparece 71 vezes nas fixtures, com despachos como "Parecer do Relator, Dep. Lucas Ramos (PSB-PE), pela aprovação, com substitutivo." O tipo `501` ("Recebimento - Relator(a)") registra a apresentação do PRL no mesmo instante; `330` é a leitura e `336`, a aprovação do parecer.

**Decisão (plan.md D4):** gera o evento `parecer` a tramitação de código `322`, no intervalo, cujo órgão é a comissão do item. Uma só tramitação `322` gera um evento, e várias no intervalo geram um evento com todas em `tramitacoes`. O conteúdo do parecer não é registrado (PRODUCT.md, §9).

**Por quê:** `322` é o lançamento do parecer; `501` e `330` descrevem o mesmo ato e duplicariam o evento, e `336` é a votação, que o PRODUCT.md não pede.

## R5. Retrato anterior, rotação e reexecução no mesmo dia

**Problema:** o `atual.json` é sobrescrito a cada execução. Numa reexecução no mesmo dia ele já é o de hoje, e comparar com ele esvaziaria o arquivo do dia.

**Decisão (clarify, Q5):** cópia rotativa `data/anterior.json`, sem depender do `git`. O "dia" de um retrato é a data de `meta.gerado_em` em Brasília.

| `atual.json` no disco | Retrato anterior | `anterior.json` depois | Arquivo do dia |
|---|---|---|---|
| Não existe | nenhum | não muda | linha de base, "primeiro retrato" |
| Dia anterior, versão 3, válido | ele mesmo | passa a ser ele | comparação |
| Dia anterior, outra versão | ele mesmo | passa a ser ele | linha de base, "formato anterior incompatível" |
| Dia anterior, ilegível ou fora do contrato | — | não muda | **falha** (`interna`) |
| Dia de hoje | `anterior.json` (se existe e é válido) | não muda | comparação, ou linha de base se não existe |
| Dia de hoje, `anterior.json` ilegível ou fora do contrato | — | não muda | **falha** (`interna`) |
| Data futura | — | não muda | **falha** (`interna`) |

**Idempotência:** na primeira execução do dia o `atual.json` é do dia anterior e a cópia rotaciona; na segunda, o `atual.json` já é de hoje e a cópia não é tocada. As duas comparam o mesmo par de retratos. O arquivo do dia só traz `dados_camara_em` do lote (estável), nunca a hora da execução.

**Dia perdido:** se ontem a coleta falhou, o `atual.json` continua sendo o de anteontem e é o retrato anterior; o arquivo cobre os dois dias e diz as datas (FR-004).

**Descartados:** (a) histórico do Git: faria o código depender do `git` e do checkout raso do Actions, e os testes teriam de montar repositórios; (b) um arquivo por dia: duplica o que o Git já guarda (PRODUCT.md, D8).

## R6. Tramitações do intervalo

**Fatos:** a API de tramitações devolve a lista inteira, ordenada por data, e a ordem real é a `sequencia` (docs/fontes.md: a 27 aparece antes da 26 no mesmo dia). Ela não pagina (REL, R1). Está ao vivo, enquanto o lote é de madrugada.

**Decisão:** para uma referência cuja sequência mudou, o intervalo é `anterior < sequencia <= hoje`, ordenado por sequência, onde `hoje` é `ultimoStatus_sequencia` do lote de hoje. A tramitação de sequência `hoje` DEVE existir na resposta; senão, a resposta é incoerente com o lote e a execução falha (`formato_alterado`). Se a sequência de hoje for **menor** que a do retrato anterior para a mesma referência, também falha.

**Por quê:** o limite superior impede que lançamentos feitos depois da geração do lote entrem no arquivo de hoje e o façam diferir numa reexecução (constituição, V). Eles entram no dia seguinte, quando o lote os alcança.

**Referência diferente** (o item passou a ser apensado a outra principal, deixou de ser, ou a raiz mudou): as sequências de duas proposições não se comparam. Vale a regra de data, igual à de R7: tramitações da **nova** referência com data igual ou maior que a data de `dados_camara_em` do retrato anterior e sequência até a de hoje.

**Cache:** uma resposta por referência dentro da execução (o apensado e a principal compartilham a leitura).

## R7. Motivo de "entrou"

**Problema:** o retrato anterior só guarda os itens da lista. Um item que entrou pode ter chegado à comissão agora, ou já estar lá e ter ganhado uma etiqueta. O estado do lote de ontem não foi guardado.

**Decisão (plan.md D5):** ler as tramitações da referência até a sequência de hoje e procurar a **chegada à comissão**: a tramitação que inicia a **passagem mais recente** da referência pela comissão. "Passagem" tem a definição da REL (`relatoria.py`): só órgãos que recebem a matéria (recebimento `500` ou designação `320`) e a própria comissão contam; **MESA, CCP e PLEN nunca iniciam passagem**. Isso importa: nas fixtures, muitas mudanças de órgão para a CE são só a matéria passando pela MESA ("Notificação de Apensação") e voltando, sem chegada nova. A função `relatoria.inicio_da_passagem(tramitacoes, comissao)` reaproveita o mesmo laço de `relator_atual`. Se a data dela é igual ou maior que a data de `dados_camara_em` do retrato anterior (em Brasília): `chegou_a_comissao`. Senão, se o item tem etiqueta: `ganhou_etiqueta` (qual). Senão (candidato com relator indeterminado e sem etiqueta): `nao_determinado`.

**Por quê:** é a única fonte que responde "desde quando está aqui". A comparação é por data porque muitas tramitações trazem só a data (`T00:00`).

**Limite conhecido:** a janela é de um dia. Um item que chegou à comissão na madrugada do dia do lote anterior, antes da geração dele, sairia como "chegou à comissão" mesmo já estando lá sem etiqueta. É o preço de não guardar o estado de ontem fora da lista; fica registrado no `PRODUCT.md` (D6 do plano). A alternativa, guardar no retrato todos os candidatos da coleta, aumentaria o `atual.json` e mudaria o que ele significa.

## R8. Gravar quatro arquivos, tudo ou nada

**Fato:** `status.gravar_par` já grava dois arquivos com temporários e restauração do primeiro se a troca do segundo falhar (AGE).

**Decisão:** `saida.gravar_todos(escritas)` generaliza o mesmo algoritmo para N pares `(texto, destino)`: todos os temporários primeiro; depois as trocas em ordem; se uma falhar, restaura as já trocadas, em ordem inversa, ao conteúdo anterior (ou as remove, se não existiam). `gravar_par` vira um invólucro, e os testes dele continuam valendo.

**O workflow:** só a morte do processo entre duas trocas deixa arquivos trocados pela metade. O passo de falha do workflow já restaura o `atual.json` do Git; passa a restaurar também `anterior.json` e `data/mudancas`, cada um com `|| true` (um caminho que não existe no Git faria o `git checkout` abortar tudo se fosse num comando só), e a remover o arquivo de mudanças novo, não rastreado.

## R9. Categorias de falha

**Decisão (plan.md D2):** nenhuma categoria nova.

| Situação | Categoria | Repete? |
|---|---|---|
| Rede ou HTTP nas tramitações | `fonte_indisponivel` (existente) | sim |
| Tramitações malformadas, sem a sequência de hoje, ou sequência de hoje menor que a anterior | `formato_alterado` | não |
| Retrato anterior ilegível, fora do contrato ou de data futura | `interna` | não |
| Falha ao gravar | `interna` | não |

**Por quê:** o contrato do `status.json` da AGE lista as categorias; uma nova mudaria o contrato e os consumidores futuros (AVI e PAG). A mensagem de cada falha diz o motivo e o arquivo.

## R10. Volume e tempo

Em dia comum, de 0 a 10 referências com sequência alterada, mais as de itens que entraram ou saíram. Na posse (01/02/2027) e na recomposição das comissões, estimam-se algumas dezenas, até uns 150 pedidos, sequenciais e de menos de 1 s: dois a três minutos. A REL já mede cerca de 60 pedidos por execução. O job tem teto de 240 min e o `timeout` interno é de 200 min.

## R11. Dependências

Nenhuma nova. `json`, `re`, `datetime` e `dataclasses` bastam. Não há biblioteca externa para datas nem para comparar JSON.

## R12. Testes

Nenhum teste usa rede. Os retratos sintéticos são derivados do `data/atual.json` real (23 itens): o teste copia o documento, altera um campo por vez e compara. As tramitações vêm de respostas reais salvas, injetadas por função.

| Caso | Origem |
|---|---|
| Arquivado, art. 105 | tramitações reais de 2086175 (502, seq. 42) |
| Arquivado sem menção | a mesma tramitação com o despacho trocado, dentro do teste |
| Parecer | 322 real de 2330962; item sintético com `comissao` igual ao órgão |
| Relator designado, devolvido, substituído | designação (320) e devolução (507) reais das fixtures da REL |
| Entrou por chegada, entrou por etiqueta | tramitações reais com mudança de órgão |
| Linha de base (3 motivos) e reexecução no mesmo dia | arquivos em `tmp_path` |
| Falhas | respostas de tramitações malformadas, vazias, sem a sequência de hoje; retratos corrompidos |

Nenhuma fixture precisa ser capturada ao vivo para os casos acima, exceto o que faltar; qualquer captura nova entra por `tests/capturar_fixtures.py` e fica registrada em `tests/fixtures/camara/README.md`.

## R13. Regras que precisam ir para o PRODUCT.md

Registradas como tarefa própria (plan.md D6): linha de base com motivo; retrato anterior por data; precedência dos motivos de saída; tabela de situações finais; intervalo das tramitações e seu limite superior; janela de um dia da entrada; arquivo do dia sem teto de eventos. Fatos de API novos (códigos 322 e 502, `despacho`, lista de situações) vão para `docs/fontes.md`.
