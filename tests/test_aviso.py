"""Orquestração do aviso diário (AVI): tipo da mensagem, envio e falhas visíveis."""

import shutil
from datetime import datetime

import pytest

import aviso_sinteticos as a
from aviso_gerar_fixtures import RAIZ
from monitor_comissoes.aviso import Caminhos, executar_envio, montar_mensagem_do_dia
from monitor_comissoes.config import Config
from monitor_comissoes.erros import FalhaDeEnvio
from monitor_comissoes.estoque import BRASILIA
from monitor_comissoes.resumo import LIMITE, tamanho
from monitor_comissoes.saida import serializar
from monitor_comissoes.telegram import ClienteTelegram
from test_telegram import CHAT, TOKEN, Rede, http_erro, ok

CONFIG = Config(("CE", "CREDN"), 2003)
AGORA = datetime(2026, 10, 20, 7, 17, tzinfo=BRASILIA)
AMBIENTE = {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": CHAT}


def preparar(tmp_path, cenario: str) -> Caminhos:
    """Copia um cenário de tests/fixtures/aviso/ para `tmp_path` e devolve os caminhos."""
    shutil.copytree(RAIZ / cenario, tmp_path, dirs_exist_ok=True)
    return Caminhos.ao_lado_de(tmp_path / "atual.json")


def gravar(caminho, documento):
    caminho.write_text(serializar(documento), encoding="utf-8")


class ClienteFalso:
    def __init__(self, falha: Exception | None = None):
        self.enviados: list[str] = []
        self.falha = falha

    def enviar(self, texto: str) -> None:
        if self.falha:
            raise self.falha
        self.enviados.append(texto)


def fabrica(cliente):
    chamadas = []

    def criar(token, chat_id):
        chamadas.append((token, chat_id))
        return cliente

    criar.chamadas = chamadas
    return criar


def rodar(caminhos, cliente, ambiente=AMBIENTE, agora=AGORA):
    return executar_envio(caminhos, CONFIG, lambda: agora, ambiente, fabrica(cliente))


def dados(caminhos):
    """Os bytes de todos os arquivos de dados (para provar que nada foi tocado)."""
    raiz = caminhos.atual.parent
    return {
        str(p.relative_to(raiz)): p.read_bytes()
        for p in sorted(raiz.rglob("*"))
        if p.is_file() and p.name != "envio.json"
    }


# --- Caminhos -----------------------------------------------------------------------------------


def test_caminhos_ficam_ao_lado_do_atual(tmp_path):
    caminhos = Caminhos.ao_lado_de(tmp_path / "data" / "atual.json")

    assert caminhos.status == tmp_path / "data" / "status.json"
    assert caminhos.mudancas == tmp_path / "data" / "mudancas"
    assert caminhos.envio == tmp_path / "data" / "envio.json"


def test_caminhos_aceitam_substituicoes(tmp_path):
    caminhos = Caminhos.ao_lado_de(tmp_path / "atual.json", status=tmp_path / "outro.json")

    assert caminhos.status == tmp_path / "outro.json"


# --- decisão do tipo (T014) ----------------------------------------------------------------------


def test_status_ok_do_dia_gera_mensagem_normal(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    mensagem = montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date())

    assert mensagem.tipo == "normal" and mensagem.dia == "2026-10-20"
    assert mensagem.texto.startswith("Monitor de comissões · dados de 20/10 · 105 itens")


def test_status_de_falha_do_dia_gera_erro_com_o_motivo(tmp_path):
    caminhos = preparar(tmp_path, "falha")

    mensagem = montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date())

    assert mensagem.tipo == "erro" and mensagem.dia == "2026-10-20"
    assert "falhou: a Câmara não atualizou os arquivos [arquivos_desatualizados]" in mensagem.texto


def test_falha_sem_retrato_bom_diz_que_nao_ha_dados_bons(tmp_path):
    caminhos = preparar(tmp_path, "sem-retrato")

    assert montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date()).texto.endswith(
        "Ainda não há dados bons."
    )


def test_sem_status_a_coleta_de_hoje_nao_rodou(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    caminhos.status.unlink()

    mensagem = montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date())

    assert mensagem.tipo == "erro"
    assert "Não há registro de coleta." in mensagem.texto


def test_status_de_outro_dia_a_coleta_de_hoje_nao_rodou(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    mensagem = montar_mensagem_do_dia(caminhos, CONFIG, datetime(2026, 10, 21, 7, 17).date())

    assert mensagem.tipo == "erro" and mensagem.dia == "2026-10-21"
    assert "A coleta de hoje (21/10) não rodou. Último registro: 20/10, ok." in mensagem.texto


def test_o_dia_vem_do_parametro_e_nao_do_relogio(tmp_path):
    caminhos = preparar(tmp_path, "completo")

    mensagem = montar_mensagem_do_dia(caminhos, CONFIG, datetime(2030, 1, 1).date())

    assert mensagem.dia == "2030-01-01"


@pytest.mark.parametrize(
    ("estragar", "motivo"),
    [
        ("sem_mudancas", "2026-10-20.json"),
        ("versao", "versao_formato"),
        ("data", "difere da data_referencia"),
        ("retrato", "dados_camara_em"),
        ("sem_link", "link"),
        ("lixo", "JSON"),
    ],
)
def test_entrada_incoerente_falha_sem_mensagem(tmp_path, estragar, motivo):
    caminhos = preparar(tmp_path, "completo")
    arquivo = caminhos.mudancas / "2026-10-20.json"
    documento = a.completo()
    if estragar == "sem_mudancas":
        arquivo.unlink()
    elif estragar == "versao":
        documento["meta"]["versao_formato"] = 9
        gravar(arquivo, documento)
    elif estragar == "data":
        gravar(arquivo, a.mudancas(dia="2026-10-19"))
    elif estragar == "retrato":
        gravar(caminhos.status, a.status_ok(dados_camara_em="2026-10-20T05:00:00+00:00"))
    elif estragar == "sem_link":
        documento["eventos"][0]["link"] = ""
        gravar(arquivo, documento)
    else:
        arquivo.write_text("{ lixo", encoding="utf-8")

    with pytest.raises(FalhaDeEnvio, match=motivo):
        montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date())


def test_status_invalido_falha_sem_mensagem(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    caminhos.status.write_text("{ lixo", encoding="utf-8")

    with pytest.raises(FalhaDeEnvio, match="status"):
        montar_mensagem_do_dia(caminhos, CONFIG, AGORA.date())


# --- envio (T015) --------------------------------------------------------------------------------


def test_envio_com_sucesso_imprime_ok_e_sai_com_zero(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso()
    criar = fabrica(cliente)

    codigo = executar_envio(caminhos, CONFIG, lambda: AGORA, AMBIENTE, criar)

    saida = capsys.readouterr()
    assert codigo == 0
    assert saida.out.startswith("OK: mensagem normal de 20/10 enviada (")
    assert saida.out.rstrip().endswith("caracteres)")
    assert len(cliente.enviados) == 1 and tamanho(cliente.enviados[0]) <= LIMITE
    assert criar.chamadas == [(TOKEN, CHAT)]
    assert saida.err == ""


def test_mensagem_de_erro_tambem_e_enviada(tmp_path, capsys):
    caminhos = preparar(tmp_path, "falha")
    cliente = ClienteFalso()

    assert rodar(caminhos, cliente) == 0

    assert cliente.enviados[0].startswith("⚠ ERRO")
    assert capsys.readouterr().out.startswith("OK: mensagem de erro de 20/10 enviada (")


@pytest.mark.parametrize("faltando", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"])
@pytest.mark.parametrize("vazia", [False, True])
def test_variavel_ausente_ou_vazia_falha_citando_o_nome(tmp_path, capsys, faltando, vazia):
    caminhos = preparar(tmp_path, "completo")
    ambiente = (
        {**AMBIENTE, faltando: ""}
        if vazia
        else {k: v for k, v in AMBIENTE.items() if k != faltando}
    )
    cliente = ClienteFalso()

    codigo = rodar(caminhos, cliente, ambiente)

    saida = capsys.readouterr()
    assert codigo == 1 and cliente.enviados == []
    assert f"FALHA [envio]: variável {faltando} ausente" in saida.err
    assert TOKEN not in saida.err and CHAT not in saida.err


@pytest.mark.parametrize(
    ("codigo_http", "fixture", "trecho"),
    [(400, "erro-400.json", "400"), (401, "erro-401.json", "401"), (403, "erro-403.json", "403")],
)
def test_recusa_da_bot_api_falha_com_codigo_e_descricao(
    tmp_path, capsys, codigo_http, fixture, trecho
):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteTelegram(
        TOKEN, CHAT, abrir=Rede(http_erro(codigo_http, fixture)), dormir=lambda s: None
    )

    codigo = executar_envio(caminhos, CONFIG, lambda: AGORA, AMBIENTE, lambda t, c: cliente)

    erro = capsys.readouterr().err
    assert codigo == 1
    assert erro.startswith("FALHA [envio]: ") and trecho in erro
    assert TOKEN not in erro and CHAT not in erro


def test_bot_api_fora_do_ar_depois_das_tres_tentativas_sai_com_um(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    rede = Rede(*[http_erro(502, None, b"{}") for _ in range(3)])
    cliente = ClienteTelegram(TOKEN, CHAT, abrir=rede, dormir=lambda s: None)

    codigo = executar_envio(caminhos, CONFIG, lambda: AGORA, AMBIENTE, lambda t, c: cliente)

    assert codigo == 1 and len(rede.pedidos) == 3
    assert "3 tentativas" in capsys.readouterr().err


def test_envio_de_ponta_a_ponta_com_a_bot_api_simulada(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    rede = Rede(ok())
    cliente = ClienteTelegram(TOKEN, CHAT, abrir=rede, dormir=lambda s: None)

    codigo = executar_envio(caminhos, CONFIG, lambda: AGORA, AMBIENTE, lambda t, c: cliente)

    assert codigo == 0 and len(rede.pedidos) == 1


def test_falha_de_envio_nao_toca_em_nenhum_arquivo_de_dados(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    antes = dados(caminhos)

    rodar(caminhos, ClienteFalso(FalhaDeEnvio("a Bot API recusou")))

    assert dados(caminhos) == antes


def test_sucesso_tambem_nao_toca_nos_arquivos_de_coleta(tmp_path):
    caminhos = preparar(tmp_path, "completo")
    antes = dados(caminhos)

    rodar(caminhos, ClienteFalso())

    assert dados(caminhos) == antes


def test_entrada_incoerente_sai_com_um_sem_enviar(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    (caminhos.mudancas / "2026-10-20.json").unlink()
    cliente = ClienteFalso()

    codigo = rodar(caminhos, cliente)

    assert codigo == 1 and cliente.enviados == []
    assert "FALHA [envio]: " in capsys.readouterr().err


def test_excecao_inesperada_tambem_sai_com_um_sem_vazar_o_token(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")
    cliente = ClienteFalso(RuntimeError(f"estourou com {TOKEN} e {CHAT}"))

    codigo = rodar(caminhos, cliente)

    erro = capsys.readouterr().err
    assert codigo == 1 and "RuntimeError" in erro
    assert TOKEN not in erro and CHAT not in erro


def test_o_token_nunca_aparece_na_saida_de_um_envio_bem_sucedido(tmp_path, capsys):
    caminhos = preparar(tmp_path, "completo")

    rodar(caminhos, ClienteFalso())

    saida = capsys.readouterr()
    assert TOKEN not in saida.out + saida.err and CHAT not in saida.out + saida.err
