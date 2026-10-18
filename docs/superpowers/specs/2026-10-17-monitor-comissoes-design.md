# Monitor de comissões — design (brainstorm de 17/10/2026)

Registro da sessão de brainstorm de produto. **A referência canônica para o Spec Kit é o [PRODUCT.md](../../../PRODUCT.md) e o [ROADMAP.md](../../../ROADMAP.md).** Este documento guarda o caminho: a hipótese inicial, o que a sondagem mudou, as alternativas consideradas e o desenho aprovado. Se algo divergir, valem os dois documentos da raiz.

Classificação: **arquitetural** (produto novo, repositório vazio). Por decisão do autor, a sessão parou na definição de produto, sem plano de implementação. A implementação será feita depois, feature por feature, com o Spec Kit.

## 1. Entendimento acordado

- **Para quem:** o gabinete de um deputado federal do NOVO a partir de 1º/02/2027, sobretudo o chefe de gabinete e a assessoria legislativa. O produto também é peça de portfólio (joaorighetto.github.io).
- **Pergunta diária:** o que de interesse do partido está parado na CE e na CREDN, com quem está e o que mudou desde ontem?
- **Restrições dadas:**
  - Python 3.13 com uv, JSON versionado no Git, GitHub Actions e GitHub Pages; sem servidor nem banco.
  - Todo item com link oficial.
  - Falhar de forma visível.
  - Segredos só em env e secrets.
  - Visual com o Design System do portfólio.
- **Suposições:**
  - O sucesso é a assessoria ler o resumo no celular e saber em um minuto se precisa agir.
  - Até a posse, o produto roda como protótipo com a bancada atual do NOVO.

## 2. O que a sondagem mudou na hipótese inicial

Os detalhes e links estão em [docs/fontes.md](../../fontes.md).

| Hipótese inicial | O que a sondagem mostrou | Efeito no desenho |
|---|---|---|
| A API de proposições por partido serve de base | Sem datas, a API devolve só os últimos 30 dias, limita intervalos a 3 meses e não filtra por órgão | O estoque sai do lote completo diário (D7) |
| Os arquivos anuais trazem o que tramitou no ano | Trazem o que foi **apresentado** no ano, e a Câmara regenera todos diariamente | É preciso ler de 2003 até o ano atual, cerca de 1 GB por dia |
| "Último relator do NOVO" identifica a relatoria | `uriUltimoRelator` mantém o relator que devolveu a matéria e até o de outra comissão | A regra passa a ser o relator atual na comissão atual (D3), feature REL |
| O partido do autor é um dado simples | O lote registra o partido na data da autoria, e 10 itens divergem entre esse partido e o atual | Etiquetas `autoria NOVO` e `autor hoje no NOVO` (D2) |
| "Estar na comissão" é o órgão do último status | Metade do estoque são apensados com status congelado | Os apensados seguem a raiz da cadeia (D4) |
| O fim da legislatura arquiva os PL | Desde a Resolução 33/2022, só arquiva o que tramitou por 3 legislaturas completas, e o desarquivamento foi revogado | ARQ é descartada (D6) |
| O tamanho da lista é desconhecido | São cerca de 54 itens num estoque de cerca de 1.500 PL/PLP | Página única, sem paginação, e resumo em uma mensagem |

## 3. Perguntas discutidas e alternativas

Uma pergunta por vez. A opção escolhida está em **negrito**.

1. **Escopo de tipos e comissões:**
   - **PL e PLP, com as comissões numa lista de configuração**;
   - só PL, com as comissões fixas no código;
   - PL, PLP, PDL e PEC.
2. **"Do NOVO":**
   - **a união com etiqueta de motivo**;
   - só o partido na data;
   - só o partido atual.
3. **Estar na comissão:**
   - **o último status, com os apensados seguindo a principal**, e "a caminho" como feature futura;
   - o último status literal;
   - "a caminho" já na primeira versão.
4. **Avisos:**
   - **um resumo diário único, sempre enviado**, com a pauta para o futuro;
   - só quando há mudança;
   - com a pauta já na primeira versão.
5. **Arquivamento:**
   - **não é feature; é regra de domínio e motivo de saída**;
   - um selo de estimativa na página;
   - a feature ARQ completa.
6. **Página pública:** a proposta foi aprovada como apresentada (PRODUCT.md §6.2).
7. **Fora de escopo:** a divisão em "futuro" (CAM, PAU, GAB) e "não planejado" foi aprovada como apresentada (PRODUCT.md §9).

### Abordagens de coleta

- **A. Lote completo todo dia, com a API só para detalhar.** Foi a escolhida: tem uma fonte de verdade, é determinística e coincide com a sondagem. Custa cerca de 1 GB por dia e os dados são do dia anterior.
- B. API diária com reconciliação semanal pelo lote. Baixaria menos, mas teria duas fontes a reconciliar e centenas de chamadas por dia, cada uma um ponto de falha.
- C. Só API. Descartada: sem filtro por órgão e com janela de 3 meses, montar o estoque exigiria cerca de 95 janelas desde 2003, mais uma consulta por item.

## 4. Desenho aprovado

### 4.1 Regras de domínio (seção 1, aprovada)

Ficam em PRODUCT.md §5:
- universo;
- proposição de referência e apensados;
- estar na comissão;
- etiquetas e relator atual;
- parado há;
- eventos de mudança;
- arquivamento.

### 4.2 Fluxo, falhas e verificação (seção 2, aprovada)

Um workflow diário do GitHub Actions, por volta das 7h de Brasília, com etapas separadas e testáveis uma a uma:

```
coleta ──► estoque e filtro ──► mudanças ──► publicação (commit + Pages) ──► aviso (Telegram)
  lote        data/atual.json    data/mudancas/AAAA-MM-DD.json      página           resumo
```

| Etapa | Entrada | Saída | Falha |
|---|---|---|---|
| Coleta | URLs do lote a partir do ano mínimo | CSV em pasta temporária, fora do Git | HTTP, colunas, contagem ou `Last-Modified` inválidos → erro |
| Estoque e filtro | CSV, `/deputados?siglaPartido=NOVO`, tramitações dos candidatos | `data/atual.json` (itens e `meta`) | Estoque implausível, lista vazia ou erro na API → erro |
| Mudanças | `atual.json` de hoje e o do commit anterior, tramitações dos itens com sequência alterada | `data/mudancas/AAAA-MM-DD.json` | Erro na API → erro |
| Publicação | JSON | Commit diário; HTML estático, JSON e CSV no Pages. O HTML não vai para o Git | Erro no commit ou no deploy → workflow vermelho |
| Aviso | Mudanças, `atual.json`, `status.json` | Uma mensagem no Telegram | Workflow vermelho e e-mail do GitHub ao dono |

- **Princípio:** nenhuma falha publica uma lista nova. O último `atual.json` bom fica como está, `data/status.json` registra o erro, e a página e o Telegram o anunciam.
- **Ausência de execução:** a página detecta no navegador quando `verificado_em` tem mais de 30 horas. O resumo diário sempre enviado também denuncia a falha.
- **Verificação:**
  - testes sem rede, com recortes reais dos CSV em `tests/fixtures`;
  - os casos da sondagem como testes de aceitação (PL 937/2022, 3514/2023, 3871/2024, 4047/2019, 1843/2022, 4501/2023);
  - retratos sintéticos para testar as mudanças;
  - teste do limite de 4.096 caracteres do resumo;
  - um comando manual contra a fonte real, fora da suíte.

### 4.3 Features (seção 3, aprovada)

Estão em ROADMAP.md. Ordem: COL → AGE → REL → MUD → AVI → PAG. Futuras: CAM, PAU e GAB. ARQ foi descartada.

Diferenças em relação à lista inicial sugerida:
- **REL saiu de dentro de COL.** A regra do relator atual exige tramitações e tem casos de borda próprios.
- **AGE subiu para depois de COL**, para que o histórico no Git comece a se acumular cedo.
- **A falha visível ficou distribuída:** a validação em COL, `status.json` e plausibilidade em AGE, e a mensagem de erro em AVI.
- **ARQ foi descartada.**

## 5. Pontos em aberto para as specs

- **Como identificar, nas tramitações, a designação e a devolução do relator** (descrição ou `idTipoTramitacao`). É matéria da spec de REL, conferida com os casos da sondagem.
- **Como identificar parecer apresentado e situação final** (aprovado, arquivado, transformado em norma) pelos códigos de situação e de tramitação. É matéria da spec de MUD.
- **O teto de eventos do resumo e o formato da mensagem.** É matéria da spec de AVI.
- **Como trazer os tokens e o CSS do DS para este repositório** (cópia versionada ou referência). É matéria da spec de PAG.
- **Se os commits do bot contam como atividade para o GitHub não desativar o cron.** É matéria da spec de AGE.
- **Como a Câmara conta as "3 legislaturas completas" do art. 105, VI.** Não bloqueia nada, porque o produto não prevê arquivamento.
