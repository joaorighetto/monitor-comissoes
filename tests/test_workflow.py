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


def test_permissao_so_de_escrita_em_conteudo_e_timeout_de_240_minutos():
    conteudo = texto()

    assert blocos(conteudo, "permissions") == [["contents: write"]]
    assert "timeout-minutes: 240" in conteudo


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


def test_a_coleta_roda_sob_timeout_no_python_do_venv():
    conteudo = texto()

    assert "timeout --kill-after=10m --signal=TERM 200m .venv/bin/python -m" in conteudo
    # 200 + 10 de kill-after tem de caber no teto do job (240), com folga para o commit
    assert "timeout-minutes: 240" in conteudo


def test_nao_usa_segredos():
    assert "secrets." not in texto()


# --- US2 ------------------------------------------------------------------------------------------


def passo_de_coleta() -> str:
    conteudo = texto()
    inicio = conteudo.index("python -m monitor_comissoes.diaria executar")
    return conteudo[inicio:]


def test_o_passo_guarda_o_codigo_de_saida_e_continua_para_registrar_a_falha():
    passo = passo_de_coleta()

    assert "set +e" in texto()
    assert "codigo=$?" in passo
    assert "set -e" in passo


def linhas_do_passo() -> list[str]:
    return [linha.strip() for linha in passo_de_coleta().splitlines() if linha.strip()]


def test_em_falha_restaura_cada_arquivo_de_dados_antes_de_commitar():
    linhas = linhas_do_passo()

    se = linhas.index('if [ "$codigo" -ne 0 ]; then')
    # Um `git checkout --` por caminho, cada um com `|| true`: um caminho que o Git não conhece
    # (primeiro dia, ou arquivo novo) faria o comando inteiro abortar se fosse tudo de uma vez.
    assert linhas[se + 1 : se + 6] == [
        "git checkout -- data/atual.json || true",
        "git checkout -- data/anterior.json || true",
        "git checkout -- data/mudancas || true",
        "git clean -fdq -- data/mudancas || true",
        "fi",
    ]


def test_status_e_sempre_adicionado_e_os_dados_so_no_ramo_de_sucesso():
    linhas = linhas_do_passo()

    assert [linha for linha in linhas if linha.startswith("git add")] == [
        "git add data/status.json",
        "git add data/atual.json",
        "git add data/mudancas",
        "git add data/anterior.json",
    ]
    se = linhas.index('if [ "$codigo" -eq 0 ]; then')
    assert linhas[se + 1 : se + 7] == [
        "git add data/atual.json",
        "git add data/mudancas",
        "if [ -e data/anterior.json ]; then",
        "git add data/anterior.json",
        "fi",
        "fi",
    ]
    assert linhas.index("git add data/status.json") < se


def test_o_passo_termina_com_o_codigo_da_coleta_depois_de_commit_e_push():
    linhas = linhas_do_passo()

    def comando(prefixo):
        return next(i for i, linha in enumerate(linhas) if linha.startswith(prefixo))

    assert comando("git commit") < comando("git pull --rebase") < comando("git push")
    assert comando("git push") < comando('exit "$codigo"')


# --- US3 ------------------------------------------------------------------------------------------


def test_entrada_aceitar_variacao_e_booleana_e_desligada_por_padrao():
    bloco = blocos(texto(), "aceitar_variacao")[0]

    assert "type: boolean" in bloco
    assert "default: false" in bloco


def test_a_confirmacao_so_chega_a_coleta_no_disparo_manual():
    conteudo = texto()

    assert "github.event_name == 'workflow_dispatch' && inputs.aceitar_variacao" in conteudo
    assert conteudo.count("--aceitar-variacao") == 1
    linhas = [linha.strip() for linha in conteudo.splitlines()]
    se = linhas.index('if [ "$ACEITAR_VARIACAO" = "true" ]; then')
    assert "--aceitar-variacao" in linhas[se + 1]


def test_a_entrada_nao_e_interpolada_dentro_do_script():
    conteudo = texto()
    inicio = conteudo.index("run: |\n          # Falha da coleta")
    fim = conteudo.find("\n      - ", inicio)  # o script vai até o passo seguinte, se houver

    assert "${{" not in conteudo[inicio : fim if fim != -1 else None]


# --- US5 ------------------------------------------------------------------------------------------


def test_duas_execucoes_nao_rodam_ao_mesmo_tempo():
    assert blocos(texto(), "concurrency") == [["group: coleta-diaria", "cancel-in-progress: false"]]


def test_gitignore_ignora_temporarios_em_qualquer_pasta_de_dados():
    linhas = (Path(__file__).parent.parent / ".gitignore").read_text(encoding="utf-8").splitlines()

    # Os temporários de `gravar_todos` ficam ao lado de cada destino, inclusive em data/mudancas/.
    assert "data/**/*.tmp" in linhas


# --- PAU ------------------------------------------------------------------------------------------


def test_salva_o_indice_de_autoria_no_cache_so_depois_da_coleta_com_sucesso():
    conteudo = texto()
    inicio = conteudo.index("uses: actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9")
    passo = conteudo[conteudo.rindex("- ", 0, inicio) :]

    assert conteudo.index("- name: Coleta e commit") < inicio
    assert "if: success()" in passo
    assert blocos(passo, "with")[0] == [
        "path: cache/indice-autoria.json",
        "key: indice-autoria-${{ github.run_id }}-${{ github.run_attempt }}",
    ]
