"""Execução diária (AGE): caminho feliz, falhas, plausibilidade, tentativas e reexecução."""

import csv
import io
import json
from datetime import datetime, timedelta

import pytest

from conftest import TransporteFalso
from monitor_comissoes import diaria, status
from monitor_comissoes.coleta import coletar, executar
from monitor_comissoes.config import Config
from monitor_comissoes.diaria import main
from monitor_comissoes.erros import FONTE_INDISPONIVEL, FalhaDeColeta
from monitor_comissoes.estoque import BRASILIA as FUSO
from monitor_comissoes.saida import serializar

CONFIG_BASE = 'comissoes = ["CE", "CREDN"]\nano_minimo = 2003\n'


class Relogio:
    """Relógio de teste: devolve sempre o mesmo instante, ou avança `passo` a cada leitura."""

    def __init__(self, inicio: datetime, passo: timedelta = timedelta(0)):
        self.momento = inicio
        self.passo = passo
        self.leituras = 0

    def __call__(self) -> datetime:
        atual = self.momento
        self.momento += self.passo
        self.leituras += 1
        return atual


class Dormidas:
    """`dormir` falso: só registra os segundos pedidos."""

    def __init__(self):
        self.pedidos: list[float] = []

    def __call__(self, segundos: float) -> None:
        self.pedidos.append(segundos)


@pytest.fixture
def caminhos(tmp_path):
    (tmp_path / "config.toml").write_text(CONFIG_BASE, encoding="utf-8")
    return {
        "config": tmp_path / "config.toml",
        "atual": tmp_path / "data" / "atual.json",
        "status": tmp_path / "data" / "status.json",
    }


def executar_main(caminhos, transporte, relogio, dormir=None, *, aceitar=False):
    argumentos = [
        "executar",
        "--config",
        str(caminhos["config"]),
        "--atual",
        str(caminhos["atual"]),
        "--status",
        str(caminhos["status"]),
    ]
    if aceitar:
        argumentos.append("--aceitar-variacao")
    return main(argumentos, transporte=transporte, relogio=relogio, dormir=dormir or Dormidas())


def ler(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


# --- US1: caminho feliz ------------------------------------------------------------------------


def test_sucesso_grava_atual_identico_ao_da_coleta_e_status_ok(
    caminhos, transporte, agora, tmp_path
):
    esperado = tmp_path / "esperado" / "atual.json"
    executar(Config(("CE", "CREDN"), 2003), transporte, agora, esperado)
    coletado = coletar(Config(("CE", "CREDN"), 2003), transporte, agora)

    codigo = executar_main(caminhos, transporte, Relogio(agora))

    assert codigo == 0
    assert caminhos["atual"].read_text(encoding="utf-8") == esperado.read_text(encoding="utf-8")
    status = ler(caminhos["status"])
    meta = ler(caminhos["atual"])["meta"]
    assert status["resultado"] == "ok"
    assert status["tentativas"] == 1
    assert status["falha"] is None
    assert status["variacao_aceita"] is None
    assert status["ultimo_retrato_bom"] == {
        "gerado_em": meta["gerado_em"],
        "dados_camara_em": meta["dados_camara_em"],
        "total_itens": meta["total_itens"],
        "estoque_bruto": coletado.estoque_bruto,
    }
    assert status["verificado_em"] == agora.isoformat(timespec="seconds")
    assert status["data_referencia"] == "2026-10-18"


def test_sucesso_imprime_a_linha_de_resumo(caminhos, transporte, agora, capsys):
    coletado = coletar(Config(("CE", "CREDN"), 2003), transporte, agora)
    dia = coletado.dados_camara_em.astimezone(FUSO).strftime("%d/%m/%Y")

    codigo = executar_main(caminhos, transporte, Relogio(agora))

    assert codigo == 0
    saida = capsys.readouterr().out
    total = len(coletado.documento["itens"])
    assert saida == (
        f"OK: {total} itens · estoque bruto {coletado.estoque_bruto} · tentativas 1"
        f" · dados da Câmara de {dia}\n"
    )


def test_primeiro_dia_cria_a_pasta_data_e_os_dois_arquivos(caminhos, transporte, agora):
    assert not caminhos["atual"].parent.exists()

    assert executar_main(caminhos, transporte, Relogio(agora)) == 0

    assert caminhos["atual"].exists()
    assert caminhos["status"].exists()
    assert sorted(p.name for p in caminhos["atual"].parent.iterdir()) == [
        "atual.json",
        "status.json",
    ]


def test_lista_identica_a_anterior_ainda_grava_os_dois_arquivos(caminhos, transporte, agora):
    executar_main(caminhos, transporte, Relogio(agora))
    antes_atual = ler(caminhos["atual"])
    antes_status = ler(caminhos["status"])

    assert executar_main(caminhos, transporte, Relogio(agora + timedelta(hours=2))) == 0

    depois_atual = ler(caminhos["atual"])
    depois_status = ler(caminhos["status"])
    assert [i["id"] for i in depois_atual["itens"]] == [i["id"] for i in antes_atual["itens"]]
    assert depois_atual["meta"]["gerado_em"] != antes_atual["meta"]["gerado_em"]
    assert depois_status["verificado_em"] != antes_status["verificado_em"]


def test_mesmo_relogio_gera_arquivos_identicos_byte_a_byte(tmp_path, transporte, agora):
    resultados = []
    for nome in ("a", "b"):
        pasta = tmp_path / nome
        pasta.mkdir()
        (pasta / "config.toml").write_text(CONFIG_BASE, encoding="utf-8")
        caminhos = {
            "config": pasta / "config.toml",
            "atual": pasta / "data" / "atual.json",
            "status": pasta / "data" / "status.json",
        }
        assert executar_main(caminhos, transporte, Relogio(agora)) == 0
        resultados.append((caminhos["atual"].read_bytes(), caminhos["status"].read_bytes()))

    assert resultados[0] == resultados[1]


def test_mensagem_de_sucesso(caminhos, transporte, agora, capsys):
    executar_main(caminhos, transporte, Relogio(agora))
    capsys.readouterr()
    coletado = coletar(Config(("CE", "CREDN"), 2003), transporte, agora)

    codigo = main(["mensagem", "--status", str(caminhos["status"])])

    assert codigo == 0
    total = len(coletado.documento["itens"])
    assert capsys.readouterr().out == (
        f"dados: 2026-10-18 · ok · {total} itens · estoque bruto {coletado.estoque_bruto}\n"
    )


def test_mensagem_sem_status_ou_com_status_invalido_sai_com_1(caminhos, capsys):
    assert main(["mensagem", "--status", str(caminhos["status"])]) == 1
    assert "status" in capsys.readouterr().err

    caminhos["status"].parent.mkdir(parents=True)
    caminhos["status"].write_text("{ não é json", encoding="utf-8")
    assert main(["mensagem", "--status", str(caminhos["status"])]) == 1
    assert "status" in capsys.readouterr().err


def test_serializacao_do_status_e_do_atual_usa_o_mesmo_formato(caminhos, transporte, agora):
    executar_main(caminhos, transporte, Relogio(agora))

    for arquivo in ("atual", "status"):
        assert caminhos[arquivo].read_text(encoding="utf-8") == serializar(ler(caminhos[arquivo]))


# --- US2: falha visível, dados bons intactos ------------------------------------------------------

CONFIG_SEM_REPETICAO = CONFIG_BASE + "[execucao]\ntentativas = 1\n"


def reescrever_csv(corpo: bytes, alterar) -> bytes:
    leitor = csv.reader(io.StringIO(corpo.decode("utf-8-sig"), newline=""), delimiter=";")
    linhas = alterar(list(leitor))
    saida = io.StringIO(newline="")
    csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n").writerows(linhas)
    return saida.getvalue().encode("utf-8-sig")


def sem_coluna(nome):
    def alterar(linhas):
        i = linhas[0].index(nome)
        return [[v for k, v in enumerate(linha) if k != i] for linha in linhas]

    return lambda corpo: reescrever_csv(corpo, alterar)


@pytest.fixture
def dia1(caminhos, agora):
    """Um primeiro dia bem-sucedido, com o config sem repetição para as falhas do dia seguinte."""
    caminhos["config"].write_text(CONFIG_SEM_REPETICAO, encoding="utf-8")
    assert executar_main(caminhos, TransporteFalso(), Relogio(agora)) == 0
    return {
        "atual": caminhos["atual"].read_bytes(),
        "status": ler(caminhos["status"]),
        "agora2": agora + timedelta(hours=2),
    }


def falha_fonte(transporte, agora2):
    transporte.erro["proposicoes-2010.csv"] = FalhaDeColeta(
        FONTE_INDISPONIVEL, "proposicoes-2010.csv: HTTP 503"
    )


def falha_formato(transporte, agora2):
    transporte.transformar["proposicoes-2020.csv"] = sem_coluna("ultimoStatus_dataHora")


def falha_idade(transporte, agora2):
    transporte.last_modified["proposicoes-2021.csv"] = agora2 - timedelta(hours=36, minutes=1)


def falha_dispersao(transporte, agora2):
    transporte.last_modified["proposicoes-2021.csv"] = agora2 - timedelta(hours=1)


def falha_incompleto(transporte, agora2):
    transporte.transformar["proposicoes-2018.csv"] = lambda corpo: reescrever_csv(
        corpo, lambda linhas: linhas[:1]
    )


def falha_api(transporte, agora2):
    transporte.erro["deputados"] = FalhaDeColeta(FONTE_INDISPONIVEL, "deputados: HTTP 503")


CATEGORIAS_DA_COLETA = [
    (falha_fonte, "fonte_indisponivel", "proposicoes-2010.csv"),
    (falha_formato, "formato_alterado", "coluna ultimoStatus_dataHora"),
    (falha_idade, "arquivos_desatualizados", "a Câmara não atualizou os arquivos"),
    (falha_dispersao, "arquivos_desatualizados", "gerados em momentos diferentes"),
    (falha_incompleto, "arquivo_incompleto", "proposicoes-2018.csv"),
    (falha_api, "api_deputados", "deputados do NOVO"),
]


def conferir_falha_com_dados_bons_intactos(caminhos, dia1, capsys, codigo, categoria, trecho):
    erro = capsys.readouterr().err
    assert codigo == 1
    assert erro.startswith(f"FALHA [{categoria}]: "), erro
    assert trecho in erro, erro
    assert caminhos["atual"].read_bytes() == dia1["atual"]  # idêntico byte a byte
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "falha"
    assert status_novo["falha"]["categoria"] == categoria
    assert trecho in status_novo["falha"]["motivo"]
    assert status_novo["variacao_aceita"] is None
    assert status_novo["ultimo_retrato_bom"] == dia1["status"]["ultimo_retrato_bom"]
    assert sorted(p.name for p in caminhos["atual"].parent.iterdir()) == [
        "atual.json",
        "status.json",
    ]  # sem .tmp
    return status_novo


@pytest.mark.parametrize(("preparar", "categoria", "trecho"), CATEGORIAS_DA_COLETA)
def test_falha_da_coleta_mantem_o_atual_e_registra_o_status(
    caminhos, dia1, capsys, preparar, categoria, trecho
):
    transporte = TransporteFalso()
    preparar(transporte, dia1["agora2"])
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    status_novo = conferir_falha_com_dados_bons_intactos(
        caminhos, dia1, capsys, codigo, categoria, trecho
    )
    assert status_novo["tentativas"] == 1


def test_lista_filtrada_vazia_falha_como_estoque_vazio(caminhos, dia1, capsys):
    caminhos["config"].write_text(
        'comissoes = ["CXYZ"]\nano_minimo = 2003\n[execucao]\ntentativas = 1\n', encoding="utf-8"
    )
    capsys.readouterr()

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]))

    conferir_falha_com_dados_bons_intactos(
        caminhos, dia1, capsys, codigo, "estoque_vazio", "nenhum item"
    )


def test_configuracao_invalida_falha_sem_coletar_e_registra_zero_tentativas(caminhos, dia1, capsys):
    caminhos["config"].write_text("comissoes = []\nano_minimo = 2003\n", encoding="utf-8")
    transporte = TransporteFalso()
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    status_novo = conferir_falha_com_dados_bons_intactos(
        caminhos, dia1, capsys, codigo, "configuracao", "comissoes"
    )
    assert status_novo["tentativas"] == 0
    assert transporte.pedidos == []


class TransporteQueQuebra(TransporteFalso):
    def obter_json(self, url):
        raise KeyError("itens")


def test_excecao_inesperada_vira_falha_interna(caminhos, dia1, capsys):
    capsys.readouterr()

    codigo = executar_main(caminhos, TransporteQueQuebra(), Relogio(dia1["agora2"]))

    conferir_falha_com_dados_bons_intactos(caminhos, dia1, capsys, codigo, "interna", "KeyError")


def test_falha_no_primeiro_dia_nao_cria_atual_e_o_retrato_e_nulo(caminhos, agora, capsys):
    transporte = TransporteFalso()
    falha_api(transporte, agora)

    codigo = executar_main(caminhos, transporte, Relogio(agora))

    assert codigo == 1
    assert not caminhos["atual"].exists()
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "falha"
    assert status_novo["ultimo_retrato_bom"] is None
    assert [p.name for p in caminhos["atual"].parent.iterdir()] == ["status.json"]


def test_atual_sentinela_fica_intacto_e_o_retrato_e_nulo(caminhos, agora):
    caminhos["atual"].parent.mkdir(parents=True)
    caminhos["atual"].write_text('{"sentinela": true}\n', encoding="utf-8")
    transporte = TransporteFalso()
    falha_api(transporte, agora)

    codigo = executar_main(caminhos, transporte, Relogio(agora))

    assert codigo == 1
    assert caminhos["atual"].read_text(encoding="utf-8") == '{"sentinela": true}\n'
    assert ler(caminhos["status"])["ultimo_retrato_bom"] is None


def test_sucesso_depois_de_falha_no_mesmo_dia_nao_carrega_resto_da_falha(caminhos, dia1, capsys):
    transporte = TransporteFalso()
    falha_api(transporte, dia1["agora2"])
    assert executar_main(caminhos, transporte, Relogio(dia1["agora2"])) == 1
    assert ler(caminhos["status"])["resultado"] == "falha"

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]))

    assert codigo == 0
    status_final = ler(caminhos["status"])
    assert status_final["resultado"] == "ok"
    assert status_final["falha"] is None
    assert "api_deputados" not in caminhos["status"].read_text(encoding="utf-8")


def falhar_na_preparacao(monkeypatch, numero_da_chamada):
    """Faz `OSError` na preparação do N-ésimo temporário de `status.gravar_par`."""
    original = status.escrever_temporario
    chamadas = []

    def falso(texto, destino):
        chamadas.append(destino)
        if len(chamadas) == numero_da_chamada:
            raise OSError("disco cheio (simulado)")
        return original(texto, destino)

    monkeypatch.setattr(status, "escrever_temporario", falso)


@pytest.mark.parametrize("quem", [1, 2], ids=["atual", "status"])
def test_falha_ao_preparar_um_dos_arquivos_nao_troca_nenhum(
    caminhos, dia1, capsys, monkeypatch, quem
):
    falhar_na_preparacao(monkeypatch, quem)
    capsys.readouterr()

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]))

    status_novo = conferir_falha_com_dados_bons_intactos(
        caminhos, dia1, capsys, codigo, "interna", "disco cheio"
    )
    assert status_novo["tentativas"] == 1


def test_se_nem_o_status_de_falha_pode_ser_gravado_sai_com_1_sem_tocar_no_atual(
    caminhos, dia1, capsys, monkeypatch
):
    def quebrado(*args, **kwargs):
        raise OSError("sem permissão (simulado)")

    monkeypatch.setattr(diaria, "gravar_status", quebrado)
    transporte = TransporteFalso()
    falha_api(transporte, dia1["agora2"])
    status_antes = caminhos["status"].read_bytes()
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    assert codigo == 1
    erro = capsys.readouterr().err
    assert "FALHA [interna]" in erro
    assert caminhos["atual"].read_bytes() == dia1["atual"]
    assert caminhos["status"].read_bytes() == status_antes


# --- US3: plausibilidade do estoque bruto -------------------------------------------------------


def trocar_orgao(corpo: bytes) -> bytes:
    """Tira do estoque as proposições da CE e da CREDN do arquivo (muda o órgão para a CFT)."""

    def alterar(linhas):
        i = linhas[0].index("ultimoStatus_siglaOrgao")
        for linha in linhas[1:]:
            if linha[i] in ("CE", "CREDN"):
                linha[i] = "CFT"
        return linhas

    return reescrever_csv(corpo, alterar)


def queda_de_28_por_cento(transporte):
    """Estoque bruto das fixtures: 7. Tirando as 2 de 2011, fica 5 (-28,6%), com os 2 itens."""
    transporte.transformar["proposicoes-2011.csv"] = trocar_orgao


def queda_de_14_por_cento(transporte):
    """Tirando a de 2003, o estoque fica 6 (-14,3%)."""
    transporte.transformar["proposicoes-2003.csv"] = trocar_orgao


def sem_autores_do_novo_em_2022(transporte):
    """A lista filtrada cai de 2 itens para 1, e o estoque bruto não muda."""

    def alterar(linhas):
        i = linhas[0].index("siglaPartidoAutor")
        for linha in linhas[1:]:
            if linha[i] == "NOVO":
                linha[i] = "PL"
        return linhas

    transporte.transformar["proposicoesAutores-2022.csv"] = lambda c: reescrever_csv(c, alterar)


def test_queda_acima_de_20_por_cento_bloqueia_e_mantem_os_dados_bons(caminhos, dia1, capsys):
    transporte = TransporteFalso()
    queda_de_28_por_cento(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    status_novo = conferir_falha_com_dados_bons_intactos(
        caminhos, dia1, capsys, codigo, "estoque_implausivel", "7 → 5"
    )
    assert "-28,6%" in status_novo["falha"]["motivo"]
    assert dia1["status"]["ultimo_retrato_bom"]["estoque_bruto"] == 7


def test_variacao_dentro_do_limite_grava_normalmente(caminhos, dia1):
    transporte = TransporteFalso()
    queda_de_14_por_cento(transporte)

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    assert codigo == 0
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "ok"
    assert status_novo["ultimo_retrato_bom"]["estoque_bruto"] == 6
    assert status_novo["variacao_aceita"] is None


def test_variacao_da_lista_filtrada_nao_e_criterio_de_plausibilidade(caminhos, dia1):
    transporte = TransporteFalso()
    sem_autores_do_novo_em_2022(transporte)

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    assert codigo == 0
    assert ler(caminhos["status"])["ultimo_retrato_bom"]["total_itens"] == 1
    assert ler(caminhos["status"])["ultimo_retrato_bom"]["estoque_bruto"] == 7


def test_comissao_sem_nenhuma_proposicao_falha_no_primeiro_dia(caminhos, agora, capsys):
    caminhos["config"].write_text('comissoes = ["CXYZ"]\nano_minimo = 2003\n', encoding="utf-8")

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(agora))

    assert codigo == 1
    assert "FALHA [estoque_vazio]" in capsys.readouterr().err
    assert not caminhos["atual"].exists()
    assert ler(caminhos["status"])["falha"]["categoria"] == "estoque_vazio"


def test_a_base_do_dia_seguinte_a_uma_falha_e_o_retrato_bom(caminhos, dia1, agora):
    falhou = TransporteFalso()
    falha_api(falhou, dia1["agora2"])
    assert executar_main(caminhos, falhou, Relogio(dia1["agora2"])) == 1
    assert ler(caminhos["status"])["ultimo_retrato_bom"]["estoque_bruto"] == 7

    transporte = TransporteFalso()
    queda_de_28_por_cento(transporte)
    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(hours=3)))

    status_novo = ler(caminhos["status"])
    assert codigo == 1
    assert status_novo["falha"]["categoria"] == "estoque_implausivel"
    assert "7 → 5" in status_novo["falha"]["motivo"]


def test_sem_status_a_variacao_nao_se_aplica_e_a_execucao_avisa(caminhos, dia1, capsys):
    caminhos["status"].unlink()
    transporte = TransporteFalso()
    queda_de_28_por_cento(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    assert codigo == 0
    assert "sem base para comparar a variação" in capsys.readouterr().err
    assert ler(caminhos["status"])["ultimo_retrato_bom"]["estoque_bruto"] == 5


def test_status_que_nao_descreve_o_atual_nao_serve_de_base(caminhos, dia1, capsys):
    outro = ler(caminhos["status"])
    outro["ultimo_retrato_bom"]["gerado_em"] = "2026-10-17T03:00:00-03:00"
    caminhos["status"].write_text(serializar(outro), encoding="utf-8")
    transporte = TransporteFalso()
    queda_de_28_por_cento(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    assert codigo == 0
    assert "sem base para comparar a variação" in capsys.readouterr().err


def test_confirmacao_manual_aceita_a_variacao_e_registra(caminhos, dia1, capsys):
    transporte = TransporteFalso()
    queda_de_28_por_cento(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]), aceitar=True)

    assert codigo == 0
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "ok"
    assert status_novo["variacao_aceita"] == {
        "estoque_anterior": 7,
        "estoque_novo": 5,
        "variacao_percentual": -28.6,
    }
    assert status_novo["ultimo_retrato_bom"]["estoque_bruto"] == 5
    assert main(["mensagem", "--status", str(caminhos["status"])]) == 0
    assert capsys.readouterr().out.endswith(
        "dados: 2026-10-18 · ok · variação aceita manualmente (7 → 5, -28,6%)\n"
    )


@pytest.mark.parametrize("preparar", [falha_api, falha_formato, falha_fonte])
def test_a_confirmacao_nao_libera_outras_falhas(caminhos, dia1, capsys, preparar):
    transporte = TransporteFalso()
    preparar(transporte, dia1["agora2"])
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]), aceitar=True)

    assert codigo == 1
    assert caminhos["atual"].read_bytes() == dia1["atual"]
    assert ler(caminhos["status"])["resultado"] == "falha"


def test_no_dia_seguinte_a_uma_variacao_aceita_o_limite_volta_a_valer(caminhos, dia1, agora):
    aceita = TransporteFalso()
    queda_de_28_por_cento(aceita)
    assert executar_main(caminhos, aceita, Relogio(dia1["agora2"]), aceitar=True) == 0

    mesmo_estoque = TransporteFalso()
    queda_de_28_por_cento(mesmo_estoque)
    assert executar_main(caminhos, mesmo_estoque, Relogio(agora + timedelta(hours=3))) == 0
    assert ler(caminhos["status"])["variacao_aceita"] is None  # sem resto da aceitação

    voltou = TransporteFalso()  # estoque de volta a 7: +40% sobre a base aceita (5)
    codigo = executar_main(caminhos, voltou, Relogio(agora + timedelta(hours=4)))

    assert codigo == 1
    status_novo = ler(caminhos["status"])
    assert status_novo["falha"]["categoria"] == "estoque_implausivel"
    assert "5 → 7" in status_novo["falha"]["motivo"]
