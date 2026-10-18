# Agendamento diário e o prazo de 60 dias do GitHub

Consulta feita em **2026-10-18** (feature AGE). Responde à pergunta em aberto do `ROADMAP.md`:
o GitHub desativa o agendamento de um repositório público por inatividade, e os commits do
próprio bot contam como atividade?

## A regra oficial

> "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days."

Em português: em repositório público, os workflows agendados são desativados automaticamente
quando não houve atividade no repositório por 60 dias. Fontes oficiais:

- [Eventos que disparam workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [Desativar e reativar um workflow](https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow)

Este repositório é público (constituição, princípio VI), então a regra se aplica.

## O que a fonte oficial não diz

- **O que conta como "atividade do repositório".** As duas páginas não definem o termo.
- **Se commits feitos por um workflow com o `GITHUB_TOKEN` contam.** Nem afirmam nem negam.

## Fontes não oficiais consultadas

Não são afirmação do GitHub; valem só como indício:

- Guias e discussões descrevem a regra, e um deles diz que qualquer commit reinicia a contagem.
- O projeto [efrecon/gh-action-keepalive](https://github.com/efrecon/gh-action-keepalive) existe
  para evitar essa desativação e funciona gerando um commit na branch principal, o que sugere que
  commits automáticos contam. O mesmo projeto avisa que um método anterior de simular atividade
  deixou de contornar o prazo.

## Conclusão

**O risco não foi confirmado nem afastado por fonte oficial.** É plausível que o commit diário do
bot já seja atividade suficiente, mas isso é hipótese.

Se a hipótese estiver errada, o agendamento é desativado sem aviso. Um agendamento desativado não
roda de novo sozinho, e nenhum outro workflow agendado do repositório se salvaria, porque todos
seriam desativados.

## Como o produto sinaliza o problema

- Ausência do commit diário do bot no histórico do Git (PRODUCT.md, D8).
- A página mostrará a faixa de "dados atrasados" depois de 30 horas sem verificação (feature PAG,
  ainda não implementada). A AGE só garante que `verificado_em` no `data/status.json` é o da
  última execução.

## Mitigações

Propostas para decisão do mantenedor; **nenhuma foi implementada**:

1. **Não fazer nada** e confiar no commit diário. Custo zero. Se a hipótese estiver errada, o
   produto para em silêncio, com o sinal descrito acima.
2. **Teste empírico.** O primeiro sinal real só aparece depois de 60 dias de operação. Anotar a
   data de início e, por volta do dia 55, conferir na aba Actions que o workflow segue ativo.
3. **Atividade humana periódica.** O mantenedor faz um commit próprio (por exemplo, uma linha no
   changelog) a cada 50 dias. Manual, mas independente da hipótese.
4. **Gatilho externo.** O `workflow_dispatch` chamado por um agendador de fora do GitHub. Exige
   um token em segredo, o que a constituição permite (princípio VI), mas aumenta a superfície.
   Não recomendado antes de se saber se há risco.

## Se o agendamento for desativado

Reativar na aba Actions do repositório (workflow "Coleta diária" → "Enable workflow") ou com
`gh workflow enable coleta-diaria.yml`.

## Data de início da operação

Anotar aqui o dia do primeiro commit do bot depois do merge: _a preencher_.
