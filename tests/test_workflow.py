"""Verificação textual do workflow (AGE). Não substitui a execução real no GitHub (quickstart)."""

import re
from pathlib import Path

RAIZ = Path(__file__).parent.parent
WORKFLOW = RAIZ / ".github" / "workflows" / "coleta-diaria.yml"
CI = RAIZ / ".github" / "workflows" / "ci.yml"


def texto() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def usos(arquivo: Path) -> dict[str, str]:
    """Mapa ação -> linha `uses:` completa (com o pin), de um workflow."""
    achados = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        casado = re.search(r"uses:\s*(\S+?)@\S+", linha)
        if casado:
            achados[casado.group(1)] = linha.strip()
    return achados


# --- US1 ------------------------------------------------------------------------------------------


def test_agendamento_diario_as_0637_utc():
    assert 'cron: "37 6 * * *"' in texto()


def test_disparo_manual_com_a_entrada_aceitar_variacao():
    conteudo = texto()

    assert "workflow_dispatch:" in conteudo
    assert "aceitar_variacao:" in conteudo


def test_nao_ha_gatilho_de_push_nem_de_pull_request():
    gatilhos = texto().split("jobs:")[0]

    assert not re.search(r"^\s*push:", gatilhos, re.MULTILINE)
    assert not re.search(r"^\s*pull_request:", gatilhos, re.MULTILINE)


def blocos(conteudo: str, chave: str) -> list[list[str]]:
    """Linhas filhas (mais indentadas) de cada ocorrência de `chave:` no texto do workflow."""
    linhas = conteudo.splitlines()
    achados = []
    for i, linha in enumerate(linhas):
        if linha.strip() == f"{chave}:":
            recuo = len(linha) - len(linha.lstrip())
            filhas = []
            for seguinte in linhas[i + 1 :]:
                if seguinte.strip() and len(seguinte) - len(seguinte.lstrip()) <= recuo:
                    break
                if seguinte.strip():
                    filhas.append(seguinte.strip())
            achados.append(filhas)
    return achados


def test_permissao_so_de_escrita_em_conteudo_e_timeout_de_150_minutos():
    conteudo = texto()

    assert blocos(conteudo, "permissions") == [["contents: write"]]
    assert "timeout-minutes: 150" in conteudo


def test_usa_os_mesmos_pins_de_checkout_e_setup_uv_do_ci():
    do_workflow, do_ci = usos(WORKFLOW), usos(CI)

    for acao in ("actions/checkout", "astral-sh/setup-uv"):
        assert acao in do_workflow
        assert do_workflow[acao] == do_ci[acao]


def test_instala_pelo_lock_e_chama_o_modulo_da_execucao_diaria():
    conteudo = texto()

    assert "uv sync --locked" in conteudo
    assert "python -m monitor_comissoes.diaria executar" in conteudo
    assert "github-actions[bot]" in conteudo


def test_nao_usa_segredos():
    assert "secrets." not in texto()
