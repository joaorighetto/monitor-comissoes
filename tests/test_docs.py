"""O documento do risco de 60 dias existe e traz fonte, data e conclusão (AGE, FR-026, SC-008)."""

from pathlib import Path

DOCUMENTO = Path(__file__).parent.parent / "docs" / "agendamento-60-dias.md"


def texto() -> str:
    return DOCUMENTO.read_text(encoding="utf-8")


def test_traz_os_links_oficiais_e_a_frase_da_regra():
    conteudo = texto()

    assert (
        "https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows"
        in conteudo
    )
    assert (
        "https://docs.github.com/en/actions/using-workflows/disabling-and-enabling-a-workflow"
        in conteudo
    )
    assert (
        "scheduled workflows are automatically disabled when no repository activity "
        "has occurred in 60 days"
    ) in conteudo


def test_traz_a_data_da_consulta_a_conclusao_e_as_mitigacoes():
    conteudo = texto()

    assert "2026-10-18" in conteudo
    assert "## Conclusão" in conteudo
    assert "## Mitigações" in conteudo
    assert "nenhuma foi implementada" in conteudo


def test_registra_a_decisao_do_mantenedor_com_as_datas_de_45_e_55_dias():
    conteudo = texto()

    assert "## Decisão do mantenedor (2026-10-18)" in conteudo
    assert "lembrete a cada 45 dias" in conteudo.lower()
    assert "2026-12-02" in conteudo
    assert "2026-12-12" in conteudo
