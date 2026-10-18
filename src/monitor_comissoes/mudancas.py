"""Mudanças desde o retrato anterior (MUD): eventos, motivos e o arquivo do dia.

Formato em specs/004-mudancas-desde-ontem/contracts/mudancas-json.md; regras de comparação em
data-model.md. O arquivo não tem horário de execução: só datas e o `dados_camara_em` do lote,
para duas execuções sobre os mesmos dados darem o mesmo arquivo (constituição, V).
"""

import re
from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime
from typing import Any

from .erros import FORMATO_ALTERADO, INTERNA, FalhaDeColeta
from .estoque import BRASILIA, EstadoDeSaida
from .relatoria import inicio_da_passagem
from .retratos import Comparacao
from .tramitacoes import Tramitacao

VERSAO_FORMATO = 1
LINK_OFICIAL = "https://www.camara.leg.br/propostas-legislativas/"

# Ordem de saída dos tipos de evento (PRODUCT.md, §5.6).
TIPOS = ("entrou", "saiu", "situacao", "relator", "parecer", "etiquetas")
# Campos próprios de cada tipo, depois de `link` e antes de `tramitacoes`.
CAMPOS_PROPRIOS = {
    "entrou": ("motivo", "etiquetas"),
    "saiu": ("motivo", "destino", "outros_fatos"),
    "situacao": ("de", "para"),
    "relator": ("mudanca", "de", "para"),
    "parecer": (),
    "etiquetas": ("ganhou", "perdeu"),
}
CAMPOS_COMUNS = ("tipo", "id", "identificacao", "comissao", "link")
CAMPOS_DA_TRAMITACAO = ("sequencia", "data_hora", "orgao", "codigo", "descricao")
ETIQUETAS = ("autoria NOVO", "autor hoje no NOVO", "relatoria NOVO")
MUDANCAS_DE_RELATOR = ("designado", "devolveu", "substituido")

# Códigos de motivo (contrato). As situações finais são o motivo "da situação" (research R2).
MOTIVOS_DE_ENTRADA = ("chegou_a_comissao", "ganhou_etiqueta", "nao_determinado")
SITUACAO_FINAL_ARQUIVADO = "arquivado"
SITUACAO_FINAL_ARQUIVADO_ART_105 = "arquivado_art_105"
MOTIVOS_DE_SAIDA_POR_SITUACAO = (
    SITUACAO_FINAL_ARQUIVADO_ART_105,
    SITUACAO_FINAL_ARQUIVADO,
    "transformado_em_norma",
    "aprovado_segue_ao_senado",
    "encerrado",
)
MOTIVOS_DE_SAIDA = (
    *MOTIVOS_DE_SAIDA_POR_SITUACAO,
    "apensado_fora_da_lista",
    "outro_orgao",
    "perdeu_etiquetas",
    "nao_determinado",
)
MOTIVOS_DE_LINHA_DE_BASE = ("primeiro retrato", "formato anterior incompatível")
MOTIVOS_DE_RESSALVA = (
    "relator indeterminado ontem",
    "relator indeterminado hoje",
    "relator indeterminado nos dois retratos",
)

# Situação (texto exato de `ultimoStatus_descricaoSituacao`) -> código do motivo de saída.
# Tabela decidida pelo mantenedor em 18/10/2026 (plan.md, D1): só rotula o motivo da saída e nunca
# inclui nem exclui item. Situação fora da tabela cai em "foi para outro órgão".
SITUACOES_FINAIS = {
    "Arquivada": SITUACAO_FINAL_ARQUIVADO,
    "Transformado em Norma Jurídica": "transformado_em_norma",
    "Aguardando Apreciação pelo Senado Federal": "aprovado_segue_ao_senado",
    "Aguardando Envio ao Senado Federal": "aprovado_segue_ao_senado",
    "Enviada ao Senado Federal": "aprovado_segue_ao_senado",
    "Vetado totalmente": "encerrado",
    "Recusado": "encerrado",
    "Retirado pelo(a) Autor(a)": "encerrado",
    "Devolvida ao(à) Autor(a)": "encerrado",
    "Transformado em nova proposição": "encerrado",
    "Perdeu a Eficácia": "encerrado",
    "Tramitação Finalizada": "encerrado",
}

CODIGO_PARECER = "322"  # "Parecer do(a) Relator(a)" (plan.md, D4)
CODIGO_ARQUIVAMENTO = "502"  # "Arquivamento" (research R3)
# "Arquivado nos termos do Artigo 105 do Regimento Interno..." (tramitação 502).
PADRAO_ART_105 = re.compile(r"art(?:igo|\.)?\s*105\b", re.IGNORECASE)


# --- construção -------------------------------------------------------------------------------


def nome_do_arquivo(data: date) -> str:
    return f"{data.isoformat()}.json"


def _tramitacao(t: Tramitacao) -> dict:
    return {
        "sequencia": t.sequencia,
        "data_hora": t.data_hora,
        "orgao": t.orgao,
        "codigo": t.codigo,
        "descricao": t.descricao,
    }


def evento(
    tipo: str,
    *,
    id: int,
    identificacao: str,
    comissao: str,
    link: str,
    tramitacoes: Iterable[Tramitacao] = (),
    **proprios: Any,
) -> dict:
    """Um evento com os campos na ordem do contrato. Exige exatamente os campos do `tipo`."""
    if tipo not in CAMPOS_PROPRIOS:
        raise ValueError(f"tipo desconhecido: {tipo!r}")
    esperados = CAMPOS_PROPRIOS[tipo]
    faltam = [c for c in esperados if c not in proprios]
    sobram = [c for c in proprios if c not in esperados]
    if faltam:
        raise ValueError(f"evento {tipo}: faltam campos {faltam}")
    if sobram:
        raise ValueError(f"evento {tipo}: campos a mais {sobram}")
    return {
        "tipo": tipo,
        "id": id,
        "identificacao": identificacao,
        "comissao": comissao,
        "link": link,
        **{campo: proprios[campo] for campo in esperados},
        "tramitacoes": [_tramitacao(t) for t in tramitacoes],
    }


def ordenar_eventos(eventos: Iterable[dict], comissoes: tuple[str, ...]) -> list[dict]:
    """Por comissão (a da configuração; as de fora depois, por sigla), tipo e `id`."""

    def chave(e: dict):
        comissao = e["comissao"]
        posicao = comissoes.index(comissao) if comissao in comissoes else len(comissoes)
        fora = "" if comissao in comissoes else comissao
        return (posicao, fora, TIPOS.index(e["tipo"]), e["id"])

    return sorted(eventos, key=chave)


def montar_arquivo(
    *,
    data: date,
    retrato: dict,
    retrato_anterior: dict | None,
    linha_de_base: dict | None,
    eventos: list[dict],
    ressalvas: list[dict],
) -> dict:
    """O arquivo do dia na ordem fixa do contrato. Não valida: `validar_arquivo` é à parte."""
    return {
        "meta": {
            "versao_formato": VERSAO_FORMATO,
            "data": data.isoformat(),
            "retrato": retrato,
            "retrato_anterior": retrato_anterior,
            "linha_de_base": linha_de_base,
            "total_eventos": len(eventos),
            "total_por_tipo": {t: sum(1 for e in eventos if e.get("tipo") == t) for t in TIPOS},
        },
        "eventos": eventos,
        "ressalvas": ressalvas,
    }


TEXTO_DO_MOTIVO = {
    "chegou_a_comissao": "chegou à comissão",
    SITUACAO_FINAL_ARQUIVADO_ART_105: "arquivado, art. 105",
    SITUACAO_FINAL_ARQUIVADO: "arquivado",
    "transformado_em_norma": "transformado em norma jurídica",
    "aprovado_segue_ao_senado": "aprovado, segue ao Senado",
    "encerrado": "encerrado",
    "apensado_fora_da_lista": "apensado a uma proposição fora da lista",
    "outro_orgao": "foi para outro órgão",
    "nao_determinado": "não determinado",
}


class _Contexto:
    """O que a comparação precisa saber de fora: tramitações (uma consulta por referência), o corte
    de data do retrato anterior e os itens de hoje."""

    def __init__(self, obter, corte: date, ids_hoje: set[int]):
        self._obter = obter
        self._cache: dict[int, list[Tramitacao]] = {}
        self.corte = corte
        self.ids_hoje = ids_hoje

    def tramitacoes(self, id_referencia: int) -> list[Tramitacao]:
        if id_referencia not in self._cache:
            self._cache[id_referencia] = sorted(
                self._obter(id_referencia), key=lambda x: x.sequencia
            )
        return self._cache[id_referencia]


def _referencia_id(item: dict) -> int:
    """A referência do item: a raiz da cadeia de apensação, ou ele mesmo (PRODUCT.md, §5.2)."""
    return item["apensado_a"]["id"] if item["apensado_a"] else item["id"]


def _dia(t: Tramitacao) -> date:
    return date.fromisoformat(t.data_hora[:10])


def _ate_hoje(ctx: _Contexto, id_referencia: int, sequencia_de_hoje: int) -> list[Tramitacao]:
    """As tramitações da referência até a sequência do lote de hoje (research R6).

    A resposta DEVE conter essa sequência; senão, a API e o lote não descrevem o mesmo momento e
    o arquivo de hoje seria incerto. Lançamentos posteriores ao lote ficam para amanhã.
    """
    todas = ctx.tramitacoes(id_referencia)
    if not any(x.sequencia == sequencia_de_hoje for x in todas):
        raise FalhaDeColeta(
            FORMATO_ALTERADO,
            f"tramitações da proposição {id_referencia}: "
            f"a sequência {sequencia_de_hoje} do lote não existe na resposta",
        )
    return [x for x in todas if x.sequencia <= sequencia_de_hoje]


def _intervalo(
    ctx: _Contexto,
    referencia_de_hoje: int,
    sequencia_de_hoje: int,
    referencia_anterior: int,
    sequencia_anterior: int,
) -> list[Tramitacao]:
    """Tramitações desde o retrato anterior, até a sequência de hoje.

    Mesma referência: sequência maior que a anterior (sem consulta se nada mudou). Referência
    diferente: as sequências de proposições distintas não se comparam, então vale a data do lote
    anterior.
    """
    if referencia_de_hoje == referencia_anterior:
        if sequencia_de_hoje < sequencia_anterior:
            raise FalhaDeColeta(
                FORMATO_ALTERADO,
                f"proposição {referencia_de_hoje}: a sequência do último status regrediu "
                f"de {sequencia_anterior} para {sequencia_de_hoje}",
            )
        if sequencia_de_hoje == sequencia_anterior:
            return []
        ate = _ate_hoje(ctx, referencia_de_hoje, sequencia_de_hoje)
        return [x for x in ate if x.sequencia > sequencia_anterior]
    ate = _ate_hoje(ctx, referencia_de_hoje, sequencia_de_hoje)
    return [x for x in ate if _dia(x) >= ctx.corte]


def _base(tipo: str, item: dict, **proprios: Any) -> dict:
    return evento(
        tipo,
        id=item["id"],
        identificacao=item["identificacao"],
        comissao=item["comissao"],
        link=item["link"],
        **proprios,
    )


def _entrou(ctx: _Contexto, item: dict) -> list[dict]:
    referencia = _referencia_id(item)
    ate = _ate_hoje(ctx, referencia, item["ultimo_status_sequencia"])
    chegada = inicio_da_passagem(ate, item["comissao"])
    novas = [x for x in ate if _dia(x) >= ctx.corte]
    etiquetas = list(item["etiquetas"])
    if chegada is not None and _dia(chegada) >= ctx.corte:
        motivo = {"codigo": "chegou_a_comissao", "texto": TEXTO_DO_MOTIVO["chegou_a_comissao"]}
    elif etiquetas:
        motivo = {
            "codigo": "ganhou_etiqueta",
            "texto": f"ganhou etiqueta: {', '.join(etiquetas)}",
        }
    else:
        motivo = {"codigo": "nao_determinado", "texto": TEXTO_DO_MOTIVO["nao_determinado"]}
    return [_base("entrou", item, motivo=motivo, etiquetas=etiquetas, tramitacoes=novas)]


def _fatos_da_saida(
    ctx: _Contexto, item: dict, estado: EstadoDeSaida, tramitacoes: list[Tramitacao]
) -> list[str]:
    """Os códigos de motivo que valem, do mais ao menos informativo (clarify, Q4)."""
    fatos: list[str] = []
    final = SITUACOES_FINAIS.get(estado.situacao)
    if final is not None:
        if final == SITUACAO_FINAL_ARQUIVADO and any(
            x.codigo == CODIGO_ARQUIVAMENTO and PADRAO_ART_105.search(x.despacho)
            for x in tramitacoes
        ):
            final = SITUACAO_FINAL_ARQUIVADO_ART_105
        fatos.append(final)
    raiz = estado.apensado_a
    if raiz is not None and raiz["id"] != _referencia_id(item) and raiz["id"] not in ctx.ids_hoje:
        fatos.append("apensado_fora_da_lista")
    fatos.append("outro_orgao" if not estado.na_comissao else "perdeu_etiquetas")
    return fatos


def _saiu(ctx: _Contexto, item: dict, estado: EstadoDeSaida) -> list[dict]:
    if not estado.existe:
        return [
            _base(
                "saiu",
                item,
                motivo={
                    "codigo": "nao_determinado",
                    "texto": TEXTO_DO_MOTIVO["nao_determinado"],
                },
                destino={"orgao": None, "situacao": None, "apensado_a": None},
                outros_fatos=[],
            )
        ]
    tramitacoes = _intervalo(
        ctx,
        estado.referencia_id,
        estado.sequencia,
        _referencia_id(item),
        item["ultimo_status_sequencia"],
    )
    fatos = _fatos_da_saida(ctx, item, estado, tramitacoes)
    principal, outros = fatos[0], fatos[1:]
    if principal == "perdeu_etiquetas" and not item["etiquetas"]:
        # Estava na lista só como candidato à relatoria com relator indeterminado: não há etiqueta
        # a "perder", e o motivo honesto é não saber.
        motivo = {"codigo": "nao_determinado", "texto": TEXTO_DO_MOTIVO["nao_determinado"]}
    elif principal == "perdeu_etiquetas":
        motivo = {
            "codigo": principal,
            "texto": f"perdeu as etiquetas: {', '.join(item['etiquetas'])}",
        }
    else:
        motivo = {"codigo": principal, "texto": TEXTO_DO_MOTIVO[principal]}
    return [
        _base(
            "saiu",
            item,
            motivo=motivo,
            destino={
                "orgao": estado.orgao,
                "situacao": estado.situacao,
                "apensado_a": estado.apensado_a,
            },
            outros_fatos=outros,
            tramitacoes=tramitacoes,
        )
    ]


def _relator_do_evento(relator: dict | None) -> dict | None:
    if relator is None:
        return None
    return {k: relator[k] for k in ("id", "nome", "partido_hoje")}


def _ressalva(item: dict, ontem: bool, hoje: bool) -> dict:
    quando = {
        (True, False): "ontem",
        (False, True): "hoje",
        (True, True): "nos dois retratos",
    }[(ontem, hoje)]
    return {
        "id": item["id"],
        "identificacao": item["identificacao"],
        "comissao": item["comissao"],
        "link": item["link"],
        "motivo": f"relator indeterminado {quando}",
    }


def _mantido(ctx: _Contexto, a: dict, h: dict) -> tuple[list[dict], list[dict]]:
    """Os eventos e as ressalvas de um item que está nos dois retratos."""
    referencia_h, referencia_a = _referencia_id(h), _referencia_id(a)
    sequencia_h, sequencia_a = h["ultimo_status_sequencia"], a["ultimo_status_sequencia"]
    mudou_a_tramitacao = referencia_h != referencia_a or sequencia_h != sequencia_a
    # Só quem teve o último status alterado consulta tramitações: é nelas que está o parecer.
    tramitacoes = (
        _intervalo(ctx, referencia_h, sequencia_h, referencia_a, sequencia_a)
        if mudou_a_tramitacao
        else []
    )
    eventos: list[dict] = []
    ressalvas: list[dict] = []

    if a["situacao"] != h["situacao"]:
        eventos.append(
            _base("situacao", h, de=a["situacao"], para=h["situacao"], tramitacoes=tramitacoes)
        )

    indeterminado_a = a["relator_indeterminado"] is not None
    indeterminado_h = h["relator_indeterminado"] is not None
    if indeterminado_a or indeterminado_h:
        ressalvas.append(_ressalva(h, indeterminado_a, indeterminado_h))
    else:
        antes, depois = _relator_do_evento(a["relator"]), _relator_do_evento(h["relator"])
        if antes is None and depois is not None:
            mudanca = "designado"
        elif antes is not None and depois is None:
            mudanca = "devolveu"
        elif antes is not None and depois is not None and antes["id"] != depois["id"]:
            mudanca = "substituido"
        else:
            mudanca = None
        if mudanca is not None:
            eventos.append(
                _base("relator", h, mudanca=mudanca, de=antes, para=depois, tramitacoes=tramitacoes)
            )

    if any(x.codigo == CODIGO_PARECER and x.orgao == h["comissao"] for x in tramitacoes):
        eventos.append(_base("parecer", h, tramitacoes=tramitacoes))

    ganhou = [e for e in ETIQUETAS if e in h["etiquetas"] and e not in a["etiquetas"]]
    perdeu = [e for e in ETIQUETAS if e in a["etiquetas"] and e not in h["etiquetas"]]
    if ganhou or perdeu:
        eventos.append(_base("etiquetas", h, ganhou=ganhou, perdeu=perdeu, tramitacoes=tramitacoes))
    return eventos, ressalvas


def comparar(
    comparacao: Comparacao,
    documento_hoje: dict,
    estados_de_saida: Mapping[int, EstadoDeSaida],
    obter_tramitacoes: Callable[[int], list[Tramitacao]],
    comissoes: tuple[str, ...],
    hoje: date,
) -> dict:
    """O arquivo do dia: linha de base, ou os eventos entre o retrato anterior e o de hoje.

    `estados_de_saida` (id -> estado do lote de quem saiu da lista) e `obter_tramitacoes` (id da
    referência -> tramitações) são injetados: a comparação não faz I/O. As tramitações são
    consultadas uma vez por referência.
    """
    meta_hoje = documento_hoje["meta"]
    gerado_em = datetime.fromisoformat(meta_hoje["gerado_em"]).astimezone(BRASILIA)
    retrato = {"dia": gerado_em.date().isoformat(), "dados_camara_em": meta_hoje["dados_camara_em"]}
    if comparacao.anterior is None:
        return montar_arquivo(
            data=hoje,
            retrato=retrato,
            retrato_anterior=comparacao.retrato_anterior,
            linha_de_base={
                "motivo": comparacao.motivo_linha_de_base,
                "total_itens": len(documento_hoje["itens"]),
            },
            eventos=[],
            ressalvas=[],
        )

    anteriores = {i["id"]: i for i in comparacao.anterior.documento["itens"]}
    de_hoje = {i["id"]: i for i in documento_hoje["itens"]}
    corte = comparacao.anterior.dados_camara_em.astimezone(BRASILIA).date()
    ctx = _Contexto(obter_tramitacoes, corte, set(de_hoje))
    sem_estado = EstadoDeSaida(False, None, None, None, None, None, False)

    eventos: list[dict] = []
    for id_ in sorted(de_hoje.keys() - anteriores.keys()):
        eventos += _entrou(ctx, de_hoje[id_])
    for id_ in sorted(anteriores.keys() - de_hoje.keys()):
        eventos += _saiu(ctx, anteriores[id_], estados_de_saida.get(id_, sem_estado))
    ressalvas: list[dict] = []
    for id_ in sorted(anteriores.keys() & de_hoje.keys()):
        dos_eventos, das_ressalvas = _mantido(ctx, anteriores[id_], de_hoje[id_])
        eventos += dos_eventos
        ressalvas += das_ressalvas
    return montar_arquivo(
        data=hoje,
        retrato=retrato,
        retrato_anterior=comparacao.retrato_anterior,
        linha_de_base=None,
        eventos=ordenar_eventos(eventos, comissoes),
        ressalvas=ressalvas,
    )


ROTULOS_DOS_TIPOS = {
    "entrou": "entrou",
    "saiu": "saiu",
    "situacao": "situação",
    "relator": "relator",
    "parecer": "parecer",
    "etiquetas": "etiquetas",
}


def resumo(documento: dict) -> str:
    """Resumo de uma linha do arquivo, para a saída da execução diária."""
    meta = documento["meta"]
    if meta["linha_de_base"] is not None:
        return f"linha de base ({meta['linha_de_base']['motivo']})"
    total = meta["total_eventos"]
    if total == 0:
        return "sem mudanças"
    partes = ", ".join(
        f"{meta['total_por_tipo'][t]} {ROTULOS_DOS_TIPOS[t]}"
        for t in TIPOS
        if meta["total_por_tipo"][t]
    )
    return f"{total} {'evento' if total == 1 else 'eventos'} ({partes})"


# --- validação --------------------------------------------------------------------------------


def _invalido(detalhe: str) -> FalhaDeColeta:
    return FalhaDeColeta(INTERNA, f"arquivo de mudanças inválido: {detalhe}")


def _inteiro(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _texto_cheio(valor) -> bool:
    return isinstance(valor, str) and valor != ""


def _lista_de_textos(valor) -> bool:
    return isinstance(valor, list) and all(isinstance(v, str) for v in valor)


def _data_do_retrato(valor, nome: str) -> None:
    if not (
        isinstance(valor, dict)
        and list(valor) == ["dia", "dados_camara_em"]
        and all(_texto_cheio(v) for v in valor.values())
    ):
        raise _invalido(f"meta.{nome} deve ser {{dia, dados_camara_em}}")


def _validar_meta(meta, documento: dict) -> None:
    campos = [
        "versao_formato",
        "data",
        "retrato",
        "retrato_anterior",
        "linha_de_base",
        "total_eventos",
        "total_por_tipo",
    ]
    if not isinstance(meta, dict) or list(meta) != campos:
        raise _invalido(f"campos do meta devem ser {campos}")
    if meta["versao_formato"] != VERSAO_FORMATO:
        raise _invalido(f"versao_formato {meta['versao_formato']!r} não suportada")
    if not _texto_cheio(meta["data"]):
        raise _invalido("meta.data deve ser texto")
    _data_do_retrato(meta["retrato"], "retrato")
    if meta["retrato_anterior"] is not None:
        _data_do_retrato(meta["retrato_anterior"], "retrato_anterior")
    base = meta["linha_de_base"]
    if base is None:
        if meta["retrato_anterior"] is None:
            raise _invalido("sem linha de base, meta.retrato_anterior é obrigatório")
    else:
        if not (
            isinstance(base, dict)
            and list(base) == ["motivo", "total_itens"]
            and base["motivo"] in MOTIVOS_DE_LINHA_DE_BASE
            and _inteiro(base["total_itens"])
            and base["total_itens"] >= 0
        ):
            raise _invalido(
                f"linha de base deve ser {{motivo em {MOTIVOS_DE_LINHA_DE_BASE}, total}}"
            )
        if documento["eventos"] or documento["ressalvas"]:
            raise _invalido("linha de base não pode ter eventos nem ressalvas")
    eventos = documento["eventos"]
    if meta["total_eventos"] != len(eventos):
        raise _invalido("meta.total_eventos não bate com os eventos")
    por_tipo = meta["total_por_tipo"]
    if not isinstance(por_tipo, dict) or list(por_tipo) != list(TIPOS):
        raise _invalido(f"meta.total_por_tipo deve ter as chaves {list(TIPOS)} nesta ordem")
    for tipo in TIPOS:
        if por_tipo[tipo] != sum(1 for e in eventos if e["tipo"] == tipo):
            raise _invalido(f"meta.total_por_tipo[{tipo!r}] não bate com os eventos")


def _validar_tramitacoes(lista, onde: str) -> None:
    if not isinstance(lista, list):
        raise _invalido(f"{onde}: tramitacoes deve ser uma lista")
    anterior = None
    for t in lista:
        if not (
            isinstance(t, dict)
            and list(t) == list(CAMPOS_DA_TRAMITACAO)
            and _inteiro(t["sequencia"])
            and all(isinstance(t[c], str) for c in CAMPOS_DA_TRAMITACAO[1:])
        ):
            raise _invalido(f"{onde}: tramitacoes deve ter {list(CAMPOS_DA_TRAMITACAO)}")
        if anterior is not None and t["sequencia"] <= anterior:
            raise _invalido(f"{onde}: tramitacoes fora de ordem ou repetidas ({t['sequencia']})")
        anterior = t["sequencia"]


def _validar_motivo(motivo, codigos: tuple[str, ...], onde: str) -> None:
    if not (
        isinstance(motivo, dict)
        and list(motivo) == ["codigo", "texto"]
        and motivo["codigo"] in codigos
        and _texto_cheio(motivo["texto"])
    ):
        raise _invalido(f"{onde}: motivo deve ser {{codigo em {list(codigos)}, texto}}")


def _validar_relator(valor, onde: str) -> None:
    if not (
        isinstance(valor, dict)
        and list(valor) == ["id", "nome", "partido_hoje"]
        and _inteiro(valor["id"])
        and isinstance(valor["nome"], str)
        and isinstance(valor["partido_hoje"], str)
    ):
        raise _invalido(f"{onde}: relator deve ser {{id, nome, partido_hoje}}")


def _validar_proprios(e: dict, onde: str) -> None:
    tipo = e["tipo"]
    if tipo == "entrou":
        _validar_motivo(e["motivo"], MOTIVOS_DE_ENTRADA, onde)
        if not _lista_de_textos(e["etiquetas"]):
            raise _invalido(f"{onde}: etiquetas deve ser lista de textos")
    elif tipo == "saiu":
        _validar_motivo(e["motivo"], MOTIVOS_DE_SAIDA, onde)
        destino = e["destino"]
        if not (
            isinstance(destino, dict)
            and list(destino) == ["orgao", "situacao", "apensado_a"]
            and all(
                destino[c] is None or isinstance(destino[c], str) for c in ("orgao", "situacao")
            )
            and (destino["apensado_a"] is None or isinstance(destino["apensado_a"], dict))
        ):
            raise _invalido(f"{onde}: destino deve ser {{orgao, situacao, apensado_a}}")
        if not _lista_de_textos(e["outros_fatos"]):
            raise _invalido(f"{onde}: outros_fatos deve ser lista de textos")
    elif tipo == "situacao":
        if not (_texto_cheio(e["de"]) and _texto_cheio(e["para"]) and e["de"] != e["para"]):
            raise _invalido(f"{onde}: situacao deve ter 'de' e 'para' diferentes")
    elif tipo == "relator":
        mudanca, de, para = e["mudanca"], e["de"], e["para"]
        if mudanca not in MUDANCAS_DE_RELATOR:
            raise _invalido(f"{onde}: relator com mudanca {mudanca!r} desconhecida")
        esperado = {
            "designado": (False, True),
            "devolveu": (True, False),
            "substituido": (True, True),
        }[mudanca]
        if (de is not None, para is not None) != esperado:
            raise _invalido(f"{onde}: relator {mudanca} com 'de' e 'para' incoerentes")
        for lado in (de, para):
            if lado is not None:
                _validar_relator(lado, onde)
        if mudanca == "substituido" and de["id"] == para["id"]:
            raise _invalido(f"{onde}: relator substituído pelo mesmo relator")
    elif tipo == "etiquetas":
        ganhou, perdeu = e["ganhou"], e["perdeu"]
        if not (_lista_de_textos(ganhou) and _lista_de_textos(perdeu)):
            raise _invalido(f"{onde}: etiquetas deve ter listas de textos")
        if not ganhou and not perdeu:
            raise _invalido(f"{onde}: etiquetas sem ganho nem perda")
        if not all(x in ETIQUETAS for x in (*ganhou, *perdeu)):
            raise _invalido(f"{onde}: etiqueta desconhecida")


def _validar_evento(e, posicao: int) -> tuple[int, str]:
    onde = f"eventos[{posicao}]"
    if not isinstance(e, dict) or e.get("tipo") not in CAMPOS_PROPRIOS:
        tipo = e.get("tipo") if isinstance(e, dict) else e
        raise _invalido(f"{onde}: tipo desconhecido ({tipo!r})")
    campos = [*CAMPOS_COMUNS, *CAMPOS_PROPRIOS[e["tipo"]], "tramitacoes"]
    if list(e) != campos:
        raise _invalido(f"{onde}: campos do evento devem ser {campos}")
    if not _inteiro(e["id"]):
        raise _invalido(f"{onde}: id deve ser inteiro")
    if not (_texto_cheio(e["identificacao"]) and _texto_cheio(e["comissao"])):
        raise _invalido(f"{onde}: identificacao e comissao devem ser texto")
    if not (isinstance(e["link"], str) and e["link"].startswith(LINK_OFICIAL)):
        raise _invalido(f"{onde}: link deve ser a ficha oficial ({LINK_OFICIAL}...)")
    _validar_proprios(e, onde)
    _validar_tramitacoes(e["tramitacoes"], onde)
    return e["id"], e["tipo"]


def _validar_ressalva(r, posicao: int) -> None:
    onde = f"ressalvas[{posicao}]"
    if not (
        isinstance(r, dict)
        and list(r) == ["id", "identificacao", "comissao", "link", "motivo"]
        and _inteiro(r["id"])
        and _texto_cheio(r["identificacao"])
        and _texto_cheio(r["comissao"])
        and isinstance(r["link"], str)
        and r["link"].startswith(LINK_OFICIAL)
        and r["motivo"] in MOTIVOS_DE_RESSALVA
    ):
        raise _invalido(f"{onde}: ressalva fora do contrato")


def validar_arquivo(documento: dict) -> None:
    """Confere as regras de consistência do contrato; levanta `FalhaDeColeta(INTERNA)`.

    Uma violação aqui é erro nosso (a comparação montou algo incoerente): melhor falhar a
    execução do que gravar um arquivo que o gabinete leria como verdade.
    """
    if not isinstance(documento, dict) or list(documento) != ["meta", "eventos", "ressalvas"]:
        raise _invalido("campos esperados ['meta', 'eventos', 'ressalvas']")
    if not isinstance(documento["eventos"], list) or not isinstance(documento["ressalvas"], list):
        raise _invalido("eventos e ressalvas devem ser listas")
    vistos: set[tuple[int, str]] = set()
    for posicao, e in enumerate(documento["eventos"]):
        chave = _validar_evento(e, posicao)
        if chave in vistos:
            raise _invalido(f"evento {chave[1]} repetido para o item {chave[0]}")
        vistos.add(chave)
    _validar_meta(documento["meta"], documento)
    for posicao, r in enumerate(documento["ressalvas"]):
        _validar_ressalva(r, posicao)
