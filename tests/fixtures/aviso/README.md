# Fixtures da AVI

Todos os arquivos são **sintéticos**, derivados dos contratos (`specs/004-mudancas-desde-ontem/contracts/`,
`specs/002-execucao-diaria-agendada/contracts/` e `specs/005-resumo-telegram/contracts/`). Nenhum foi
capturado da rede e nenhum contém token ou chat_id.

## Cenários (`<cenário>/atual.json`, `status.json`, `mudancas/AAAA-MM-DD.json`)

Gerados por `tests/aviso_gerar_fixtures.py` a partir de `tests/aviso_sinteticos.py`; o teste
`tests/test_aviso_sinteticos.py` confere que os arquivos versionados são iguais ao que o gerador grava.

| Cenário | O que mostra |
|---|---|
| `completo` | Um evento de cada um dos seis tipos (CE e CREDN) e uma ressalva de relator indeterminado |
| `sem-eventos` | Arquivo de mudanças sem eventos nem linha de base |
| `linha-base-primeiro` | Linha de base, motivo "primeiro retrato" |
| `linha-base-formato` | Linha de base, motivo "formato anterior incompatível" |
| `intervalo` | Retrato anterior três dias antes do de hoje |
| `falha` | `status.json` de falha (`arquivos_desatualizados`) e nenhum arquivo de mudanças do dia |
| `sem-retrato` | Falha sem nenhum retrato bom |

Os ids, identificações e links dos itens são **reais** (do `data/atual.json` de 20/10/2026). O que é
inventado: os motivos e as situações dos eventos, os relatores trocados e os dois itens marcados com
`principal_nao_localizada` (o `data/atual.json` real não tem nenhum).

## `telegram/`

Exemplos do formato de resposta da Bot API (`sendMessage`), escritos à mão a partir da documentação
publicada pelo Telegram; não são capturas.
