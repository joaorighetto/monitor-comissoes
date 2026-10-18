# Contrato: comando da execução diária

O comando da COL (`python -m monitor_comissoes`) **não muda**: mesmas opções, mesma saída, mesmos códigos (contrato da COL). A AGE acrescenta um módulo próprio.

## Invocação

```bash
uv run python -m monitor_comissoes.diaria executar [--config config.toml] [--atual data/atual.json] [--status data/status.json] [--aceitar-variacao]
uv run python -m monitor_comissoes.diaria mensagem [--status data/status.json]
```

## `executar`

| Opção | Padrão | Uso |
|---|---|---|
| `--config` | `config.toml` | Arquivo de configuração (inclui a tabela opcional `[execucao]`) |
| `--atual` | `data/atual.json` | Arquivo de dados |
| `--status` | `data/status.json` | Arquivo de status |
| `--aceitar-variacao` | desligada | Ignora **somente** a falha de variação acima do limite, só nesta execução. Não ignora estoque vazio nem nenhuma outra falha |

Sem variáveis de ambiente e sem segredos.

### Efeitos

- Sucesso: prepara os dois arquivos como temporários e só então troca o `atual.json` e o `status.json` (se a preparação de qualquer um falhar, nenhum é trocado), imprime em `stdout` uma linha `OK: N itens · estoque bruto B · tentativas T · dados da Câmara de DD/MM/AAAA` e sai com 0.
- Falha: **não toca no `atual.json`**, grava o `status.json` com `resultado = "falha"`, imprime em `stderr` uma linha `FALHA [categoria]: motivo` e sai com 1.
- Cada tentativa que falha por causa repetível imprime em `stderr` `TENTATIVA n de N falhou [categoria]: motivo; nova tentativa em M minutos`.
- Se nem o `status.json` puder ser gravado, imprime `FALHA [interna]: …` em `stderr` e sai com 1.
- Arquivos temporários são apagados em sucesso e em falha.

### Códigos de saída

| Código | Significado |
|---|---|
| 0 | Sucesso: `atual.json` e `status.json` gravados |
| 1 | Qualquer falha das categorias de [../data-model.md](../data-model.md) |

### Ordem de verificação

1. Configuração, antes de qualquer rede.
2. Leitura da base de comparação (`status.json` e `atual.json`, se existirem).
3. Coleta da COL, com repetição das falhas repetíveis.
4. Estoque bruto vazio.
5. Variação do estoque bruto.
6. Gravação do `atual.json` e do `status.json`.

## `mensagem`

Lê o `status.json` e imprime em `stdout` a mensagem de uma linha do commit (tabela em [../data-model.md](../data-model.md), "Mensagem do commit"). Sai com 1 e escreve em `stderr` se o arquivo não existir ou não for válido. Não usa rede.

## Configuração: tabela `[execucao]`

```toml
[execucao]
tentativas = 4                  # coletas por execução, contando a primeira
espera_minutos = 30             # espera entre tentativas
limite_variacao_percentual = 20 # variação do estoque bruto acima da qual a execução falha
```

Opcional; valores padrão iguais aos do exemplo. Validação em [../data-model.md](../data-model.md).
