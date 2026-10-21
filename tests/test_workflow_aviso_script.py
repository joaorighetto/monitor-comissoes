"""Executa de verdade o script do passo "Enviar e registrar" do workflow do aviso (AVI).

Sem rede e sem GitHub: um remoto bare local, um clone de trabalho e um Python falso em
`.venv/bin/python` que grava (ou não) o `data/envio.json` e sai com o código escolhido. Cobre o que
o teste textual não pega: a ordem do `git`, o primeiro dia, a falha e o remoto adiantado.
"""

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "aviso-diario.yml"

pytestmark = pytest.mark.skipif(
    not all(shutil.which(c) for c in ("bash", "git")), reason="precisa de bash e git"
)

PYTHON_FALSO = """#!/bin/bash
echo "$@" >> "$FAKE_LOG"
case "$3" in
  enviar)
    case "$FAKE_MODO" in
      ok)
        mkdir -p data
        echo '{"envio": "hoje"}' > data/envio.json
        exit 0 ;;
      ja) exit 0 ;;
      falha) exit 1 ;;
      suja)
        mkdir -p data
        echo '{"envio": "sujo"}' > data/envio.json
        exit 1 ;;
    esac ;;
  mensagem) echo "aviso: teste" ;;
esac
"""


def script_do_passo() -> str:
    linhas = WORKFLOW.read_text(encoding="utf-8").splitlines()
    inicio = next(
        i for i, linha in enumerate(linhas) if linha.strip() == "- name: Enviar e registrar"
    )
    run = next(i for i in range(inicio, len(linhas)) if linhas[i].strip() == "run: |")
    recuo = len(linhas[run]) - len(linhas[run].lstrip())
    corpo = []
    for linha in linhas[run + 1 :]:
        if linha.strip() and len(linha) - len(linha.lstrip()) <= recuo:
            break
        corpo.append(linha)
    return textwrap.dedent("\n".join(corpo)) + "\n"


def git(*argumentos, cwd):
    resultado = subprocess.run(
        ["git", *argumentos], cwd=cwd, capture_output=True, text=True, check=True
    )
    return resultado.stdout.strip()


def configurar(pasta: Path):
    git("config", "user.name", "github-actions[bot]", cwd=pasta)
    git("config", "user.email", "bot@example.invalid", cwd=pasta)
    git("config", "commit.gpgsign", "false", cwd=pasta)


class Ambiente:
    def __init__(self, raiz: Path, com_envio_previo: bool):
        self.raiz = raiz
        self.remoto = raiz / "remoto.git"
        self.trabalho = raiz / "trabalho"
        self.temporario = raiz / "runner-temp"
        self.temporario.mkdir()
        git("init", "--bare", "-b", "main", str(self.remoto), cwd=raiz)
        self.trabalho.mkdir()
        git("init", "-q", "-b", "main", cwd=self.trabalho)
        configurar(self.trabalho)
        (self.trabalho / "LEIA.md").write_text("semente\n", encoding="utf-8")
        if com_envio_previo:
            (self.trabalho / "data").mkdir()
            (self.trabalho / "data" / "envio.json").write_text('{"envio": "ontem"}\n')
        git("add", "-A", cwd=self.trabalho)
        git("commit", "-q", "-m", "semente", cwd=self.trabalho)
        git("remote", "add", "origin", str(self.remoto), cwd=self.trabalho)
        git("push", "-q", "-u", "origin", "main", cwd=self.trabalho)
        python = self.trabalho / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_text(PYTHON_FALSO, encoding="utf-8")
        python.chmod(0o755)
        (self.trabalho / ".git" / "info" / "exclude").write_text(".venv/\n", encoding="utf-8")
        self.log = raiz / "chamadas.log"

    def rodar(self, modo: str):
        script = self.raiz / "passo.sh"
        script.write_text(script_do_passo(), encoding="utf-8")
        ambiente = {
            **os.environ,
            "FAKE_MODO": modo,
            "FAKE_LOG": str(self.log),
            "GITHUB_REF_NAME": "main",
            "RUNNER_TEMP": str(self.temporario),
        }
        # Como o Actions executa `shell: bash`.
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
            cwd=self.trabalho,
            env=ambiente,
            capture_output=True,
            text=True,
        )

    def no_remoto(self, caminho: str) -> str | None:
        resultado = subprocess.run(
            ["git", "--git-dir", str(self.remoto), "show", f"main:{caminho}"],
            capture_output=True,
            text=True,
        )
        return resultado.stdout if resultado.returncode == 0 else None

    def arquivos_do_ultimo_commit(self) -> list[str]:
        saida = git(
            "--git-dir", str(self.remoto), "show", "--name-only", "--format=", "main", cwd=self.raiz
        )
        return sorted(saida.splitlines())

    def mensagem_do_ultimo_commit(self) -> str:
        return git("--git-dir", str(self.remoto), "log", "-1", "--format=%s", "main", cwd=self.raiz)

    def commits_no_remoto(self) -> int:
        return int(git("--git-dir", str(self.remoto), "rev-list", "--count", "main", cwd=self.raiz))

    def chamadas(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def com_envio(tmp_path):
    return Ambiente(tmp_path, com_envio_previo=True)


@pytest.fixture
def primeiro_dia(tmp_path):
    return Ambiente(tmp_path, com_envio_previo=False)


def test_sucesso_commita_so_o_registro_com_a_mensagem_do_cli_e_empurra(com_envio):
    resultado = com_envio.rodar("ok")

    assert resultado.returncode == 0, resultado.stderr
    assert com_envio.arquivos_do_ultimo_commit() == ["data/envio.json"]
    assert com_envio.mensagem_do_ultimo_commit() == "aviso: teste"
    assert com_envio.no_remoto("data/envio.json") == '{"envio": "hoje"}\n'


def test_o_registro_de_antes_e_guardado_para_a_mensagem_do_commit(com_envio):
    com_envio.rodar("ok")

    antes = com_envio.temporario / "envio-antes.json"
    assert antes.read_text() == '{"envio": "ontem"}\n'
    chamada = next(c for c in com_envio.chamadas() if " mensagem " in f" {c} ")
    assert "--antes " in chamada and chamada.endswith("envio-antes.json")


def test_primeiro_dia_sem_registro_no_git_funciona(primeiro_dia):
    resultado = primeiro_dia.rodar("ok")

    assert resultado.returncode == 0, resultado.stderr
    assert primeiro_dia.arquivos_do_ultimo_commit() == ["data/envio.json"]
    assert not (primeiro_dia.temporario / "envio-antes.json").exists()


def test_ja_enviado_nao_commita_nada_e_termina_verde(com_envio):
    antes = com_envio.commits_no_remoto()

    resultado = com_envio.rodar("ja")

    assert resultado.returncode == 0, resultado.stderr
    assert com_envio.commits_no_remoto() == antes


def test_falha_de_envio_nao_commita_e_termina_vermelho(com_envio):
    antes = com_envio.commits_no_remoto()

    resultado = com_envio.rodar("falha")

    assert resultado.returncode == 1
    assert com_envio.commits_no_remoto() == antes


def test_falha_que_deixou_o_registro_sujo_restaura_o_que_o_git_tem(com_envio):
    antes = com_envio.commits_no_remoto()

    resultado = com_envio.rodar("suja")

    assert resultado.returncode == 1
    assert (com_envio.trabalho / "data" / "envio.json").read_text() == '{"envio": "ontem"}\n'
    assert com_envio.commits_no_remoto() == antes


def test_falha_no_primeiro_dia_nao_tropeca_na_falta_do_registro(primeiro_dia):
    resultado = primeiro_dia.rodar("falha")

    assert resultado.returncode == 1
    assert "pathspec" not in resultado.stderr


def test_remoto_adiantado_nao_impede_o_commit_do_registro(com_envio):
    outro = com_envio.raiz / "outro"
    git("clone", "-q", str(com_envio.remoto), str(outro), cwd=com_envio.raiz)
    configurar(outro)
    (outro / "OUTRO.md").write_text("chegou antes\n", encoding="utf-8")
    git("add", "-A", cwd=outro)
    git("commit", "-q", "-m", "alguém empurrou", cwd=outro)
    git("push", "-q", "origin", "main", cwd=outro)
    antes = com_envio.commits_no_remoto()

    resultado = com_envio.rodar("ok")

    assert resultado.returncode == 0, resultado.stderr
    assert com_envio.commits_no_remoto() == antes + 1
    assert com_envio.arquivos_do_ultimo_commit() == ["data/envio.json"]
    assert com_envio.no_remoto("OUTRO.md") == "chegou antes\n"
