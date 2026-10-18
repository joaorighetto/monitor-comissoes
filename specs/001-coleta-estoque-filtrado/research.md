# Research: COL — Coleta e estoque filtrado

Decisões técnicas do plano. Os itens R2, R3, R4, R7 e R10 foram conferidos contra a fonte real em 18/10/2026, depois que o domínio da Câmara foi liberado no ambiente. As conferências são pontuais (cabeçalhos, amostras e um arquivo anual); a captura completa das fixtures ainda não foi feita.

## R1. Cliente HTTP: biblioteca padrão, sem dependência nova

- **Decision**: usar `urllib.request`, com uma camada fina (`transporte.py`) que faz novas tentativas e devolve corpo e cabeçalhos.
- **Rationale**: a constituição (princípio I) exige justificativa escrita para qualquer dependência. As necessidades são simples: GET com cabeçalhos, leitura em blocos para disco, `Content-Length`, `Last-Modified` e novas tentativas. A biblioteca padrão cobre tudo.
- **Alternatives considered**: `requests` ou `httpx` (conveniência de API, mas uma dependência a mais para manter e atualizar; o ganho não paga). `urllib3` com `Retry` (idem).

## R2. Formato das datas dos arquivos (conferido)

- **Decision**: o parser de `ultimoStatus_dataHora` e `dataApresentacao` é estrito, no formato ISO sem fuso, `AAAA-MM-DDTHH:MM:SS`. Um valor que não segue esse formato falha a execução com "formato alterado: coluna X". Datas sem fuso são tratadas como horário de Brasília.
- **Conferido na fonte real**: `dataApresentacao` = `2004-05-13T14:41:00` e `ultimoStatus_dataHora` = `2024-12-17T00:00:00` (amostra de `proposicoes-2024.csv`).
- **Rationale**: aceitar variações em silêncio violaria a falha visível (princípio III).
- **Alternatives considered**: parser tolerante que tenta vários formatos. Rejeitado: esconde mudança de formato.

## R3. Detecção de arquivo incompleto

- **Decision**, conforme o esclarecimento da spec: (a) se o servidor informar `Content-Length`, comparar com os bytes recebidos; (b) validar, em uma leitura completa do arquivo, que toda linha tem o mesmo número de colunas do cabeçalho e que o leitor de CSV não termina dentro de um campo entre aspas. Ambos viram "arquivo incompleto".
- **Rationale**: dá uma regra testável sem depender do dia anterior. O leitor de CSV em modo estrito detecta corte dentro de um campo entre aspas, que é o caso mais provável com `ementa` e `despacho` longos.
- **Alternatives considered**: mínimo de linhas por ano (rejeitado na spec; fica com a AGE).
- **Conferido na fonte real**: `proposicoes-2024.csv` responde com `Content-Length: 53086966` e `Last-Modified: Sat, 17 Oct 2026 04:33:58 GMT`. Logo, a verificação (a) é viável. Se um arquivo vier sem `Content-Length`, só vale (b), e o código trata essa ausência como falha de formato em vez de seguir sem a checagem.
- **Cuidados de leitura**: os arquivos têm BOM UTF-8 (ler como `utf-8-sig`), separador `;`, campos entre aspas e quebras de linha dentro de `ementaDetalhada` e `keywords`. O limite de tamanho de campo do leitor de CSV precisa ser aumentado.

## R4. Esquema real dos arquivos e da API (conferido)

- **Decision**: as colunas usadas são as documentadas em `docs/fontes.md` §1. A captura de fixtures verifica cada uma e registra os cabeçalhos HTTP (`Content-Length`, `Last-Modified`, `Content-Type`) em `tests/fixtures/camara/manifesto.json`.
- **Conferido na fonte real**: o cabeçalho de `proposicoes-2024.csv` tem as 31 colunas documentadas; o de `proposicoesAutores-2024.csv` tem as 12. Em autores que não são deputados (por exemplo, "Senado Federal - Rogério Carvalho"), `idDeputadoAutor` vem vazio e `siglaPartidoAutor` vem preenchido ("PT"). Um senador com partido NOVO satisfaria `autoria NOVO` pela regra do `PRODUCT.md` §5.4; a spec já cobre o caso.
- **Colunas de `proposicoes-{ano}.csv` usadas**: `id`, `siglaTipo`, `numero`, `ano`, `ementa`, `dataApresentacao`, `uriPropPrincipal`, `ultimoStatus_dataHora`, `ultimoStatus_siglaOrgao`, `ultimoStatus_descricaoSituacao`.
- **Colunas de `proposicoesAutores-{ano}.csv` usadas**: `idProposicao`, `idDeputadoAutor`, `nomeAutor`, `siglaPartidoAutor`, `ordemAssinatura`.
- **API** (conferida): `GET /api/v2/deputados?siglaPartido=NOVO&itens=100`, com `Accept: application/json`. Resposta: `dados[]` com `id`, `nome`, `siglaPartido`, e `links[]` com `rel`/`href` (também no cabeçalho `Link`). Em 18/10/2026, `X-Total-Count: 5`. A paginação segue o `rel: "next"` de `links`; sem `next`, acabou. Conferir que o total de itens lidos bate com `X-Total-Count` é uma checagem barata de completude.

## R5. Estratégia de leitura: poucas passadas, memória constante

- **Decision**: baixar cada arquivo para um diretório temporário e ler em fluxo (`csv.reader`, nunca carregar o arquivo inteiro). Passadas:
  1. API de deputados (falha cedo, antes de baixar 1 GB).
  2. Para cada ano: baixar `proposicoesAutores` e `proposicoes`; validar completude (R3).
  3. Leitura dos autores: ids das proposições com `autoria NOVO` ou com autor na lista de deputados do NOVO → conjunto de candidatas.
  4. Leitura das proposições: mapa `id → id da principal` somente para linhas que têm principal (estimativa de algumas centenas de milhares de entradas, sem o texto).
  5. Subida das cadeias (com detecção de ciclo) → conjunto de ids de referência necessários.
  6. Segunda leitura das proposições, extraindo apenas as linhas das candidatas (PL e PLP) e das referências.
  7. Segunda leitura dos autores, extraindo todos os autores das candidatas que entraram na lista (para mostrar autores com partido na data).
- **Rationale**: manter todos os registros em memória custaria gigabytes. O mapa de apensação é pequeno, e as linhas completas só são guardadas para as dezenas de ids que importam. Os arquivos ficam em disco durante a execução (cerca de 1 GB, aceitável em runner do Actions).
- **Alternatives considered**: carregar tudo em memória (rejeitado: memória). Baixar de novo para cada passada (rejeitado: dobra o tráfego). Banco SQLite temporário (rejeitado pela simplicidade e porque não é preciso consultar de forma ad hoc).

## R6. Relógio e fuso

- **Decision**: "agora" é injetável. O fuso de Brasília é fixo em UTC−3 (`datetime.timezone`), sem depender de base de fusos do sistema. "Parado há" = dias inteiros entre a data do último status e a data de Brasília da geração.
- **Rationale**: o Brasil não tem horário de verão desde 2019, então UTC−3 é suficiente. O relógio injetável torna os testes e a repetibilidade determinísticos.
- **Observação**: duas execuções em dias de Brasília diferentes darão `parado_ha_dias` diferentes, mesmo com os mesmos dados. A repetibilidade da spec (SC-004) vale para execuções no mesmo dia, ou com o relógio fixado.

## R7. Desempenho e volume (medição parcial)

- **Decision**: nenhuma meta formal. Meta interna de menos de 20 minutos por execução. Registrar aqui o tempo e o pico de memória da primeira execução completa.
- **Medido em 18/10/2026** com o maior arquivo, `proposicoes-2025.csv`: 90.184.324 bytes e 107.587 linhas (igual à sondagem). Download em 6,9 s (~13 MB/s). Leitura completa com `csv.reader` em modo estrito, com conferência de colunas por linha, em 0,6 s, com pico de 12 MB de memória.
- **Extrapolação, não medida**: para ~1 GB, o download deve levar da ordem de 80 s e a leitura, alguns segundos por passada. A folga sobre a meta é grande; o gargalo é a rede. A primeira execução completa confirma ou corrige.
- **Rationale**: a medição de um arquivo real mostra que Python puro basta e que paralelizar não se justifica.
- **Alternatives considered**: paralelizar downloads. Rejeitado até medir: complexidade sem necessidade comprovada.

## R8. Formato da configuração: TOML

- **Decision**: `config.toml` na raiz, lido com `tomllib` (biblioteca padrão), com `comissoes` e `ano_minimo`.
- **Rationale**: permite comentários explicando, por exemplo, por que o ano mínimo é 2003, o que ajuda quem for editar sem conhecer o código. Não é dependência nova.
- **Alternatives considered**: `config.json` (sem comentários). Variáveis de ambiente (reservadas a segredos pelo princípio VI; comissão não é segredo e precisa ficar versionada). **Confirmado pelo mantenedor em 18/10/2026: TOML.**

## R13. Instalação do pacote: `uv_build`

- **Decision**: `[build-system]` com `uv_build` e `package = true` em `pyproject.toml`, para que `uv run python -m monitor_comissoes` encontre o pacote em `src/`.
- **Rationale**: conferido em 18/10/2026: com `package = false`, `src/` não está em `sys.path` no `uv run` (só o pytest tem `pythonpath = ["src"]`). Decidido pelo mantenedor (opção A).
- **Alternatives considered**: `PYTHONPATH=src` antes de cada comando (rejeitada).
- **Consequência**: o `uv.lock` muda e deve ser comitado junto, porque o CI usa `uv sync --locked`.

## R9. Gravação atômica

- **Decision**: gravar em `data/atual.json.tmp` na mesma pasta, fazer `flush` e `fsync`, e então `os.replace` para `data/atual.json`. Em qualquer exceção antes do `os.replace`, o temporário é apagado e o arquivo anterior permanece.
- **Rationale**: `os.replace` é atômico no mesmo sistema de arquivos. Garante que `atual.json` nunca fica pela metade (FR-018).

## R10. Link oficial da proposição (conferido)

- **Decision**: `https://www.camara.leg.br/propostas-legislativas/{id}`.
- **Conferido**: `GET /propostas-legislativas/2319917` (PL 937/2022, da sondagem) responde 302 para `https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2319917&fichaAmigavel=nao`, a ficha da proposição. O link é estável e corresponde ao id. A conferência manual (quickstart) repete isso para os três casos de aceitação.
- **Alternatives considered**: usar o campo `urlInteiroTeor` (leva ao documento, não à ficha da proposição).

## R11. Ordem determinística dos itens

- **Decision**: ordenar por data do último status crescente (parado há mais tempo primeiro) e, em empate, por `id` crescente.
- **Rationale**: coincide com a ordem padrão da página (PRODUCT.md §5.5) e é estável. Não depende da ordem dos arquivos.

## R12. Fixtures

- **Decision**: recortes reais, ou seja, linhas copiadas sem alteração dos arquivos da Câmara (cabeçalho completo preservado) e a resposta real da API de deputados, mais um `manifesto.json` com cabeçalhos HTTP. Um `README` em `tests/fixtures/camara/` registra a data da captura e as linhas escolhidas. A captura é feita por `tests/capturar_fixtures.py`, que escolhe as linhas pelos ids dos casos de aceitação, suas cadeias de apensação e algumas linhas de contraste.
- **Casos derivados**: o ciclo de apensação e a "principal não localizada" provavelmente não existem nos dados reais. Eles são variações de linhas reais com `uriPropPrincipal` alterada, **identificadas como derivadas** no README e nos nomes dos arquivos.
- **Rationale**: a spec pede fixtures reais; o que não existe na realidade precisa ser sintético, mas sem se passar por real.
