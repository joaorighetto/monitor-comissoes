"""Respostas da API da Câmara usadas pela checagem da pauta, validadas na leitura.

Cada função devolve os objetos no formato da API, já conferidos (data-model.md, "Validação das
respostas da API"). Qualquer desvio falha a checagem inteira: `formato_alterado` com o campo, ou
`fonte_indisponivel` com o endpoint.
"""

import json
import re
from datetime import date

from ..coleta import URL_BASE
from ..erros import FONTE_INDISPONIVEL, FORMATO_ALTERADO, FalhaDeColeta
from ..transporte import RecursoInexistente, RespostaJson, Transporte

API = f"{URL_BASE}/api/v2"
PADRAO_INICIO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _endpoint(url: str) -> str:
    return url.removeprefix(API)


def _formato(url: str, detalhe: str) -> FalhaDeColeta:
    return FalhaDeColeta(FORMATO_ALTERADO, f"{_endpoint(url)}: {detalhe}")


def _pedir(transporte: Transporte, url: str) -> RespostaJson:
    try:
        return transporte.obter_json(url)
    except RecursoInexistente:
        raise
    except FalhaDeColeta as erro:
        raise FalhaDeColeta(FONTE_INDISPONIVEL, f"{_endpoint(url)}: {erro.motivo}") from erro


def _corpo(resposta: RespostaJson, url: str, tipo: type) -> dict:
    try:
        corpo = json.loads(resposta.corpo)
    except (ValueError, UnicodeDecodeError) as erro:
        raise _formato(url, f"resposta não é JSON ({erro})") from erro
    if not isinstance(corpo, dict) or not isinstance(corpo.get("dados"), tipo):
        raise _formato(url, f"campo dados ausente ou não é {tipo.__name__}")
    return corpo


def _inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _exigir(condicao: bool, url: str, campo: str, valor) -> None:
    if not condicao:
        raise _formato(url, f"campo {campo} fora do formato ({valor!r})")


def obter_orgao(transporte: Transporte, sigla: str) -> int:
    """O id do órgão da comissão `sigla` (research R1): exatamente um órgão com essa sigla."""
    url = f"{API}/orgaos?sigla={sigla}"
    dados = _corpo(_pedir(transporte, url), url, list)["dados"]
    if len(dados) != 1 or not isinstance(dados[0], dict) or dados[0].get("sigla") != sigla:
        raise _formato(url, f"esperado exatamente um órgão {sigla}, vieram {len(dados)}")
    _exigir(_inteiro(dados[0].get("id")), url, "id", dados[0].get("id"))
    return dados[0]["id"]


def _validar_evento(evento, url: str) -> dict:
    _exigir(isinstance(evento, dict), url, "evento", evento)
    _exigir(_inteiro(evento.get("id")), url, "id", evento.get("id"))
    inicio = evento.get("dataHoraInicio")
    valido = isinstance(inicio, str) and PADRAO_INICIO.fullmatch(inicio) is not None
    _exigir(valido, url, "dataHoraInicio", inicio)
    for campo in ("situacao", "descricaoTipo"):
        _exigir(isinstance(evento.get(campo), str), url, campo, evento.get(campo))
    orgaos = evento.get("orgaos")
    valido = isinstance(orgaos, list) and all(
        isinstance(o, dict) and _inteiro(o.get("id")) and isinstance(o.get("sigla"), str)
        for o in orgaos
    )
    _exigir(valido, url, "orgaos", orgaos)
    return evento


def obter_eventos(transporte: Transporte, id_orgao: int, inicio: date, fim: date) -> list[dict]:
    """Os eventos do órgão de `inicio` a `fim`, inclusive (research R2), com a paginação conferida.

    Uma página perdida esconderia uma reunião: o total entregue tem de ser o do `X-Total-Count`.
    """
    primeira = (
        f"{API}/orgaos/{id_orgao}/eventos?dataInicio={inicio.isoformat()}"
        f"&dataFim={fim.isoformat()}&itens=100"
    )
    url = primeira
    eventos: list[dict] = []
    total_anunciado: int | None = None
    visitadas: set[str] = set()
    while url:
        if not url.startswith(f"{API}/"):
            raise _formato(primeira, f"link de paginação fora da API da Câmara: {url!r}")
        if url in visitadas:
            raise _formato(primeira, "a paginação voltou a uma página já lida")
        visitadas.add(url)
        resposta = _pedir(transporte, url)
        corpo = _corpo(resposta, url, list)
        eventos.extend(_validar_evento(e, url) for e in corpo["dados"])
        if total_anunciado is None:
            anunciado = resposta.cabecalhos.get("x-total-count")
            if anunciado is None or not anunciado.isdigit():
                raise _formato(url, f"X-Total-Count ausente ou inválido ({anunciado!r})")
            total_anunciado = int(anunciado)
        links = corpo.get("links") or []
        proxima = [
            link.get("href")
            for link in links
            if isinstance(link, dict) and link.get("rel") == "next"
        ]
        url = proxima[0] if proxima else ""
    if total_anunciado != len(eventos):
        raise _formato(
            primeira, f"a API anunciou {total_anunciado} eventos e entregou {len(eventos)}"
        )
    return eventos


def obter_evento(transporte: Transporte, id_evento: int) -> dict | None:
    """O evento pelo id (`/eventos/{id}`), ou `None` se a Câmara responde 404 (research R7)."""
    url = f"{API}/eventos/{id_evento}"
    try:
        resposta = _pedir(transporte, url)
    except RecursoInexistente:
        return None
    return _validar_evento(_corpo(resposta, url, dict)["dados"], url)


def _validar_proposicao(proposicao, url: str, campo: str) -> None:
    if proposicao is None:
        return
    _exigir(isinstance(proposicao, dict), url, campo, proposicao)
    _exigir(_inteiro(proposicao.get("id")), url, f"{campo}.id", proposicao.get("id"))
    sigla = proposicao.get("siglaTipo")
    _exigir(isinstance(sigla, str), url, f"{campo}.siglaTipo", sigla)
    for parte in ("numero", "ano"):
        valor = proposicao.get(parte)
        digitos = isinstance(valor, str) and valor.isdigit()
        _exigir(_inteiro(valor) or digitos, url, f"{campo}.{parte}", valor)


def _validar_item(item, url: str) -> dict:
    _exigir(isinstance(item, dict), url, "item", item)
    _exigir(_inteiro(item.get("ordem")), url, "ordem", item.get("ordem"))
    _exigir(isinstance(item.get("titulo"), str), url, "titulo", item.get("titulo"))
    for campo in ("proposicao_", "proposicaoRelacionada_", "relator", "situacaoItem"):
        _exigir(campo in item, url, campo, "ausente")
    _validar_proposicao(item["proposicao_"], url, "proposicao_")
    _validar_proposicao(item["proposicaoRelacionada_"], url, "proposicaoRelacionada_")
    relator = item["relator"]
    if relator is not None:
        _exigir(isinstance(relator, dict), url, "relator", relator)
        _exigir(_inteiro(relator.get("id")), url, "relator.id", relator.get("id"))
        _exigir(isinstance(relator.get("nome"), str), url, "relator.nome", relator.get("nome"))
    situacao = item["situacaoItem"]
    _exigir(situacao is None or isinstance(situacao, str), url, "situacaoItem", situacao)
    return item


def obter_pauta(transporte: Transporte, id_evento: int) -> list[dict]:
    """Os itens da pauta da reunião (`/eventos/{id}/pauta`), cada um validado."""
    url = f"{API}/eventos/{id_evento}/pauta"
    try:
        resposta = _pedir(transporte, url)
    except RecursoInexistente as erro:  # a pauta de uma reunião listada tem de existir
        raise FalhaDeColeta(FONTE_INDISPONIVEL, f"{_endpoint(url)}: {erro.motivo}") from erro
    return [_validar_item(item, url) for item in _corpo(resposta, url, list)["dados"]]
