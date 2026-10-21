# Implementation Plan: PAG — Página pública

**Branch**: nenhuma criada (o `CLAUDE.md` proíbe criar ou trocar de branch sem pedido do mantenedor) | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-pagina-publica/spec.md`

## Summary

Um comando novo, `python -m monitor_comissoes.pagina gerar`, lê os três arquivos de dados que a coleta já commitou (`data/atual.json`, `data/status.json`, `data/mudancas/AAAA-MM-DD.json`), valida cada um contra o contrato e **gera na memória** o site inteiro: `index.html`, o CSS e o JS do DS, as fontes, uma cópia byte a byte do `atual.json` e o `itens.csv`. Só depois de tudo pronto grava a pasta de saída. Um workflow novo, disparado ao fim de toda "Coleta diária", roda o comando e publica a pasta no GitHub Pages. Nada gerado entra no Git.

Abordagem (detalhes em [research.md](research.md)): só biblioteca padrão e **nenhuma dependência de pacote nova**.
- **HTML por funções Python** com `html.escape` em todo texto da Câmara (FR-020), sem motor de templates. O gerador não lê o relógio: a mesma entrada dá o mesmo site, byte a byte (SC-008).
- **DS vendorizado**: os tokens azuis, o CSS dos FilterChips e as quatro fontes são copiados do portfólio para `src/monitor_comissoes/pagina/estatico/`, com as URLs das fontes reescritas para caminhos relativos. A geração não depende do repositório Portfolio nem da rede.
- **Sem JS por padrão**: a lista completa, ordenada, é o HTML. Os chips nascem `hidden` e o JS os liberta; a faixa de atraso nasce `hidden` e o JS a mostra. Um único `pagina.js`, sem biblioteca, com duas funções puras testáveis com Node.
- **Falha antes de escrever**: arquivo ilegível, de versão desconhecida ou incoerente com o `status.json` levanta `FalhaDePagina` com o nome do arquivo; nada é gravado, o passo de publicação do workflow não roda e a página publicada fica como está.
- **Workflow próprio** (`publicar-pagina.yml`), `workflow_run` da coleta (qualquer resultado) e `workflow_dispatch`, com as ações oficiais de Pages. A coleta (AGE), o aviso (AVI) e as regras de COL/REL/MUD não mudam.

## Technical Context

**Language/Version**: Python 3.13 (constitution).

**Primary Dependencies**: nenhuma nova. Biblioteca padrão (`json`, `csv`, `html`, `datetime`, `pathlib`, `dataclasses`, `argparse`). Reaproveita `status.ler_status`, `mudancas.validar_arquivo` e `estoque.BRASILIA`. Desenvolvimento: `pytest`, `ruff` (já existentes). `node` só como ferramenta de teste do `pagina.js`, que já vem nos executores do GitHub Actions (justificativa em [research.md](research.md), R4).

**Storage**: arquivos JSON versionados no Git (entrada, só leitura). Saída gerada em pasta ignorada pelo Git (`site/`). `config.toml` ganha o valor de `aviso.pagina_url`.

**Testing**: pytest com entradas salvas em `tests/fixtures/pagina/` (um retrato real de 105 itens e documentos sintéticos de `status.json` e de mudanças), a guarda `sem_rede` do `conftest.py` e Node para o JS. Nenhum teste usa rede.

**Target Platform**: Linux (GitHub Actions) e desenvolvimento local (Windows). A página alvo é qualquer navegador moderno, em especial Chrome e Safari no celular.

**Project Type**: CLI / biblioteca interna (projeto único) que gera um site estático.

**Performance Goals**: geração em poucos segundos para ~100 itens (meta, sem teste: seria frágil); `index.html` com menos de 400 KB para os 105 itens do retrato real (conferido por teste, T011).

**Constraints**: sem JS tudo funciona; endereços relativos (a página fica em `/monitor-comissoes/`, não na raiz do domínio); sem requisição a terceiros (nem fontes nem CDN); todo `href` vindo dos dados é `https://www.camara.leg.br/…`; idempotente.

**Scale/Scope**: ~100 itens hoje, até algumas centenas; 7 arquivos de mudanças; dias de posse podem ter centenas de eventos (o teto por dia os recolhe, sem removê-los).

## Constitution Check

*GATE: avaliado antes da pesquisa e reavaliado depois do desenho.*

| Princípio | Avaliação |
|---|---|
| I. Simplicidade | **Passa.** Sem servidor, sem banco, sem pacote novo. Entram **ativos copiados** do DS (CSS e 4 fontes, ~100 KB), justificados em [research.md](research.md) R3: a alternativa (ler do portfólio ou de um CDN) criaria dependência de rede e de outro repositório na geração. `node` é só ferramenta de teste, já presente no CI. |
| II. Fonte oficial e rastreável | **Passa.** Todo item e todo evento têm o link oficial que os dados já trazem; a geração falha se um link faltar ou não for `https://www.camara.leg.br/…`. A página não inclui nem exclui item: a lista é a do `atual.json` (FR-008). |
| III. Falha visível | **Passa.** Faixa de erro com o motivo do `status.json`, faixa de atraso no navegador e, na geração, falha com o nome do arquivo antes de escrever qualquer coisa. O workflow não publica se a geração falhar; a página anterior permanece. Lista vazia nunca é publicada (a geração falha). |
| IV. Testes sem rede | **Passa.** Fixtures salvas, geração pura, guarda de rede ativa. As tarefas começam pelos testes. |
| V. Idempotência | **Passa.** O gerador não lê o relógio nem usa ordem de dicionário não determinística; duas execuções com a mesma entrada dão arquivos idênticos. Republicar não gera aviso nem commit. |
| VI. Segredos fora do código | **Passa.** A feature não usa segredo. O workflow usa só o `GITHUB_TOKEN` com permissões mínimas (`contents: read`, `pages: write`, `id-token: write`). Um teste confere que nenhum arquivo publicado contém o texto de `TELEGRAM_*`. |
| VII. Escopo controlado | **Passa.** Só o recorte da linha PAG. Sem busca, paginação, histórico além de 7 dias nem a página do portfólio. As `ressalvas` do arquivo de mudanças **não** são exibidas (não estão no §6.2); o item já carrega a marca "relator indeterminado". |

**Stack fixada**: Python 3.13, uv, ruff, pytest, GitHub Actions, GitHub Pages, JSON no Git. Nada trocado: não há emenda à constituição.

**Reavaliação depois do desenho:** continua passando. A tabela de complexidade fica vazia.

### Conferência com o PRODUCT.md

O desenho segue D8, D9, D10, §6.2, §7, §8 e §10. Três pontos pedem **emenda ao PRODUCT.md, na mesma mudança da implementação**, sem conflito material:

1. **§6.2 e §10**: registrar que a publicação é por workflow próprio, disparado ao fim da coleta (decidido pelo mantenedor em 20/10/2026), e que os ativos do DS são copiados para o repositório (R3).
2. **§6.2, item 2**: o texto "A atualização de DD/MM falhou (motivo). Dados de DD/MM." usa como primeira data o dia da execução que falhou (`data_referencia`), que é o mesmo dia de `verificado_em`.
3. **§6.2, item 3**: quando o arquivo de mudanças do dia do retrato não existe (antes da primeira execução com a MUD), "mudanças desde o retrato anterior" diz "sem comparação ainda", e não zero.

### Riscos aceitos

- **Pages precisa estar habilitado** (Settings → Pages → Source: GitHub Actions). É uma configuração da conta que o código não faz; sem ela o passo de deploy falha, visivelmente. A ordem de ativação está no [quickstart.md](quickstart.md).
- **`aviso.pagina_url` antes do primeiro deploy.** Se a mudança for mergeada antes de o Pages estar habilitado, o "veja a página" do Telegram aponta para uma página que ainda não existe. A ordem do quickstart evita isso.
- **Endereço da página.** O endereço previsto, `https://joaorighetto.github.io/monitor-comissoes/`, vem do nome do repositório. Se o site de usuário usar domínio próprio, o endereço muda; o deploy imprime o endereço real e o quickstart manda conferir antes de preencher a configuração.
- **Faixa de atraso depende do relógio do leitor.** Sem JS, ou com relógio errado, ela não é confiável; isso fica no bloco "Limites".
- **CSV não neutraliza fórmulas.** O CSV traz o texto da Câmara como está (FR-017); uma ementa que comece com `=` seria interpretada pelo Excel. Risco baixo (fonte oficial) e aceito para não alterar o conteúdo.
- **`workflow_run` só dispara no branch padrão.** Por isso o workflow também tem `workflow_dispatch`, e ignora execuções da coleta feitas fora do branch padrão.

## Project Structure

### Documentation (this feature)

```text
specs/006-pagina-publica/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── pagina-html.md   # Estrutura, textos e atributos da página
│   ├── site.md          # Arquivos publicados, endereços e colunas do CSV
│   └── pagina-cli.md    # CLI `gerar`, códigos de saída e workflow
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
.github/workflows/
└── publicar-pagina.yml          # novo: gera e publica no Pages ao fim da coleta

config.toml                       # aviso.pagina_url preenchido
.gitignore                        # + site/

src/monitor_comissoes/
├── erros.py                      # + FalhaDePagina (sem categoria; nunca vai ao status.json)
└── pagina/                       # novo
    ├── __init__.py
    ├── __main__.py               # python -m monitor_comissoes.pagina
    ├── cli.py                    # `gerar`: lê, valida, monta na memória, grava
    ├── entradas.py               # lê e valida atual, status e mudanças da janela
    ├── modelo.py                 # ordem, números, chips, janela de 7 dias, faixas (puro)
    ├── html.py                   # renderiza index.html (puro, com escape)
    ├── tabela.py                 # renderiza o itens.csv (puro)
    ├── site.py                   # monta o conjunto de arquivos e o grava
    └── estatico/                 # copiado do DS do portfólio (R3)
        ├── estilo.css            # tokens azuis + CSS usado + estilos da página
        ├── pagina.js             # chips e faixa de atraso
        ├── LEIAME.md             # origem, data da cópia e como atualizar
        └── fontes/*.woff2        # 4 arquivos

tests/
├── fixtures/pagina/              # novo: atual-real.json (105 itens), status-*.json, mudancas/
├── pagina_sinteticos.py          # novo: construtores de entradas sintéticas
├── test_pagina_entradas.py       # leitura, versões, incoerências, links
├── test_pagina_modelo.py         # ordem, números, chips, janela de 7 dias, faixas
├── test_pagina_html.py           # estrutura, escape, marcas, ordem, sem JS
├── test_pagina_mudancas.py       # os 6 tipos, dias especiais, teto por dia
├── test_pagina_csv.py            # colunas, separador, BOM, acentos
├── test_pagina_cli.py            # ponta a ponta, idempotência byte a byte, falha sem escrever
├── test_pagina_estaticos.py      # sem URL externa, fontes relativas, alvos de 44 px
├── test_pagina_js.py             # filtrar e atrasada, via Node
├── test_workflow_pagina.py       # verificação textual do workflow
├── test_config.py                # o teste do config.toml do repositório passa a exigir a pagina_url
├── test_resumo.py                # + o link da página no aviso (sem barra duplicada)
└── test_sem_segredos.py          # + .js e .css entre os sufixos varridos
```

**Structure Decision**: projeto único, com um subpacote `pagina/` porque o assunto traz arquivos estáticos e vários módulos. Entrada (`entradas.py`), regra de exibição (`modelo.py`) e saída (`html.py`, `tabela.py`) ficam separadas e puras; só `cli.py` e `site.py` tocam o disco. Os módulos existentes (`status.py`, `mudancas.py`) são reutilizados, não alterados.

## Complexity Tracking

Sem violações do Constitution Check. Nada a justificar.
