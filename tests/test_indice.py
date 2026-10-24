"""Índice de autoria (contracts/indice-autoria.md): construção pelo lote, serialização e leitura."""

import csv
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from monitor_comissoes.erros import ENTRADA_INVALIDA, FalhaDeColeta
from monitor_comissoes.indice import TIPOS, construir_indice, ler_indice, serializar_indice
from monitor_comissoes.lote import Lote

FIXTURES = Path(__file__).parent / "fixtures" / "camara"
BRASILIA = timezone(timedelta(hours=-3))
AGORA = datetime(2026, 10, 24, 3, 58, 2, tzinfo=BRASILIA)
MINIMO = datetime(2026, 10, 24, 4, 31, 37, tzinfo=UTC)
CAMPOS = ["versao_formato", "gerado_em", "dados_camara_em", "anos_lidos", "tipos", "proposicoes"]


def lote_das_fixtures():
    return Lote(
        diretorio=FIXTURES,
        anos=tuple(range(2003, 2027)),
        last_modified_min=MINIMO,
        last_modified_max=MINIMO + timedelta(hours=1),
    )


def _csv(caminho, cabecalho, linhas):
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


def lote_sintetico(tmp_path, proposicoes, autores_por_ano):
    """proposicoes: {ano: [(id, siglaTipo)]}; autores_por_ano: {ano: [(idProp, idDep, partido)]}."""
    for ano in proposicoes:
        _csv(
            tmp_path / f"proposicoes-{ano}.csv",
            ["id", "siglaTipo", "numero", "ano"],
            [(pid, tipo, "1", str(ano)) for pid, tipo in proposicoes[ano]],
        )
        _csv(
            tmp_path / f"proposicoesAutores-{ano}.csv",
            ["idProposicao", "idDeputadoAutor", "siglaPartidoAutor"],
            autores_por_ano.get(ano, []),
        )
    anos = tuple(sorted(proposicoes))
    return Lote(tmp_path, anos, MINIMO, MINIMO)


def test_inclui_toda_proposicao_dos_seis_tipos_e_so_elas():
    esperados = set()
    for arquivo in FIXTURES.glob("proposicoes-*.csv"):
        with open(arquivo, encoding="utf-8-sig", newline="") as f:
            for linha in csv.DictReader(f, delimiter=";"):
                if linha["siglaTipo"] in TIPOS:
                    esperados.add(linha["id"])

    indice = construir_indice(lote_das_fixtures(), AGORA)

    assert set(indice["proposicoes"]) == esperados
    assert len(esperados) == 150
    assert "SBT" not in TIPOS


def test_autoria_novo_e_deputados_autores_das_fixtures():
    proposicoes = construir_indice(lote_das_fixtures(), AGORA)["proposicoes"]

    # PL com 11 autores, três que assinaram como NOVO.
    autoria, deputados = proposicoes["2141142"]
    assert autoria == 1
    assert deputados == sorted(deputados)
    assert len(deputados) == 11
    assert {204519, 204461, 204532} <= set(deputados)
    # Três autores do PSDB: está no lote, sem autoria do NOVO.
    assert proposicoes["2137635"] == [0, [178844, 178912, 178916]]
    # Sem nenhuma linha de autor.
    assert proposicoes["267841"] == [0, []]
    # Autor sem id de deputado (órgão ou senador): não entra na lista.
    assert proposicoes["260688"] == [0, []]


def test_deputados_sem_repeticao_em_ordem_e_autores_de_outro_ano(tmp_path):
    lote = lote_sintetico(
        tmp_path,
        {2020: [("10", "PL"), ("11", "REQ"), ("12", "SBT")], 2021: [("20", "PEC")]},
        {
            2020: [
                ("10", "300", "PT"),
                ("10", "100", "NOVO"),
                ("10", "300", "PT"),
                ("20", "5", ""),
            ],
            2021: [("11", "", "NOVO"), ("12", "100", "NOVO")],
        },
    )

    proposicoes = construir_indice(lote, AGORA)["proposicoes"]

    assert proposicoes == {"10": [1, [100, 300]], "11": [1, []], "20": [0, [5]]}


def test_meta_segue_o_atual_da_mesma_coleta(tmp_path):
    lote = lote_sintetico(tmp_path, {2003: [("1", "PL")], 2026: []}, {})

    indice = construir_indice(lote, datetime(2026, 10, 24, 6, 58, 2, tzinfo=UTC))

    assert list(indice) == CAMPOS
    assert indice["versao_formato"] == 1
    assert indice["gerado_em"] == "2026-10-24T03:58:02-03:00"
    assert indice["dados_camara_em"] == "2026-10-24T04:31:37+00:00"
    assert indice["anos_lidos"] == [2003, 2026]
    assert indice["tipos"] == ["MSC", "PDL", "PEC", "PL", "PLP", "REQ"]


def test_serializacao_compacta_na_ordem_do_contrato(tmp_path):
    lote = lote_sintetico(tmp_path, {2020: [("10", "PL")]}, {2020: [("10", "7", "NOVO")]})

    texto = serializar_indice(construir_indice(lote, AGORA))

    assert texto.startswith('{"versao_formato":1,"gerado_em":"2026-10-24T03:58:02-03:00",')
    assert texto.endswith('"proposicoes":{"10":[1,[7]]}}\n')
    assert texto.count("\n") == 1


def _gravar(tmp_path, documento):
    caminho = tmp_path / "indice-autoria.json"
    caminho.write_text(
        documento if isinstance(documento, str) else json.dumps(documento), encoding="utf-8"
    )
    return caminho


def _valido():
    return {
        "versao_formato": 1,
        "gerado_em": "2026-10-24T03:58:02-03:00",
        "dados_camara_em": "2026-10-24T04:31:37+00:00",
        "anos_lidos": [2003, 2026],
        "tipos": ["MSC", "PDL", "PEC", "PL", "PLP", "REQ"],
        "proposicoes": {"2645503": [0, [220629]], "1": [1, []]},
    }


def test_ler_devolve_o_indice_gravado(tmp_path):
    lote = lote_sintetico(tmp_path, {2020: [("10", "PL")]}, {2020: [("10", "7", "NOVO")]})
    indice = construir_indice(lote, AGORA)
    caminho = tmp_path / "indice.json"
    caminho.write_text(serializar_indice(indice), encoding="utf-8")

    assert ler_indice(caminho) == indice
    assert ler_indice(_gravar(tmp_path, _valido())) == _valido()


def _sem(campo):
    documento = _valido()
    del documento[campo]
    return documento


def _com(campo, valor):
    documento = _valido()
    documento[campo] = valor
    return documento


@pytest.mark.parametrize(
    "documento",
    [
        "{não é json",
        "[]",
        _com("versao_formato", 2),
        *[_sem(campo) for campo in CAMPOS],
        _com("gerado_em", None),
        _com("dados_camara_em", 3),
        _com("anos_lidos", [2003]),
        _com("anos_lidos", ["2003", 2026]),
        _com("tipos", "PL"),
        _com("proposicoes", []),
        _com("proposicoes", {"abc": [0, []]}),
        _com("proposicoes", {"1": [2, []]}),
        _com("proposicoes", {"1": [True, []]}),
        _com("proposicoes", {"1": [0]}),
        _com("proposicoes", {"1": [0, ["7"]]}),
        _com("proposicoes", {"1": [0, 7]}),
    ],
)
def test_ler_falha_com_entrada_invalida_e_o_caminho(tmp_path, documento):
    caminho = _gravar(tmp_path, documento)

    with pytest.raises(FalhaDeColeta) as erro:
        ler_indice(caminho)

    assert erro.value.categoria == ENTRADA_INVALIDA
    assert str(caminho) in erro.value.motivo


def test_ler_falha_com_arquivo_ausente(tmp_path):
    caminho = tmp_path / "cache" / "indice-autoria.json"

    with pytest.raises(FalhaDeColeta) as erro:
        ler_indice(caminho)

    assert erro.value.categoria == ENTRADA_INVALIDA
    assert str(caminho) in erro.value.motivo
    assert "não existe" in erro.value.motivo
