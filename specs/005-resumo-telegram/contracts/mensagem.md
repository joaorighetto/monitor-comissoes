# Contrato: a mensagem do dia

Texto puro (sem `parse_mode`), em português, datas `DD/MM`, até **4.096 unidades UTF-16**. Linhas separadas por `\n`, sem espaços no fim. O mesmo conjunto de arquivos e o mesmo `hoje` dão o mesmo texto, byte a byte.

## Tipos

| Tipo (registro) | Quando | Primeira linha |
|---|---|---|
| `normal` | `status.resultado == ok` e `data_referencia == hoje` | `Monitor de comissões` (começa assim, nunca com `⚠`) |
| `erro` | falha da coleta, ou coleta de hoje que não rodou | `⚠ ERRO · Monitor de comissões · DD/MM` (sempre começa com `⚠ ERRO`) |

## Mensagem normal com eventos

```text
Monitor de comissões · dados de 20/10 · 105 itens
3 eventos: 1 entrou · 1 situação · 1 relator

CE
• Entrou: PL AAA/AAAA — chegou à comissão
  https://www.camara.leg.br/propostas-legislativas/1
• Relator: PL BBB/BBBB — designado Fulano (NOVO)
  https://www.camara.leg.br/propostas-legislativas/2

CREDN
• Situação: PL CCC/CCCC — Aguardando Parecer → Pronta para Pauta
  https://www.camara.leg.br/propostas-legislativas/3

⚠ 1 item com relator indeterminado:
• PL DDD/DDDD (CE)
  https://www.camara.leg.br/propostas-legislativas/4

e mais 12, veja a página
https://exemplo.github.io/monitor
```

(Nomes e números fictícios.)

Regras:

1. **Linha 1:** `Monitor de comissões · dados de DD/MM · N itens`. `DD/MM` é o dia, em Brasília, de `dados_camara_em`; `N` é `status.ultimo_retrato_bom.total_itens`.
2. **Linha 2:** `K eventos:` seguido, por tipo com contagem maior que zero, de `contagem rótulo` separados por ` · `, na ordem entrou, saiu, situação, relator, parecer, etiquetas. A contagem é a de `meta.total_por_tipo`, **inclusive os omitidos**. Singular: `1 evento:`.
3. **Grupos:** um por comissão **com evento selecionado**, na ordem de `config.comissoes`: o nome da comissão em linha própria, depois os eventos. Linha em branco entre grupos.
4. **Evento:** uma linha `• Rótulo: IDENTIFICAÇÃO — detalhe` e, logo abaixo, a linha do link oficial recuada em dois espaços. Nenhum evento sai sem link.
5. **Rodapé de excedente:** só quando há omitidos: `e mais N, veja a página` + linha com a URL; sem `aviso.pagina_url`, `e mais N, veja o arquivo do dia` + a URL do arquivo do dia. `N` é exatamente o número de eventos omitidos.
6. **Seleção sob o teto:** alternando entre as comissões (R4 do [research.md](../research.md)); a seleção para no primeiro evento que não cabe.
7. **Avisos** (depois dos grupos, antes do rodapé): ver abaixo.

### Linha de detalhe por tipo

Rótulo: `Entrou`, `Saiu`, `Situação`, `Relator`, `Parecer`, `Etiquetas`.

| Tipo | Detalhe (depois de `IDENTIFICAÇÃO — `) |
|---|---|
| `entrou` | `motivo.texto` (por exemplo `chegou à comissão`, `ganhou etiqueta: autor hoje no NOVO`, `não determinado`) |
| `saiu` | `motivo.texto`; se `destino.apensado_a` existe, ` (apensado a IDENT)`; senão, se o motivo é `outro_orgao`, ` (destino: ÓRGÃO)`; senão, se `destino.situacao` existe e o motivo é `encerrado`, ` (SITUAÇÃO)` |
| `situacao` | `DE → PARA`; se `comissao_de` difere de `comissao`, ` (veio da COMISSÃO_DE)` |
| `relator` | `designado NOME (PARTIDO)`; `devolveu NOME (PARTIDO)`; ou `NOME_DE (PARTIDO) → NOME_PARA (PARTIDO)` para `substituido` |
| `parecer` | `parecer do relator` |
| `etiquetas` | `ganhou A, B` e/ou `perdeu C`, separados por `; ` |

As tramitações do intervalo **não** entram na mensagem; o link leva a elas. O conteúdo de pareceres também não.

## Mensagem sem mudanças

```text
Monitor de comissões
sem mudanças · 105 itens · dados de 20/10
```

Mais os avisos, se houver (mesma forma acima). Não há linha de totais de eventos nem grupos.

## Linha de base

```text
Monitor de comissões
linha de base criada com 105 itens · dados de 20/10
Primeiro retrato: ainda não há com o que comparar.
```

Para `"formato anterior incompatível"`, a terceira linha é `O retrato anterior estava num formato incompatível: a comparação recomeça amanhã.` Sem eventos e sem avisos de relator (o arquivo não tem ressalvas); o aviso de "principal não localizada" continua valendo.

## Intervalo de mais de um dia

Quando `meta.retrato_anterior.dia` e `meta.retrato.dia` distam mais de um dia, uma linha `Cobre de DD/MM a DD/MM: um dia ficou sem retrato.`, **logo depois da última linha do cabeçalho** (a linha de totais, ou a linha `sem mudanças · ...`) e antes de qualquer grupo.

## Avisos

```text
⚠ 2 itens com relator indeterminado:
• PL DDD/DDDD (CE)
  https://...
• PL EEE/EEEE (CREDN)
  https://...
⚠ 1 item com principal não localizada:
• PL FFF/FFFF (CE)
  https://...
```

- Primeiro `relator indeterminado` (das `ressalvas`), depois `principal não localizada` (dos itens do `atual.json`). Cada aviso só existe quando a contagem é maior que zero.
- Plural pela contagem (`1 item`, `2 itens`).
- A **contagem é sempre inteira**. A lista de itens de cada aviso ocupa no máximo **1.200 unidades**; o que não couber vira, na linha seguinte, `• e mais M itens` (sem link, `M` exato).
- Ordem dos itens: comissão da configuração, depois `id`.

## Mensagem de erro da coleta

```text
⚠ ERRO · Monitor de comissões · 20/10
A atualização de 20/10 falhou: <motivo> [<categoria>]
Nenhuma lista nova foi publicada. Últimos dados bons: dados de 19/10 (105 itens).
```

- `<motivo>` e `<categoria>` são os de `status.falha`, sem reescrever. Se o texto total passar do teto, o motivo é cortado no fim e termina com `…`.
- Sem retrato bom: a terceira linha é `Nenhuma lista nova foi publicada. Ainda não há dados bons.`
- Sem eventos, sem totais do dia.

## Mensagem "a coleta de hoje não rodou"

```text
⚠ ERRO · Monitor de comissões · 20/10
A coleta de hoje (20/10) não rodou. Último registro: 19/10, ok.
Nenhuma lista nova foi publicada. Últimos dados bons: dados de 19/10 (105 itens).
```

- `Último registro: DD/MM, <resultado>` vem do `status.json`. Sem `status.json`: `A coleta de hoje (20/10) não rodou. Não há registro de coleta.`
- A terceira linha é a mesma da mensagem de erro (com ou sem dados bons).

## Invariantes (verificadas nos testes)

1. `tamanho(texto) <= 4096` em qualquer entrada, inclusive com centenas de eventos e com `motivo` enorme.
2. Todo evento exibido tem uma linha de link logo abaixo; nenhum aparece cortado.
3. `N` do `e mais N` é igual a `meta.total_eventos − eventos exibidos`.
4. A linha de totais e os avisos aparecem inteiros (contagem) com ou sem excedente.
5. O texto é idêntico em duas formatações da mesma entrada.
6. O texto de uma mensagem normal nunca começa com `⚠`; o de erro sempre começa com `⚠ ERRO`.
