# Monitor de comissões — Constituição

## Princípios fundamentais

### I. Todo item é conferível na fonte oficial

Todo item exibido ou enviado pelo produto DEVE trazer o link para a página oficial da proposição
na Câmara dos Deputados. Todo dado exibido DEVE vir de uma fonte pública e oficial, e a saída DEVE
informar de quando é o dado. O produto NÃO DEVE gerar texto próprio sobre o conteúdo das
proposições (resumo de ementa por IA, previsão de votação, chance de aprovação). O produto NÃO é
publicação oficial e a saída DEVE dizer isso.

*Por quê:* o gabinete decide a partir desta lista. Ele só pode confiar nela se conseguir conferir
cada linha onde vale a palavra oficial.

### II. Falhar de forma visível

Nenhuma falha DEVE publicar uma lista nova. Diante de fonte fora do ar, formato alterado, arquivos
desatualizados, estoque implausível (estoque vazio ou variação de mais de 20% em um dia), lista
filtrada vazia ou erro na API, a execução DEVE terminar com erro, manter o último retrato bom
intacto, registrar a falha em `data/status.json` e anunciá-la na página e no Telegram. Não DEVE
existir publicação parcial. Uma lista vazia ou parcial nunca DEVE ser tratada como válida. A
ausência de execução também DEVE ser perceptível, pela faixa de dados atrasados e pelo resumo
diário que deixa de chegar.

*Por quê:* uma lista vazia ou parcial publicada como verdade é o pior erro possível para quem
decide a partir dela. O silêncio nunca pode significar "parou de funcionar".

### III. Nada muda em silêncio

Nenhum item DEVE entrar na lista, sair dela ou mudar de estado sem que o motivo fique registrado.
Cada saída DEVE ter motivo e destino (outro órgão, situação final, arquivamento, apensação, perda
de etiqueta). Quando não for possível determinar um dado (por exemplo, "principal não localizada"),
o item DEVE aparecer com a marca correspondente, e o resumo DEVE avisar. O resumo diário DEVE ser
enviado todos os dias, inclusive sem mudanças. O histórico DEVE ser versionado no Git, com commit
diário de `data/atual.json` mesmo sem mudanças.

*Por quê:* quem lê precisa saber o que mudou e por quê. Um commit ausente denuncia que a execução
não rodou.

### IV. Regras de domínio explícitas e testadas antes de implementadas

As regras de domínio (universo, proposição de referência, estar na comissão, etiquetas, relator
atual, parado há, eventos de mudança) vivem em `PRODUCT.md`, que é a referência canônica. O código
NÃO DEVE implementar regra que o `PRODUCT.md` não descreva. Uma mudança de regra DEVE alterar o
`PRODUCT.md` antes do código. Os testes de cada regra DEVEM ser escritos antes da implementação,
rodar sem rede e usar fixtures com recortes reais dos CSV em `tests/fixtures`. Os casos verificados
na sondagem (PL 937/2022, PL 3514/2023, PL 3871/2024, PL 4047/2019, PL 1843/2022 e PL 4501/2023)
DEVEM existir como testes de aceitação. Cada passo do fluxo (coleta, estoque e filtro, mudanças,
publicação, aviso) DEVE ser testável isoladamente.

*Por quê:* os apensados, o partido na data e o "último relator" enganam. Só casos reais fixados em
teste impedem que uma regra volte a errar.

### V. Simplicidade operacional

O produto DEVE rodar sem servidor próprio e sem banco de dados. O histórico fica em arquivos JSON
no Git, a execução fica no GitHub Actions e a publicação fica no GitHub Pages. O uso do lote
completo da Câmara como fonte do estoque (a API só detalha) DEVE ser mantido, para que haja uma
única fonte de verdade em vez de duas reconciliadas. Mudar de comissão ou de ano mínimo DEVE ser
feito por configuração, sem alterar o código. Complexidade além disso (banco, servidor, login,
vários gabinetes, bot com comandos) DEVE ser justificada por escrito no plano e aprovada antes de
entrar.

*Por quê:* o produto é mantido por uma pessoa e precisa continuar funcionando sem cuidados diários.

### VI. Segredos fora do código

O token do bot e o `chat_id` do Telegram DEVEM existir apenas em variáveis de ambiente e em secrets
do GitHub. O arquivo `.env` local DEVE ficar fora do Git. Segredos NÃO DEVEM aparecer em código,
fixtures, logs, mensagens de erro, `data/` nem na página publicada.

*Por quê:* o repositório e a página são públicos, e um segredo publicado não se recupera.

### VII. Saídas acessíveis e sem dependência de JavaScript

A página pública DEVE ser HTML estático gerado em Python e DEVE funcionar sem JavaScript: sem JS,
todos os itens aparecem e os chips apenas deixam de filtrar. A página DEVE usar o Design System do
portfólio (tokens azuis, FilterChips) e respeitar as regras de acessibilidade, foco e área de
toque dele. O significado de qualquer estado (erro, atraso) DEVE vir do texto, não só da cor. A
página e o resumo DEVEM ser legíveis no celular. O resumo diário DEVE caber em uma única mensagem
do Telegram (4.096 caracteres), e o excedente DEVE ser resumido como "e mais N, veja a página".

*Por quê:* o público lê no celular, e a página é também peça de portfólio avaliada no celular.

## Restrições técnicas e de escopo

- Linguagem e ferramentas: Python 3.13, gerenciado com uv.
- Fonte de dados: Dados Abertos da Câmara dos Deputados (lote CSV e API v2). Os números e as
  decisões de fonte estão em `docs/fontes.md`.
- Universo: proposições de tipo PL e PLP nas comissões da lista de configuração, hoje CE e CREDN.
- Escopo fechado: Senado, outros tipos de proposição (REQ, PDL, PEC), previsão de votação, bot com
  comandos, login e conteúdo de pareceres NÃO DEVEM entrar sem emenda ao `PRODUCT.md` e a esta
  constituição, quando o princípio afetado for outro.
- A coleta NÃO DEVE gravar arquivos do lote no Git. Eles ficam em pasta temporária.
- O HTML gerado NÃO DEVE ser versionado no Git. Ele vai ao GitHub Pages.
- O arquivamento (RICD, art. 105) NÃO é feature. Quando ocorre, é motivo de saída do item.
- A página de projeto no portfólio (EmbedFrame) pertence ao repositório do portfólio, não a este.

## Fluxo de desenvolvimento

- Cada feature do `ROADMAP.md` DEVE seguir o fluxo do Spec Kit (spec, plano, tarefas, implementação)
  e DEVE poder ser entregue sozinha, na ordem COL → AGE → REL → MUD → AVI → PAG, ou na ordem que o
  `ROADMAP.md` registrar.
- Toda spec e todo plano DEVEM referir as regras do `PRODUCT.md` em vez de reescrevê-las. Se uma
  spec contradizer o `PRODUCT.md`, o `PRODUCT.md` DEVE ser corrigido antes, ou a spec ajustada.
- O "Constitution Check" do plano DEVE avaliar cada princípio acima. Qualquer violação DEVE ser
  justificada na tabela de complexidade do plano.
- A suíte de testes DEVE passar sem rede. A verificação contra a fonte real é um comando manual,
  fora da suíte.
- Antes de uma feature ser considerada concluída, o autor DEVE rodar a suíte e conferir o resultado
  contra os casos de aceitação do `ROADMAP.md`.

## Governança

Esta constituição prevalece sobre as demais práticas do projeto. Em conflito com `PRODUCT.md`,
`ROADMAP.md` ou qualquer spec, os princípios acima valem, e o outro documento DEVE ser corrigido.

**Emendas.** Toda emenda DEVE ser feita por commit que altere este arquivo, com o motivo e o
impacto descritos na mensagem. Quando a emenda mudar uma regra já implementada, o commit ou o plano
da mesma mudança DEVE trazer o plano de migração dos dados e dos testes.

**Versionamento.** A versão segue o versionamento semântico:
- MAJOR: remoção ou redefinição incompatível de princípio ou da governança;
- MINOR: princípio ou seção novos, ou ampliação relevante da orientação;
- PATCH: esclarecimentos, redação e correções sem mudar o sentido.

**Conformidade.** Todo plano e toda revisão de mudança DEVEM verificar a conformidade com os
princípios. O autor DEVE revisar a constituição quando uma feature descobrir que um princípio não
se sustenta, em vez de contorná-lo. Orientação de uso no dia a dia: `PRODUCT.md`, `ROADMAP.md` e
`docs/fontes.md`.

**Version**: 1.0.0 | **Ratified**: 2026-10-17 | **Last Amended**: 2026-10-17
