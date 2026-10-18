# Fontes de dados — resultado da sondagem

Consultas feitas em **17/10/2026** durante o brainstorm de produto. Os números são uma fotografia desse dia e servem para dimensionar o produto, não como dado publicado.

## 1. Arquivos em lote (Dados Abertos da Câmara)

Página: <https://dadosabertos.camara.leg.br/swagger/arquivos.html>

URLs usadas (CSV, separador `;`, UTF-8 com BOM, campos entre aspas):

- `https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv`
- `https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/csv/proposicoesAutores-{ano}.csv`
- `https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/csv/proposicoesTemas-{ano}.csv`

### O que foi confirmado

- **Os arquivos são atualizados todo dia.** Em 17/10/2026, o `Last-Modified` era 04:34 UTC para `proposicoes-2025.csv` e 05:21 UTC para `proposicoesAutores-2025.csv` (de 01h34 a 02h21 em Brasília).
- **Cada arquivo anual reúne as proposições apresentadas naquele ano**, não as que tramitaram nele. Em `proposicoes-2025.csv`, 107.529 de 107.587 linhas foram apresentadas em 2025; as outras são casos residuais. Por isso, **montar o estoque de uma comissão exige ler todos os anos** dos quais ainda pode haver proposição tramitando.
- O servidor não comprime as respostas: pedir `Accept-Encoding: gzip` não reduz o `Content-Length`. Os CSV de `proposicoes` de 1990 a 2026 somam cerca de 830 MB; somados aos `proposicoesAutores`, o total baixado foi de 1,2 GB. A partir de 2003, só os `proposicoes` somam cerca de 720 MB, e com os autores o total fica perto de 1 GB. Os anos recentes pesam mais: 2023 e 2024 têm cerca de 53 MB cada, e 2025, 90 MB.
- **A Câmara regenera todos os arquivos anuais todo dia, inclusive os antigos.** Em 17/10/2026, `proposicoes-2004.csv`, `-2011` e `-2019` tinham `Last-Modified` entre 04:31 e 04:34 UTC do mesmo dia, cada um com um ETag novo. Download condicional por ETag ou `Last-Modified` não reduz o volume.
- O arquivo traz proposições de todos os tipos (REQ, PRL, EMC, RIC…). O tipo PL é uma fração pequena.

### Colunas de `proposicoes-{ano}.csv`

`id; uri; siglaTipo; numero; ano; codTipo; descricaoTipo; ementa; ementaDetalhada; keywords; dataApresentacao; uriOrgaoNumerador; uriPropAnterior; uriPropPrincipal; uriPropPosterior; urlInteiroTeor; urnFinal; ultimoStatus_dataHora; ultimoStatus_sequencia; ultimoStatus_uriRelator; ultimoStatus_idOrgao; ultimoStatus_siglaOrgao; ultimoStatus_uriOrgao; ultimoStatus_regime; ultimoStatus_descricaoTramitacao; ultimoStatus_idTipoTramitacao; ultimoStatus_descricaoSituacao; ultimoStatus_idSituacao; ultimoStatus_despacho; ultimoStatus_apreciacao; ultimoStatus_url`

- **Último status completo**: órgão (`ultimoStatus_siglaOrgao` e `ultimoStatus_idOrgao`), situação, despacho, regime, apreciação e relator (`ultimoStatus_uriRelator`, uma URI de `/deputados/{id}` **sem partido**).
- `uriPropPrincipal` vem preenchido em **todas** as 710 proposições "Tramitando em Conjunto" do estoque da CE e da CREDN. Assim, dá para subir na cadeia de apensação até a proposição principal só com o arquivo em lote.
- A coluna `ano` nem sempre é igual ao ano de `dataApresentacao`: as duas coincidem em 48.270 das 107.587 linhas de 2025. Para identificar a proposição, use `siglaTipo numero/ano` como a Câmara exibe e confira na página oficial.

### Colunas de `proposicoesAutores-{ano}.csv`

`idProposicao; uriProposicao; idDeputadoAutor; uriAutor; codTipoAutor; tipoAutor; nomeAutor; siglaPartidoAutor; uriPartidoAutor; siglaUFAutor; ordemAssinatura; proponente`

- **Há partido do autor** (`siglaPartidoAutor`), ao contrário da API `/proposicoes/{id}/autores`.
- **O partido registrado é o da data da autoria, não o atual.** Exemplos verificados:
  - Luiz Lima (id 204455) aparece como PSL em proposições de 2019 a 2022, UNIÃO em 02/2022, PL de 03/2022 a 04/2025 e NOVO de 03/2025 a 09/2026. A API `/deputados/204455` dá NOVO como partido atual.
  - Ricardo Salles (id 220633) aparece como PL de 02/2023 a 08/2024 e NOVO de 08/2024 em diante.
  - Há sobreposição curta entre os dois últimos partidos de Luiz Lima: PL até 23/04/2025 e NOVO desde 31/03/2025. Provavelmente reflete a data da proposição, e não a da assinatura. Isso não foi investigado.
- Para autores que não são deputados (Senado, Executivo), `idDeputadoAutor` vem vazio.

### Colunas de `proposicoesTemas-{ano}.csv`

`uriProposicao; siglaTipo; numero; ano; codTema; tema; relevancia`

## 2. API v2

Documentação: <https://dadosabertos.camara.leg.br/swagger/api.html> (JSON em `/api/v2/api-docs`)

### `/api/v2/proposicoes` sem datas devolve só a tramitação recente — **confirmado**

Diz a descrição oficial do endpoint: "por padrão, são retornadas todas as proposições que foram apresentadas ou tiveram alguma mudança de situação nos últimos 30 dias".

- `?siglaPartidoAutor=NOVO&siglaTipo=PL&itens=100` sem datas devolveu 25 itens, todos de 2021 a 2026.
- **O intervalo entre `dataInicio` e `dataFim`, e também entre `dataApresentacaoInicio` e `dataApresentacaoFim`, tem limite de 3 meses.** Acima disso, a resposta é HTTP 400 com "A diferença entre as datas não pode ser maior que 3 meses".
- A listagem não traz o status. Seria preciso consultar `/proposicoes/{id}` item a item.
- Volume diário: `?siglaTipo=PL,PLP&dataInicio=2026-10-15&dataFim=2026-10-15` devolveu 53 proposições, em menos de 1 segundo. Era período eleitoral, com a Câmara em ritmo reduzido; em semanas normais o número deve ser maior.
- **Conclusão: a API não serve para montar o estoque.** Serve para detalhar e conferir itens específicos.

### `/api/v2/proposicoes/{id}/tramitacoes` e o "último relator"

- `uriUltimoRelator` aponta para o **último relator designado**, e não para o relator atual na comissão:
  - **PL 937/2022** (id 2319917), na CE com situação "Aguardando Designação de Relator(a)": o relator Luiz Lima devolveu a matéria sem manifestação em 20/05/2026, mas `uriUltimoRelator` continua sendo ele.
  - **PL 3514/2023** (id 2373721), na CREDN com situação "Aguardando Designação de Relator(a)": `uriUltimoRelator` é Luiz Lima, que foi relator na **Comissão do Esporte** (CESPO), a comissão anterior.
- **Fatos da API de tramitações, conferidos em 18/10/2026 em 63 histórias** (feature REL; detalhes em `specs/003-relatoria-novo-atual/research.md`):
  - A resposta não traz `X-Total-Count` nem link de próxima página: vem inteira.
  - A ordem é por data e hora, não por `sequencia` (aparece a 27 antes da 26 no mesmo dia). A leitura deve ordenar por `sequencia`.
  - `uriUltimoRelator` repete o último relator designado em **toda** tramitação seguinte, também depois da devolução e em outra comissão. Só a tramitação de designação (`codTipoTramitacao` `320`) diz quem foi designado.
  - `codTipoTramitacao` vem como texto. Encerram a relatoria `507` (Recebimento - Relator(a) Sem Manifestação) e `1250`/`1255` (Saída de Relator(a) da Comissão). Mantêm: `170`, `322`, `501`.
  - O tipo `500` (Recebimento) serve a "Recebimento pela CE." e também a "Mantido o parecer da Relatora…": não marca sozinho a entrada na comissão.
  - Órgãos como a `SGM` aparecem só com notificações (`1005`) e nunca recebem a matéria.
- O despacho registra o partido do relator **na data da designação**. Por exemplo, em 09/04/2025: "Designado Relator, Dep. Luiz Lima (PL-RJ)". Depois disso, os despachos já mostram "(NOVO-RJ)".
- `/proposicoes/{id}` → `statusProposicao` bate com `ultimoStatus_*` do arquivo em lote nos dois casos conferidos.

### `/api/v2/deputados`

- `/deputados?siglaPartido=NOVO` devolve os deputados **em exercício** do NOVO. Em 17/10/2026, eram Adriana Ventura (204528), Gilson Marques (204365), Luiz Lima (204455), Marcel van Hattem (156190) e Ricardo Salles (220633).
- `/deputados/{id}` → `ultimoStatus.siglaPartido` dá o partido atual (ou o último).

## 3. Estoque na CE e na CREDN em 17/10/2026

Critério: `ultimoStatus_siglaOrgao` igual a `CE` ou `CREDN` em qualquer arquivo de 1990 a 2026. Não há PL anterior a 2003 nessas comissões.

| | CE | CREDN |
|---|---|---|
| PL | 1.356 | 159 |
| PLP | 12 | 4 |
| PDL | 42 | 16 |
| Todos os tipos (inclui REQ) | ~4.500 | ~2.700 |

Situação dos PL, PLP, PEC e PDL:

| Situação | CE | CREDN |
|---|---|---|
| Tramitando em Conjunto (apensados) | 702 | 38 |
| Aguardando Parecer | 431 | 66 |
| Pronta para Pauta | 175 | 15 |
| Aguardando Designação de Relator(a) | 102 | 60 |

- Dos apensados da CE, 668 têm a proposição principal na própria CE. Em 8 casos a principal está na CFT, e em 2 está fora de comissão.
- Há apensados com último status muito antigo (por exemplo, 2013). Para eles, o status útil é o da proposição principal.

### Filtro NOVO (PL e PLP)

| Critério | Itens |
|---|---|
| A — algum autor assinou como NOVO (partido na data) | 20 (19 com o NOVO como primeiro autor) |
| B — algum autor é hoje deputado do NOVO | 18 |
| R — último relator é hoje deputado do NOVO | 34 |
| **A ∪ B ∪ R** | **56** (46 na CE, 10 na CREDN; 53 PL e 3 PLP) |
| A ∪ B ∪ R sem os apensados | 48 |

- B − A: 4 itens. São PL de deputados que entraram no NOVO depois de apresentá-los, como os de Luiz Lima e Ricardo Salles assinados quando eram do PL.
- A − B: 6 itens. São PL de quem assinou como NOVO e hoje não é deputado do NOVO, por ter mudado de partido ou deixado o mandato.
- Dos 34 do critério R, vários têm o relator do NOVO **apenas como último relator histórico**: devolveu sem manifestação ou foi relator em outra comissão.
- 10 deputados já assinaram proposições como NOVO em algum momento.

**Ordem de grandeza: cerca de 50 itens.** É uma lista que cabe numa página e num resumo diário, sem precisar de paginação ou busca sofisticada.

## 4. Arquivamento ao fim da legislatura (RICD, art. 105)

Fonte oficial: Regimento Interno, Resolução nº 17/1989, texto atualizado —
<https://www2.camara.leg.br/legin/fed/rescad/1989/resolucaodacamaradosdeputados-17-21-setembro-1989-320110-normaatualizada-pl.html>

Alteração: Resolução nº 33/2022 —
<https://www2.camara.leg.br/legin/int/rescad/2022/resolucaodacamaradosdeputados-33-4-agosto-2022-793091-publicacaooriginal-165882-pl.html>

Texto vigente (trechos relevantes, texto legal):

> Art. 105. Finda a legislatura, arquivar-se-ão todas as proposições que no seu decurso tenham sido submetidas à deliberação da Câmara e ainda se encontrem em tramitação, salvo: (Caput com redação dada pela Resolução nº 33, de 2022)
> I, II, III e V – (Revogados pela Resolução nº 33, de 2022)
> IV – as de iniciativa popular;
> VI – as destinadas à elaboração das espécies normativas referidas no art. 59 da Constituição Federal que não tenham tramitado por 3 (três) legislaturas completas; (em vigor a partir de 1º/2/2023)
> VII – os projetos de código;
> VIII – as relativas a tratados internacionais e as de concessão, renovação e permissão de exploração de serviços de radiodifusão sonora e de sons e imagens;
> IX – as relativas às contas do Presidente da República;
> X – as aprovadas pela Câmara e revisadas pelo Senado Federal.
> § 1º (Parágrafo único transformado em § 1º e revogado pela Resolução nº 33, de 2022)
> § 2º No caso de arquivamento de proposição submetida à tramitação conjunta, observar-se-á que permanecerão válidos os pareceres aprovados, que instruirão as proposições remanescentes, mantida a distribuição da matéria às Comissões, ressalvada a hipótese de deferimento de requerimento em sentido diverso pelo Presidente da Câmara.

Regra de transição (Res. 33/2022, art. 3º): "Finda a 56ª legislatura, arquivar-se-ão definitivamente as proposições que se encontrem em tramitação por 5 (cinco) legislaturas completas".

### Consequências para o produto

- **Desde 2023, um PL não é mais arquivado só porque a legislatura terminou.** É arquivado apenas se já tramitou por 3 legislaturas completas. PL e PLP são espécies do art. 59 da Constituição.
- **O desarquivamento a pedido do autor deixou de existir**: o antigo parágrafo único foi revogado.
- A 57ª legislatura termina em 31/01/2027, e a 58ª começa em 1º/02/2027.
- Estimativa, contando as legislaturas completas posteriores à de apresentação: **95 PL/PLP do estoque da CE e da CREDN** têm 3 ou mais legislaturas completas ao fim da 57ª, todos apresentados antes de 01/02/2015. **Apenas 2 dos 56 itens do filtro NOVO** estão nesse grupo: PL 3961/2004 e PL 791/2011.
- **Não foi confirmado** como a Câmara conta "tramitado por 3 legislaturas completas". A dúvida é se conta ou não a legislatura de apresentação e como trata períodos em que a proposição ficou arquivada. A estimativa acima é uma hipótese.
