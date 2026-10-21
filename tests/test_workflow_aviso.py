"""Verificação textual do workflow do aviso (AVI). Não substitui a execução real (quickstart)."""

import re

from test_workflow import RAIZ, WORKFLOW, blocos, usos

AVISO = RAIZ / ".github" / "workflows" / "aviso-diario.yml"


def texto() -> str:
    return AVISO.read_text(encoding="utf-8")


def passo_de_envio() -> str:
    conteudo = texto()
    return conteudo[conteudo.index("- name: Enviar e registrar") :]


def test_agendamento_diario_as_1017_utc_que_e_0717_de_brasilia():
    assert 'cron: "17 10 * * *"' in texto()


def test_disparo_manual_sem_entradas():
    conteudo = texto()

    assert "workflow_dispatch:" in conteudo
    assert "inputs:" not in conteudo


def test_nao_ha_gatilho_de_push_nem_de_pull_request():
    gatilhos = texto().split("jobs:")[0]

    assert not re.search(r"^\s*push:", gatilhos, re.MULTILINE)
    assert not re.search(r"^\s*pull_request:", gatilhos, re.MULTILINE)


def test_usa_o_mesmo_grupo_de_concorrencia_da_coleta_sem_cancelar():
    def grupo(conteudo):
        return re.search(r"concurrency:\s*\n\s*group:\s*(\S+)", conteudo).group(1)

    assert grupo(texto()) == grupo(WORKFLOW.read_text(encoding="utf-8")) == "coleta-diaria"
    assert blocos(texto(), "concurrency") == [["group: coleta-diaria", "cancel-in-progress: false"]]


def test_permissao_de_escrita_so_para_o_conteudo():
    assert blocos(texto(), "permissions") == [["contents: write"]]


def test_tem_tempo_limite():
    assert re.search(r"timeout-minutes:\s*\d+", texto())


def test_os_pins_das_acoes_sao_os_mesmos_da_coleta():
    aviso, coleta = usos(AVISO), usos(WORKFLOW)

    assert set(aviso) == {"actions/checkout", "astral-sh/setup-uv"}
    for acao, linha in aviso.items():
        assert linha == coleta[acao]


def test_segredos_so_em_env_e_vindos_de_secrets():
    conteudo = texto()

    assert "TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}" in conteudo
    assert "TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}" in conteudo
    env = blocos(conteudo, "env")
    assert env and all(
        linha.startswith("TELEGRAM_") and "${{ secrets." in linha
        for bloco in env
        for linha in bloco
        if not linha.startswith("#")
    )


def test_nenhuma_interpolacao_dentro_do_script():
    for bloco in blocos(texto(), "run"):
        assert not any("${{" in linha for linha in bloco)
    scripts = re.findall(r"run: \|\n((?:[ ]{10,}.*\n?)+)", texto())
    assert scripts and not any("${{" in s for s in scripts)


def test_o_script_nao_imprime_nem_ecoa_os_segredos():
    script = passo_de_envio()

    assert not re.search(r"echo[^\n]*TELEGRAM", script)
    assert "set -x" not in texto() and "set -o xtrace" not in texto()


def test_guarda_o_codigo_commita_so_o_registro_e_sai_com_o_codigo():
    script = passo_de_envio()

    assert "set +e" in script and "codigo=$?" in script and 'exit "$codigo"' in script
    assert "git checkout -- data/envio.json 2>/dev/null || true" in script
    assert re.findall(r"git add\s+(\S+)", script) == ["data/envio.json"]
    assert "git pull --rebase" in script and script.count("git push") == 2
    assert "monitor_comissoes.aviso mensagem" in script
    assert "monitor_comissoes.aviso enviar" in script


def test_o_commit_so_acontece_quando_o_registro_mudou():
    script = passo_de_envio()

    assert "git status --porcelain -- data/envio.json" in script
    assert script.index("git status --porcelain") < script.index("git commit")


def test_nao_toca_nos_arquivos_da_coleta():
    conteudo = texto()

    for proibido in ("data/atual.json", "data/status.json", "data/anterior.json", "data/mudancas"):
        assert proibido not in conteudo


def test_executa_o_python_do_venv():
    assert ".venv/bin/python -m monitor_comissoes.aviso enviar" in texto()
