# Pesquisa: REL — Relatoria NOVO atual

Conferências feitas em 18/10/2026 contra a API real da Câmara (rede liberada), sobre 25 referências: as da lista atual (`data/atual.json`) mais PL 4501/2023, PL 937/2022 e PL 3514/2023. Nada disto substitui a captura de fixtures (primeira tarefa).

## R1. Contrato real de `/api/v2/proposicoes/{id}/tramitacoes`

**Decisão:** ler a resposta inteira de uma vez, sem paginação, e validar o formato campo a campo.

**Fatos conferidos (25 respostas):**

- A resposta tem `dados` (lista) e `links` (só `self`). **Não há `X-Total-Count`** nem link `next`, e as listas chegam inteiras (de 15 a 80 tramitações). Por isso a verificação de "total anunciado" que a COL faz em `/deputados` não existe aqui.
- Campos usados: `sequencia` (inteiro), `dataHora` (`AAAA-MM-DDTHH:MM`, sem segundos), `siglaOrgao`, `codTipoTramitacao` (**string**, não inteiro), `descricaoTramitacao`, `uriUltimoRelator` (URI de `/deputados/{id}` ou nulo).
- **A ordem da resposta é por data e hora, não por sequência**: aparecem `27` antes de `26` no mesmo dia (PL 937/2022) e `19` antes de `18` na mesma hora (PL 3514/2023). A regra DEVE ordenar por `sequencia` (spec FR-007).
- **`uriUltimoRelator` é "pegajoso"**: toda tramitação posterior à primeira designação repete o último relator, inclusive depois de ele devolver a matéria (PL 937/2022) e já em outra comissão (PL 3514/2023). Só a tramitação de **designação (320)** traz o designado; o campo das outras NÃO pode ser lido como relator.
- O cabeçalho `retry-after: 30` aparece em toda resposta, sem 429. Ignorado; o transporte já repete 429 e 5xx.

**Como a falha é detectada sem total anunciado (FR-012):** JSON inválido, `dados` ausente ou não lista, campo obrigatório ausente ou de tipo errado, `sequencia` repetida, lista vazia, qualquer link `next` (paginação inesperada) ou link fora de `https://dadosabertos.camara.leg.br/api/` falham a execução inteira. Lista vazia é falha porque toda proposição tem ao menos a apresentação.

**Alternativas rejeitadas:** conferir a última `sequencia` com `ultimoStatus_sequencia` do lote. O lote é do dia anterior e a API é ao vivo, então a diferença é normal e geraria falso alarme.

## R2. Regra do relator atual (máquina de estados por passagem)

**Decisão:** percorrer as tramitações em ordem de `sequencia`, com a comissão C vinda do lote (`ultimoStatus_siglaOrgao` da referência):

1. Só **órgãos que recebem a matéria** contam. São a comissão do lote e todo órgão que registra, na própria história, um recebimento (`500`) ou uma designação de relator (`320`), exceto `MESA`, `CCP` e `PLEN`. Tramitações dos demais são ignoradas: nas fixtures recapturadas aparece a `SGM` ("Notificações", `1005`), que só notifica e nunca recebe a matéria. A revisão independente mostrou que tratá-la como comissão apagaria o relator em silêncio (CE `320` → SGM → CE `501`).
2. Quando o órgão da tramitação muda (entre órgãos que recebem a matéria), começa uma **nova passagem**: o relator é zerado. É isto que faz a designação de uma passagem anterior não valer (decidido no clarify) e que descarta o relator da CESPO no PL 3514/2023.
3. Dentro de C: `320` (Designação de Relator) define o relator pelo `uriUltimoRelator` **dessa** tramitação e a data da designação; `507` (Recebimento - Relator(a) Sem Manifestação, a devolução), `1250` e `1255` (Saída de Relator(a) da Comissão) zeram o relator. Os demais tipos de relatoria (`170` devolução **ao** relator, `322` parecer, `501` recebimento do parecer) mantêm o relator.
4. No fim, o relator atual é o que sobrou. Se a última passagem **não** é em C, o item é "relator indeterminado" (divergência entre o lote e a API, por exemplo a matéria mudou de comissão entre as duas fontes).

**Por que não usar o tipo `500` (Recebimento) como "entrada na comissão":** o mesmo código serve para "Recebimento pela CE." e para "Mantido o parecer da Relatora…" (PL 1843/2022 e PL 3871/2024). Usá-lo zeraria o relator em pleno exercício e daria PL 1843/2022 sem relatoria. A mudança de órgão não depende de texto.

**Resultado nas 25 referências (inclui os 3 casos da sondagem):** coincide com o esperado em todos.

| Caso | Resultado | Por quê |
|---|---|---|
| PL 937/2022 (CE) | sem relator | `507` em 20/05/2026 depois da designação de Luiz Lima |
| PL 3514/2023 (CREDN) | sem relator | designação em CESPO; a passagem pela CREDN não tem designação |
| PL 4501/2023 (CE) | Luiz Lima (NOVO), desde 09/04/2025 | última designação na CE, sem devolução |
| PL 1843/2022 (CE) | Adriana Ventura (NOVO), desde 09/04/2025 | `500` "Mantido o parecer" não zera; `170` mantém |
| PL 3075/2022 (CE) | Adriana Ventura (NOVO) | designada em 09/04/2025 |
| PL 648/2024, PL 4781/2025, PL 330/2025 | sem relator | `507` no fim, ou nunca designado |

Nenhuma das 25 referências caiu em "indeterminado".

**Classificação dos tipos (tabela fechada no código):**

| `codTipoTramitacao` | Descrição | Efeito |
|---|---|---|
| 320 | Designação de Relator(a) | define o relator (id pelo `uriUltimoRelator` da própria tramitação) |
| 507, 1250, 1255 | Devolução sem manifestação; Saída de Relator(a) da Comissão (sem ou com parecer) | zera o relator |
| 170, 322, 501 | Devolução ao relator; Parecer do relator; Recebimento de parecer | mantém o relator |
| qualquer outro código cuja `descricaoTramitacao` contenha "relator" | desconhecido | **relator indeterminado** (FR-011) |
| demais | irrelevantes para relatoria | ignorados |

**Decidido pelo mantenedor (18/10/2026):** `1250` e `1255` (o relator saiu da comissão) encerram a relatoria. `PRODUCT.md` D3 só nomeava devolução sem manifestação e substituição; a regra será registrada em `PRODUCT.md` §5.4 (T028). Nos dados reais ela quase sempre é seguida de nova designação (23 das 33 saídas nas 25 histórias; nas outras 10 a matéria foi devolvida em seguida), então hoje nenhum resultado muda; o efeito aparece no dia em que alguém sair da comissão sem redesignação.

Outra situação ainda não coberta pelos dados reais: designação (`320`) sem `uriUltimoRelator` → indeterminado; tipo novo de relatoria → indeterminado.

## R3. Candidatos à relatoria NOVO pelo lote

**Decisão:** uma passagem a mais sobre os arquivos de proposições (já baixados) lê a coluna `ultimoStatus_uriRelator` e reúne os ids das linhas cujo órgão está em `comissoes` e cujo relator é deputado do NOVO em exercício. São candidatos as próprias linhas e os apensados cuja raiz está nesse conjunto. Só a confirmação pelas tramitações (R2) dá a etiqueta.

**Por quê:** `uriUltimoRelator` aponta sempre para o último relator designado (R1), então o relator atual, se existir, é ele. Quem tem outro relator na referência nunca tem `relatoria NOVO`. Isso evita ler tramitações de todo o estoque (cerca de 1.500 referências na CE e na CREDN).

**Volume:** referências lidas = referências de todos os itens com etiqueta de autoria (spec, clarify 1) ∪ referências dos candidatos. Hoje, algo como 25 + 10 a 30. Mais as consultas de partido (R4). Tudo sequencial, com as novas tentativas do transporte.

**Medição real (18/10/2026, `uv run python -m monitor_comissoes`):** 105 itens (CE 96, CREDN 9), 54 consultas de tramitações e 14 de `/deputados/{id}`, execução inteira em 3 min 55 s (inclui o download do lote). Os 105 itens: 46 não apensados (a sondagem contou 48 sem apensados) e 59 apensados, 44 deles à raiz PL 3961/2004, cuja relatora é Adriana Ventura. A sondagem de 17/10 (56 itens) contava o relator do último status de cada apensado, que fica congelado; a herança da relatoria da principal (D4) é o que faz o total subir. Nenhum item ficou com relator indeterminado.

**Alternativa rejeitada:** ler tramitações de todas as referências do estoque bruto (≈1.500 chamadas por dia, sem ganho porque o candidato já vem do lote).

## R4. Partido de hoje do relator

**Decisão:** `GET /api/v2/deputados/{id}` e ler `dados.ultimoStatus.siglaPartido` e `ultimoStatus.nomeEleitoral`, um pedido por relator distinto. Relatores que estão na lista de em exercício do NOVO dispensam a consulta (`partido_hoje = "NOVO"`, nome já conhecido).

**Conferido:** 220560 (Thiago de Joaldo, REPUBLICANOS), 204455 (Luiz Lima, NOVO), 74090 (Átila Lins, PSD). Resposta de um objeto só, sem paginação. Falha (HTTP, JSON, campo ausente) falha a execução inteira com a categoria `api_deputados`, já existente.

**Limite:** quem tem `ultimoStatus.situacao` diferente de "Exercício" (licenciado) pode vir com `siglaPartido = NOVO` sem constar da lista de em exercício. A etiqueta segue só a lista (PRODUCT.md §8); `partido_hoje` é informativo.

## R5. Categorias de falha das tramitações (decidido em 18/10/2026)

**Decisão:** não criar categoria nova. Usar as existentes:

- Rede, HTTP 5xx/429 depois das tentativas do transporte → `fonte_indisponivel` (já repetível pela AGE).
- Resposta com formato inesperado (JSON inválido, campo ausente ou de tipo errado, lista vazia, `sequencia` repetida, link `next`, link fora da API) → `formato_alterado` (não repetível: repetir não conserta formato).
- Falha ao obter o partido do relator → `api_deputados` (já existe).

**Por quê:** o motivo no texto do erro já diz qual API falhou; nada muda no contrato do `status.json` da AGE; e resposta malformada deixa de ser repetida 4 vezes à toa (uma categoria nova, copiando `api_deputados`, entraria em `REPETIVEIS` e repetiria tudo).

**Alternativa rejeitada:** `api_tramitacoes` próprio. Ganho só de rótulo, ao custo de uma emenda no contrato da AGE.

## R6. Formato do `atual.json`

**Decisão:** `versao_formato` do `atual.json` passa de 1 para 2, com os campos novos do item descritos em [contracts/atual-json.md](contracts/atual-json.md). A AGE lê apenas `gerado_em`, `dados_camara_em` e `total_itens` do `meta` (`retrato_do_atual`), e o `versao_formato` do `status.json` é outro campo; nada quebra. `meta` não muda de forma.

## R7. Fixtures

**Decisão:** estender `tests/capturar_fixtures.py` (com rede, uma vez) para:

1. Acrescentar às linhas do lote os casos: PL 937/2022, PL 3514/2023, PL 4501/2023 (+ cadeias completas), as linhas cujo `ultimoStatus_uriRelator` é de deputado do NOVO na CE e na CREDN e **os apensados dessas raízes** (herança real), mais um PL de autoria do NOVO com relator de outro partido (PL 3871/2024, já presente).
2. Salvar as respostas reais de tramitações em `tests/fixtures/camara/tramitacoes/{id}.json` para cada referência selecionada, e as de `/deputados/{id}` dos relatores em `tests/fixtures/camara/deputados/{id}.json`.
3. Registrar tudo no `manifesto.json` e no `README.md` das fixtures.

Casos que **não existem** nos dados reais (devolução e redesignação em sequências inventadas, passagem anterior pela mesma comissão, tipo novo de relatoria, designação sem relator, sequência repetida) são derivados dentro do próprio teste a partir de tramitações reais, como a COL fez com o ciclo de apensação. Nenhum arquivo derivado fica no diretório.

**Risco:** recapturar o lote muda o ponto de partida dos testes de COL e AGE (data dos dados, deputados em exercício). O README já prevê o ajuste; a tarefa de recaptura inclui rodar a suíte e conferir cada diferença.

## R8. Dependências e configuração

**Decisão:** nenhuma dependência nova; só `urllib`, `json`, `csv`. Nenhuma chave nova em `config.toml`: os órgãos de apoio e a tabela de tipos são regra de domínio fixa no código (R2), como os tipos PL/PLP.

## R9. Limites conhecidos (revisão independente, 18/10/2026)

- **Corpo que não é JSON** numa resposta 200 (por exemplo, página de erro de gateway) em `/tramitacoes` é `formato_alterado` e não é repetido pela AGE, enquanto o mesmo defeito em `/deputados` (lista do NOVO) é `api_deputados`, repetível. Mantido como decidido (decisão 2): a mensagem diz o motivo. Se na prática o gateway devolver HTML com frequência, tratar "corpo não JSON" como `fonte_indisponivel`.
- **Passagem por "Devolução à CCP" (`1010`) e volta à mesma comissão** conta como a mesma passagem (a CCP é órgão de apoio): a designação anterior seguiria valendo. Só há uma ocorrência nas fixtures, sem relator em vigor. Risco teórico, sem regra no `PRODUCT.md`.
- **Defasagem lote × API:** o candidato nasce do lote, gerado de madrugada. Uma designação do NOVO feita depois da geração só aparece no dia seguinte (limite do `PRODUCT.md` §8). Não há trilha de auditoria de candidatos × confirmados no `meta`; fica como melhoria futura.
- **Fixtures sintéticas:** o transporte falso só serve tramitações neutras (`tramitacoes_sinteticas`) nos dois testes que trocam comissões ou anos lidos.
- **Suposição do código, não do `PRODUCT.md`:** toda comissão que recebe a matéria registra um `500` (Recebimento) ou um `320` (Designação) na própria história. Vale para as 63 histórias das fixtures. Se uma comissão aparecer só com outros tipos (por exemplo, a matéria foi enviada à CFT depois da geração do lote e a CFT ainda não registrou recebimento), ela é ignorada e o relator da passagem anterior continua valendo até o dia seguinte. Alternativa registrada: tratar como serviço só uma lista conhecida de tipos de notificação (`1005`, `1050`). Revisar se a Câmara mudar o padrão.
- **Referência compartilhada e defasagem do lote:** dois apensados da mesma raiz podem ser tratados de forma diferente se o lote aponta, para a raiz, um relator de outro partido e as tramitações já dizem que o relator é do NOVO. O candidato é definido pelo relator do último status da referência (`deve_ler_tramitacoes`); um apensado só de relatoria não entra nesse dia, o apensado com autoria entra. Some no dia seguinte, quando o lote alcança a API.
