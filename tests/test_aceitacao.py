"""Casos de aceitação da COL sobre as fixtures reais da Câmara (sem rede)."""

import csv
import io
import json
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import pytest

from conftest import FIXTURES, TransporteFalso
from monitor_comissoes.cli import main
from monitor_comissoes.coleta import executar
from monitor_comissoes.config import Config

CONFIG_REPO = Path(__file__).parent.parent / "config.toml"
MANIFESTO = json.loads((FIXTURES / "manifesto.json").read_text(encoding="utf-8"))
CONTRASTE = MANIFESTO["selecao"]["contraste"]


def gerar(config, transporte, agora, tmp_path):
    saida = tmp_path / "data" / "atual.json"
    executar(config, transporte, agora, saida)
    return json.loads(saida.read_text(encoding="utf-8"))


def por_identificacao(documento):
    return {i["identificacao"]: i for i in documento["itens"]}


@pytest.fixture
def documento(config, transporte, agora, tmp_path):
    return gerar(config, transporte, agora, tmp_path)


def test_pl_1843_2022_tem_autoria_novo(documento):
    item = por_identificacao(documento)["PL 1843/2022"]

    assert item["etiquetas"] == ["autoria NOVO"]
    assert item["comissao"] == "CE"
    assert item["situacao"] == "Aguardando Parecer"
    assert item["id"] == 2331032
    assert [a["nome"] for a in item["autores"]] == ["Lucas Gonzalez"]
    assert item["autores"][0]["partido_na_data"] == "NOVO"


def test_pl_3871_2024_tem_so_autor_hoje_no_novo(documento):
    item = por_identificacao(documento)["PL 3871/2024"]

    # Luiz Lima assinou quando era do PL; hoje é deputado em exercício do NOVO.
    assert item["etiquetas"] == ["autor hoje no NOVO"]
    assert item["autores"][0]["partido_na_data"] == "PL"
    assert item["autores"][0]["id_deputado"] == 204455


def test_parado_ha_conta_a_partir_do_ultimo_status(documento):
    item = por_identificacao(documento)["PL 1843/2022"]

    esperado = (date(2026, 10, 18) - date(2025, 10, 16)).days
    assert item["ultimo_status_em"] == "2025-10-16T00:00:00"
    assert item["parado_ha_dias"] == esperado


@pytest.mark.parametrize("motivo", sorted(CONTRASTE))
def test_linhas_de_contraste_nao_entram(documento, motivo):
    # REQ e PDL na CE, PL de outro partido na CE e PL do NOVO fora das comissões.
    assert CONTRASTE[motivo] not in {i["id"] for i in documento["itens"]}


def test_todo_item_tem_link_oficial_etiqueta_e_comissao_da_lista(documento):
    assert documento["itens"]
    for item in documento["itens"]:
        assert item["link"] == f"https://www.camara.leg.br/propostas-legislativas/{item['id']}"
        assert item["etiquetas"]
        assert set(item["etiquetas"]) <= {"autoria NOVO", "autor hoje no NOVO"}
        assert item["comissao"] in ("CE", "CREDN")
        assert item["tipo"] in ("PL", "PLP")


def test_arquivo_termina_com_quebra_de_linha_e_usa_utf8(config, transporte, agora, tmp_path):
    gerar(config, transporte, agora, tmp_path)

    texto = (tmp_path / "data" / "atual.json").read_text(encoding="utf-8")

    assert texto.endswith("}\n")
    assert "\\u00" not in texto


def test_comando_imprime_resumo_e_sai_com_zero(transporte, agora, tmp_path, capsys):
    saida = tmp_path / "atual.json"

    codigo = main(
        ["--config", str(CONFIG_REPO), "--saida", str(saida)], transporte=transporte, agora=agora
    )

    linha = capsys.readouterr().out.strip()
    assert codigo == 0
    assert linha.startswith("OK: ")
    assert "CE:" in linha and "CREDN:" in linha
    assert saida.exists()


# --- US2: apensados ------------------------------------------------------------------------

PL_4047_2019 = 2211957  # apensado; a cadeia real termina no PL 3047/2015, na CFT
PL_3047_2015 = 1734799  # raiz real da cadeia do PL 4047/2019
PL_1843_2022 = 2331032


def variar_principal(transporte, arquivo, id_proposicao, novo_principal):
    """Variante DERIVADA de uma linha real: troca só o uriPropPrincipal da proposição.

    Existe apenas dentro do teste; nada é gravado em tests/fixtures/.
    """

    def transformar(corpo: bytes) -> bytes:
        leitor = csv.reader(
            io.StringIO(corpo.decode("utf-8-sig"), newline=""), delimiter=";", strict=True
        )
        cabecalho = next(leitor)
        i_id, i_principal = cabecalho.index("id"), cabecalho.index("uriPropPrincipal")
        linhas = list(leitor)
        for linha in linhas:
            if int(linha[i_id]) == id_proposicao:
                linha[i_principal] = (
                    f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{novo_principal}"
                )
        saida = io.StringIO(newline="")
        escritor = csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
        return saida.getvalue().encode("utf-8-sig")

    transporte.transformar[arquivo] = transformar


def test_pl_4047_2019_fica_fora_porque_a_raiz_da_cadeia_esta_na_cft(documento):
    assert PL_4047_2019 not in {i["id"] for i in documento["itens"]}
    # O status do próprio apensado é da CE, e o autor (Luiz Lima) é hoje do NOVO.
    assert "PL 4047/2019" not in por_identificacao(documento)


def test_apensado_a_uma_raiz_na_comissao_entra_com_status_da_raiz(
    config, transporte, agora, tmp_path
):
    # Derivada: o PL 4047/2019 passa a ser apensado direto ao PL 1843/2022 (CE).
    variar_principal(transporte, "proposicoes-2019.csv", PL_4047_2019, PL_1843_2022)

    item = por_identificacao(gerar(config, transporte, agora, tmp_path))["PL 4047/2019"]

    assert item["etiquetas"] == ["autor hoje no NOVO"]
    assert item["apensado_a"]["identificacao"] == "PL 1843/2022"
    assert item["apensado_a"]["link"].endswith(f"/{PL_1843_2022}")
    assert item["comissao"] == "CE"
    assert (
        item["situacao"] == "Aguardando Parecer"
    )  # situação da raiz, não "Tramitando em Conjunto"
    assert item["ultimo_status_em"] == "2025-10-16T00:00:00"
    assert item["principal_nao_localizada"] is False


def test_raiz_inexistente_vira_principal_nao_localizada(config, transporte, agora, tmp_path):
    # Derivada: o PL 4047/2019 passa a apontar para um id que não existe em nenhum arquivo.
    variar_principal(transporte, "proposicoes-2019.csv", PL_4047_2019, 999_999_999)

    item = por_identificacao(gerar(config, transporte, agora, tmp_path))["PL 4047/2019"]

    assert item["principal_nao_localizada"] is True
    assert item["apensado_a"] is None
    assert item["comissao"] == "CE"
    assert item["situacao"] == "Tramitando em Conjunto"  # o próprio status


def test_ciclo_de_apensacao_termina_normalmente_com_a_marca(config, transporte, agora, tmp_path):
    # Derivada: a raiz real (PL 3047/2015) passa a ser apensada ao PL 4047/2019, fechando o ciclo.
    variar_principal(transporte, "proposicoes-2015.csv", PL_3047_2015, PL_4047_2019)

    item = por_identificacao(gerar(config, transporte, agora, tmp_path))["PL 4047/2019"]

    assert item["principal_nao_localizada"] is True
    assert item["apensado_a"] is None


# --- US4: configuração ---------------------------------------------------------------------


def test_trocar_a_comissao_muda_o_resultado_sem_mexer_no_codigo(transporte, agora, tmp_path):
    # O PL 7843/2017 (autoria do NOVO) está na MESA nas fixtures reais.
    documento = gerar(Config(("MESA",), 2003), transporte, agora, tmp_path)

    identificacoes = set(por_identificacao(documento))
    assert "PL 7843/2017" in identificacoes
    assert "PL 1843/2022" not in identificacoes  # é da CE
    assert {i["comissao"] for i in documento["itens"]} == {"MESA"}
    assert documento["meta"]["comissoes"] == ["MESA"]


def test_so_a_ce_exclui_os_itens_da_credn(config, transporte, agora, tmp_path):
    documento = gerar(Config(("CE",), 2003), transporte, agora, tmp_path)

    assert {i["comissao"] for i in documento["itens"]} == {"CE"}
    assert list(documento["meta"]["total_por_comissao"]) == ["CE"]


def test_ano_minimo_limita_os_arquivos_pedidos(transporte, agora, tmp_path):
    documento = gerar(Config(("CE", "CREDN"), 2023), transporte, agora, tmp_path)

    pedidos = transporte.arquivos_pedidos()
    anos = {int(nome.rsplit("-", 1)[1].split(".")[0]) for nome in pedidos}
    assert anos == {2023, 2024, 2025, 2026}
    assert len(pedidos) == 2 * 4
    # O PL 1843/2022 foi apresentado em 2022: o arquivo de 2022 nem é lido.
    assert "PL 1843/2022" not in por_identificacao(documento)
    assert "PL 3871/2024" in por_identificacao(documento)


def test_ano_minimo_no_futuro_falha_antes_de_baixar_qualquer_arquivo(transporte, agora, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('comissoes = ["CE"]\nano_minimo = 2027\n', encoding="utf-8")

    codigo = main(["--config", str(config), "--saida", str(tmp_path / "a.json")],
                  transporte=transporte, agora=agora)  # fmt: skip

    assert codigo == 1
    assert transporte.pedidos == []


# --- US5: repetibilidade e meta ------------------------------------------------------------

ORDEM_DO_META = [
    "versao_formato", "gerado_em", "dados_camara_em", "comissoes", "ano_minimo", "anos_lidos",
    "total_itens", "total_por_comissao", "deputados_novo_em_exercicio",
]  # fmt: skip


def bytes_gerados(config, transporte, agora, tmp_path, nome="atual.json"):
    saida = tmp_path / nome
    executar(config, transporte, agora, saida)
    return saida.read_bytes()


def sem_gerado_em(documento):
    copia = json.loads(json.dumps(documento))
    copia["meta"].pop("gerado_em")
    return copia


def test_duas_execucoes_com_a_mesma_entrada_geram_arquivos_identicos(config, agora, tmp_path):
    primeiro = bytes_gerados(config, TransporteFalso(), agora, tmp_path, "a.json")
    segundo = bytes_gerados(config, TransporteFalso(), agora, tmp_path, "b.json")

    assert primeiro == segundo


def test_no_mesmo_dia_so_o_momento_de_geracao_muda(config, agora, tmp_path):
    depois = agora.replace(hour=11, minute=30)  # ainda dentro das 36 horas das fixtures

    a = json.loads(bytes_gerados(config, TransporteFalso(), agora, tmp_path, "a.json"))
    b = json.loads(bytes_gerados(config, TransporteFalso(), depois, tmp_path, "b.json"))

    assert a["meta"]["gerado_em"] == "2026-10-18T09:00:00-03:00"
    assert b["meta"]["gerado_em"] == "2026-10-18T11:30:00-03:00"
    assert sem_gerado_em(a) == sem_gerado_em(b)


def test_em_outro_dia_so_o_parado_ha_muda(config, agora, tmp_path):
    # As fixtures são de 17/10; no dia seguinte elas passariam de 36 horas. Fixamos o
    # Last-Modified para isolar o efeito do relógio.
    def transporte_fixo():
        transporte = TransporteFalso()
        for nome in MANIFESTO["arquivos"]:
            transporte.last_modified[nome] = datetime(2026, 10, 18, 10, 0, tzinfo=UTC)
        return transporte

    amanha = agora + timedelta(days=1)

    a = json.loads(bytes_gerados(config, transporte_fixo(), agora, tmp_path, "a.json"))
    b = json.loads(bytes_gerados(config, transporte_fixo(), amanha, tmp_path, "b.json"))

    for item in a["itens"] + b["itens"]:
        item.pop("parado_ha_dias")
    assert sem_gerado_em(a) == sem_gerado_em(b)


def test_meta_traz_origem_e_parametros_na_ordem_do_contrato(documento):
    meta = documento["meta"]

    assert list(meta) == ORDEM_DO_META
    assert meta["versao_formato"] == 1
    assert meta["comissoes"] == ["CE", "CREDN"]
    assert meta["ano_minimo"] == 2003
    assert meta["anos_lidos"] == [2003, 2026]
    assert meta["total_itens"] == len(documento["itens"])
    assert list(meta["total_por_comissao"]) == ["CE", "CREDN"]


def test_dados_camara_em_e_o_last_modified_mais_antigo(documento):
    mais_antigo = min(
        parsedate_to_datetime(a["last_modified"]).astimezone(UTC)
        for a in MANIFESTO["arquivos"].values()
    )

    assert documento["meta"]["dados_camara_em"] == mais_antigo.isoformat(timespec="seconds")
    assert documento["meta"]["dados_camara_em"].endswith("+00:00")


def test_meta_lista_os_deputados_do_novo_usados_ordenados_por_id(documento):
    assert documento["meta"]["deputados_novo_em_exercicio"] == [
        {"id": 156190, "nome": "Marcel van Hattem"},
        {"id": 204365, "nome": "Gilson Marques"},
        {"id": 204455, "nome": "Luiz Lima"},
        {"id": 204528, "nome": "Adriana Ventura"},
        {"id": 220633, "nome": "Ricardo Salles"},
    ]


def test_invariantes_do_contrato(documento):
    meta, itens = documento["meta"], documento["itens"]

    assert meta["total_itens"] == len(itens) > 0
    assert sum(meta["total_por_comissao"].values()) == meta["total_itens"]
    assert len({i["id"] for i in itens}) == len(itens)
    for item in itens:
        assert item["link"] and item["etiquetas"]
        assert item["comissao"] in meta["comissoes"]
        if item["principal_nao_localizada"]:
            assert item["apensado_a"] is None
    ordem = [(i["ultimo_status_em"], i["id"]) for i in itens]
    assert ordem == sorted(ordem)
