# Contrato: `data/envio.json`

Registro do último envio de cada tipo de mensagem. Existe para a reexecução no mesmo dia não repetir a mensagem (constituição, V). Codificação UTF-8, `ensure_ascii` desligado, indentação de 2 espaços, uma quebra de linha no fim, ordem de campos fixa (a mesma de `serializar` dos demais arquivos).

## Estrutura

```json
{
  "versao_formato": 1,
  "ultimo_envio": {
    "normal": "2026-10-20",
    "erro": null
  }
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `versao_formato` | inteiro | `1`. Qualquer outro valor falha o envio |
| `ultimo_envio.normal` | `null` ou `AAAA-MM-DD` | Dia da última mensagem normal que o Telegram aceitou |
| `ultimo_envio.erro` | `null` ou `AAAA-MM-DD` | Dia da última mensagem de erro (da coleta ou "a coleta de hoje não rodou") que o Telegram aceitou |

O arquivo não traz hora, texto, token nem chat_id.

## Regras

1. **Ausente** = nada enviado ainda (`normal` e `erro` nulos). O primeiro envio cria o arquivo.
2. **Inválido** (JSON ilegível, objeto com campos a mais ou a menos, data fora do formato, versão desconhecida) falha o envio, sem enviar e sem sobrescrever o arquivo.
3. **Consulta:** antes de enviar, se `ultimo_envio[tipo] == hoje`, o envio não acontece, a execução imprime `JÁ ENVIADO: ...` e sai com 0.
4. **Gravação:** só depois de a Bot API responder `ok: true`. Grava o dia de hoje no tipo enviado e preserva o outro tipo. A gravação é atômica (`gravar_atomico` da COL). Falha ao gravar depois de um envio aceito sai com 1 e diz que a mensagem **foi** enviada, para ninguém reenviar sem ver.
5. **Falha de envio** não toca no arquivo.
6. **Um tipo, um dia:** uma normal e uma de erro por dia. Uma mensagem normal depois de uma de erro do mesmo dia é enviada (a falha foi superada); uma de erro depois de uma normal também (falha real posterior).
7. **Reenvio manual de propósito:** o mantenedor apaga o dia do tipo desejado (ou o arquivo) em um commit e dispara o workflow. Não há opção de linha de comando para forçar.

## Compatibilidade

- Nenhum outro arquivo de dados muda. O `status.json` não ganha campo.
- O workflow de envio é o único que o grava e o commita; a coleta não o lê nem o toca.
