"""Verificação textual do workflow da pauta (PAU). Não substitui a execução real (quickstart)."""

import re

from test_workflow import RAIZ, WORKFLOW, blocos, usos

PAUTA = RAIZ / ".github" / "workflows" / "checagem-pauta.yml"
AVISO = RAIZ / ".github" / "workflows" / "aviso-diario.yml"
CACHE = "actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9"
BRASILIA = -3


def texto() -> str:
    return PAUTA.read_text(encoding="utf-8")


def passo_de_checagem() -> str:
    conteudo = texto()
    return conteudo[conteudo.index("- name: Checar e registrar") :]


def linhas_do_passo() -> list[str]:
    return [linha.strip() for linha in passo_de_checagem().splitlines() if linha.strip()]


def crons(conteudo: str) -> list[tuple[int, int]]:
    """(hora, minuto) UTC de cada `cron` diário do workflow."""
    achados = re.findall(r'cron: "(\d+) (\d+) \* \* \*"', conteudo)
    assert len(achados) == len(re.findall(r"cron:", conteudo)), "só crons diários"
    return [(int(hora), int(minuto)) for minuto, hora in achados]


def em_brasilia(hora: int, minuto: int) -> int:
    """Minutos desde a meia-noite de Brasília."""
    return ((hora + BRASILIA) % 24) * 60 + minuto


def tempo_limite() -> int:
    return int(re.search(r"timeout-minutes:\s*(\d+)", texto()).group(1))


def test_tres_checagens_por_dia_e_nenhuma_outra():
    assert crons(texto()) == [(8, 47), (18, 17), (1, 47)]


def test_a_checagem_da_manha_termina_uma_hora_antes_do_aviso():
    [aviso] = crons(AVISO.read_text(encoding="utf-8"))
    [manha] = [c for c in crons(texto()) if em_brasilia(*c) < em_brasilia(*aviso)]

    assert em_brasilia(*manha) + tempo_limite() + 60 <= em_brasilia(*aviso)


def test_uma_checagem_depois_das_14h_e_outra_depois_das_22h_de_brasilia():
    horarios = [em_brasilia(*c) for c in crons(texto())]

    assert any(14 * 60 <= h < 22 * 60 for h in horarios)
    assert any(h >= 22 * 60 for h in horarios)


def test_disparo_manual_sem_entradas():
    conteudo = texto()

    assert "workflow_dispatch:" in conteudo
    assert "inputs:" not in conteudo


def test_nao_ha_gatilho_de_push_nem_de_pull_request():
    gatilhos = texto().split("jobs:")[0]

    assert not re.search(r"^\s*push:", gatilhos, re.MULTILINE)
    assert not re.search(r"^\s*pull_request:", gatilhos, re.MULTILINE)


def test_grupo_de_concorrencia_proprio_sem_cancelar():
    assert blocos(texto(), "concurrency") == [["group: pauta", "cancel-in-progress: false"]]
    assert "group: pauta" not in WORKFLOW.read_text(encoding="utf-8")


def test_permissao_de_escrita_so_para_o_conteudo_e_tempo_limite():
    assert blocos(texto(), "permissions") == [["contents: write"]]
    assert 0 < tempo_limite() <= 30


def test_os_pins_das_acoes_sao_os_mesmos_da_coleta():
    pauta, coleta = usos(PAUTA), usos(WORKFLOW)

    assert set(pauta) == {"actions/checkout", "astral-sh/setup-uv", "actions/cache/restore"}
    for acao in ("actions/checkout", "astral-sh/setup-uv"):
        assert pauta[acao] == coleta[acao]
    assert "uv sync --locked" in texto()


def test_restaura_o_indice_mais_recente_do_cache_antes_de_checar():
    conteudo = texto()
    inicio = conteudo.index(f"uses: {CACHE}")
    passo = conteudo[inicio : conteudo.index("- name:", inicio)]

    assert [linha.strip() for linha in blocos(passo, "with")[0]] == [
        "path: cache/indice-autoria.json",
        "key: indice-autoria-",
        "restore-keys: indice-autoria-",
    ]
    assert inicio < conteudo.index("- name: Checar e registrar")


def test_nao_usa_segredos_nem_interpola_no_script():
    assert "secrets." not in texto()
    assert "${{" not in passo_de_checagem()


def test_guarda_o_codigo_e_em_falha_desfaz_a_pasta_de_pautas():
    linhas = linhas_do_passo()

    assert ".venv/bin/python -m monitor_comissoes.pauta checar" in linhas
    assert "set +e" in linhas and "codigo=$?" in linhas and "set -e" in linhas
    se = linhas.index('if [ "$codigo" -ne 0 ]; then')
    assert linhas[se + 1 : se + 4] == [
        "git checkout -- data/pautas 2>/dev/null || true",
        "git clean -fdq -- data/pautas || true",
        "fi",
    ]


def test_status_sempre_adicionado_e_as_pautas_so_em_sucesso():
    linhas = linhas_do_passo()

    assert [linha for linha in linhas if linha.startswith("git add")] == [
        "git add data/status-pauta.json",
        "git add data/pautas",
    ]
    se = linhas.index('if [ "$codigo" -eq 0 ]; then')
    assert linhas[se + 1 : se + 3] == ["git add data/pautas", "fi"]
    assert linhas.index("git add data/status-pauta.json") < se


def test_commita_com_a_mensagem_da_pauta_empurra_e_devolve_o_codigo():
    linhas = linhas_do_passo()

    def comando(prefixo):
        return next(i for i, linha in enumerate(linhas) if linha.startswith(prefixo))

    assert "monitor_comissoes.pauta mensagem" in linhas[comando("git commit")]
    assert comando("git commit") < comando("git pull --rebase") < comando("git push")
    assert sum(linha.startswith("git push") for linha in linhas) == 2
    assert linhas[-1] == 'exit "$codigo"'


def test_nao_toca_nos_arquivos_da_coleta_nem_do_aviso():
    conteudo = texto()

    for proibido in (
        "data/atual.json",
        "data/status.json",
        "data/anterior.json",
        "data/mudancas",
        "data/envio.json",
    ):
        assert proibido not in conteudo
