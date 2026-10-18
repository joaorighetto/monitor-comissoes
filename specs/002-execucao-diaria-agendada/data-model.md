# Data Model: AGE — Execução diária agendada

Entidades da spec com seus campos, fontes e regras de validação. Os formatos de arquivo completos estão em [contracts/](contracts/).

## Configuração (`config.toml`), campos novos

Os campos da COL (`comissoes`, `ano_minimo`) não mudam. A AGE acrescenta uma tabela `[execucao]`, **opcional**: sem ela valem os padrões abaixo, e um `config.toml` da COL continua válido.

| Campo | Tipo | Padrão | Regra de validação |
|---|---|---|---|
| `execucao.tentativas` | inteiro | 4 | Entre 1 e 10 (FR-019) |
| `execucao.espera_minutos` | inteiro | 30 | Entre 0 e 120 (FR-019) |
| `execucao.limite_variacao_percentual` | inteiro | 20 | Entre 1 e 100 (FR-018) |

Valor inválido → falha de configuração (`configuracao`), sem repetição, registrada no `status.json`. Chave desconhecida na tabela também é inválida, para que um erro de digitação não deixe o padrão valendo em silêncio.

## Estoque bruto

Número inteiro. É a contagem, nos arquivos `proposicoes-{ano}.csv` do lote, das proposições com `siglaTipo` ∈ {`PL`, `PLP`} e `ultimoStatus_siglaOrgao` ∈ `comissoes` (órgão do **próprio** último status, sem resolver apensação, sem etiquetas). Na sondagem de 17/10/2026: 1.531.

Regras:
- É calculado na mesma coleta que gera o `atual.json`, sobre os mesmos arquivos.
- Zero → falha `estoque_vazio`.
- Não é gravado no `atual.json`; vai para `ultimo_retrato_bom.estoque_bruto` do `status.json`.

## Retrato bom

O `data/atual.json` mais recente que passou em todas as checagens. Para a AGE, o retrato bom é descrito por quatro campos, todos no `status.json`:

| Campo | Origem |
|---|---|
| `gerado_em` | `meta.gerado_em` do `atual.json` |
| `dados_camara_em` | `meta.dados_camara_em` do `atual.json` |
| `total_itens` | `meta.total_itens` do `atual.json` |
| `estoque_bruto` | contagem da coleta que gerou esse `atual.json`. `null` apenas quando o retrato é recomposto em falha e não há base válida (regra de coerência abaixo) |

Se o `atual.json` não existir, ou existir sem um `meta` válido (campos acima ausentes ou com tipo errado), não há retrato bom: `ultimo_retrato_bom` é `null`. O arquivo **não é alterado** por isso.

Regra de coerência: o `estoque_bruto` só serve de base para a comparação do dia seguinte se o `gerado_em` registrado no status for igual ao `meta.gerado_em` do `atual.json` em disco. Se forem diferentes, ou se faltar um dos arquivos, não há base (ver "Base de comparação").

## Status da execução (`data/status.json`)

Descreve a **última execução**, bem-sucedida ou não. Campos e exemplos em [contracts/status-json.md](contracts/status-json.md).

| Campo | Tipo | Regra |
|---|---|---|
| `versao_formato` | inteiro | 1 |
| `resultado` | `"ok"` ou `"falha"` | |
| `verificado_em` | texto ISO 8601 com fuso, Brasília | Momento em que a execução terminou, em sucesso ou falha |
| `data_referencia` | texto `AAAA-MM-DD` | Data de Brasília de `verificado_em` (FR-024a) |
| `tentativas` | inteiro ≥ 0 | Coletas efetivamente tentadas. 0 se a execução falhou antes de coletar (configuração inválida) |
| `falha` | `null` ou `{categoria, motivo}` | `null` se e somente se `resultado = "ok"` (FR-013) |
| `variacao_aceita` | `null` ou `{estoque_anterior, estoque_novo, variacao_percentual}` | Só preenchido em sucesso com confirmação manual e variação acima do limite (FR-018b) |
| `ultimo_retrato_bom` | `null` ou objeto de quatro campos | Em sucesso, o retrato recém-gravado. Em falha, o retrato mantido. `null` quando não existe `atual.json` |

Invariantes:
1. `resultado = "ok"` ⇒ `falha = null` e `ultimo_retrato_bom ≠ null`.
2. `resultado = "falha"` ⇒ `falha ≠ null` e `variacao_aceita = null`.
3. `ultimo_retrato_bom.gerado_em` é igual ao `meta.gerado_em` do `atual.json` que ficou em disco ao fim da execução.
4. Mesmos dados e mesmo relógio ⇒ arquivo idêntico byte a byte (FR-012).

## Base de comparação

O estoque bruto do `ultimo_retrato_bom` do `status.json` lido no início da execução, **se** passar na regra de coerência. Caso contrário, não há base, e a variação não se aplica (primeiro dia, ou arquivos que não se correspondem). Nesse caso a execução avisa em `stderr`, e as checagens de estoque bruto vazio e de lista vazia continuam valendo.

## Categorias de falha

As sete da COL mais duas, `estoque_implausivel` e `interna`. A coluna "Repete?" diz se a AGE tenta de novo depois de esperar (FR-019, FR-020).

| Categoria | Origem | Repete? | Exemplo de motivo |
|---|---|---|---|
| `configuracao` | COL (inclui os campos novos de `[execucao]`) | Não | `execucao.tentativas deve ser um inteiro entre 1 e 10` |
| `fonte_indisponivel` | COL | **Sim** | `proposicoes-2024.csv: HTTP 503` |
| `formato_alterado` | COL | Não | `proposicoes-2024.csv: formato alterado: coluna ultimoStatus_dataHora` |
| `arquivos_desatualizados` | COL (idade e dispersão) | **Sim** | `os arquivos da Câmara foram gerados em momentos diferentes (…)` |
| `arquivo_incompleto` | COL | **Sim** | `proposicoes-2025.csv: recebidos 100 de 200 bytes` |
| `api_deputados` | COL | **Sim** | `não foi possível obter os deputados do NOVO` |
| `estoque_vazio` | COL (lista filtrada vazia) e AGE (estoque bruto vazio) | Não | `nenhum PL/PLP nas comissões acompanhadas` |
| `estoque_implausivel` | AGE | Não | `estoque bruto variou -28,2% (1531 → 1100); o limite é de 20%` |
| `interna` | AGE e COL (exceção inesperada) | Não | `KeyError: 'itens'` |

A falha ao commitar ou empurrar para o repositório **não** é categoria do `status.json`: nesse caso não há como gravar o registro. Ela aparece só como workflow vermelho e no log do passo (FR-008).

## Execução diária

Uma rodada do workflow. Ciclo de vida:

```text
início
  └─ ler config ──inválida──────────────────────────────► falha (configuracao, 0 tentativas)
  └─ ler base (status.json + atual.json)
  └─ tentativa n (1..N)
        ├─ coleta falha, repetível, n < N ──► esperar ──► tentativa n+1
        ├─ coleta falha, repetível, n = N ──────────────► falha
        ├─ coleta falha, não repetível ────────────────► falha
        └─ coleta ok
             └─ plausibilidade
                  ├─ estoque bruto = 0 ───────────────► falha (estoque_vazio)
                  ├─ variação > limite, sem confirmação ► falha (estoque_implausivel)
                  └─ passa (ou variação aceita) ──────► gravar atual.json, gravar status.json (ok)
```

Em qualquer falha, só o `status.json` é gravado. O `atual.json` não é tocado.

## Mensagem do commit

Uma linha, gerada a partir do `status.json`:

| Situação | Mensagem |
|---|---|
| Sucesso | `dados: AAAA-MM-DD · ok · N itens · estoque bruto B` |
| Sucesso com variação aceita | `dados: AAAA-MM-DD · ok · variação aceita manualmente (A → B, ±X,X%)` |
| Falha | `dados: AAAA-MM-DD · falha [categoria]` |
