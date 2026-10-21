"""O PRODUCT.md registra as decisões da página pública (PAG; emendas do plan.md)."""

from pathlib import Path

PRODUCT = Path(__file__).parent.parent / "PRODUCT.md"


def texto() -> str:
    return PRODUCT.read_text(encoding="utf-8")


def secao(inicio: str, fim: str) -> str:
    conteudo = texto()
    return conteudo[conteudo.index(inicio) : conteudo.index(fim)]


def test_a_publicacao_e_por_workflow_proprio_ao_fim_da_coleta():
    pagina = secao("### 6.2 Página pública", "## 7. Falhar de forma visível")

    assert "**Publicação.**" in pagina
    assert "workflow próprio" in pagina
    assert "ao fim de toda execução da coleta (com sucesso ou falha)" in pagina
    assert "Nada gerado é commitado." in pagina


def test_a_faixa_de_erro_diz_o_que_cada_data_significa():
    pagina = secao("### 6.2 Página pública", "## 7. Falhar de forma visível")

    assert "o primeiro DD/MM é o dia da execução que falhou" in pagina
    assert "o segundo, a data dos últimos dados bons" in pagina


def test_sem_arquivo_de_mudancas_do_dia_os_numeros_dizem_sem_comparacao_ainda():
    pagina = secao("### 6.2 Página pública", "## 7. Falhar de forma visível")

    assert '"sem comparação ainda", nunca zero' in pagina


def test_os_sete_dias_e_o_teto_por_dia_estao_descritos():
    pagina = secao("### 6.2 Página pública", "## 7. Falhar de forma visível")

    assert "7 dias de calendário que terminam no dia do retrato" in pagina
    assert "Os 20 primeiros eventos de cada dia ficam abertos" in pagina
    assert "sem perder nenhum" in pagina


def test_autor_sem_partido_aparece_so_com_o_nome():
    pagina = secao("### 6.2 Página pública", "## 7. Falhar de forma visível")

    assert "só o nome, quando o autor não tem partido" in pagina


def test_as_restricoes_tecnicas_registram_o_workflow_e_a_copia_do_ds():
    restricoes = texto()[texto().index("## 10. Restrições técnicas") :]

    assert "publicada por workflow próprio ao fim da coleta (§6.2)" in restricoes
    assert "src/monitor_comissoes/pagina/estatico/" in restricoes
    assert "onde o repositório do portfólio não existe" in restricoes


def test_o_bloco_de_limites_traz_os_limites_do_leitor_e_diz_o_que_ficou_fora():
    pagina = secao("### 6.2 Página pública", "## 7. Falhar de forma visível")

    assert "os limites da seção 8 que valem para quem lê a lista" in pagina
    assert "relógio do aparelho" in pagina
    assert "Ficam fora o arquivamento e o volume da coleta" in pagina
