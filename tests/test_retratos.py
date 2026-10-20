"""Retrato (`atual.json`) como base de comparação da MUD: leitura e validação."""

import copy
import json
from datetime import date

import pytest

import sinteticos as s
from monitor_comissoes.erros import INTERNA, FalhaDeColeta
from monitor_comissoes.retratos import ler

ORIGEM = "data/atual.json"


def lido(documento, **argumentos):
    return ler(json.dumps(documento), ORIGEM, **argumentos)


def invalido(texto, detalhe, **argumentos):
    with pytest.raises(FalhaDeColeta) as erro:
        ler(texto, ORIGEM, **argumentos)
    assert erro.value.categoria == INTERNA
    assert "retrato anterior inválido" in erro.value.motivo
    assert ORIGEM in erro.value.motivo
    assert detalhe in erro.value.motivo


def base():
    return s.retrato([s.item(1), s.item(2, relator=s.relator(referencia=2))])


# --- o que passa ----------------------------------------------------------------------------


def test_retrato_valido_da_versao_3():
    retrato = lido(base())

    assert retrato.compativel is True
    assert retrato.dia == date(2026, 10, 18)
    assert retrato.gerado_em.isoformat() == "2026-10-18T03:40:12-03:00"
    assert retrato.dados_camara_em.isoformat() == "2026-10-18T04:31:36+00:00"
    assert [i["id"] for i in retrato.documento["itens"]] == [1, 2]


def test_o_dia_e_a_data_de_gerado_em_em_brasilia_mesmo_com_outro_fuso():
    # 01:30 UTC de 19/10 ainda é 22:30 de 18/10 em Brasília.
    retrato = lido(s.retrato([s.item(1)], gerado_em="2026-10-19T01:30:00+00:00"))

    assert retrato.dia == date(2026, 10, 18)


@pytest.mark.parametrize("versao", [1, 2])
def test_versoes_antigas_sao_validas_mas_incompativeis_e_os_itens_nao_sao_validados(versao):
    documento = s.retrato([], versao=versao)
    documento["itens"] = [{"id": 1, "so_o_formato_antigo": True}]

    retrato = lido(documento)

    assert retrato.compativel is False
    assert retrato.dia == date(2026, 10, 18)


def test_versao_futura_tambem_e_incompativel():
    assert lido(s.retrato([], versao=4)).compativel is False


def test_sem_validar_itens_so_o_meta_precisa_estar_legivel():
    documento = base()
    documento["itens"] = "estragado"

    retrato = lido(documento, validar_itens=False)

    assert retrato.dia == date(2026, 10, 18)
    assert retrato.compativel is True


# --- o que falha: arquivo e meta ----------------------------------------------------------


@pytest.mark.parametrize("texto", ["", "{", "não é json", "[1, 2]", '"texto"', "null"])
def test_texto_que_nao_e_um_objeto_json_falha(texto):
    invalido(texto, "objeto")


@pytest.mark.parametrize("faltando", ["meta", "itens"])
def test_objeto_sem_meta_ou_sem_itens_falha(faltando):
    documento = base()
    del documento[faltando]

    invalido(json.dumps(documento), faltando)


def test_meta_que_nao_e_objeto_falha():
    documento = base()
    documento["meta"] = []

    invalido(json.dumps(documento), "meta")


@pytest.mark.parametrize("versao", [None, "3", 3.0, True, [3]])
def test_versao_de_formato_que_nao_e_inteiro_falha(versao):
    documento = base()
    documento["meta"]["versao_formato"] = versao

    invalido(json.dumps(documento), "versao_formato")


@pytest.mark.parametrize("campo", ["gerado_em", "dados_camara_em"])
@pytest.mark.parametrize(
    "valor",
    [None, 5, "", "ontem", "2026-13-40T00:00:00-03:00", "2026-10-18T03:40:12", "2026-10-18"],
)
def test_data_e_hora_ausente_invalida_ou_sem_fuso_falha(campo, valor):
    documento = base()
    if valor is None:
        del documento["meta"][campo]
    else:
        documento["meta"][campo] = valor

    invalido(json.dumps(documento), campo)


# --- o que falha: itens da versão 3 -------------------------------------------------------


def trocar(campo, valor):
    documento = base()
    if valor is ...:
        del documento["itens"][0][campo]
    else:
        documento["itens"][0][campo] = valor
    return json.dumps(documento)


def test_itens_que_nao_e_lista_falha():
    documento = base()
    documento["itens"] = {"1": {}}

    invalido(json.dumps(documento), "itens")


def test_item_que_nao_e_objeto_falha():
    documento = base()
    documento["itens"][1] = "PL 2/2020"

    invalido(json.dumps(documento), "itens[1]")


@pytest.mark.parametrize(
    "campo",
    [
        "id",
        "identificacao",
        "link",
        "comissao",
        "situacao",
        "etiquetas",
        "relator",
        "relator_indeterminado",
        "apensado_a",
        "ultimo_status_sequencia",
    ],
)
def test_campo_exigido_ausente_falha(campo):
    invalido(trocar(campo, ...), campo)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("id", "1"),
        ("id", True),
        ("id", 1.5),
        ("identificacao", 7),
        ("link", None),
        ("comissao", ["CE"]),
        ("situacao", None),
        ("etiquetas", "autoria NOVO"),
        ("etiquetas", ["autoria NOVO", 3]),
        ("relator", "Luiz Lima"),
        ("relator", {"id": "1", "nome": "x", "partido_hoje": "NOVO"}),
        ("relator", {"id": 1, "nome": None, "partido_hoje": "NOVO"}),
        ("relator", {"id": 1, "nome": "x"}),
        ("relator_indeterminado", "motivo"),
        ("apensado_a", "PL 9/2019"),
        ("apensado_a", {"id": "9", "identificacao": "PL 9/2019", "link": "x"}),
        ("apensado_a", {"id": 9}),
        ("ultimo_status_sequencia", "41"),
        ("ultimo_status_sequencia", True),
        ("ultimo_status_sequencia", 0),
        ("ultimo_status_sequencia", -1),
        ("ultimo_status_sequencia", 4.5),
    ],
)
def test_campo_exigido_de_tipo_errado_falha(campo, valor):
    invalido(trocar(campo, valor), campo)


def test_id_repetido_falha_e_diz_qual():
    documento = base()
    documento["itens"][1]["id"] = 1

    invalido(json.dumps(documento), "id repetido: 1")


def test_a_validacao_nao_altera_o_documento_lido():
    documento = base()
    antes = copy.deepcopy(documento)

    lido(documento)

    assert documento == antes


def test_a_versao_comparavel_e_a_que_a_coleta_grava():
    from monitor_comissoes.coleta import VERSAO_FORMATO
    from monitor_comissoes.retratos import VERSAO_COMPARAVEL

    assert VERSAO_COMPARAVEL == VERSAO_FORMATO


# --- preparar: qual é o retrato anterior (research R5) -----------------------------------------

from monitor_comissoes.retratos import preparar  # noqa: E402

HOJE = date(2026, 10, 19)
ONTEM = "2026-10-18T03:40:12-03:00"
ONTEM_LOTE = "2026-10-18T04:31:36+00:00"
HOJE_GERADO = "2026-10-19T03:40:12-03:00"


def gravar(caminho, documento=None, *, texto=None):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes((texto if texto is not None else json.dumps(documento)).encode("utf-8"))
    return caminho


@pytest.fixture
def arquivos(tmp_path):
    return tmp_path / "data" / "atual.json", tmp_path / "data" / "anterior.json"


def v3(gerado_em=ONTEM, dados_camara_em=ONTEM_LOTE, versao=3):
    return s.retrato(
        [s.item(1), s.item(2)], gerado_em=gerado_em, dados_camara_em=dados_camara_em, versao=versao
    )


def test_sem_atual_e_sem_anterior_e_primeiro_retrato(arquivos):
    atual, anterior = arquivos

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is None
    assert c.motivo_linha_de_base == "primeiro retrato"
    assert c.retrato_anterior is None
    assert c.copia_anterior is None


def test_sem_atual_mas_com_anterior_valido_compara_com_o_anterior(arquivos):
    atual, anterior = arquivos
    gravar(anterior, v3())

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is not None and c.motivo_linha_de_base is None
    assert c.copia_anterior is None


def test_atual_de_dia_anterior_versao_3_e_o_retrato_anterior_e_vira_a_copia(arquivos):
    atual, anterior = arquivos
    texto_original = json.dumps(v3(), indent=2) + "  \r\n"  # espaços e CRLF no fim: nada se perde
    gravar(atual, texto=texto_original)

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is not None and c.anterior.compativel
    assert c.anterior.dia == date(2026, 10, 18)
    assert c.motivo_linha_de_base is None
    assert c.retrato_anterior == {"dia": "2026-10-18", "dados_camara_em": ONTEM_LOTE}
    assert c.copia_anterior == texto_original  # texto original, byte a byte, sem reserializar


@pytest.mark.parametrize("versao", [1, 2])
def test_atual_de_dia_anterior_em_versao_antiga_e_linha_de_base_incompativel(arquivos, versao):
    atual, anterior = arquivos
    documento = v3(versao=versao)
    documento["itens"] = [{"formato": "antigo"}]
    texto_original = json.dumps(documento)
    gravar(atual, texto=texto_original)

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is None
    assert c.motivo_linha_de_base == "formato anterior incompatível"
    assert c.retrato_anterior == {"dia": "2026-10-18", "dados_camara_em": ONTEM_LOTE}
    assert c.copia_anterior == texto_original


@pytest.mark.parametrize(
    "texto",
    ["", "{", "não é json", "[]", '{"meta": {}, "itens": []}'],
    ids=["vazio", "json-truncado", "nao-json", "lista", "meta-vazio"],
)
def test_atual_sem_meta_legivel_falha_com_o_nome_do_arquivo(arquivos, texto):
    atual, anterior = arquivos
    gravar(atual, texto=texto)

    with pytest.raises(FalhaDeColeta) as erro:
        preparar(atual, anterior, HOJE)

    assert erro.value.categoria == INTERNA
    assert str(atual) in erro.value.motivo


def test_atual_de_dia_anterior_com_itens_estragados_falha(arquivos):
    atual, anterior = arquivos
    documento = v3()
    documento["itens"][0]["ultimo_status_sequencia"] = "x"
    gravar(atual, documento)

    with pytest.raises(FalhaDeColeta) as erro:
        preparar(atual, anterior, HOJE)

    assert erro.value.categoria == INTERNA
    assert "ultimo_status_sequencia" in erro.value.motivo


def test_atual_que_nao_e_utf8_falha(arquivos):
    atual, anterior = arquivos
    atual.parent.mkdir(parents=True)
    atual.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(FalhaDeColeta) as erro:
        preparar(atual, anterior, HOJE)

    assert erro.value.categoria == INTERNA
    assert str(atual) in erro.value.motivo


def test_atual_de_hoje_com_anterior_valido_usa_o_anterior_sem_rotacionar(arquivos):
    atual, anterior = arquivos
    gravar(atual, v3(gerado_em=HOJE_GERADO, dados_camara_em="2026-10-19T04:31:36+00:00"))
    gravar(anterior, v3())

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is not None and c.anterior.dia == date(2026, 10, 18)
    assert c.retrato_anterior == {"dia": "2026-10-18", "dados_camara_em": ONTEM_LOTE}
    assert c.copia_anterior is None


def test_atual_de_hoje_sem_anterior_e_primeiro_retrato(arquivos):
    atual, anterior = arquivos
    gravar(atual, v3(gerado_em=HOJE_GERADO))

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is None
    assert c.motivo_linha_de_base == "primeiro retrato"
    assert c.retrato_anterior is None
    assert c.copia_anterior is None


@pytest.mark.parametrize("texto", ["", "{", "não é json"])
def test_atual_de_hoje_com_anterior_ilegivel_falha(arquivos, texto):
    atual, anterior = arquivos
    gravar(atual, v3(gerado_em=HOJE_GERADO))
    gravar(anterior, texto=texto)

    with pytest.raises(FalhaDeColeta) as erro:
        preparar(atual, anterior, HOJE)

    assert erro.value.categoria == INTERNA
    assert str(anterior) in erro.value.motivo


def test_atual_de_hoje_com_itens_estragados_nao_falha_porque_sera_sobrescrito(arquivos):
    atual, anterior = arquivos
    documento = v3(gerado_em=HOJE_GERADO)
    documento["itens"] = "estragado"
    gravar(atual, documento)
    gravar(anterior, v3())

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is not None and c.copia_anterior is None


def test_atual_de_hoje_com_anterior_em_versao_antiga_e_linha_de_base_sem_rotacao(arquivos):
    atual, anterior = arquivos
    gravar(atual, v3(gerado_em=HOJE_GERADO))
    gravar(anterior, v3(versao=2))

    c = preparar(atual, anterior, HOJE)

    assert c.anterior is None
    assert c.motivo_linha_de_base == "formato anterior incompatível"
    assert c.retrato_anterior == {"dia": "2026-10-18", "dados_camara_em": ONTEM_LOTE}
    assert c.copia_anterior is None


def test_atual_de_data_futura_falha(arquivos):
    atual, anterior = arquivos
    gravar(atual, v3(gerado_em="2026-10-20T03:40:12-03:00"))

    with pytest.raises(FalhaDeColeta) as erro:
        preparar(atual, anterior, HOJE)

    assert erro.value.categoria == INTERNA
    assert "data futura" in erro.value.motivo and "2026-10-20" in erro.value.motivo


def test_anterior_que_nao_e_de_um_dia_anterior_ao_de_hoje_falha(arquivos):
    atual, anterior = arquivos
    gravar(atual, v3(gerado_em=HOJE_GERADO))
    gravar(anterior, v3(gerado_em="2026-10-19T01:00:00-03:00"))

    with pytest.raises(FalhaDeColeta) as erro:
        preparar(atual, anterior, HOJE)

    assert erro.value.categoria == INTERNA
    assert str(anterior) in erro.value.motivo and "dia anterior" in erro.value.motivo


def test_preparar_nao_altera_nenhum_arquivo(arquivos):
    atual, anterior = arquivos
    gravar(atual, v3())
    antes = atual.read_bytes()

    preparar(atual, anterior, HOJE)

    assert atual.read_bytes() == antes
    assert not anterior.exists()
