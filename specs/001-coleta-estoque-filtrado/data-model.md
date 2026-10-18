# Data Model: COL — Coleta e estoque filtrado

Entidades da spec com seus campos, fontes e regras de validação. Nomes de campos de entrada são as colunas documentadas em `docs/fontes.md`.

## Configuração (`config.toml`)

| Campo | Tipo | Regra de validação |
|---|---|---|
| `comissoes` | lista de textos | Não vazia; cada sigla é texto não vazio, sem repetição e sem espaço no começo ou no fim |
| `ano_minimo` | inteiro | Entre 1990 e o ano corrente |

Valor inválido → falha de configuração antes de qualquer acesso à rede (FR-020).

## Proposição (linha de `proposicoes-{ano}`)

| Campo | Coluna de origem | Observação |
|---|---|---|
| `id` | `id` | Chave única da proposição |
| `tipo` | `siglaTipo` | Candidata somente se `PL` ou `PLP` |
| `numero`, `ano` | `numero`, `ano` | Identificação exibida: `tipo numero/ano` |
| `ementa` | `ementa` | |
| `data_apresentacao` | `dataApresentacao` | Data estrita (R2) |
| `id_principal` | `uriPropPrincipal` | Último trecho numérico da URI; vazio = sem principal |
| `ultimo_status_em` | `ultimoStatus_dataHora` | Data e hora estritas (R2), horário de Brasília |
| `orgao` | `ultimoStatus_siglaOrgao` | Comparado com `comissoes` |
| `situacao` | `ultimoStatus_descricaoSituacao` | |

## Autor (linha de `proposicoesAutores-{ano}`)

| Campo | Coluna de origem | Observação |
|---|---|---|
| `id_proposicao` | `idProposicao` | Liga ao `id` da proposição |
| `id_deputado` | `idDeputadoAutor` | Vazio para autor que não é deputado |
| `nome` | `nomeAutor` | |
| `partido_na_data` | `siglaPartidoAutor` | Partido na data da autoria |
| `ordem` | `ordemAssinatura` | Ordenação dos autores no item |

## Deputado do NOVO em exercício (API)

| Campo | Origem | Observação |
|---|---|---|
| `id` | `dados[].id` | Base de `autor hoje no NOVO` |
| `nome` | `dados[].nome` | Registrado no `meta` para auditoria |

Validação da resposta (qualquer falha é `api_deputados`): o cabeçalho `X-Total-Count` deve existir; o total de deputados lidos deve ser igual a ele; a lista não pode ser vazia; cada link de paginação deve começar com o endereço da API da Câmara (`https://dadosabertos.camara.leg.br/api/`).

## Referência

Resultado de subir a cadeia de apensação de uma candidata.

| Estado | Condição | Efeito |
|---|---|---|
| Própria | A candidata não tem principal | Comissão, situação e "parado há" da própria candidata |
| Raiz | A cadeia termina numa proposição presente nos arquivos lidos | Comissão, situação e "parado há" da raiz; o item mostra "apensado a" |
| Não localizada | A raiz não está nos arquivos lidos, ou a cadeia tem ciclo | Usa o status da própria candidata; o item leva `principal_nao_localizada` (esclarecimento 1) |

## Item do estoque

Candidata que (a) está na comissão segundo sua referência e (b) tem ao menos uma etiqueta. Formato completo em [contracts/atual-json.md](contracts/atual-json.md).

Regras:
- `etiquetas ⊆ {autoria NOVO, autor hoje no NOVO}`, em ordem fixa, sem repetição, e nunca vazia.
- `autoria NOVO` ⇔ algum autor tem `partido_na_data = "NOVO"`.
- `autor hoje no NOVO` ⇔ algum autor tem `id_deputado` na lista de deputados do NOVO em exercício.
- As etiquetas usam os autores da própria candidata, nunca os da referência.
- `comissao` ∈ `comissoes` configuradas.

## Meta

Descrito em [contracts/atual-json.md](contracts/atual-json.md). Campos: versão do formato, momento da geração, data dos dados da Câmara (a mais antiga entre os `Last-Modified`), comissões e ano mínimo, anos lidos, total e total por comissão, deputados do NOVO em exercício usados.

## Transições e ciclo de vida

Não há estado persistente entre execuções nesta feature. O único estado é o arquivo `data/atual.json`, que muda de um valor completo para outro valor completo, ou não muda (gravação atômica).

## Erros (categorias de falha)

| Categoria | Quando | Exemplo de mensagem |
|---|---|---|
| `configuracao` | Valor inválido no `config.toml` | `ano_minimo deve ser um inteiro entre 1990 e 2026` |
| `fonte_indisponivel` | Rede ou HTTP com erro depois das novas tentativas | `fonte indisponível: proposicoes-2024.csv (HTTP 503)` |
| `formato_alterado` | Coluna ausente ou valor fora do formato | `formato alterado: coluna ultimoStatus_dataHora` |
| `arquivos_desatualizados` | `Last-Modified` com mais de 36 horas | `a Câmara não atualizou os arquivos` |
| `arquivo_incompleto` | Arquivo vazio, sem linhas ou cortado | `arquivo incompleto: proposicoes-2025.csv` |
| `api_deputados` | Falha ao obter os deputados do NOVO | `não foi possível obter os deputados do NOVO` |
| `estoque_vazio` | Lista filtrada sem itens | `nenhum item após os filtros` |
