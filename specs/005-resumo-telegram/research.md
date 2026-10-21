# Pesquisa: AVI — Resumo diário no Telegram

Nenhuma pendência `NEEDS CLARIFICATION` restou na spec. As decisões abaixo cobrem o que o desenho precisava fechar.

## R1. Cliente da Bot API: `urllib`, sem dependência nova

- **Decisão:** `POST https://api.telegram.org/bot<TOKEN>/sendMessage` com corpo JSON, feito com `urllib.request` da biblioteca padrão, e `abrir`/`dormir` injetáveis, no mesmo molde do `TransporteHttp`.
- **Justificativa:** uma única chamada, sem webhooks nem atualizações (o bot só envia). A constituição (I) exige justificativa escrita para dependência nova; aqui não há dependência.
- **Alternativas:** `python-telegram-bot` e `requests` — rejeitadas; trazem dependências transitivas e recursos que o produto não usa.

## R2. Texto puro, sem `parse_mode`

- **Decisão:** enviar o campo `text` sem `parse_mode`, e `link_preview_options: {"is_disabled": true}`.
- **Justificativa:** nomes, situações e identificações vêm da Câmara. Em `MarkdownV2` e `HTML`, um caractere especial sem escape faz o Telegram recusar a mensagem inteira (FR-018). Em texto puro, não há escape. As URLs completas viram links sozinhas. Desligar a pré-visualização evita cartões enormes de 30 links por mensagem.
- **Custo:** sem negrito. A hierarquia vem de linhas em branco, do marcador `•` e do nome da comissão em linha própria.
- **Alternativa:** `entities` explícitas para negrito — rejeitada por exigir deslocamentos em UTF-16 e não pagar o ganho.

## R3. Contagem do teto: unidades UTF-16, limite 4.096

- **Decisão:** medir o texto em unidades UTF-16 (`len(texto.encode("utf-16-le")) // 2`) e exigir `<= 4096`.
- **Justificativa:** a Bot API limita `text` a 4.096 caracteres e, na prática, os clientes contam em UTF-16. UTF-16 é sempre maior ou igual à contagem de pontos de código, então a medida é conservadora. O texto é quase todo BMP; só um caractere fora do BMP custa 2.
- **Alternativa:** `len(texto)` — rejeitada por poder contar a menos com caracteres fora do BMP.

## R4. Seleção de eventos sob o teto: alternar entre as comissões

- **Decisão (do mantenedor):** fila por comissão na ordem do arquivo (tipo, id); retirar um evento de cada comissão por vez, na ordem da configuração, enquanto o texto couber. A mensagem mostra os grupos na ordem da configuração e, dentro do grupo, a ordem do arquivo.
- **Algoritmo (como implementado):** a cada evento candidato, monta-se o texto **real** inteiro (cabeçalho, grupos, avisos e o rodapé "e mais N" com o N exato daquele estado) e mede-se em UTF-16; o evento só é aceito se o texto couber em 4.096. Se não couber, a seleção **para** (não pula para um evento menor, para que a ordem não se perca) e o estado anterior, já validado, é o resultado. Assim o rodapé entra na conta com os dígitos certos, e incluir o último evento (que elimina o rodapé) também é medido. O estado inicial (sem evento algum) precisa caber; senão o aviso é grande demais (`ValueError`).
- **Alternativas:** ordem do arquivo e prioridade por tipo — rejeitadas pelo mantenedor.

## R5. Avisos com limite próprio

- **Decisão:** a contagem de cada aviso (principal não localizada, relator indeterminado) entra sempre inteira; a lista de itens do aviso ocupa no máximo **1.200 unidades** por aviso, e o excedente vira "e mais M". Os avisos são reservados antes dos eventos.
- **Justificativa:** a spec manda que o aviso nunca suma, mas um aviso com dezenas de itens poderia, sozinho, estourar a mensagem. Com a reserva, o teto de 4.096 vale sempre. Esse limite é um detalhe que a spec não fixa, e o plano o registra para o mantenedor ver (FR-007).
- **Alternativa:** listar todos sem limite — rejeitada: pode passar de 4.096 e a Bot API recusaria a mensagem.

## R6. Dia, tipo e registro de envio

- **Decisão:** `hoje` é a data de Brasília do relógio da execução. O **tipo** da mensagem é decidido assim:
  1. `status.json` ausente, ou com `data_referencia` diferente de `hoje` → tipo **erro**, "a coleta de hoje não rodou";
  2. `resultado == "falha"` → tipo **erro**, com o motivo do `status.json`;
  3. `resultado == "ok"` → tipo **normal**, com o arquivo de mudanças de `data_referencia`.
  `data/envio.json` guarda `{"normal": dia|null, "erro": dia|null}`. Se o dia do tipo decidido já é o de hoje, não envia e sai com 0.
- **Justificativa:** reproduz o clarify: uma normal e uma de erro por dia; falha seguida de sucesso envia a normal. O registro só guarda o último dia de cada tipo, porque os dias só crescem.
- **Observação:** uma execução manual depois da meia-noite, antes da coleta, vê `data_referencia` de ontem e envia "a coleta de hoje não rodou". É verdadeiro (a coleta de hoje ainda não rodou) e está no quickstart.

## R7. Coerência das entradas (FR-022)

- **Decisão:** num dia de tipo normal o envio confere: `mudancas.meta.versao_formato == 1`; `mudancas.meta.data == status.data_referencia`; `mudancas.meta.retrato.dados_camara_em == status.ultimo_retrato_bom.dados_camara_em`; todo evento tem `link`; `meta.total_eventos == len(eventos)`. O `atual.json` precisa ter `meta.versao_formato` 2 ou 3 (as versões que trazem `principal_nao_localizada`, `identificacao`, `link` e `comissao`); outra versão falha. Qualquer divergência falha o envio, sem mensagem.
- **Justificativa:** o contrato da MUD congela com a AVI (assumption da spec). Quem lê confere a versão, como o contrato do `atual.json` pede. O `atual.json` ainda commitado hoje está na versão 2; a próxima coleta o leva à 3, e as duas servem para o que a AVI lê.

## R8. Total de itens e "dados de DD/MM"

- **Decisão:** o total de itens vem de `status.ultimo_retrato_bom.total_itens` (que a AGE já confere com o `atual.json`); "dados de DD/MM" é o dia de `dados_camara_em` em Brasília. Na linha de base, o N vem de `meta.linha_de_base.total_itens`.
- **Justificativa:** evita reler os 105 itens só para contar; a lista de itens do `atual.json` só é lida para os avisos de "principal não localizada".

## R9. Retentativas do envio

- **Decisão:** até **3 tentativas** no total. Repetem: erro de rede/timeout, HTTP 5xx e HTTP 429 (espera `parameters.retry_after` da resposta, limitada a 60 s; se pedir mais, falha). Esperas de 5 s e 15 s nos demais casos. Não repetem: 400, 401, 403, 404 e resposta com `ok: false` — a descrição que o Telegram devolve vai na mensagem de falha. Tudo com `dormir` injetável.
- **Justificativa:** falhas passageiras não devem derrubar o dia; erros de configuração (token errado, bot removido do grupo) não melhoram ao repetir. As constantes ficam no código, não em `config.toml` (nada a editar sem mudar o código, como nas esperas do `TransporteHttp`).

## R10. Segredo fora das mensagens de erro

- **Decisão:** a URL com o token nunca entra em texto de erro. As falhas são montadas só com o código HTTP, a descrição do Telegram e o nome do tipo da exceção de rede; o texto das exceções do `urllib` (que pode conter a URL) passa por `_sem_segredos()`, que troca o token e o chat_id por `***`. Um teste envia um token falso reconhecível e confere que ele não aparece em nenhuma saída, nem no log nem em `stderr`.
- **Justificativa:** `urllib.error.URLError` e `HTTPError` costumam repetir a URL; o log do Actions é público (constituição VI).

## R11. Workflow e concorrência

- **Decisão:** `aviso-diario.yml` com `cron: "17 10 * * *"` (10:17 UTC = 07:17 de Brasília, sem horário de verão desde 2019; fora do topo da hora, como a coleta), `workflow_dispatch` e `concurrency: {group: coleta-diaria, cancel-in-progress: false}`, o mesmo grupo da coleta. `permissions: contents: write`. Mesmos pins de ação do `coleta-diaria.yml`. O passo de envio guarda o código de saída, commita `data/envio.json` se mudou (`git diff --quiet`), faz `pull --rebase` e `push` (com uma segunda tentativa) e só então devolve o código.
- **Justificativa:** o mesmo grupo faz o envio esperar uma coleta em andamento (que pode durar até 200 min mais esperas) e evita ler `status.json` de ontem enquanto a de hoje ainda não terminou. O push do registro e o push da coleta nunca disputam.
- **Alternativas:** passo extra no `coleta-diaria.yml` (rejeitado no clarify: o resumo chegaria de madrugada) e grupo de concorrência próprio (rejeitado: o envio poderia ler dados de ontem durante a coleta).

## R12. Configuração

- **Decisão:** tabela opcional `[aviso]` em `config.toml`: `pagina_url` (padrão `""`) e `repositorio` (padrão `"joaorighetto/monitor-comissoes"`). `pagina_url` vazio ou começando com `https://`; `repositorio` no formato `dono/nome`. O link do arquivo do dia é `https://github.com/{repositorio}/blob/main/data/mudancas/AAAA-MM-DD.json`.
- **Justificativa:** o clarify manda o endereço da página em `config.toml`; o repositório em configuração evita escrever o endereço no código e deixa o teste determinístico.
