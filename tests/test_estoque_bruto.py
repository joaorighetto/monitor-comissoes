"""Estoque bruto (AGE, FR-015a) e a divisão `coletar`/`executar` da COL."""

import csv
import json

from conftest import FIXTURES
from monitor_comissoes.coleta import coletar, executar
from monitor_comissoes.lote import contar_estoque_bruto
from monitor_comissoes.saida import serializar

COMISSOES = ("CE", "CREDN")


def cabecalho_real() -> list[str]:
    with open(FIXTURES / "proposicoes-2024.csv", encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f, delimiter=";"))


def escrever_proposicoes(caminho, linhas):
    """Grava um CSV no formato da Câmara com as colunas reais e só tipo e órgão preenchidos."""
    colunas = cabecalho_real()
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        escritor.writerow(colunas)
        for numero, (tipo, orgao, principal) in enumerate(linhas, start=1):
            linha = dict.fromkeys(colunas, "")
            linha.update(
                id=str(numero),
                siglaTipo=tipo,
                ultimoStatus_siglaOrgao=orgao,
                uriPropPrincipal=principal,
            )
            escritor.writerow([linha[c] for c in colunas])


def test_conta_pl_e_plp_pelo_orgao_do_proprio_ultimo_status(tmp_path):
    arquivo = tmp_path / "proposicoes-2024.csv"
    escrever_proposicoes(
        arquivo,
        [
            ("PL", "CE", ""),  # conta
            ("PLP", "CREDN", ""),  # conta
            ("REQ", "CE", ""),  # outro tipo: não conta
            ("PDL", "CREDN", ""),  # outro tipo: não conta
            ("PL", "CFT", ""),  # outro órgão: não conta
            # apensado: vale o próprio órgão (CE), e não o da raiz (CFT)
            ("PL", "CE", "https://dadosabertos.camara.leg.br/api/v2/proposicoes/5"),
        ],
    )

    assert contar_estoque_bruto(arquivo, ("PL", "PLP"), COMISSOES) == 3


def test_arquivo_so_com_cabecalho_conta_zero(tmp_path):
    arquivo = tmp_path / "proposicoes-2024.csv"
    escrever_proposicoes(arquivo, [])

    assert contar_estoque_bruto(arquivo, ("PL", "PLP"), COMISSOES) == 0


def test_estoque_bruto_das_fixtures_reais_confere_com_contagem_independente(
    config, transporte, agora
):
    esperado = 0
    for ano in range(2003, 2027):
        with open(FIXTURES / f"proposicoes-{ano}.csv", encoding="utf-8-sig", newline="") as f:
            for linha in csv.DictReader(f, delimiter=";"):
                if (
                    linha["siglaTipo"] in ("PL", "PLP")
                    and linha["ultimoStatus_siglaOrgao"] in COMISSOES
                ):
                    esperado += 1

    coletado = coletar(config, transporte, agora)

    assert esperado > 0
    assert coletado.estoque_bruto == esperado


def test_coletar_nao_grava_nada_e_executar_grava_o_mesmo_documento(
    config, transporte, agora, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    coletado = coletar(config, transporte, agora)

    assert list(tmp_path.iterdir()) == []

    saida = tmp_path / "data" / "atual.json"
    executar(config, transporte, agora, saida)

    assert saida.read_text(encoding="utf-8") == serializar(coletado.documento)
    assert json.loads(saida.read_text(encoding="utf-8"))["meta"]["total_itens"] == len(
        coletado.documento["itens"]
    )
    assert coletado.dados_camara_em.tzinfo is not None
