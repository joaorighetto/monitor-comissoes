# Pesquisa: PAG — Página pública

Não restou nenhum ponto "NEEDS CLARIFICATION" na spec. Estas são as decisões de desenho, cada uma com a alternativa descartada. Os fatos sobre o repositório foram conferidos nos arquivos citados.

## R1. HTML escrito por funções Python, sem motor de templates

- **Decisão**: `html.py` monta o documento com funções pequenas e `html.escape(texto, quote=True)` em **todo** texto e atributo que vem dos dados. Um helper `esc()` é o único caminho de texto para o HTML.
- **Por quê**: a constituição (I) exige justificativa escrita para dependência nova; Jinja2 resolveria o escape, mas é um pacote a mais para uma página. O risco do escape manual é coberto por teste (FR-020): uma ementa com `<script>`, `&` e aspas deve sair como texto.
- **Alternativas**: Jinja2 (dependência nova, sem ganho que justifique); `string.Template` (sem escape automático, mesmo risco, menos legível).

## R2. Subpacote `pagina/` com módulos puros e uma casca fina

- **Decisão**: `entradas` (lê e valida) → `modelo` (decide o que mostrar) → `html` e `tabela` (renderizam) → `site` (junta e grava) → `cli`. Só `cli` e `site` tocam o disco; o gerador **não lê o relógio**.
- **Por quê**: o que a página mostra (ordem, números, chips, janela de 7 dias, faixas) é regra testável sem HTML; o HTML é testável sem disco. Sem relógio, a idempotência (V) é por construção.
- **Alternativa**: um módulo único `pagina.py` (como `aviso.py`). Descartada: a feature tem HTML, CSV, estáticos e regras; um arquivo ficaria com ~800 linhas, parecido com `mudancas.py` (740), que já é o limite de leitura confortável.

## R3. Design System vendorizado, não referenciado

- **Decisão**: copiar para `src/monitor_comissoes/pagina/estatico/`: os tokens azuis (`../Portfolio/design-system/export/tokens.azul.css`, 3,9 KB), os trechos do `components/bundle.css` que a página usa (`.pf-wrap`, tipografia, `.pf-chips`, `.pf-chip`, `.pf-muted`, `.pf-btn--link`) e as quatro fontes `.woff2` (92 KB). Um `LEIAME.md` registra a origem, a data da cópia e como recopiar. Nas `@font-face`, `url("/fonts/…")` vira `url("fontes/…")`: a página fica em `/monitor-comissoes/`, não na raiz do domínio.
- **Por quê**: a geração roda no GitHub Actions, onde o repositório Portfolio não existe, e a página não pode depender de um CDN (PRODUCT.md, §10 pede o DS; D9 pede página que funcione sem JS, e uma fonte externa que falha deixaria o texto sem a fonte). O DS diz "tokens azuis" e "FilterChips"; o resto do bundle (nav, hero, cards) não é usado.
- **Alternativas**: link direto para o CSS publicado do portfólio (acopla a página a outro site e a uma URL que pode mudar); submódulo do Git (complexidade e permissão para um repositório particular); `@import` de CDN de fontes (terceiro, privacidade, nenhum teste possível sem rede).
- **Riscos**: o DS pode evoluir e a cópia ficar velha. O `LEIAME.md` e o teste de URLs externas mantêm isso visível; recopiar é uma tarefa manual e rara.
- **Tema**: o próprio `tokens.azul.css` já traz claro, escuro por `prefers-color-scheme` e `data-theme`. A página não oferece botão de tema (fora do §6.2).

## R4. Um `pagina.js`, sem biblioteca, testado com Node

- **Decisão**: um arquivo, ~60 linhas, sem dependência. Duas funções puras: `filtrar(itens, comissao, motivo)` (devolve os ids visíveis) e `atrasada(verificadoEm, agora)` (verdadeiro se passou de 30 horas). O resto (ligar chips, alternar `hidden`, anunciar "Mostrando N de M") é cola de DOM em `aplicar(documento, …)` e `verificarAtraso(documento, agora)`, que recebem o `document` por parâmetro e por isso também são testáveis com um `document` falso. O arquivo termina com `if (typeof module !== "undefined") module.exports = {...}` para os testes o carregarem.
- **Teste**: `test_pagina_js.py` roda `node -e` sobre o arquivo e confere as funções com entradas salvas (todas as combinações dos chips, borda de 30 horas). O teste é pulado se `node` não existir; o executor do GitHub Actions tem Node, então no CI ele roda sempre. O teste de estrutura do HTML confere que o `pagina.js` é o único script e que não há `eval` nem atributos `on*`.
- **Por quê**: SC-005 pede que qualquer combinação de chips mostre exatamente os itens certos; sem executar o JS isso só se confere à mão. Node não é dependência do produto: o produto publicado é só HTML/CSS/JS.
- **Alternativas**: Playwright/Selenium (dependência pesada, navegador no CI); reimplementar a regra em Python para testar (testaria a cópia, não o código que roda); sem teste automático do JS (deixaria o SC-005 só manual).

## R5. Sem JS: tudo visível e nenhum controle morto

- **Decisão**: os dois grupos de chips são emitidos com o atributo `hidden`; o JS o remove. A faixa de atraso também nasce `hidden`, com o texto completo já escrito e o instante em `data-verificado-em`; o JS só a mostra. Os itens nunca nascem escondidos: o filtro só esconde depois de uma escolha.
- **Por quê**: FR-015 e SC-004. O DS diz "sem JavaScript, todos os projetos aparecem". Se o JS falhar ao carregar, o pior caso é a lista inteira sem filtro.
- **Alternativa**: `<noscript>` com aviso "ative o JS" (ruído; a lista inteira já funciona).

## R6. Janela de 7 dias e arquivos de mudanças

- **Decisão**: `D` é o dia (Brasília) de `meta.gerado_em` do `atual.json` (o dia do retrato, igual ao `retrato.dia` do arquivo de mudanças). A janela é de `D-6` a `D`, 7 dias de calendário, mais recente primeiro. Para cada dia da janela, se `data/mudancas/AAAA-MM-DD.json` existe, é lido e validado; se não existe, o dia aparece como "sem arquivo de mudanças neste dia" (US4, cenário 4; o texto não afirma que a coleta falhou, porque o arquivo também falta antes da primeira execução com a MUD). Se nenhum dos 7 dias tem arquivo, a seção toda diz que ainda não há mudanças registradas (US4, cenário 6). Arquivos fora da janela não são lidos: um arquivo antigo corrompido não derruba a página de hoje. Um arquivo **dentro** da janela ilegível, fora do contrato (`mudancas.validar_arquivo`) ou de versão desconhecida falha a geração, com o nome do arquivo.
- **Conferência cruzada**: o arquivo do dia `D` (se existir) deve ter `meta.retrato.dados_camara_em` igual ao do `atual.json`; senão a geração falha (os dois descreveriam retratos diferentes).
- **Números**: "mudanças desde o retrato anterior" é `meta.total_eventos` do arquivo de `D`. Linha de base: o texto da linha de base. Arquivo de `D` ausente: "sem comparação ainda". Nunca zero inventado.
- **Por quê**: em dia de falha da coleta (`status.data_referencia = D+1`, `atual.json` ainda de `D`), a janela continua ancorada no retrato exibido, e não no relógio.
- **Alternativa**: ancorar em `status.data_referencia`. Descartada: em dia de falha o dia mais recente da janela seria `D+1`, que nunca tem arquivo, e a seção abriria com um dia vazio.

## R7. Eventos: texto do arquivo onde existe, estrutura onde não

- **Decisão**: o motivo de entrada e de saída, a mudança de situação e as etiquetas vêm do arquivo (`motivo.texto`, `de`/`para`, `comissao_de`, `ganhou`/`perdeu`); o código só escolhe o rótulo de cada tipo e monta a frase. Cada evento mostra `identificacao` como link para `link`, a comissão e, quando houver, as tramitações em lista recolhida (`<details>`). O conteúdo do parecer não é reproduzido (PRODUCT.md, §9).
- **Teto por dia**: `TETO_EVENTOS_POR_DIA = 20`. Os 20 primeiros do dia (na ordem do arquivo: comissão, tipo, id) ficam abertos e o resto, num `<details>` com o título "e mais N eventos de DD/MM". Nenhum evento sai da página (FR-016).
- **Por quê**: o arquivo já traz os textos decididos pelo mantenedor (PRODUCT.md, §5.6); duplicá-los no código criaria uma segunda fonte para o mesmo texto. Vinte cabem numa tela de celular rolada sem esconder o dia seguinte.
- **Alternativa**: reaproveitar `resumo.py` (texto do Telegram). Descartada: ele devolve texto puro, com o teto de 4.096 caracteres e a mistura de comissões, que não servem ao HTML.

## R8. Download: `atual.json` é cópia, CSV é derivado

- **Decisão**: `atual.json` é copiado byte a byte para a saída (o que se baixa é o que o Git guarda). O `itens.csv` sai de `csv.writer` com `delimiter=";"`, `lineterminator="\r\n"` e gravação em UTF-8 com BOM (`utf-8-sig`). Colunas e junção de listas em [contracts/site.md](contracts/site.md).
- **Por quê**: FR-017 (decisão do mantenedor em 20/10/2026) e a fidelidade ao `atual.json`.
- **Alternativa**: gerar o JSON de novo para a página. Descartada: seria uma segunda serialização do mesmo dado.

## R9. Gravação só depois de tudo pronto

- **Decisão**: `site.py` monta o dicionário `{caminho relativo: bytes}` na memória; só então cria a pasta e grava cada arquivo, com escrita para um arquivo temporário e `os.replace`. Qualquer erro anterior deixa a pasta de saída intocada (ou inexistente).
- **Por quê**: FR-013 e SC-009. No workflow, a falha da geração impede o upload do artefato, e o Pages continua com a versão anterior.
- **Alternativa**: gerar direto na pasta e limpar em caso de erro. Descartada: falha entre a escrita e a limpeza deixaria meio site.

## R10. Validação das entradas (FR-013)

- **Decisão**: `entradas.py` valida só o que a página usa, com a mesma disciplina de `entradas.py` do AVI (versão suportada, tipos, campos obrigatórios, nome do arquivo na mensagem):
  - `atual.json`: `meta.versao_formato` em (2, 3); `meta` com `gerado_em`, `dados_camara_em`, `comissoes`, `total_itens`, `total_por_comissao`; `itens` lista **não vazia** com `total_itens` igual ao tamanho; cada item com os campos da página; `link`, `apensado_a.link` e `relator.fonte` começando por `https://www.camara.leg.br/`.
  - `status.json`: via `status.ler_status` (já valida o contrato); arquivo ausente falha. `resultado = ok` exige `atual.meta.dados_camara_em` igual a `ultimo_retrato_bom.dados_camara_em`; `resultado = falha` exige `ultimo_retrato_bom` não nulo e igual ao `atual.json` (o retrato mantido).
  - mudanças: R6.
- **Por quê**: constituição III. Um `atual.json` de outro retrato que o do status é exatamente o caso que a faixa de erro poderia esconder.
- **Alternativa**: confiar nos arquivos porque a coleta já os validou. Descartada: a página é a última linha de defesa antes do leitor, e a conferência é barata.

## R11. Workflow de publicação

- **Decisão**: `.github/workflows/publicar-pagina.yml`:
  - `on.workflow_run`: `workflows: ["Coleta diária"]`, `types: [completed]`, com `if` que aceita só execuções do branch padrão (`github.event.workflow_run.head_branch == github.event.repository.default_branch`) e todo `workflow_dispatch`;
  - `permissions`: `contents: read`, `pages: write`, `id-token: write`;
  - `concurrency: {group: pagina, cancel-in-progress: false}`;
  - passos: `actions/checkout` (sem `ref`, para pegar o commit do bot e não o `head_sha` da coleta), `setup-uv`, `uv sync --locked`, `python -m monitor_comissoes.pagina gerar --saida site`, `actions/configure-pages`, `actions/upload-pages-artifact` (`path: site`), `actions/deploy-pages` com `environment: github-pages`, e a impressão do endereço.
- **Versões das ações**: o repositório usa `actions/checkout@v7`; as ações de Pages (`configure-pages`, `upload-pages-artifact`, `deploy-pages`) têm de ter a versão estável mais recente conferida na implementação (tarefa própria), e fixadas como o `setup-uv`, por SHA com a versão em comentário.
- **Por quê**: decisão do mantenedor em 20/10/2026 (workflow próprio ao fim da coleta). `head_sha` da coleta é o commit **antes** do commit do bot; fazer checkout dele publicaria os dados de ontem. O deploy só roda se o `gerar` passou.
- **Alternativas**: etapa dentro da coleta (descartada na clarificação); `schedule` próprio (descartada na clarificação); publicar a partir de uma pasta `docs/` commitada (inflaria o histórico do Git com HTML gerado e criaria um segundo commit diário).

## R12. `aviso.pagina_url` e documentos

- **Decisão**: `config.toml` recebe `pagina_url = "https://joaorighetto.github.io/monitor-comissoes/"` (a validação existente já aceita qualquer `https://`). O PRODUCT.md recebe as três emendas de [plan.md](plan.md) na mesma mudança.
- **Conferir na implementação**: como o `resumo.py` junta `pagina_url` a texto (barra final, parâmetros), para o link do Telegram não sair com `//`.

## R13. Acessibilidade verificável sem navegador

- **Decisão**: o que dá para afirmar por teste de texto é afirmado: `lang="pt-BR"`, `meta viewport`, um `h1`, uma lista de itens como `ol`, `aria-pressed` e `role="group"` com `aria-label` nos chips, região `aria-live="polite"` para "Mostrando N de M", faixas com `role` e texto, `min-height: 44px` em chips e links de ação no CSS, `:focus-visible` no CSS, nenhuma `outline: none` sem substituto, `prefers-color-scheme` nos tokens. Contraste vem dos tokens do DS (verificado AA pelo DS). O que exige olho (rolagem lateral em 360 px, foco, leitura em tema escuro) está no [quickstart.md](quickstart.md) e é conferido no navegador antes de fechar.
- **Alternativa**: ferramenta automática (axe) — exige navegador no CI; fica como possível melhoria futura, fora do recorte.
