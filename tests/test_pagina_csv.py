"""O itens.csv (PAG, FR-017; contracts/site.md): separador, BOM, colunas e fidelidade."""

import csv
import io

import pagina_sinteticos as p
from monitor_comissoes.pagina import modelo, tabela

CABECALHO = [
    "identificação",
    "link oficial",
    "ementa",
    "comissão",
    "situação",
    "parado há (dias)",
    "etiquetas",
    "autores",
    "relator atual",
    "apensado a",
    "marcas",
]


def ler(conteudo: bytes) -> list[list[str]]:
    texto = conteudo.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texto, newline=""), delimiter=";"))


def csv_de(*itens) -> bytes:
    return tabela.renderizar(list(itens))


def relator(nome="Luiz Lima", partido="NOVO"):
    return {
        "id": 1,
        "nome": nome,
        "partido_hoje": partido,
        "designado_em": "2025-04-09T00:00:00",
        "fonte": "https://www.camara.leg.br/propostas-legislativas/1",
    }


def test_comeca_com_o_bom_do_utf8_e_usa_ponto_e_virgula_e_crlf():
    conteudo = csv_de(p.item_completo(id=1))

    assert conteudo.startswith(b"\xef\xbb\xbf")
    primeira = conteudo.decode("utf-8-sig").split("\r\n")[0]
    assert primeira == ";".join(CABECALHO)
    assert conteudo.endswith(b"\r\n")
    assert b"\n" not in conteudo.replace(b"\r\n", b"")


def test_cabecalho_exato():
    assert ler(csv_de(p.item_completo(id=1)))[0] == CABECALHO


def test_o_retrato_real_tem_106_linhas_e_cada_campo_bate_com_o_atual_json():
    itens = modelo.ordenar(p.retrato_real()["itens"])
    linhas = ler(tabela.renderizar(itens))

    assert len(linhas) == 106
    for linha, item in zip(linhas[1:], itens, strict=True):
        assert len(linha) == 11
        assert linha[0] == item["identificacao"]
        assert linha[1] == item["link"]
        assert linha[2] == item["ementa"]
        assert linha[3] == item["comissao"]
        assert linha[4] == item["situacao"]
        assert linha[5] == str(item["parado_ha_dias"])
        assert linha[6] == " | ".join(item["etiquetas"])


def test_autores_na_ordem_com_o_partido_na_data():
    item = p.item_completo(id=1)
    item["autores"] = [
        {"nome": "Paula Belmonte", "id_deputado": 2, "partido_na_data": "CIDADANIA", "ordem": 2},
        {"nome": "Adriana Ventura", "id_deputado": 1, "partido_na_data": "NOVO", "ordem": 1},
        {"nome": "Comissão Especial", "id_deputado": None, "partido_na_data": "", "ordem": 3},
    ]

    linha = ler(csv_de(item))[1]

    assert linha[7] == "Adriana Ventura (NOVO) | Paula Belmonte (CIDADANIA) | Comissão Especial"


def test_etiquetas_unidas_por_barra_vertical():
    linha = ler(csv_de(p.item_completo(id=1, etiquetas=("autoria NOVO", "autor hoje no NOVO"))))[1]

    assert linha[6] == "autoria NOVO | autor hoje no NOVO"


def test_relator_e_apensado_vazios_quando_nao_ha():
    linha = ler(csv_de(p.item_completo(id=1, relator=None)))[1]

    assert linha[8] == "" and linha[9] == "" and linha[10] == ""


def test_relator_e_apensado_quando_ha():
    apensado = {
        "id": 2190633,
        "identificacao": "PL 155/2019",
        "link": "https://www.camara.leg.br/propostas-legislativas/2190633",
    }
    linha = ler(csv_de(p.item_completo(id=1, relator=relator(), apensado_a=apensado)))[1]

    assert linha[8] == "Luiz Lima (NOVO)"
    assert linha[9] == "PL 155/2019"


def test_marcas_unidas_por_barra_vertical():
    so_principal = p.item_completo(id=1, principal_nao_localizada=True)
    as_duas = p.item_completo(
        id=2, principal_nao_localizada=True, relator_indeterminado={"motivo": "x"}
    )

    linhas = ler(csv_de(so_principal, as_duas))

    assert linhas[1][10] == "principal não localizada"
    assert linhas[2][10] == "principal não localizada | relator indeterminado"


def test_campo_com_separador_aspas_e_quebra_de_linha_volta_igual():
    ementa = 'Texto com ; ponto e vírgula, "aspas" e\nquebra de linha'
    item = p.item_completo(id=1)
    item["ementa"] = ementa

    conteudo = csv_de(item)

    assert ler(conteudo)[1][2] == ementa
    assert b'""aspas""' in conteudo


def test_acentos_preservados_em_utf8():
    item = p.item_completo(id=1, situacao="Aguardando Designação de Relator")
    item["ementa"] = "Altera a Lei nº 13.979, que dispõe sobre a UNIÃO."

    conteudo = csv_de(item)

    assert "Altera a Lei nº 13.979, que dispõe sobre a UNIÃO." in conteudo.decode("utf-8")
    assert ler(conteudo)[1][4] == "Aguardando Designação de Relator"


def test_ementa_que_comeca_com_igual_nao_e_alterada():
    item = p.item_completo(id=1)
    item["ementa"] = "=SOMA(1;2)"

    assert ler(csv_de(item))[1][2] == "=SOMA(1;2)"


def test_duas_geracoes_dao_os_mesmos_bytes():
    itens = modelo.ordenar(p.retrato_real()["itens"])

    assert tabela.renderizar(itens) == tabela.renderizar(itens)
