"""Transporte falso e construtores sintéticos da pauta (PAU), no formato das respostas reais.

O `TransportePauta` serve as fixtures de tests/fixtures/pauta/ pela URL pedida. Os construtores
seguem as chaves das respostas salvas (conferidas em test_pauta_sinteticos.py); cada teste altera um
campo por vez. Nada aqui usa a rede.
"""

import copy
import json
import re
import urllib.error
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from monitor_comissoes.transporte import RespostaJson, TransporteHttp

FIXTURES = Path(__file__).parent / "fixtures"
PAUTA = FIXTURES / "pauta"
API = "https://dadosabertos.camara.leg.br/api/v2"
SIGLAS = {2009: "CE", 2018: "CREDN"}
NOMES_ORGAOS = {
    2009: "Comissão de Educação",
    2018: "Comissão de Relações Exteriores e de Defesa Nacional",
}


def chave(url: str) -> str:
    """O nome da fixture que responde à URL (sem `.json`), ou a própria URL se não houver padrão.

    A página 1 de uma lista é a fixture; outras páginas só existem como resposta sobreposta.
    """
    partes = urlsplit(url)
    consulta = {nome: valores[0] for nome, valores in parse_qs(partes.query).items()}
    caminho = partes.path.removeprefix("/api/v2")
    if consulta.get("pagina", "1") != "1":
        return url
    if caminho == "/orgaos" and "sigla" in consulta:
        return f"orgaos/{consulta['sigla']}"
    if achado := re.fullmatch(r"/orgaos/(\d+)/eventos", caminho):
        return f"eventos/{achado[1]}-{consulta.get('dataInicio')}-{consulta.get('dataFim')}"
    if achado := re.fullmatch(r"/eventos/(\d+)(/pauta)?", caminho):
        return f"{'pautas' if achado[2] else 'eventos'}/{achado[1]}"
    if caminho == "/deputados" and consulta.get("siglaPartido") == "NOVO":
        return "deputados-novo"
    return url


class TransportePauta:
    """Serve as fixtures da pauta como a Câmara serviria.

    respostas[chave]: documento (dict ou list) ou bytes servido no lugar da fixture; a chave é a de
    `chave(url)` (por exemplo "pautas/83091", "eventos/99999" ou a URL de uma página 2).
    cabecalhos[chave]: cabeçalhos da resposta sobreposta (nomes em minúsculas).
    erro[chave]: exceção levantada ao pedir a URL (use `falha_http` para um erro HTTP real).
    pedidos: as URLs pedidas, em ordem.
    """

    def __init__(self):
        manifesto = json.loads((PAUTA / "manifesto.json").read_text(encoding="utf-8"))
        self._total = {
            nome.removesuffix(".json"): dados["x_total_count"]
            for nome, dados in manifesto["arquivos"].items()
        }
        self.pedidos: list[str] = []
        self.respostas: dict[str, object] = {}
        self.cabecalhos: dict[str, dict[str, str]] = {}
        self.erro: dict[str, Exception] = {}

    def obter_json(self, url: str) -> RespostaJson:
        self.pedidos.append(url)
        nome = chave(url)
        if nome in self.erro:
            raise self.erro[nome]
        if nome in self.respostas:
            corpo = self.respostas[nome]
            if not isinstance(corpo, bytes):
                corpo = json.dumps(corpo, ensure_ascii=False).encode()
            return RespostaJson(corpo=corpo, cabecalhos=self.cabecalhos.get(nome, {}))
        if nome == "deputados-novo":
            corpo = (FIXTURES / "camara" / "deputados-novo.json").read_bytes()
            return RespostaJson(corpo=corpo, cabecalhos={"x-total-count": "5"})
        arquivo = PAUTA / f"{nome}.json"
        assert arquivo.exists(), f"fixture ausente para {url}"
        total = self._total.get(nome)
        cabecalhos = {} if total is None else {"x-total-count": total}
        return RespostaJson(corpo=arquivo.read_bytes(), cabecalhos=cabecalhos)

    def baixar(self, url, destino):
        raise AssertionError(f"a checagem da pauta não baixa arquivos: {url}")

    def pedidos_por_chave(self) -> list[str]:
        return [chave(url) for url in self.pedidos]


def falha_http(url: str, codigo: int) -> Exception:
    """A exceção que o `TransporteHttp` real levanta para um HTTP `codigo` em `url`."""

    def abrir(requisicao, timeout):
        raise urllib.error.HTTPError(url, codigo, "erro simulado", {}, None)

    try:
        TransporteHttp(abrir=abrir, dormir=lambda _: None).obter_json(url)
    except Exception as erro:
        return erro
    raise AssertionError("o transporte deveria ter falhado")  # pragma: no cover


def _orgao(id_orgao):
    sigla = SIGLAS.get(id_orgao, f"O{id_orgao}")
    nome = NOMES_ORGAOS.get(id_orgao, f"Órgão {id_orgao}")
    return {
        "id": id_orgao,
        "uri": f"{API}/orgaos/{id_orgao}",
        "sigla": sigla,
        "nome": nome,
        "apelido": nome,
        "codTipoOrgao": 2,
        "tipoOrgao": "Comissão Permanente",
        "nomePublicacao": nome,
        "nomeResumido": nome,
    }


def evento(id, inicio, situacao="Convocada", tipo="Reunião Deliberativa", orgao=2009):
    """Um evento como vem em `/orgaos/{id}/eventos` (`inicio` no formato `AAAA-MM-DDTHH:MM`)."""
    return {
        "id": id,
        "uri": f"{API}/eventos/{id}",
        "dataHoraInicio": inicio,
        "dataHoraFim": None,
        "situacao": situacao,
        "descricaoTipo": tipo,
        "descricao": "Discussão e votação de propostas legislativas",
        "localExterno": None,
        "orgaos": [_orgao(orgao)],
        "localCamara": {
            "nome": "Anexo II, Plenário 10",
            "predio": None,
            "sala": None,
            "andar": None,
        },
        "urlRegistro": None,
    }


def detalhe_evento(id, inicio, situacao="Convocada", tipo="Reunião Deliberativa", orgao=2009):
    """O corpo de `/eventos/{id}`: o evento da lista com os campos a mais do detalhe."""
    dados = {
        "uriDeputados": None,
        "uriConvidados": None,
        "fases": None,
        **evento(id, inicio, situacao, tipo, orgao),
        "requerimentos": [],
        "urlDocumentoPauta": f"{API}/eventos/{id}/pauta",
    }
    return {"dados": dados, "links": [{"rel": "self", "href": f"{API}/eventos/{id}"}]}


def lista_eventos(eventos, orgao=2009, inicio="2026-10-17", fim="2026-10-31"):
    """O corpo de `/orgaos/{id}/eventos` com uma página só."""
    url = f"{API}/orgaos/{orgao}/eventos?dataInicio={inicio}&dataFim={fim}"
    pagina = f"{url}&pagina=1&itens=100"
    return {
        "dados": list(eventos),
        "links": [
            {"rel": "self", "href": f"{url}&itens=100"},
            {"rel": "first", "href": pagina},
            {"rel": "last", "href": pagina},
        ],
    }


def _proposicao(id, identificacao, como_texto):
    sigla, numero_ano = identificacao.split(" ")
    numero, ano = numero_ano.split("/")
    return {
        "id": id,
        "uri": f"{API}/proposicoes/{id}",
        "siglaTipo": sigla,
        "codTipo": "139" if como_texto else 139,
        "numero": numero if como_texto else int(numero),
        "ano": ano if como_texto else int(ano),
        "ementa": f"Ementa do {identificacao}.",
        "dataApresentacao": None if como_texto else "2026-04-07T13:40",
    }


def _relator(id, nome, partido):
    return {
        "id": id,
        "uri": f"{API}/deputados/{id}",
        "nome": nome,
        "siglaPartido": partido,
        "uriPartido": None,
        "siglaUf": "SP",
        "idLegislatura": 57,
        "urlFoto": f"https://www.camara.leg.br/internet/deputado/bandep/{id}.jpg",
        "email": None,
    }


def item_pauta(ordem, proposicao=None, relacionada=None, relator=None, situacao_item=None):
    """Um item de `/eventos/{id}/pauta`.

    proposicao e relacionada: `(id, "PL 1234/2020")`. Na relacionada, `numero` e `ano` vêm como
    texto, como na API (research R4). relator: `(id, nome)` ou `(id, nome, siglaPartido)`; sem o
    partido, `siglaPartido` é nulo, como acontece na fonte.
    """
    titulo = proposicao[1] if proposicao else f"Item {ordem}"
    return {
        "ordem": ordem,
        "topico": "Proposições Sujeitas à Apreciação Conclusiva pelas Comissões",
        "regime": "Ordinário",
        "codRegime": 21,
        "titulo": titulo,
        "proposicao_": _proposicao(*proposicao, como_texto=False) if proposicao else None,
        "relator": _relator(*relator, *([None] if len(relator) == 2 else [])) if relator else None,
        "textoParecer": None,
        "proposicaoRelacionada_": _proposicao(*relacionada, como_texto=True)
        if relacionada
        else None,
        "uriVotacao": None,
        "situacaoItem": situacao_item,
    }


def pauta(itens):
    """O corpo de `/eventos/{id}/pauta`."""
    return {"dados": list(itens), "links": []}


def indice(proposicoes, *, gerado_em="2026-10-24T03:58:02-03:00", anos_lidos=(2003, 2026)):
    """O documento do `cache/indice-autoria.json` (contracts/indice-autoria.md).

    proposicoes: `{id: (autoria_novo, [ids de deputados])}`, com `autoria_novo` 0 ou 1.
    """
    return {
        "versao_formato": 1,
        "gerado_em": gerado_em,
        "dados_camara_em": "2026-10-24T04:31:37+00:00",
        "anos_lidos": list(anos_lidos),
        "tipos": ["MSC", "PDL", "PEC", "PL", "PLP", "REQ"],
        "proposicoes": {
            str(id): [autoria, sorted(set(deputados))]
            for id, (autoria, deputados) in proposicoes.items()
        },
    }


def deputados_novo(ids):
    """O corpo de `/deputados?siglaPartido=NOVO`, com nomes da fixture real quando há."""
    reais = json.loads((FIXTURES / "camara" / "deputados-novo.json").read_text(encoding="utf-8"))
    nomes = {d["id"]: d["nome"] for d in reais["dados"]}
    dados = [_relator(id, nomes.get(id, f"Deputado {id}"), "NOVO") for id in ids]
    for deputado in dados:
        deputado["uriPartido"] = f"{API}/partidos/37901"
    return {"dados": dados, "links": []}


EVENTO_LINK = "https://www.camara.leg.br/evento-legislativo/"
PROPOSICAO_LINK = "https://www.camara.leg.br/propostas-legislativas/"


def reuniao_gravada(
    id,
    inicio="2026-10-28T10:00",
    situacao="convocada",
    chaves=(),
    *,
    comissao="CE",
    vista_desde="2026-10-23T22:47:30-03:00",
):
    """Uma reunião como fica em `checagem.reunioes` do arquivo do dia (contracts/pauta-json.md).

    `chaves`: as chaves da pauta, `p:{id}` ou `t:{titulo}`, na ordem da pauta.
    """
    pauta_gravada = []
    for ordem, chave_item in enumerate(chaves, start=1):
        if chave_item.startswith("p:"):
            id_proposicao = int(chave_item[2:])
            proposicao = {
                "id": id_proposicao,
                "identificacao": f"PL {id_proposicao}/2020",
                "link": f"{PROPOSICAO_LINK}{id_proposicao}",
            }
            titulo = proposicao["identificacao"]
        else:
            proposicao, titulo = None, chave_item[2:]
        pauta_gravada.append(
            {"chave": chave_item, "ordem": ordem, "titulo": titulo, "proposicao": proposicao}
        )
    return {
        "id": id,
        "comissao": comissao,
        "inicio": inicio,
        "situacao": situacao,
        "situacao_camara": {"convocada": "Convocada", "cancelada": "Cancelada"}.get(
            situacao, "Encerrada (Final)"
        ),
        "link": f"{EVENTO_LINK}{id}",
        "vista_desde": vista_desde,
        "itens": [],
        "requerimentos": {"total": 0, "listados": []},
        "outros": {"total": 0},
        "pauta": pauta_gravada,
    }


def arquivo_do_dia(
    data="2026-10-24",
    reunioes=(),
    alteracoes=(),
    *,
    checada_em="2026-10-24T05:49:12-03:00",
    linha_de_base=None,
):
    """O arquivo `data/pautas/AAAA-MM-DD.json` completo (contracts/pauta-json.md)."""
    return {
        "meta": {
            "versao_formato": 1,
            "data": data,
            "comissoes": ["CE", "CREDN"],
            "linha_de_base": linha_de_base,
        },
        "checagem": {
            "checada_em": checada_em,
            "janela": {"inicio": "2026-10-17", "fim": "2026-10-31"},
            "lote": {"dados_camara_em": "2026-10-24T04:31:37+00:00"},
            "inventario": {"gerado_em": "2026-10-24T08:34:13-03:00"},
            "deputados_novo_em_exercicio": [{"id": 204455, "nome": "Luiz Lima"}],
            "reunioes": copy.deepcopy(list(reunioes)),
        },
        "alteracoes": copy.deepcopy(list(alteracoes)),
    }


def itens_reais(id_evento):
    """Os itens da pauta salva de `id_evento`, no formato da API."""
    return json.loads((PAUTA / "pautas" / f"{id_evento}.json").read_text(encoding="utf-8"))["dados"]


def item_real(id_evento, ordem):
    """O item de `ordem` da pauta salva de `id_evento`."""
    return next(item for item in itens_reais(id_evento) if item["ordem"] == ordem)
