"""Executa de verdade o script do passo "Coleta e commit" do workflow (AGE).

Sem rede e sem GitHub: um repositório remoto bare local, um clone de trabalho e um Python falso em
`.venv/bin/python` que grava (ou não) os arquivos e sai com o código escolhido. Cobre o que o
teste textual não pega: a ordem do `git`, o primeiro dia, a falha sem status e o remoto adiantado.
"""

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "coleta-diaria.yml"

pytestmark = pytest.mark.skipif(
    not all(shutil.which(c) for c in ("bash", "git", "timeout")),
    reason="precisa de bash, git e timeout",
)

PYTHON_FALSO = """#!/bin/bash
echo "$@" >> "$FAKE_LOG"
case "$3" in
  executar)
    case "$FAKE_MODO" in
      ok)
        mkdir -p data/mudancas
        echo '{"atual": "novo"}' > data/atual.json
        echo '{"mudancas": "novo"}' > data/mudancas/2000-01-01.json
        [ -n "$FAKE_ROTACIONA" ] && echo '{"anterior": "ontem-rotacionado"}' > data/anterior.json
        echo '{"status": "ok"}' > data/status.json
        exit 0 ;;
      falha)
        mkdir -p data
        [ -n "$FAKE_SUJAR_ATUAL" ] && echo '{"atual": "sujo"}' > data/atual.json
        if [ -n "$FAKE_SUJAR_TUDO" ]; then
          mkdir -p data/mudancas
          echo '{"anterior": "sujo"}' > data/anterior.json
          echo '{"mudancas": "sujo"}' > data/mudancas/2000-01-01.json
          echo '{"mudancas": "novo-e-sujo"}' > data/mudancas/2000-01-02.json
        fi
        echo '{"status": "falha"}' > data/status.json
        exit 1 ;;
      morre) exit 1 ;;
    esac ;;
  mensagem) echo "dados: teste $FAKE_MODO" ;;
esac
"""


def script_do_passo() -> str:
    linhas = WORKFLOW.read_text(encoding="utf-8").splitlines()
    inicio = next(i for i, linha in enumerate(linhas) if linha.strip() == "- name: Coleta e commit")
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


class Ambiente:
    def __init__(self, raiz: Path, com_dados_previos: bool):
        self.raiz = raiz
        self.remoto = raiz / "remoto.git"
        self.trabalho = raiz / "trabalho"
        git("init", "--bare", "-b", "main", str(self.remoto), cwd=raiz)
        self.trabalho.mkdir()
        self._configurar(self.trabalho)
        (self.trabalho / "LEIA.md").write_text("semente\n", encoding="utf-8")
        if com_dados_previos:
            (self.trabalho / "data").mkdir()
            (self.trabalho / "data" / "atual.json").write_text('{"atual": "ontem"}\n')
            (self.trabalho / "data" / "status.json").write_text('{"status": "ontem"}\n')
            (self.trabalho / "data" / "anterior.json").write_text('{"anterior": "anteontem"}\n')
            (self.trabalho / "data" / "mudancas").mkdir()
            (self.trabalho / "data" / "mudancas" / "1999-12-31.json").write_text('{"m": 1}\n')
            (self.trabalho / "data" / "mudancas" / "2000-01-01.json").write_text('{"m": 2}\n')
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

    @staticmethod
    def _configurar(pasta: Path):
        git("init", "-q", "-b", "main", cwd=pasta)
        git("config", "user.name", "github-actions[bot]", cwd=pasta)
        git("config", "user.email", "bot@example.invalid", cwd=pasta)
        git("config", "commit.gpgsign", "false", cwd=pasta)

    def rodar(
        self,
        modo: str,
        *,
        sujar_atual: bool = False,
        sujar_tudo: bool = False,
        rotaciona: bool = False,
        aceitar: str = "false",
    ):
        script = self.raiz / "passo.sh"
        script.write_text(script_do_passo(), encoding="utf-8")
        ambiente = {
            **os.environ,
            "FAKE_MODO": modo,
            "FAKE_LOG": str(self.log),
            "GITHUB_REF_NAME": "main",
            "ACEITAR_VARIACAO": aceitar,
        }
        if sujar_atual or sujar_tudo:
            ambiente["FAKE_SUJAR_ATUAL"] = "1"
        if sujar_tudo:
            ambiente["FAKE_SUJAR_TUDO"] = "1"
        if rotaciona:
            ambiente["FAKE_ROTACIONA"] = "1"
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


@pytest.fixture
def com_dados(tmp_path):
    return Ambiente(tmp_path, com_dados_previos=True)


@pytest.fixture
def primeiro_dia(tmp_path):
    return Ambiente(tmp_path, com_dados_previos=False)


def test_sucesso_commita_atual_status_e_o_arquivo_de_mudancas_e_empurra(com_dados):
    resultado = com_dados.rodar("ok")

    assert resultado.returncode == 0, resultado.stderr
    # Sem rotação, o anterior.json não muda e fica de fora do commit.
    assert com_dados.arquivos_do_ultimo_commit() == [
        "data/atual.json",
        "data/mudancas/2000-01-01.json",
        "data/status.json",
    ]
    assert com_dados.mensagem_do_ultimo_commit() == "dados: teste ok"
    assert com_dados.no_remoto("data/atual.json") == '{"atual": "novo"}\n'


def test_falha_commita_so_o_status_restaura_o_atual_e_termina_vermelho(com_dados):
    resultado = com_dados.rodar("falha", sujar_atual=True)

    assert resultado.returncode == 1
    assert com_dados.arquivos_do_ultimo_commit() == ["data/status.json"]
    assert com_dados.no_remoto("data/atual.json") == '{"atual": "ontem"}\n'
    assert com_dados.no_remoto("data/status.json") == '{"status": "falha"}\n'
    # O atual.json no disco também voltou ao que o Git tem.
    assert (com_dados.trabalho / "data" / "atual.json").read_text() == '{"atual": "ontem"}\n'
    assert com_dados.mensagem_do_ultimo_commit() == "dados: teste falha"


def test_falha_no_primeiro_dia_nao_tropeca_na_falta_do_atual(primeiro_dia):
    resultado = primeiro_dia.rodar("falha")

    assert resultado.returncode == 1
    assert primeiro_dia.arquivos_do_ultimo_commit() == ["data/status.json"]
    assert primeiro_dia.no_remoto("data/atual.json") is None


def test_python_que_morre_sem_gravar_o_status_deixa_o_workflow_vermelho_sem_commit(com_dados):
    antes = com_dados.commits_no_remoto()

    resultado = com_dados.rodar("morre")

    assert resultado.returncode != 0
    assert com_dados.commits_no_remoto() == antes


def test_python_que_morre_no_primeiro_dia_nao_commita_nada(primeiro_dia):
    antes = primeiro_dia.commits_no_remoto()

    resultado = primeiro_dia.rodar("morre")

    assert resultado.returncode != 0
    assert primeiro_dia.commits_no_remoto() == antes


def test_push_recusado_uma_vez_e_tentado_de_novo(com_dados):
    gancho = com_dados.remoto / "hooks" / "pre-receive"
    marca = com_dados.raiz / "ja-recusou"
    gancho.write_text(
        "#!/bin/bash\n"
        f'if [ ! -e "{marca}" ]; then touch "{marca}"; echo recusado >&2; exit 1; fi\n',
        encoding="utf-8",
    )
    gancho.chmod(0o755)

    resultado = com_dados.rodar("ok")

    assert resultado.returncode == 0, resultado.stderr
    assert marca.exists()  # o primeiro push foi mesmo recusado
    assert com_dados.no_remoto("data/atual.json") == '{"atual": "novo"}\n'


def test_push_recusado_duas_vezes_deixa_o_workflow_vermelho(com_dados):
    gancho = com_dados.remoto / "hooks" / "pre-receive"
    gancho.write_text("#!/bin/bash\necho recusado >&2\nexit 1\n", encoding="utf-8")
    gancho.chmod(0o755)
    antes = com_dados.commits_no_remoto()

    resultado = com_dados.rodar("ok")

    assert resultado.returncode != 0
    assert com_dados.commits_no_remoto() == antes


def test_remoto_adiantado_nao_impede_o_commit_do_bot(com_dados, tmp_path):
    outro = tmp_path / "outro"
    outro.mkdir()
    git("clone", "-q", str(com_dados.remoto), str(outro / "clone"), cwd=outro)
    clone = outro / "clone"
    git("config", "user.name", "pessoa", cwd=clone)
    git("config", "user.email", "pessoa@example.invalid", cwd=clone)
    git("config", "commit.gpgsign", "false", cwd=clone)
    (clone / "LEIA.md").write_text("mudou durante a execução\n", encoding="utf-8")
    git("commit", "-q", "-am", "alguém empurrou", cwd=clone)
    git("push", "-q", "origin", "main", cwd=clone)

    resultado = com_dados.rodar("ok")

    assert resultado.returncode == 0, resultado.stderr
    assert com_dados.commits_no_remoto() == 3  # semente, a da pessoa e a do bot
    assert com_dados.no_remoto("LEIA.md") == "mudou durante a execução\n"
    assert com_dados.no_remoto("data/atual.json") == '{"atual": "novo"}\n'


@pytest.mark.parametrize(("entrada", "passa"), [("true", True), ("false", False), ("", False)])
def test_a_confirmacao_so_vira_flag_quando_a_variavel_e_true(com_dados, entrada, passa):
    com_dados.rodar("ok", aceitar=entrada)

    chamadas = com_dados.log.read_text(encoding="utf-8")
    executar = next(linha for linha in chamadas.splitlines() if "executar" in linha)
    assert ("--aceitar-variacao" in executar) is passa


def test_sucesso_com_rotacao_commita_os_quatro_arquivos(com_dados):
    resultado = com_dados.rodar("ok", rotaciona=True)

    assert resultado.returncode == 0, resultado.stderr
    assert com_dados.arquivos_do_ultimo_commit() == [
        "data/anterior.json",
        "data/atual.json",
        "data/mudancas/2000-01-01.json",
        "data/status.json",
    ]
    assert com_dados.no_remoto("data/anterior.json") == '{"anterior": "ontem-rotacionado"}\n'


def test_sucesso_no_primeiro_dia_nao_tropeca_na_falta_do_anterior(primeiro_dia):
    resultado = primeiro_dia.rodar("ok")

    assert resultado.returncode == 0, resultado.stderr
    assert primeiro_dia.arquivos_do_ultimo_commit() == [
        "data/atual.json",
        "data/mudancas/2000-01-01.json",
        "data/status.json",
    ]
    assert primeiro_dia.no_remoto("data/anterior.json") is None


def test_falha_restaura_atual_e_anterior_e_os_arquivos_de_mudancas(com_dados):
    resultado = com_dados.rodar("falha", sujar_tudo=True)

    assert resultado.returncode == 1
    assert com_dados.arquivos_do_ultimo_commit() == ["data/status.json"]
    pasta = com_dados.trabalho / "data"
    assert (pasta / "atual.json").read_text() == '{"atual": "ontem"}\n'
    assert (pasta / "anterior.json").read_text() == '{"anterior": "anteontem"}\n'
    # O arquivo de mudanças do mesmo dia, já rastreado, volta ao que o Git tem.
    assert (pasta / "mudancas" / "2000-01-01.json").read_text() == '{"m": 2}\n'
    # O arquivo novo, ainda não rastreado, é descartado: nem no disco, nem no remoto.
    assert not (pasta / "mudancas" / "2000-01-02.json").exists()
    assert com_dados.no_remoto("data/mudancas/2000-01-02.json") is None
    assert com_dados.no_remoto("data/mudancas/1999-12-31.json") == '{"m": 1}\n'


def test_falha_no_primeiro_dia_descarta_a_pasta_de_mudancas_nova(primeiro_dia):
    resultado = primeiro_dia.rodar("falha", sujar_tudo=True)

    assert resultado.returncode == 1
    assert primeiro_dia.arquivos_do_ultimo_commit() == ["data/status.json"]
    assert not (primeiro_dia.trabalho / "data" / "mudancas").exists()  # o clean levou a pasta nova
    assert primeiro_dia.no_remoto("data/atual.json") is None
    assert primeiro_dia.no_remoto("data/anterior.json") is None
    assert primeiro_dia.no_remoto("data/mudancas/2000-01-02.json") is None
