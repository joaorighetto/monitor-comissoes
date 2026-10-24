# Contrato: `cache/indice-autoria.json`

Derivado do lote pela coleta diária; **fora do Git** (`cache/` no `.gitignore`). Levado da coleta
à checagem da pauta pelo cache do GitHub Actions (research R8). Versão de formato 1, JSON compacto
(sem indentação).

```json
{
  "versao_formato": 1,
  "gerado_em": "2026-10-24T03:58:02-03:00",
  "dados_camara_em": "2026-10-24T04:31:37+00:00",
  "anos_lidos": [2003, 2026],
  "tipos": ["MSC", "PDL", "PEC", "PL", "PLP", "REQ"],
  "proposicoes": {
    "2645503": [0, [220629]],
    "2267727": [1, [178929, 204377, 204400, 204528]]
  }
}
```

- `proposicoes`: uma entrada por proposição dos `tipos` presente nos arquivos `proposicoes-{ano}`
  do lote. O valor é `[autoria_novo, deputados]`:
  - `autoria_novo`: `1` se alguma linha de `proposicoesAutores` da proposição tem
    `siglaPartidoAutor == "NOVO"`, senão `0`;
  - `deputados`: os `idDeputadoAutor` não vazios, sem repetição, em ordem crescente.
- Proposição sem nenhuma linha de autor entra com `[0, []]`: está no lote, sem autoria do NOVO.
- `gerado_em`, `dados_camara_em` e `anos_lidos`: os mesmos do `meta` do `atual.json` da mesma
  coleta.

## Escrita

`diaria.executar_diaria` grava o índice no mesmo `gravar_todos` do `atual.json`, do
`anterior.json`, do arquivo de mudanças e do `status.json`: tudo ou nada. Em falha da coleta, o
índice anterior fica como estava. O `python -m monitor_comissoes` (COL) não grava o índice.

## Leitura (checagem da pauta)

Falha com `entrada_invalida` e o caminho quando o arquivo não existe, não é JSON, tem
`versao_formato` diferente de 1, não tem os campos acima ou tem valor fora do formato. Um índice de
uma coleta antiga continua válido: é o "último lote bom".
