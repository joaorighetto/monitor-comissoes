"""Formatação pura da mensagem do dia (AVI): dicionários entram, texto sai.

Sem relógio, sem rede e sem disco. Formato: specs/005-resumo-telegram/contracts/mensagem.md.
"""

from datetime import date, datetime

from .config import Config
from .estoque import BRASILIA

LIMITE = 4096  # unidades UTF-16 de uma mensagem do Telegram
LIMITE_AVISO = 1200  # unidades que a lista de itens de cada aviso pode ocupar


def tamanho(texto: str) -> int:
    """Tamanho em unidades UTF-16: a medida conservadora do limite da Bot API (research R3)."""
    return len(texto.encode("utf-16-le")) // 2


def dia_mes(iso: str) -> str:
    """`DD/MM` de uma data e hora ISO com fuso, no dia de Brasília."""
    return datetime.fromisoformat(iso).astimezone(BRASILIA).strftime("%d/%m")


def destino_da_pagina(config: Config, dia: str) -> tuple[str, str]:
    """Texto e endereço do "veja a página" (FR-011): a página, ou o arquivo do dia sem ela."""
    if config.pagina_url:
        return "veja a página", config.pagina_url
    return (
        "veja o arquivo do dia",
        f"https://github.com/{config.repositorio}/blob/main/data/mudancas/{dia}.json",
    )


TITULO = "Monitor de comissões"
ROTULOS = {
    "entrou": "Entrou",
    "saiu": "Saiu",
    "situacao": "Situação",
    "relator": "Relator",
    "parecer": "Parecer",
    "etiquetas": "Etiquetas",
}
# Como a linha de totais chama cada tipo (a ordem é a de `mudancas.TIPOS`).
NOMES_NOS_TOTAIS = {tipo: rotulo.lower() for tipo, rotulo in ROTULOS.items()}
LINHA_DA_LINHA_DE_BASE = {
    "primeiro retrato": "Primeiro retrato: ainda não há com o que comparar.",
    "formato anterior incompatível": (
        "O retrato anterior estava num formato incompatível: a comparação recomeça amanhã."
    ),
}


def _itens(n: int) -> str:
    return f"{n} item" if n == 1 else f"{n} itens"


def _relator(relator: dict) -> str:
    return f"{relator['nome']} ({relator['partido_hoje']})"


def _detalhe(evento: dict) -> str:
    """O texto depois de `IDENTIFICAÇÃO — ` (tabela de contracts/mensagem.md)."""
    tipo = evento["tipo"]
    if tipo == "entrou":
        return evento["motivo"]["texto"]
    if tipo == "saiu":
        texto = evento["motivo"]["texto"]
        destino = evento["destino"]
        if destino["apensado_a"]:
            return f"{texto} (apensado a {destino['apensado_a']['identificacao']})"
        if evento["motivo"]["codigo"] == "outro_orgao" and destino["orgao"]:
            return f"{texto} (destino: {destino['orgao']})"
        if evento["motivo"]["codigo"] == "encerrado" and destino["situacao"]:
            return f"{texto} ({destino['situacao']})"
        return texto
    if tipo == "situacao":
        texto = f"{evento['de']} → {evento['para']}"
        if evento["comissao_de"] != evento["comissao"]:
            texto += f" (veio da {evento['comissao_de']})"
        return texto
    if tipo == "relator":
        mudanca = evento["mudanca"]
        if mudanca == "designado":
            return f"designado {_relator(evento['para'])}"
        if mudanca == "devolveu":
            return f"devolveu {_relator(evento['de'])}"
        return f"{_relator(evento['de'])} → {_relator(evento['para'])}"
    if tipo == "parecer":
        return "parecer do relator"
    partes = []
    if evento["ganhou"]:
        partes.append("ganhou " + ", ".join(evento["ganhou"]))
    if evento["perdeu"]:
        partes.append("perdeu " + ", ".join(evento["perdeu"]))
    return "; ".join(partes)


def _linhas_do_evento(evento: dict) -> list[str]:
    rotulo = ROTULOS[evento["tipo"]]
    return [
        f"• {rotulo}: {evento['identificacao']} — {_detalhe(evento)}",
        f"  {evento['link']}",
    ]


def _cabecalho(documento: dict, status: dict) -> list[str]:
    meta = documento["meta"]
    dados = dia_mes(meta["retrato"]["dados_camara_em"])
    base = meta["linha_de_base"]
    if base is not None:
        return [
            TITULO,
            f"linha de base criada com {_itens(base['total_itens'])} · dados de {dados}",
            LINHA_DA_LINHA_DE_BASE[base["motivo"]],
        ]
    total = _itens(status["ultimo_retrato_bom"]["total_itens"])
    if meta["total_eventos"] == 0:
        linhas = [TITULO, f"sem mudanças · {total} · dados de {dados}"]
    else:
        contagens = " · ".join(
            f"{meta['total_por_tipo'][tipo]} {nome}"
            for tipo, nome in NOMES_NOS_TOTAIS.items()
            if meta["total_por_tipo"][tipo] > 0
        )
        n = meta["total_eventos"]
        evento = "evento" if n == 1 else "eventos"
        linhas = [
            f"{TITULO} · dados de {dados} · {total}",
            f"{n} {evento}: {contagens}",
        ]
    anterior = meta["retrato_anterior"]
    if anterior is not None:
        dias = date.fromisoformat(meta["retrato"]["dia"]) - date.fromisoformat(anterior["dia"])
        if dias.days > 1:
            de = date.fromisoformat(anterior["dia"]).strftime("%d/%m")
            ate = date.fromisoformat(meta["retrato"]["dia"]).strftime("%d/%m")
            linhas.append(f"Cobre de {de} a {ate}: um dia ficou sem retrato.")
    return linhas


def _fila_por_comissao(eventos: list[dict], comissoes: tuple[str, ...]) -> dict[str, list[dict]]:
    """Os eventos de cada comissão, na ordem do arquivo; as comissões na ordem da configuração."""
    filas: dict[str, list[dict]] = {c: [] for c in comissoes}
    for evento in eventos:
        filas.setdefault(evento["comissao"], []).append(evento)
    de_fora = sorted(c for c in filas if c not in comissoes)
    return {c: filas[c] for c in (*comissoes, *de_fora)}


def _montar_texto(
    cabecalho: list[str],
    filas: dict[str, list[dict]],
    quantos: dict[str, int],
    avisos: tuple[str, ...],
    omitidos: int,
    destino: tuple[str, str],
) -> str:
    secoes = ["\n".join(cabecalho)]
    for comissao, fila in filas.items():
        if quantos[comissao] == 0:
            continue
        linhas = [comissao]
        for evento in fila[: quantos[comissao]]:
            linhas.extend(_linhas_do_evento(evento))
        secoes.append("\n".join(linhas))
    if avisos:
        secoes.append("\n".join(avisos))
    if omitidos:
        secoes.append(f"e mais {omitidos}, {destino[0]}\n{destino[1]}")
    return "\n\n".join(secoes)


def montar_normal(
    mudancas: dict,
    status: dict,
    config: Config,
    avisos: tuple[str, ...] = (),
) -> str:
    """A mensagem normal do dia: com eventos, sem mudanças ou linha de base (contracts/mensagem.md).

    `avisos` são blocos já formatados; ficam depois dos grupos e antes do rodapé, e o espaço deles
    é reservado antes dos eventos. Sob o teto, os eventos entram alternando entre as comissões,
    na ordem do arquivo dentro de cada uma, e a seleção para no primeiro que não cabe.
    """
    cabecalho = _cabecalho(mudancas, status)
    filas = _fila_por_comissao(mudancas["eventos"], config.comissoes)
    total = sum(len(f) for f in filas.values())
    destino = destino_da_pagina(config, mudancas["meta"]["data"])
    quantos = dict.fromkeys(filas, 0)

    def texto() -> str:
        return _montar_texto(
            cabecalho, filas, quantos, avisos, total - sum(quantos.values()), destino
        )

    if tamanho(texto()) > LIMITE:
        raise ValueError("o cabeçalho e os avisos não cabem em uma mensagem (aviso grande demais)")
    while any(quantos[c] < len(f) for c, f in filas.items()):
        for comissao, fila in filas.items():
            if quantos[comissao] == len(fila):
                continue
            quantos[comissao] += 1
            if tamanho(texto()) > LIMITE:
                quantos[comissao] -= 1
                return texto()
    return texto()


# --- mensagens de erro (US4) -------------------------------------------------------------------

ALERTA = "⚠ ERRO"


def _abertura_do_erro(hoje: date) -> str:
    return f"{ALERTA} · {TITULO} · {hoje.strftime('%d/%m')}"


def _dados_bons(status: dict | None) -> str:
    """A última linha das mensagens de erro: o que continua publicado."""
    retrato = None if status is None else status["ultimo_retrato_bom"]
    if retrato is None:
        return "Nenhuma lista nova foi publicada. Ainda não há dados bons."
    return (
        "Nenhuma lista nova foi publicada. Últimos dados bons: "
        f"dados de {dia_mes(retrato['dados_camara_em'])} ({_itens(retrato['total_itens'])})."
    )


def _cortado(texto: str, orcamento: int) -> str:
    """O começo de `texto` que cabe em `orcamento` unidades UTF-16, com `…` se foi cortado."""
    if tamanho(texto) <= orcamento:
        return texto
    corte = texto[: max(orcamento - 1, 0)]
    while corte and tamanho(corte) > orcamento - 1:
        corte = corte[:-1]
    return corte + "…"


def montar_erro_da_coleta(status: dict, hoje: date) -> str:
    """Mensagem de erro da coleta que falhou (FR-012): motivo, categoria e dados bons."""
    falha = status["falha"]
    dia = date.fromisoformat(status["data_referencia"]).strftime("%d/%m")
    abertura = _abertura_do_erro(hoje)
    fim = _dados_bons(status)
    resto = f"A atualização de {dia} falhou: {{motivo}} [{falha['categoria']}]"
    orcamento = LIMITE - tamanho("\n".join([abertura, resto.replace("{motivo}", ""), fim]))
    motivo = _cortado(falha["motivo"], orcamento)
    return "\n".join([abertura, resto.replace("{motivo}", motivo), fim])


def montar_coleta_nao_rodou(status: dict | None, hoje: date) -> str:
    """Mensagem de erro quando o `status.json` não é do dia da execução (FR-013a)."""
    dia = hoje.strftime("%d/%m")
    if status is None:
        registro = "Não há registro de coleta."
    else:
        ultimo = date.fromisoformat(status["data_referencia"]).strftime("%d/%m")
        registro = f"Último registro: {ultimo}, {status['resultado']}."
    return "\n".join(
        [
            _abertura_do_erro(hoje),
            f"A coleta de hoje ({dia}) não rodou. {registro}",
            _dados_bons(status),
        ]
    )


# --- avisos (US6) ------------------------------------------------------------------------------


def _bloco_de_aviso(titulo: str, itens: list[dict]) -> str:
    """Um aviso: contagem inteira e lista de itens até `LIMITE_AVISO`; o resto vira `e mais M`."""
    total = len(itens)
    cabecalho = f"⚠ {_itens(total)} com {titulo}:"

    def montar(quantos: int) -> str:
        linhas = [cabecalho]
        for item in itens[:quantos]:
            linhas.extend([f"• {item['identificacao']} ({item['comissao']})", f"  {item['link']}"])
        if quantos < total:
            linhas.append(f"• e mais {_itens(total - quantos)}")
        return "\n".join(linhas)

    quantos = 0
    while quantos < total and tamanho(montar(quantos + 1)) <= LIMITE_AVISO:
        quantos += 1
    return montar(quantos)


def blocos_de_aviso(
    ressalvas: list[dict], sem_principal: list[dict], config: Config
) -> tuple[str, ...]:
    """Os avisos do dia (FR-007): relator indeterminado e principal não localizada.

    Cada família só existe com contagem maior que zero. Os itens seguem a comissão da
    configuração e depois o `id`.
    """
    posicao = {c: i for i, c in enumerate(config.comissoes)}

    def ordenar(itens: list[dict]) -> list[dict]:
        return sorted(itens, key=lambda i: (posicao.get(i["comissao"], len(posicao)), i["id"]))

    blocos = []
    if ressalvas:
        blocos.append(_bloco_de_aviso("relator indeterminado", ordenar(ressalvas)))
    if sem_principal:
        blocos.append(_bloco_de_aviso("principal não localizada", ordenar(sem_principal)))
    return tuple(blocos)
