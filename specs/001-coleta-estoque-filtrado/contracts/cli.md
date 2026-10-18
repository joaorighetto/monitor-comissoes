# Contrato: comando

## Invocação

```bash
uv run python -m monitor_comissoes [--config config.toml] [--saida data/atual.json]
```

| Opção | Padrão | Uso |
|---|---|---|
| `--config` | `config.toml` | Arquivo de configuração |
| `--saida` | `data/atual.json` | Arquivo de saída |

Sem outras opções. Sem variáveis de ambiente (a feature não usa segredos).

## Efeitos

- Sucesso: grava (ou substitui, de forma atômica) o arquivo de saída e imprime em `stdout` uma linha: `OK: N itens (CE: a, CREDN: b) · dados da Câmara de DD/MM/AAAA`.
- Falha: não grava e não altera o arquivo de saída existente. Imprime em `stderr` uma linha: `FALHA [categoria]: motivo`.
- Arquivos temporários (downloads, `.tmp` de saída) são apagados em ambos os casos.

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | Sucesso, arquivo gravado |
| 1 | Qualquer falha das categorias abaixo |

## Categorias de falha

`configuracao`, `fonte_indisponivel`, `formato_alterado`, `arquivos_desatualizados`, `arquivo_incompleto`, `api_deputados`, `estoque_vazio`. Descrição e exemplos em [../data-model.md](../data-model.md).

Uma falha inesperada (erro de programação) também sai com código 1 e imprime `FALHA [interna]: ...` com o tipo da exceção; nunca deixa saída parcial.

## Ordem de verificação

1. Configuração (antes de qualquer rede).
2. Deputados do NOVO (antes de baixar os arquivos grandes).
3. Download e validação por ano.
4. Frescor (`Last-Modified`).
5. Cálculo do estoque.
6. Estoque vazio.
7. Gravação atômica.
