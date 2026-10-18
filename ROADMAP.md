# Roadmap

Cada feature cabe em uma spec do Spec Kit e pode ser entregue sozinha. As regras referidas aqui estão no [PRODUCT.md](PRODUCT.md).

**Ordem recomendada:** COL → AGE → REL → MUD → AVI → PAG.

- AGE vem logo depois de COL para que o histórico diário no Git comece a se acumular antes de MUD, que precisa do retrato "de ontem".
- PAG não depende de AVI. Pode vir antes, se a página do portfólio tiver pressa.

**Status:** `proposta` (ainda não começou), `em andamento` (spec iniciada, verificação completa ainda não passou), `concluída` (verificação completa e casos de aceitação passaram), `futura` (fora do recorte atual) e `descartada` (não será feita).

| ID | Feature | Resultado verificável | Inclui | Não inclui | Dependências | Status |
|---|---|---|---|---|---|---|
| COL | Coleta e estoque filtrado | `uv run` gera `data/atual.json` com os PL/PLP da CE e da CREDN que têm `autoria NOVO` ou `autor hoje no NOVO`. Os casos de aceitação de PRODUCT.md §5.4 sem relatoria passam. Uma fonte inválida faz o comando sair com erro, sem gravar | Download e validação do lote (HTTP, colunas, contagem, `Last-Modified`); lista de comissões e ano mínimo em configuração; cadeia de apensação até a raiz e "principal não localizada"; etiquetas de autoria; `/deputados?siglaPartido=NOVO`; link oficial; bloco `meta`; falha com lista filtrada vazia; testes com fixtures reais | Relatoria; comparação com ontem; agendamento; `status.json`; avisos; página | — | concluída |
| AGE | Execução diária agendada | O workflow roda todo dia e faz o commit de `data/atual.json` (mesmo sem mudanças) e de `data/status.json`. Uma falha deixa o workflow vermelho e o último `atual.json` bom intacto | Cron do Actions; commit pelo bot; novas tentativas; `status.json`; checagem de plausibilidade (variação de mais de 20%, estoque ou lista vazios); confirmação do risco de desativação após 60 dias | Telegram; página | COL | concluída |
| REL | Relatoria NOVO atual | `relatoria NOVO` só aparece quando o relator foi designado na comissão atual e não devolveu a matéria. PL 937/2022 e PL 3514/2023 ficam fora, PL 4501/2023 fica dentro. Apensados herdam o relator da principal | Leitura das tramitações dos candidatos; regra do relator atual; partido atual do relator; testes dos casos da sondagem | Histórico de relatores; relatores de outras comissões | COL | em andamento |
| MUD | Mudanças desde ontem | `data/mudancas/AAAA-MM-DD.json` lista os eventos entrou, saiu (com motivo e destino), situação, relator, parecer e etiquetas, com todas as tramitações desde o retrato anterior. O primeiro dia registra "linha de base" | Comparação por id; tramitações dos itens cuja sequência mudou; motivo "arquivado, art. 105"; testes com retratos sintéticos | Envio; página | COL; REL (desejável) | proposta |
| AVI | Resumo diário no Telegram | Um grupo recebe uma mensagem por dia, mesmo sem mudanças, com links oficiais, em até 4.096 caracteres e com teto de eventos. Uma falha gera mensagem de erro com a data dos últimos dados bons | Formatação; envio pela Bot API; secrets; "e mais N, veja a página"; testes de formatação | Comandos no bot; vários destinatários | MUD; AGE | proposta |
| PAG | Página pública | O GitHub Pages mostra a linha de atualização, a faixa de erro ou de atraso, os números, as mudanças de 7 dias e a lista com chips de comissão e de motivo, ordenada por "parado há". Tem bloco de limites e download em JSON e CSV. Funciona sem JS | HTML estático gerado em Python; tokens azuis e FilterChips do DS; aviso de dados atrasados no navegador; acessibilidade do DS | Busca; paginação; histórico de mais de 7 dias; a página de projeto no portfólio (fica no repositório Portfolio, com EmbedFrame) | COL; AGE; MUD | proposta |
| CAM | "A caminho" | A página e o resumo listam os PL/PLP distribuídos à CE ou à CREDN que ainda estão em outra comissão | Leitura do despacho de distribuição nas tramitações | — | COL; REL | futura |
| PAU | Pauta das reuniões | O resumo e a página indicam "na pauta de DD/MM" para os itens pautados | `/orgaos/{id}/eventos` e a pauta de cada evento; checagem mais de uma vez por dia | — | AVI; PAG | futura |
| GAB | Etiqueta do gabinete | Os itens com autoria ou relatoria do deputado do gabinete ganham uma etiqueta própria e um chip | Id do deputado em configuração | — | COL; REL; posse em 1º/02/2027 | futura |
| ARQ | Risco de arquivamento | — | — | Tudo. Desde a Resolução 33/2022, só cerca de 2 dos 54 itens estariam em risco, e o prazo (31/01/2027) vence antes da posse. A saída por arquivamento já é coberta por MUD (PRODUCT.md, D6) | — | descartada |
