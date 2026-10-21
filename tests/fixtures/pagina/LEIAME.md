# Fixtures da página pública (PAG)

Entradas salvas da geração da página. Nenhum teste usa a rede.

**Reais** (cópias dos arquivos do repositório em 20/10/2026, com fim de linha `\n`):

- `atual-real.json`: `data/atual.json`, versão 2 do formato, 105 itens (CE 96, CREDN 9).
- `status-ok.json`: `data/status.json` da mesma execução (`resultado` ok, coerente com o `atual-real.json`).

**Derivadas** (de `atual-real.json`; mudar o conteúdo só pelo `tests/pagina_gerar_fixtures.py`):

- `atual-formato-4.json`: o `atual-real.json` com `meta.versao_formato` 4 (versão desconhecida).
- `status-falha.json`: falha de 21/10 (`arquivos_desatualizados`) com o retrato bom do `atual-real.json`.
- `status-falha-sem-retrato.json`: falha sem `ultimo_retrato_bom`.
- `status-retrato-outro.json`: `resultado` ok, mas com o `dados_camara_em` de outro dia (incoerente com o `atual-real.json`).

**Sintéticas** (arquivos de mudanças no formato de `specs/004-mudancas-desde-ontem/contracts/mudancas-json.md`, com ids, identificações e links de itens reais e motivos inventados):

- `mudancas/2026-10-20.json`: um evento de cada um dos seis tipos, em CE e CREDN, com tramitações em dois deles. O `dados_camara_em` do retrato é o do `atual-real.json`.
- `mudancas/2026-10-19.json`: zero eventos.
- `mudancas/2026-10-18.json`: linha de base "primeiro retrato", 105 itens.
- `mudancas/2026-10-16.json`: cobre de 14 a 16/10, com um evento `saiu` apensado a uma proposição fora da lista.
- Faltam de propósito os dias 17 e 15 (dia sem arquivo).
- `mudancas-teto/2026-10-20.json`: 25 eventos, para o teto de 20 por dia.
- `mudancas-invalida-fora-da-janela/`: um `2026-10-20.json` válido e um `2026-10-10.json` corrompido, que a janela de 7 dias nunca lê.
