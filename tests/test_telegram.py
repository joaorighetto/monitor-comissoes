"""Cliente da Bot API (AVI): `abrir` e `dormir` falsos e respostas de fixtures/aviso/telegram/."""

import http.client
import io
import json
import traceback
import urllib.error
from email.message import Message

import pytest

from aviso_gerar_fixtures import RAIZ
from monitor_comissoes.erros import FalhaDeEnvio
from monitor_comissoes.telegram import LIMITE_TENTATIVAS, ClienteTelegram

TOKEN = "111111:TOKEN-FALSO-DE-TESTE"
CHAT = "-1009999999999"
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


def fixture(nome: str) -> bytes:
    return (RAIZ / "telegram" / nome).read_bytes()


class Resposta:
    def __init__(self, corpo: bytes, status: int = 200):
        self.status = status
        self._corpo = io.BytesIO(corpo)

    def read(self, n=-1):
        return self._corpo.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def http_erro(codigo: int, nome_da_fixture: str | None, corpo: bytes | None = None):
    corpo = corpo if corpo is not None else fixture(nome_da_fixture)
    return urllib.error.HTTPError(URL, codigo, "erro", Message(), io.BytesIO(corpo))


class Rede:
    """`abrir` falso: cada chamada consome o próximo item (resposta ou exceção)."""

    def __init__(self, *roteiro):
        self.roteiro = list(roteiro)
        self.pedidos = []

    def __call__(self, requisicao, timeout=None):
        self.pedidos.append(requisicao)
        item = self.roteiro.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def cliente(rede):
    esperas = []
    return ClienteTelegram(TOKEN, CHAT, abrir=rede, dormir=esperas.append), esperas


def ok():
    return Resposta(fixture("ok.json"))


# --- envio ------------------------------------------------------------------------------------


def test_um_envio_faz_um_post_para_send_message():
    rede = Rede(ok())
    c, esperas = cliente(rede)

    c.enviar("Olá, grupo")

    assert len(rede.pedidos) == 1
    pedido = rede.pedidos[0]
    assert pedido.full_url == URL
    assert pedido.get_method() == "POST"
    assert pedido.get_header("Content-type") == "application/json"
    assert esperas == []


def test_corpo_tem_chat_texto_e_previa_desligada_e_nao_tem_parse_mode():
    rede = Rede(ok())
    c, _ = cliente(rede)
    texto = "PL 1/2024 — _a_ *b* [c](d) <e> & é ✓ 😀"

    c.enviar(texto)

    corpo = json.loads(rede.pedidos[0].data.decode("utf-8"))
    assert corpo == {
        "chat_id": CHAT,
        "text": texto,
        "link_preview_options": {"is_disabled": True},
    }
    assert "parse_mode" not in corpo


def test_so_um_envio_sem_getupdates_nem_outros_metodos():
    rede = Rede(ok())
    c, _ = cliente(rede)

    c.enviar("x")

    assert [p.full_url.rsplit("/", 1)[-1] for p in rede.pedidos] == ["sendMessage"]


# --- repetições -------------------------------------------------------------------------------


def test_429_espera_o_retry_after_e_repete():
    rede = Rede(http_erro(429, "erro-429.json"), ok())
    c, esperas = cliente(rede)

    c.enviar("x")

    assert len(rede.pedidos) == 2
    assert esperas == [3]


def test_429_com_espera_maior_que_60_segundos_falha_na_hora():
    rede = Rede(http_erro(429, "erro-429-longo.json"), ok())
    c, esperas = cliente(rede)

    with pytest.raises(FalhaDeEnvio, match="600"):
        c.enviar("x")

    assert len(rede.pedidos) == 1
    assert esperas == []


def test_5xx_repete_com_esperas_de_5_e_15_segundos_e_desiste_na_terceira():
    erro = b'{"ok": false, "error_code": 502, "description": "Bad Gateway"}'
    rede = Rede(http_erro(502, None, erro), http_erro(502, None, erro), http_erro(502, None, erro))
    c, esperas = cliente(rede)

    with pytest.raises(FalhaDeEnvio, match=r"3 tentativas.*502.*Bad Gateway"):
        c.enviar("x")

    assert len(rede.pedidos) == LIMITE_TENTATIVAS == 3
    assert esperas == [5, 15]


def test_5xx_seguido_de_sucesso_envia():
    rede = Rede(http_erro(500, None, b"{}"), ok())
    c, esperas = cliente(rede)

    c.enviar("x")

    assert len(rede.pedidos) == 2
    assert esperas == [5]


@pytest.mark.parametrize(
    "falha",
    [urllib.error.URLError("sem rota"), TimeoutError("lento"), ConnectionResetError("caiu")],
)
def test_erro_de_rede_repete_e_depois_envia(falha):
    rede = Rede(falha, ok())
    c, esperas = cliente(rede)

    c.enviar("x")

    assert len(rede.pedidos) == 2
    assert esperas == [5]


def test_erro_de_rede_nas_tres_tentativas_falha():
    rede = Rede(*[urllib.error.URLError("sem rota") for _ in range(3)])
    c, _ = cliente(rede)

    with pytest.raises(FalhaDeEnvio, match="3 tentativas"):
        c.enviar("x")


# --- recusas que não se repetem ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("codigo", "nome", "descricao"),
    [
        (400, "erro-400.json", "message is too long"),
        (401, "erro-401.json", "Unauthorized"),
        (403, "erro-403.json", "bot was kicked"),
    ],
)
def test_recusa_nao_repete_e_traz_codigo_e_descricao(codigo, nome, descricao):
    rede = Rede(http_erro(codigo, nome), ok())
    c, esperas = cliente(rede)

    with pytest.raises(FalhaDeEnvio) as erro:
        c.enviar("x")

    assert str(codigo) in str(erro.value) and descricao in str(erro.value)
    assert len(rede.pedidos) == 1
    assert esperas == []


def test_404_com_corpo_que_nao_e_json_falha_sem_repetir():
    rede = Rede(http_erro(404, None, b"<html>nao achou</html>"))
    c, _ = cliente(rede)

    with pytest.raises(FalhaDeEnvio, match="404"):
        c.enviar("x")

    assert len(rede.pedidos) == 1


def test_200_com_ok_false_falha_sem_repetir():
    rede = Rede(Resposta(fixture("erro-400.json")), ok())
    c, _ = cliente(rede)

    with pytest.raises(FalhaDeEnvio, match="message is too long"):
        c.enviar("x")

    assert len(rede.pedidos) == 1


@pytest.mark.parametrize("corpo", [b"nao e json", b"[]", b'{"result": {}}'])
def test_200_sem_json_ou_sem_ok_falha(corpo):
    c, _ = cliente(Rede(Resposta(corpo)))

    with pytest.raises(FalhaDeEnvio, match="resposta"):
        c.enviar("x")


# --- segredos ---------------------------------------------------------------------------------


def tudo_que_a_falha_mostra(erro: BaseException) -> str:
    return "\n".join(
        [str(erro), repr(erro), "".join(traceback.format_exception(erro))]
        + [str(a) for a in erro.args]
    )


def test_excecao_do_urllib_que_repete_a_url_nao_vaza_o_token():
    falha = urllib.error.URLError(f"falha ao abrir {URL} para o chat {CHAT}")
    c, _ = cliente(Rede(falha, falha, falha))

    with pytest.raises(FalhaDeEnvio) as erro:
        c.enviar("x")

    saida = tudo_que_a_falha_mostra(erro.value)
    assert TOKEN not in saida and CHAT not in saida
    assert "***" in saida


def test_descricao_do_telegram_que_repete_o_token_nao_vaza():
    corpo = json.dumps(
        {"ok": False, "error_code": 400, "description": f"chat {CHAT} bot{TOKEN} invalido"}
    ).encode()
    c, _ = cliente(Rede(http_erro(400, None, corpo)))

    with pytest.raises(FalhaDeEnvio) as erro:
        c.enviar("x")

    saida = tudo_que_a_falha_mostra(erro.value)
    assert TOKEN not in saida and CHAT not in saida


def test_repr_do_cliente_nao_mostra_credenciais():
    c, _ = cliente(Rede())

    assert TOKEN not in repr(c) and CHAT not in repr(c) and TOKEN not in str(c)


def test_nada_vai_para_stdout_ou_stderr(capsys):
    c, _ = cliente(Rede(ok()))

    c.enviar("x")

    saida = capsys.readouterr()
    assert saida.out == "" and saida.err == ""


@pytest.mark.parametrize(("token", "chat"), [("", CHAT), (TOKEN, ""), ("  ", CHAT)])
def test_credencial_vazia_e_erro_de_programacao(token, chat):
    with pytest.raises(ValueError, match="credencial"):
        ClienteTelegram(token, chat, abrir=Rede(), dormir=lambda s: None)


# --- revisão da rodada 1: caracteres de controle e exceções do http.client --------------------


@pytest.mark.parametrize("sufixo", ["\n", " ", "\t", "\r\n"])
def test_segredo_com_espaco_ou_controle_e_recusado_sem_mostrar_o_valor(sufixo):
    with pytest.raises(ValueError, match="espaço ou caractere de controle") as erro:
        ClienteTelegram(TOKEN + sufixo, CHAT, abrir=Rede(), dormir=lambda s: None)

    assert TOKEN not in str(erro.value)
    with pytest.raises(ValueError, match="espaço ou caractere de controle"):
        ClienteTelegram(TOKEN, CHAT + sufixo, abrir=Rede(), dormir=lambda s: None)


def test_invalid_url_do_http_client_nao_vaza_o_token_nem_na_forma_escapada():
    falha = http.client.InvalidURL(f"URL can't contain control characters. {URL!r} ({CHAT!r})")
    c, esperas = cliente(Rede(falha))

    with pytest.raises(FalhaDeEnvio) as erro:
        c.enviar("x")

    saida = tudo_que_a_falha_mostra(erro.value)
    assert TOKEN not in saida and CHAT not in saida and "InvalidURL" in saida
    assert esperas == []


def test_value_error_ao_montar_o_pedido_nao_vaza_o_token():
    c, _ = cliente(Rede(ValueError(f"url invalida {URL}")))

    with pytest.raises(FalhaDeEnvio) as erro:
        c.enviar("x")

    assert TOKEN not in tudo_que_a_falha_mostra(erro.value)


def test_resposta_interrompida_repete_e_depois_envia():
    c, esperas = cliente(Rede(http.client.IncompleteRead(b"par"), ok()))

    c.enviar("x")

    assert esperas == [5]


def test_filtro_troca_o_segredo_cru_e_o_escapado():
    from monitor_comissoes.telegram import sem_segredos

    segredo = "abc\ndef"

    assert (
        sem_segredos(f"cru {segredo} escapado {segredo!r}"[:-1], segredo, "")
        == "cru *** escapado '***"
    )
    assert sem_segredos("sem nada", "", "") == "sem nada"
