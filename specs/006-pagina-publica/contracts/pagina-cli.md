# Contrato: CLI `gerar` e workflow de publicação

## Comando

```bash
uv run python -m monitor_comissoes.pagina gerar [--atual data/atual.json] [--status PATH] [--mudancas PATH] [--saida site]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--atual` | `data/atual.json` | O retrato a exibir |
| `--status` | `status.json` ao lado do `--atual` | O status da última execução |
| `--mudancas` | pasta `mudancas/` ao lado do `--atual` | Onde estão os `AAAA-MM-DD.json` |
| `--saida` | `site` | Pasta onde o site é gravado (criada se não existir) |

Não há opção de data nem de relógio: o gerador não lê a hora (plan.md, R2). Não lê `config.toml`: as comissões vêm do `meta` do retrato.

### Comportamento

1. Lê e valida `atual.json`, `status.json` e os arquivos de mudanças da janela (R10, R6 da [pesquisa](../research.md)).
2. Monta, **na memória**, todos os arquivos de [site.md](site.md).
3. Só então cria `--saida` e grava cada arquivo, por arquivo temporário e `os.replace`. Sobrescreve os arquivos de [site.md](site.md), que têm nomes fixos; não apaga outros arquivos da pasta.
4. Imprime em `stdout` uma linha e sai com 0:

   `OK: página gerada com N itens · dados da Câmara de DD/MM · M dias de mudanças · SAIDA`

   (`M` conta os dias da janela que tinham arquivo.)

### Falha

Imprime em `stderr` uma linha `FALHA [pagina]: motivo`, **não escreve nada**, e sai com 1. Qualquer exceção inesperada vira `FALHA [pagina]: Tipo: mensagem` com código 1 (nenhuma falha termina sem aviso). O motivo sempre traz o nome do arquivo quando a causa é um arquivo.

| Causa | Motivo (exemplo) |
|---|---|
| Arquivo ausente (`atual.json`, `status.json`) | `atual.json data/atual.json não existe` |
| JSON inválido ou ilegível | `status.json data/status.json não é um JSON válido: …` |
| Versão de formato desconhecida | `data/atual.json: meta.versao_formato 4 não suportada (esperada uma de [2, 3])` |
| Lista vazia ou `total_itens` diferente | `data/atual.json: itens vazia` |
| Retrato e status de momentos diferentes | `data/atual.json: meta.dados_camara_em … difere do ultimo_retrato_bom do status.json (…)` |
| Falha sem retrato bom | `data/status.json: resultado falha sem ultimo_retrato_bom` |
| Arquivo de mudanças da janela inválido | `arquivo de mudanças data/mudancas/2026-10-19.json fora do contrato: …` |
| Link fora de `https://www.camara.leg.br/` | `data/atual.json: itens[3].link não é um link oficial` |
| Não foi possível gravar a saída | `não foi possível gravar site/index.html: …` |

`FalhaDePagina` (em `erros.py`) é exclusiva desta feature: não tem categoria e **nunca** vai para o `status.json` (a coleta não conhece a página).

## Códigos de saída

| Código | Quando |
|---|---|
| 0 | Site gerado |
| 1 | Qualquer falha acima |
| 2 | Erro de uso (argumentos), do `argparse` |

## Workflow `publicar-pagina.yml`

| Item | Valor |
|---|---|
| Nome | `Publicar página` |
| Gatilho | `workflow_run` de `Coleta diária` (`types: [completed]`, qualquer conclusão) e `workflow_dispatch` |
| Condição | `github.event_name == 'workflow_dispatch' \|\| github.event.workflow_run.head_branch == github.event.repository.default_branch` |
| Permissões | `contents: read`, `pages: write`, `id-token: write` |
| Concorrência | grupo `pagina`, `cancel-in-progress: false` |
| Checkout | padrão (sem `ref`): o commit do bot da coleta, não o `head_sha` dela |
| Passos | `uv sync --locked`; `.venv/bin/python -m monitor_comissoes.pagina gerar --saida site`; `configure-pages`; `upload-pages-artifact` (`path: site`); `deploy-pages` (`environment: github-pages`) |
| Falha do `gerar` | o job fica vermelho, o upload e o deploy não rodam, a página publicada fica como está |
| Efeito na coleta | nenhum: é outro workflow |
| Segredos | nenhum; só o `GITHUB_TOKEN` com as permissões acima |

A coleta commita `data/status.json` mesmo quando falha; por isso a página é regenerada depois de toda coleta e a faixa de erro aparece no mesmo dia.
