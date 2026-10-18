# Contrato: o que a coleta exige das APIs da Câmara

Base: `https://dadosabertos.camara.leg.br/api/v2`. Qualquer desvio abaixo falha a execução inteira, sem gravar nada (PRODUCT.md §7).

## `GET /proposicoes/{id}/tramitacoes` → `fonte_indisponivel` (rede, HTTP) ou `formato_alterado` (conteúdo)

Exigido:

- Resposta JSON objeto com `dados` (lista **não vazia**) e `links`.
- Nenhum link com `rel` diferente de `self` (paginação inesperada é falha) e todo `href` dentro de `https://dadosabertos.camara.leg.br/api/`.
- Em cada elemento: `sequencia` inteiro; `siglaOrgao` texto; `codTipoTramitacao` texto; `dataHora` texto; `descricaoTramitacao` texto ou nulo; `uriUltimoRelator` texto ou nulo.
- `sequencia` única na resposta.
- `uriUltimoRelator` de uma tramitação `320`, quando presente, termina em `/deputados/{inteiro}`.

Não exigido (não existe na fonte, research R1): `X-Total-Count`, paginação.

Ordem de leitura: sempre por `sequencia`, nunca pela ordem da resposta.

Erros de rede e HTTP 5xx/429 passam pelas novas tentativas do transporte (3 tentativas); HTTP 4xx (incluindo 404) falha de imediato.

## `GET /deputados/{id}` → categoria `api_deputados`

Exigido:

- Objeto `dados` com `ultimoStatus.siglaPartido` e `ultimoStatus.nomeEleitoral`, ambos textos não vazios.
- Consultado uma vez por relator distinto fora da lista do NOVO em exercício.

## `GET /deputados?siglaPartido=NOVO&itens=100`

Sem mudança (COL).

## Lote (`proposicoes-AAAA.csv`)

Nova coluna obrigatória `ultimoStatus_uriRelator`. Ausente → `formato_alterado` (já existente) com o nome da coluna.
