"""As fixtures e os construtores da AVI seguem os contratos (nunca divergem dos validadores)."""

import json
from pathlib import Path

import aviso_sinteticos as a
from aviso_gerar_fixtures import RAIZ, arquivos
from monitor_comissoes import mudancas as mud
from monitor_comissoes import retratos
from monitor_comissoes.saida import serializar
from monitor_comissoes.status import ler_status

TELEGRAM = RAIZ / "telegram"


def test_fixtures_versionadas_sao_as_que_o_gerador_grava():
    for caminho, texto in arquivos().items():
        assert caminho.read_text(encoding="utf-8") == texto, caminho


def test_cada_cenario_passa_nos_validadores_dos_contratos(tmp_path):
    for nome, cenario in a.cenarios().items():
        retratos.ler(serializar(cenario["atual"]), f"{nome}/atual.json")
        status = tmp_path / f"{nome}.json"
        status.write_text(serializar(cenario["status"]), encoding="utf-8")
        assert ler_status(status) is not None
        if cenario["mudancas"] is not None:
            mud.validar_arquivo(cenario["mudancas"])


def test_o_completo_tem_um_evento_de_cada_tipo_nas_duas_comissoes():
    documento = a.completo()

    assert {e["tipo"] for e in documento["eventos"]} == set(mud.TIPOS)
    assert {e["comissao"] for e in documento["eventos"]} == {"CE", "CREDN"}
    assert len(documento["ressalvas"]) == 1


def test_muitos_eventos_distribui_em_rodizio_e_valida():
    documento = a.muitos_eventos(7)

    assert [e["comissao"] for e in documento["eventos"]] == ["CE", "CREDN"] * 3 + ["CE"]
    assert documento["meta"]["total_eventos"] == 7


def test_o_atual_do_cenario_tem_dois_itens_sem_principal_localizada():
    itens = a.atual()["itens"]

    assert sum(1 for i in itens if i["principal_nao_localizada"]) == 2


def test_respostas_da_bot_api_seguem_o_formato_publicado_e_nao_trazem_segredo():
    for arquivo in sorted(TELEGRAM.glob("*.json")):
        corpo = json.loads(arquivo.read_text(encoding="utf-8"))
        assert isinstance(corpo["ok"], bool), arquivo
        if not corpo["ok"]:
            assert isinstance(corpo["error_code"], int) and corpo["description"], arquivo
        assert "bot" not in arquivo.read_text(encoding="utf-8").lower().replace("bot was", "")


def test_fixture_de_429_traz_retry_after():
    curto = json.loads((TELEGRAM / "erro-429.json").read_text(encoding="utf-8"))
    longo = json.loads((TELEGRAM / "erro-429-longo.json").read_text(encoding="utf-8"))

    assert curto["parameters"]["retry_after"] == 3
    assert longo["parameters"]["retry_after"] == 600


def test_os_caminhos_dos_cenarios_existem():
    nomes = {p.name for p in Path(RAIZ).iterdir() if p.is_dir()}

    assert set(a.cenarios()) | {"telegram"} == nomes
