# Monitor de comissões — Constituição

## Princípios fundamentais

### I. Simplicidade antes de sofisticação

O produto DEVE rodar sem servidor e sem banco de dados. Nenhuma dependência nova DEVE entrar sem
justificativa escrita no `plan.md` da feature que a introduz.

*Por quê:* o produto é mantido por uma pessoa e precisa continuar funcionando sem cuidados diários.

### II. Fonte oficial e rastreável

Todo item publicado DEVE ter link para a fonte oficial. Toda regra de inclusão DEVE estar escrita
em `PRODUCT.md`; o código NÃO DEVE incluir nem excluir item por regra que esse documento não
descreva.

*Por quê:* o gabinete decide a partir da lista e só pode confiar nela se conseguir conferir cada
linha na fonte e entender por que cada item está ali.

### III. Falha visível

Erro de coleta ou mudança de formato da fonte DEVE interromper a publicação e gerar aviso. Uma
lista vazia ou parcial NUNCA DEVE ser publicada como se fosse completa.

*Por quê:* uma lista vazia ou parcial publicada como verdade é o pior erro possível para quem
decide a partir dela (PRODUCT.md, D10).

### IV. Testes sem rede

O comportamento DEVE ser coberto por testes que usam fixtures salvas. Nenhum teste DEVE depender
da internet.

*Por quê:* testes que dependem da fonte quebram por motivos alheios ao código e escondem
regressões reais.

### V. Idempotência

Rodar o processo duas vezes no mesmo dia DEVE produzir o mesmo resultado e NÃO DEVE gerar aviso
duplicado.

*Por quê:* novas tentativas e execuções manuais acontecem, e não podem mudar os dados nem repetir
mensagens para quem lê.

### VI. Segredos fora do código

Credenciais DEVEM existir apenas em variáveis de ambiente e em secrets do GitHub.

*Por quê:* o repositório e a página são públicos, e um segredo publicado não se recupera.

### VII. Escopo controlado

Uma spec DEVE implementar apenas o recorte da sua linha no `ROADMAP.md`. O que a coluna "Não
inclui" dessa linha lista é limite, e NÃO DEVE ser implementado pela spec.

*Por quê:* cada feature precisa poder ser entregue e verificada sozinha.

## Stack fixada

- Linguagem: Python 3.13.
- Gerenciador de pacotes e do ambiente: uv.
- Lint e formatação: ruff.
- Testes: pytest.
- Automação e integração contínua: GitHub Actions.
- Publicação: GitHub Pages.
- Armazenamento: JSON versionado no Git.

Trocar qualquer item desta lista exige emenda a esta constituição.

## Fluxo de desenvolvimento

- Cada feature do `ROADMAP.md` segue o fluxo do Spec Kit, na ordem que o `ROADMAP.md` registrar.
- O "Constitution Check" do `plan.md` DEVE avaliar cada princípio acima. Toda violação DEVE ser
  justificada na tabela de complexidade do plano.
- A suíte de testes DEVE passar, sem rede, antes de a feature ser considerada concluída.

## Governança

Esta constituição prevalece sobre `PRODUCT.md`, `ROADMAP.md` e qualquer spec, plano ou tarefa. Em
conflito material com algum deles, a execução DEVE parar e o conflito DEVE ser resolvido pelo
autor; nenhum dos lados é escolhido em silêncio.

**Emendas.** Toda emenda DEVE ser feita por commit que altere este arquivo, com o motivo e o
impacto descritos na mensagem. Quando a emenda mudar uma regra já implementada, o commit ou o plano
da mesma mudança DEVE trazer a migração do código e dos testes.

**Versionamento.** A versão segue o versionamento semântico:
- MAJOR: remoção ou redefinição incompatível de princípio ou da governança;
- MINOR: princípio ou seção novos, ou ampliação relevante da orientação;
- PATCH: esclarecimentos, redação e correções sem mudar o sentido.

**Conformidade.** Todo plano e toda revisão de mudança DEVEM verificar a conformidade com os
princípios. Orientação de uso no dia a dia: `CLAUDE.md`, `PRODUCT.md` e `ROADMAP.md`.

**Version**: 2.0.0 | **Ratified**: 2026-10-17 | **Last Amended**: 2026-10-17
