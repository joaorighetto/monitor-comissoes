"""Nenhum segredo do Telegram em arquivo versionado (AVI, constituição VI; FR-015).

Os tokens falsos dos testes (`111111:TOKEN-FALSO-DE-TESTE`) têm menos de 30 caracteres depois do
`:`, de propósito, para não casar com o formato de um token real de bot (`123456789:` + 35
caracteres). Se um teste precisar de um token falso maior, este teste vai acusá-lo.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).parent.parent
PASTAS = ("src", "tests", ".github", "data", "docs", "specs")
ARQUIVOS = ("config.toml", "pyproject.toml", "CLAUDE.md", "PRODUCT.md", "ROADMAP.md", ".gitignore")
IGNORAR = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".serena"}
SUFIXOS = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt", ".csv", ".js", ".css", ""}

TOKEN_DE_BOT = re.compile(r"(?<!\d)\d{6,}:[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_-])")
ATRIBUICAO = re.compile(r"TELEGRAM_(?:BOT_TOKEN|CHAT_ID)[ \t]*=[ \t]*[^\s\"'$]")


def arquivos_versionaveis():
    achados = [RAIZ / nome for nome in ARQUIVOS if (RAIZ / nome).exists()]
    for pasta in PASTAS:
        base = RAIZ / pasta
        if not base.exists():
            continue
        for caminho in base.rglob("*"):
            partes = set(caminho.relative_to(RAIZ).parts)
            if caminho.is_file() and not partes & IGNORAR and caminho.suffix in SUFIXOS:
                achados.append(caminho)
    return achados


def texto_de(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""  # as fixtures da Câmara não são UTF-8; nenhuma delas guarda token


def test_ha_arquivos_para_varrer():
    assert len(arquivos_versionaveis()) > 50


def test_nenhum_arquivo_traz_algo_com_cara_de_token_de_bot():
    achados = [
        f"{c.relative_to(RAIZ)}: {m.group(0)[:12]}..."
        for c in arquivos_versionaveis()
        for m in TOKEN_DE_BOT.finditer(texto_de(c))
    ]

    assert achados == []


def test_nenhum_arquivo_atribui_valor_as_variaveis_do_telegram():
    achados = [
        str(c.relative_to(RAIZ)) for c in arquivos_versionaveis() if ATRIBUICAO.search(texto_de(c))
    ]

    assert achados == []


def test_o_detector_acusa_um_token_de_formato_real():
    falso_longo = "123456789:" + "A" * 35

    assert TOKEN_DE_BOT.search(f"bot{falso_longo}/sendMessage")
    assert not TOKEN_DE_BOT.search("111111:TOKEN-FALSO-DE-TESTE")
    assert ATRIBUICAO.search("TELEGRAM_BOT_" + "TOKEN=abc")  # montado: o arquivo não se acusa
    assert not ATRIBUICAO.search("TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}")


def test_gitignore_exclui_o_env():
    linhas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in [linha.strip() for linha in linhas]


def test_o_codigo_nao_le_arquivo_env():
    achados = [
        str(c.relative_to(RAIZ))
        for c in (RAIZ / "src").rglob("*.py")
        if re.search(r"""["']\.env["']|dotenv""", texto_de(c))
    ]

    assert achados == []


def test_as_variaveis_do_telegram_so_aparecem_em_aviso_py():
    fora = [
        c.name
        for c in (RAIZ / "src").rglob("*.py")
        if "TELEGRAM_" in texto_de(c) and c.name != "aviso.py"
    ]

    assert fora == []
