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

    assert item["etiquetas"] == ["autoria NOVO", "relatoria NOVO"]
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
        assert set(item["etiquetas"]) <= {"autoria NOVO", "autor hoje no NOVO", "relatoria NOVO"}
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


# --- REL US1: relatoria NOVO atual (PRODUCT.md §5.4) ------------------------------------------


def test_pl_4501_2023_entra_so_por_relatoria_novo(documento):
    # Autoria de Duarte Jr. (PSB); o relator atual na CE é Luiz Lima, hoje do NOVO.
    item = por_identificacao(documento)["PL 4501/2023"]

    assert item["etiquetas"] == ["relatoria NOVO"]
    assert item["comissao"] == "CE"
    assert item["relator"]["id"] == 204455
    assert item["relator"]["nome"] == "Luiz Lima"
    assert item["relator"]["partido_hoje"] == "NOVO"
    assert item["relator"]["designado_em"] == "2025-04-09T00:00:00"
    assert item["relator"]["fonte"].endswith("/2388105")
    assert item["relator_indeterminado"] is None


def test_pl_937_2022_fica_fora_porque_o_relator_do_novo_devolveu_a_materia(documento):
    assert "PL 937/2022" not in por_identificacao(documento)


def test_pl_3514_2023_fica_fora_porque_o_relator_do_novo_era_da_cespo(documento):
    assert "PL 3514/2023" not in por_identificacao(documento)


def test_pl_1843_2022_tem_autoria_e_relatoria(documento):
    item = por_identificacao(documento)["PL 1843/2022"]

    assert item["etiquetas"] == ["autoria NOVO", "relatoria NOVO"]
    assert item["relator"]["nome"] == "Adriana Ventura"
    assert item["relator"]["partido_hoje"] == "NOVO"


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

    # Apensado herda o relator da principal: a relatora do PL 1843/2022 é do NOVO (REL, US2).
    assert item["etiquetas"] == ["autor hoje no NOVO", "relatoria NOVO"]
    assert item["relator"]["nome"] == "Adriana Ventura"
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
    transporte.tramitacoes_sinteticas = True  # tramitações reais só existem para a CE e a CREDN
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
    transporte.tramitacoes_sinteticas = True  # sem os anos antigos, as referências são outras
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
    assert meta["versao_formato"] == 2
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


# --- REL US2: apensados herdam o relator da principal ---------------------------------------


def test_apensados_reais_de_uma_raiz_com_relatora_do_novo_entram_com_o_relator_da_raiz(
    documento,
):
    itens = [i for i in documento["itens"] if i["apensado_a"]]
    raiz = por_identificacao(documento)["PL 3961/2004"]
    apensados = [i for i in itens if i["apensado_a"]["id"] == raiz["id"]]

    assert raiz["relator"]["nome"] == "Adriana Ventura"
    assert len(apensados) > 10  # a raiz tem dezenas de apensados na CE (fixtures reais)
    for item in apensados:
        assert item["etiquetas"] == ["relatoria NOVO"]
        assert item["relator"] == raiz["relator"]
        assert item["comissao"] == raiz["comissao"]
        assert item["situacao"] == raiz["situacao"]


def test_a_referencia_compartilhada_e_lida_uma_vez_so(config, transporte, agora, tmp_path):
    gerar(config, transporte, agora, tmp_path)

    tramitacoes = [u for u in transporte.pedidos if u.endswith("/tramitacoes")]
    assert len(tramitacoes) == len(set(tramitacoes))
    deputados = [u for u in transporte.pedidos if "/api/v2/deputados/" in u]
    assert len(deputados) == len(set(deputados))


def test_apensado_cuja_raiz_esta_fora_da_lista_continua_fora_mesmo_com_relator(documento):
    # PL 4047/2019: o autor é hoje do NOVO, mas a raiz da cadeia está na CFT.
    assert "PL 4047/2019" not in por_identificacao(documento)


# --- REL US3: relator e partido de hoje em todo item -----------------------------------------

NOVO_EM_EXERCICIO_IDS = {156190, 204365, 204455, 204528, 220633}


def test_relator_de_outro_partido_mostra_o_partido_de_hoje_sem_relatoria_novo(documento):
    item = por_identificacao(documento)["PL 3871/2024"]

    assert item["etiquetas"] == ["autor hoje no NOVO"]
    assert item["relator"] == {
        "id": 220560,
        "nome": "Thiago de Joaldo",
        "partido_hoje": "REPUBLICANOS",
        "designado_em": "2026-04-27T17:13:00",
        "fonte": "https://www.camara.leg.br/propostas-legislativas/2461936",
    }


def test_item_so_de_autoria_tambem_traz_o_relator(documento):
    item = por_identificacao(documento)["PL 5594/2020"]

    assert "relatoria NOVO" not in item["etiquetas"]
    assert item["relator"]["id"] == 178929
    assert item["relator"]["partido_hoje"]


def test_item_sem_relator_atual_traz_relator_nulo(documento):
    # PL 648/2024 tem autoria do NOVO, mas o relator devolveu a matéria (507).
    item = por_identificacao(documento)["PL 648/2024"]

    assert item["relator"] is None
    assert item["relator_indeterminado"] is None


def test_relator_mostra_o_partido_de_hoje_e_nao_o_da_designacao(documento):
    # O despacho da designação registra o partido da época (Luiz Lima já foi do PL); o item
    # mostra o de hoje, que para quem está em exercício no NOVO vem da lista do dia.
    item = por_identificacao(documento)["PL 4501/2023"]

    assert item["relator"]["partido_hoje"] == "NOVO"
    assert item["relator"]["designado_em"] == "2025-04-09T00:00:00"


def test_fonte_do_relator_e_a_ficha_da_principal_no_apensado(documento):
    apensados = [i for i in documento["itens"] if i["apensado_a"] and i["relator"]]

    assert apensados
    for item in apensados:
        assert item["relator"]["fonte"] == item["apensado_a"]["link"]


def test_relator_do_novo_dispensa_consulta_e_os_demais_sao_consultados_uma_vez(
    config, transporte, agora, tmp_path
):
    documento = gerar(config, transporte, agora, tmp_path)

    consultados = {
        int(u.rsplit("/", 1)[1]) for u in transporte.pedidos if "/api/v2/deputados/" in u
    }
    relatores = {i["relator"]["id"] for i in documento["itens"] if i["relator"]}
    assert consultados == relatores - NOVO_EM_EXERCICIO_IDS
    assert relatores & NOVO_EM_EXERCICIO_IDS  # há relatores do NOVO no resultado


def test_nas_fixtures_reais_nenhum_item_fica_com_relator_indeterminado(documento):
    assert [i["identificacao"] for i in documento["itens"] if i["relator_indeterminado"]] == []


def test_tipo_de_relatoria_novo_numa_referencia_marca_so_o_item_e_a_coleta_termina(
    config, transporte, agora, tmp_path
):
    # Derivada: a API passa a registrar um tipo de tramitação de relatoria desconhecido no PL
    # 4501/2023, que só está na lista por relatoria (candidato sem etiqueta de autoria).
    def com_tipo_novo(corpo: bytes) -> bytes:
        documento = json.loads(corpo)
        ultimo = max(t["sequencia"] for t in documento["dados"])
        documento["dados"].append(
            {
                "sequencia": ultimo + 1,
                "dataHora": "2026-10-17T10:00",
                "siglaOrgao": "CE",
                "codTipoTramitacao": "9999",
                "descricaoTramitacao": "Relator(a) Substituído",
                "uriUltimoRelator": None,
            }
        )
        return json.dumps(documento).encode()

    transporte.transformar_json["tramitacoes/2388105"] = com_tipo_novo
    base = por_identificacao(gerar(config, TransporteFalso(), agora, tmp_path))

    documento = gerar(config, transporte, agora, tmp_path)

    item = por_identificacao(documento)["PL 4501/2023"]
    assert item["etiquetas"] == []
    assert item["relator"] is None
    assert "9999" in item["relator_indeterminado"]["motivo"]
    # Os demais itens não mudam.
    outros = {k: v for k, v in por_identificacao(documento).items() if k != "PL 4501/2023"}
    assert outros == {k: v for k, v in base.items() if k != "PL 4501/2023"}
    assert documento["meta"]["total_itens"] == len(base)
