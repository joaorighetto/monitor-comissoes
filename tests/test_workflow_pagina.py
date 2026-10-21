"""Verificação textual do workflow de publicação da página (PAG). Não substitui o deploy real."""

import re

from test_workflow import RAIZ, WORKFLOW, blocos, usos

PAGINA = RAIZ / ".github" / "workflows" / "publicar-pagina.yml"
ACOES_DE_PAGES = (
    "actions/configure-pages",
    "actions/upload-pages-artifact",
    "actions/deploy-pages",
)


def texto() -> str:
    return PAGINA.read_text(encoding="utf-8")


def codigo() -> str:
    """O workflow sem as linhas de comentário."""
    linhas = [linha for linha in texto().splitlines() if not linha.strip().startswith("#")]
    return "\n".join(linhas)


def posicao(trecho: str) -> int:
    conteudo = texto()
    assert trecho in conteudo, trecho
    return conteudo.index(trecho)


def test_nome_do_workflow():
    assert texto().startswith("name: Publicar página\n")


def test_dispara_ao_fim_de_toda_coleta_diaria_e_manualmente():
    conteudo = texto()

    assert blocos(conteudo, "workflow_run") == [
        ['workflows: ["Coleta diária"]', "types: [completed]"]
    ]
    assert "workflow_dispatch:" in conteudo


def test_o_nome_da_coleta_confere_com_o_workflow_da_coleta():
    assert "name: Coleta diária" in WORKFLOW.read_text(encoding="utf-8")


def test_publica_tambem_depois_de_coleta_em_falha_sem_filtrar_pela_conclusao():
    conteudo = texto()

    assert "conclusion" not in conteudo
    assert "success" not in conteudo


def test_so_aceita_execucao_da_coleta_no_branch_padrao_ou_disparo_manual():
    condicao = re.search(r"^\s+if:\s*(.+)$", texto(), re.MULTILINE).group(1)

    assert "github.event_name == 'workflow_dispatch'" in condicao
    assert "github.event.workflow_run.head_branch == github.event.repository.default_branch" in (
        condicao
    )
    assert "||" in condicao


def test_nao_ha_gatilho_de_push_pull_request_nem_agendamento_proprio():
    gatilhos = texto().split("jobs:")[0]

    assert not re.search(r"^\s*push:", gatilhos, re.MULTILINE)
    assert not re.search(r"^\s*pull_request:", gatilhos, re.MULTILINE)
    assert "schedule:" not in gatilhos and "cron:" not in gatilhos


def test_permissoes_exatas():
    assert blocos(texto(), "permissions") == [["contents: read", "pages: write", "id-token: write"]]


def test_concorrencia_propria_sem_cancelar():
    assert blocos(texto(), "concurrency") == [["group: pagina", "cancel-in-progress: false"]]
    coleta = re.search(r"group:\s*(\S+)", WORKFLOW.read_text(encoding="utf-8")).group(1)
    assert coleta != "pagina"


def test_ambiente_github_pages_e_tempo_limite():
    conteudo = texto()

    assert blocos(conteudo, "environment") == [
        ["name: github-pages", "url: ${{ steps.deploy.outputs.page_url }}"]
    ]
    assert re.search(r"timeout-minutes:\s*\d+", conteudo)


def test_checkout_sem_ref_para_pegar_o_commit_do_bot_e_nao_o_head_sha_da_coleta():
    assert "ref:" not in codigo()
    assert "head_sha" not in codigo()


def test_checkout_e_setup_uv_iguais_aos_da_coleta():
    pagina, coleta = usos(PAGINA), usos(WORKFLOW)

    for acao in ("actions/checkout", "astral-sh/setup-uv"):
        assert pagina[acao] == coleta[acao]


def test_acoes_de_pages_fixadas_por_sha_com_a_versao_em_comentario():
    pagina = usos(PAGINA)

    for acao in ACOES_DE_PAGES:
        assert re.fullmatch(rf"(- )?uses: {acao}@[0-9a-f]{{40}} # v\d+\.\d+\.\d+", pagina[acao]), (
            acao
        )


def test_so_usa_as_acoes_esperadas():
    assert set(usos(PAGINA)) == {"actions/checkout", "astral-sh/setup-uv", *ACOES_DE_PAGES}


def test_instala_com_uv_sync_locked_e_gera_a_pagina_na_pasta_site():
    conteudo = texto()

    assert "uv sync --locked" in conteudo
    assert ".venv/bin/python -m monitor_comissoes.pagina gerar --saida site" in conteudo


def test_o_gerar_roda_antes_do_upload_e_do_deploy():
    gerar = posicao("monitor_comissoes.pagina gerar")
    configurar = posicao("actions/configure-pages")
    enviar = posicao("actions/upload-pages-artifact")
    publicar = posicao("actions/deploy-pages")

    assert gerar < configurar < enviar < publicar


def test_upload_da_pasta_site_e_deploy_com_id_para_o_endereco():
    conteudo = texto()

    assert "path: site" in conteudo
    assert "id: deploy" in conteudo


def test_nao_usa_segredo_nem_commita_nada():
    conteudo = texto()

    assert "secrets." not in conteudo
    assert not re.search(r"git (commit|push|add|pull)", conteudo)


def test_registra_a_data_da_consulta_das_versoes_das_acoes():
    assert "2026-10-20" in texto()


def test_o_endereco_publicado_vai_para_o_log_por_variavel_de_ambiente():
    conteudo = texto()

    assert "PAGINA_URL: ${{ steps.deploy.outputs.page_url }}" in conteudo
    assert 'echo "Página publicada em $PAGINA_URL"' in conteudo
