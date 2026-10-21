"""Os ativos copiados do DS: sem URL externa, fontes relativas e regras de acessibilidade."""

import re
from pathlib import Path

ESTATICO = Path(__file__).parent.parent / "src" / "monitor_comissoes" / "pagina" / "estatico"
FONTES = (
    "ibm-plex-mono-latin-400-normal.woff2",
    "ibm-plex-mono-latin-500-normal.woff2",
    "ibm-plex-mono-latin-600-normal.woff2",
    "schibsted-grotesk-latin-wght-normal.woff2",
)


def css() -> str:
    return (ESTATICO / "estilo.css").read_text(encoding="utf-8")


def test_o_css_nao_tem_url_externa():
    assert "http://" not in css()
    assert "https://" not in css()
    assert "@import" not in css()


def test_toda_fonte_usa_caminho_relativo():
    urls = re.findall(r"url\(\s*[\"']?([^\"')]+)", css())

    assert urls, "o CSS deveria declarar as fontes"
    assert all(u.startswith("fontes/") for u in urls), urls
    assert not any(u.startswith("/") for u in urls)


def test_as_quatro_fontes_existem_e_estao_declaradas():
    for nome in FONTES:
        assert (ESTATICO / "fontes" / nome).stat().st_size > 1000, nome
        assert f"fontes/{nome}" in css()


def test_os_tokens_azuis_claro_e_escuro_estao_presentes():
    texto = css()

    assert "--accent: #1d4fb8" in texto
    assert "--accent: #86abff" in texto
    assert "prefers-color-scheme: dark" in texto
    assert 'data-theme="dark"' in texto
    assert "--touch-min: 44px" in texto


def test_chips_tem_area_de_toque_foco_e_rolagem_propria():
    texto = css()
    chip = re.search(r"\.pf-chip \{[^}]*\}", texto).group(0)
    chips = re.search(r"\.pf-chips \{[^}]*\}", texto).group(0)

    assert "min-height: 44px" in chip
    assert "overflow-x: auto" in chips
    assert ".pf-chip:focus-visible" in texto
    assert 'aria-pressed="true"' in texto


def test_nenhum_foco_e_removido_sem_substituto():
    texto = css()

    assert ":focus-visible" in texto
    assert not re.search(r"outline:\s*(none|0)\b", texto)


def test_o_leiame_registra_origem_e_data_da_copia():
    leiame = (ESTATICO / "LEIAME.md").read_text(encoding="utf-8")

    assert "../Portfolio/design-system" in leiame
    assert "2026-10-20" in leiame
    assert "tokens.azul.css" in leiame


def bloco_da_pagina() -> str:
    texto = css()
    return texto[texto.index("a página (não vem do DS") :]


def test_os_estilos_da_pagina_so_usam_tokens_do_ds_nenhuma_cor_de_estado():
    bloco = bloco_da_pagina()

    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", bloco)
    assert "rgb(" not in bloco and "hsl(" not in bloco
    assert ".faixa" in bloco


def test_os_chips_do_ds_estao_no_css_da_pagina():
    texto = css()

    assert re.search(r"\.pf-chip\[aria-pressed=\"true\"\] \{[^}]*var\(--accent\)", texto)
    assert re.search(r"\.pf-chip:hover[^{]*\{[^}]*var\(--accent-soft\)", texto)


def test_a_pagina_nao_forca_rolagem_horizontal_no_corpo():
    bloco = bloco_da_pagina()

    assert "overflow-x: scroll" not in bloco
    assert not re.search(r"\bbody\s*\{[^}]*overflow-x", css())
    assert "min-width: 0" in bloco  # itens de grid que quebram texto longo


def test_links_de_apensado_tem_area_de_toque_de_44px():
    bloco = bloco_da_pagina()

    regra = re.search(r"\.item-dados a, \.evento-apensado a \{[^}]*\}", bloco).group(0)

    assert "min-height: var(--touch-min)" in regra
