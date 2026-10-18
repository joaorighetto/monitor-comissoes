from datetime import datetime

from conftest import BRASILIA
from monitor_comissoes.estoque import construir_itens, etiquetar
from monitor_comissoes.lote import Autor, Proposicao

AGORA = datetime(2026, 10, 18, 9, 0, tzinfo=BRASILIA)
COMISSOES = ("CE", "CREDN")
DEPUTADOS_NOVO = {204455, 220633}


def prop(id=1, tipo="PL", numero=10, ano=2020, orgao="CE", status=datetime(2026, 10, 8, 14, 30),
         situacao="Aguardando Parecer", principal=None):  # fmt: skip
    return Proposicao(
        id=id,
        tipo=tipo,
        numero=numero,
        ano=ano,
        ementa=f"Ementa {id}",
        data_apresentacao=datetime(ano, 3, 2, 10, 0),
        id_principal=principal,
        ultimo_status_em=status,
        orgao=orgao,
        situacao=situacao,
    )


def autor(pid=1, dep=None, partido="PL", nome="Fulano", ordem=1):
    return Autor(
        id_proposicao=pid, id_deputado=dep, nome=nome, partido_na_data=partido, ordem=ordem
    )


def itens(candidatas, autores, comissoes=COMISSOES):
    return construir_itens({p.id: p for p in candidatas}, autores, DEPUTADOS_NOVO, comissoes, AGORA)


# --- etiquetar ----------------------------------------------------------------------------


def test_autoria_novo_pelo_partido_na_data():
    assert etiquetar([autor(partido="NOVO", dep=999)], DEPUTADOS_NOVO) == ["autoria NOVO"]


def test_autor_hoje_no_novo_pelo_id_do_deputado():
    assert etiquetar([autor(partido="PL", dep=204455)], DEPUTADOS_NOVO) == ["autor hoje no NOVO"]


def test_as_duas_etiquetas_em_ordem_fixa():
    autores = [autor(partido="NOVO", dep=204455)]

    assert etiquetar(autores, DEPUTADOS_NOVO) == ["autoria NOVO", "autor hoje no NOVO"]


def test_etiquetas_sem_repeticao_com_varios_autores():
    autores = [autor(partido="NOVO", dep=1, ordem=1), autor(partido="NOVO", dep=2, ordem=2)]

    assert etiquetar(autores, DEPUTADOS_NOVO) == ["autoria NOVO"]


def test_sem_ligacao_com_o_novo_nao_ha_etiqueta():
    assert etiquetar([autor(partido="PL", dep=5), autor(partido="PT", dep=6)], DEPUTADOS_NOVO) == []


def test_autor_que_nao_e_deputado_com_partido_novo_recebe_so_autoria():
    # Senado ou Executivo: idDeputadoAutor vazio, mas o partido registrado é NOVO.
    assert etiquetar([autor(partido="NOVO", dep=None)], DEPUTADOS_NOVO) == ["autoria NOVO"]


def test_autor_sem_id_e_de_outro_partido_nao_recebe_etiqueta():
    assert etiquetar([autor(partido="PT", dep=None)], DEPUTADOS_NOVO) == []


# --- construir_itens ----------------------------------------------------------------------


def test_item_completo_conforme_o_contrato():
    p = prop(id=7, numero=1843, ano=2022, status=datetime(2026, 10, 8, 14, 30))
    autores = {7: [autor(pid=7, dep=204455, partido="PL", nome="Luiz Lima")]}

    [item] = itens([p], autores)

    assert list(item) == [
        "id", "tipo", "numero", "ano", "identificacao", "ementa", "data_apresentacao", "link",
        "autores", "etiquetas", "comissao", "situacao", "ultimo_status_em", "parado_ha_dias",
        "apensado_a", "principal_nao_localizada",
    ]  # fmt: skip
    assert item["identificacao"] == "PL 1843/2022"
    assert item["link"] == "https://www.camara.leg.br/propostas-legislativas/7"
    assert item["data_apresentacao"] == "2022-03-02T10:00:00"
    assert item["ultimo_status_em"] == "2026-10-08T14:30:00"
    assert item["parado_ha_dias"] == 10
    assert item["comissao"] == "CE"
    assert item["situacao"] == "Aguardando Parecer"
    assert item["etiquetas"] == ["autor hoje no NOVO"]
    assert item["autores"] == [
        {"nome": "Luiz Lima", "id_deputado": 204455, "partido_na_data": "PL", "ordem": 1}
    ]
    assert item["apensado_a"] is None
    assert item["principal_nao_localizada"] is False


def test_so_pl_e_plp_sao_candidatas():
    candidatas = [prop(id=1, tipo="PL"), prop(id=2, tipo="PLP"), prop(id=3, tipo="REQ"),
                  prop(id=4, tipo="PDL"), prop(id=5, tipo="PEC")]  # fmt: skip
    autores = {i: [autor(pid=i, partido="NOVO")] for i in range(1, 6)}

    assert [i["id"] for i in itens(candidatas, autores)] == [1, 2]


def test_orgao_fora_da_lista_fica_de_fora():
    candidatas = [prop(id=1, orgao="CE"), prop(id=2, orgao="CFT"), prop(id=3, orgao="")]
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (1, 2, 3)}

    assert [i["id"] for i in itens(candidatas, autores)] == [1]


def test_candidata_sem_etiqueta_ou_sem_autores_fica_de_fora():
    candidatas = [prop(id=1), prop(id=2)]
    autores = {1: [autor(pid=1, partido="PT", dep=9)]}

    assert itens(candidatas, autores) == []


def test_comissao_vem_da_configuracao():
    candidatas = [prop(id=1, orgao="CE"), prop(id=2, orgao="CREDN")]
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (1, 2)}

    assert [i["comissao"] for i in itens(candidatas, autores, comissoes=("CREDN",))] == ["CREDN"]


def test_autores_ordenados_por_ordem_de_assinatura():
    autores = {
        1: [autor(partido="NOVO", nome="B", ordem=2), autor(partido="PL", nome="A", ordem=1)]
    }

    [item] = itens([prop(id=1)], autores)

    assert [a["nome"] for a in item["autores"]] == ["A", "B"]


def test_ordem_dos_itens_parado_ha_mais_tempo_primeiro_e_id_no_empate():
    antigo = datetime(2020, 1, 1)
    recente = datetime(2026, 10, 1)
    candidatas = [prop(id=5, status=recente), prop(id=9, status=antigo), prop(id=3, status=antigo)]
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (3, 5, 9)}

    assert [i["id"] for i in itens(candidatas, autores)] == [3, 9, 5]


def test_parado_ha_conta_dias_inteiros_pela_data_de_brasilia():
    # 18/10/2026 09:00 em Brasília; último status no começo e no fim do dia 17.
    candidatas = [prop(id=1, status=datetime(2026, 10, 17, 0, 0)),
                  prop(id=2, status=datetime(2026, 10, 17, 23, 59)),
                  prop(id=3, status=datetime(2026, 10, 18, 8, 0))]  # fmt: skip
    autores = {i: [autor(pid=i, partido="NOVO")] for i in (1, 2, 3)}

    assert {i["id"]: i["parado_ha_dias"] for i in itens(candidatas, autores)} == {1: 1, 2: 1, 3: 0}
