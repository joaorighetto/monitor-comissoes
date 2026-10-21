"""As fixtures e os construtores da PAG seguem os contratos (nunca divergem dos validadores)."""

import json

import pagina_sinteticos as p
from monitor_comissoes import mudancas as mud
from monitor_comissoes.status import ler_status
from pagina_gerar_fixtures import RAIZ, arquivos

CAMPOS_DO_ITEM = (
    "id",
    "identificacao",
    "ementa",
    "link",
    "autores",
    "etiquetas",
    "comissao",
    "situacao",
    "parado_ha_dias",
    "apensado_a",
    "principal_nao_localizada",
    "relator",
    "relator_indeterminado",
)


def test_fixtures_derivadas_sao_as_que_o_gerador_grava():
    for caminho, texto in arquivos().items():
        assert caminho.read_text(encoding="utf-8") == texto, caminho


def test_o_retrato_real_traz_os_campos_que_a_pagina_usa():
    retrato = p.retrato_real()

    assert retrato["meta"]["versao_formato"] == 2
    assert retrato["meta"]["total_itens"] == len(retrato["itens"]) == 105
    assert retrato["meta"]["total_por_comissao"] == {"CE": 96, "CREDN": 9}
    for item in retrato["itens"]:
        for campo in CAMPOS_DO_ITEM:
            assert campo in item, (item["id"], campo)


def test_o_formato_4_so_difere_na_versao():
    real = p.retrato_real()
    quatro = json.loads((RAIZ / "atual-formato-4.json").read_text(encoding="utf-8"))

    assert quatro["meta"]["versao_formato"] == 4
    quatro["meta"]["versao_formato"] = 2
    assert quatro == real


def test_status_passam_no_validador_da_age(tmp_path):
    for nome in (
        "status-ok.json",
        "status-falha.json",
        "status-falha-sem-retrato.json",
        "status-retrato-outro.json",
    ):
        assert ler_status(RAIZ / nome) is not None, nome


def test_status_ok_e_coerente_com_o_retrato_real():
    status = ler_status(RAIZ / "status-ok.json")
    meta = p.retrato_real()["meta"]

    assert status["resultado"] == "ok"
    assert status["ultimo_retrato_bom"]["dados_camara_em"] == meta["dados_camara_em"]
    assert status["ultimo_retrato_bom"]["gerado_em"] == meta["gerado_em"]


def test_status_de_falha_mantem_o_retrato_bom_do_real():
    falha = ler_status(RAIZ / "status-falha.json")
    meta = p.retrato_real()["meta"]

    assert falha["resultado"] == "falha"
    assert falha["data_referencia"] == "2026-10-21"
    assert falha["ultimo_retrato_bom"]["dados_camara_em"] == meta["dados_camara_em"]
    assert ler_status(RAIZ / "status-falha-sem-retrato.json")["ultimo_retrato_bom"] is None


def test_arquivos_de_mudancas_passam_em_validar_arquivo():
    pastas = ("mudancas", "mudancas-teto", "mudancas-invalida-fora-da-janela")
    for pasta in pastas:
        for caminho in (RAIZ / pasta).glob("*.json"):
            if pasta == "mudancas-invalida-fora-da-janela" and caminho.name == "2026-10-10.json":
                continue  # corrompido de propósito
            mud.validar_arquivo(json.loads(caminho.read_text(encoding="utf-8")))


def test_o_arquivo_do_dia_20_traz_os_seis_tipos_e_o_retrato_do_real():
    documento = json.loads((RAIZ / "mudancas" / "2026-10-20.json").read_text(encoding="utf-8"))

    assert {e["tipo"] for e in documento["eventos"]} == set(mud.TIPOS)
    assert (
        documento["meta"]["retrato"]["dados_camara_em"]
        == p.retrato_real()["meta"]["dados_camara_em"]
    )
    assert any(e["tramitacoes"] for e in documento["eventos"])


def test_faltam_de_proposito_os_dias_17_e_15():
    nomes = {c.name for c in (RAIZ / "mudancas").glob("*.json")}

    assert nomes == {"2026-10-20.json", "2026-10-19.json", "2026-10-18.json", "2026-10-16.json"}


def test_a_pasta_do_teto_tem_25_eventos():
    documento = json.loads((RAIZ / "mudancas-teto" / "2026-10-20.json").read_text(encoding="utf-8"))

    assert len(documento["eventos"]) == 25


def test_o_arquivo_corrompido_nao_e_json():
    texto = (RAIZ / "mudancas-invalida-fora-da-janela" / "2026-10-10.json").read_text(
        encoding="utf-8"
    )

    try:
        json.loads(texto)
    except ValueError:
        return
    raise AssertionError("o arquivo corrompido deveria ser inválido")


def test_construtores_geram_entradas_gravaveis(tmp_path):
    retrato = p.retrato_com([p.item_completo(id=1), p.item_completo(id=2, comissao="CREDN")])
    entradas = p.gravar_entradas(
        tmp_path,
        retrato,
        p.status_ok(),
        {p.DIA: p.arquivo_de_mudancas(p.DIA, [p.evento("entrou")], dia_anterior="2026-10-19")},
    )

    assert json.loads(entradas.atual.read_text(encoding="utf-8")) == retrato
    assert ler_status(entradas.status)["resultado"] == "ok"
    assert (entradas.mudancas / f"{p.DIA}.json").exists()
