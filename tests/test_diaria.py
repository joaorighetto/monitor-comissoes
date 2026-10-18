"""Execução diária (AGE): caminho feliz, falhas, plausibilidade, tentativas e reexecução."""

import csv
import io
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from conftest import FIXTURES, TransporteFalso
from monitor_comissoes import diaria, status
from monitor_comissoes.coleta import coletar, executar
from monitor_comissoes.config import Config
from monitor_comissoes.diaria import main
from monitor_comissoes.erros import FONTE_INDISPONIVEL, REPETIVEIS, FalhaDeColeta
from monitor_comissoes.estoque import BRASILIA as FUSO
from monitor_comissoes.lote import contar_estoque_bruto
from monitor_comissoes.saida import serializar

CONFIG_BASE = 'comissoes = ["CE", "CREDN"]\nano_minimo = 2003\n'

# Estoque bruto das fixtures reais (capturadas em 18/10/2026): PL/PLP com o órgão do próprio
# último status na CE ou na CREDN. Os números são fatos das fixtures, conferidos por
# `test_estoque_bruto_das_fixtures`; recapturar as fixtures exige atualizá-los.
BRUTO = 122
ANOS_QUEDA_GRANDE = (2022, 2023, 2025)  # 18 + 11 + 14 = 43 → 79 (-35,25%)
BRUTO_QUEDA_GRANDE = 79
ANO_QUEDA_PEQUENA = 2015  # 11 → 111 (-9,02%)
BRUTO_QUEDA_PEQUENA = 111


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
        "anterior": tmp_path / "data" / "anterior.json",
        "mudancas": tmp_path / "data" / "mudancas",
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
        "--anterior",
        str(caminhos["anterior"]),
        "--mudancas",
        str(caminhos["mudancas"]),
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
        f" · dados da Câmara de {dia} · mudanças: linha de base (primeiro retrato)\n"
    )


def test_primeiro_dia_cria_a_pasta_data_e_os_arquivos(caminhos, transporte, agora):
    assert not caminhos["atual"].parent.exists()

    assert executar_main(caminhos, transporte, Relogio(agora)) == 0

    assert caminhos["atual"].exists()
    assert caminhos["status"].exists()
    # MUD: o arquivo de mudanças do dia (linha de base) entra; `anterior.json` só existe depois
    # que um atual.json de dia anterior rotaciona.
    assert sorted(p.name for p in caminhos["atual"].parent.iterdir()) == [
        "atual.json",
        "mudancas",
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
            "anterior": pasta / "data" / "anterior.json",
            "mudancas": pasta / "data" / "mudancas",
        }
        assert executar_main(caminhos, transporte, Relogio(agora)) == 0
        [mudancas] = caminhos["mudancas"].iterdir()
        resultados.append(
            (
                caminhos["atual"].read_bytes(),
                caminhos["status"].read_bytes(),
                mudancas.name,
                mudancas.read_bytes(),
            )
        )

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
        "mudancas",  # a do dia 1; a falha do dia 2 não grava outro arquivo de mudanças
        "status.json",
    ]  # sem .tmp
    assert [p.name for p in caminhos["mudancas"].iterdir()] == ["2026-10-18.json"]
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


def queda_grande(transporte):
    """Tirando as de 2022, 2023 e 2025 da CE e da CREDN, o estoque cai de 122 para 79 (-35,25%)."""
    for ano in ANOS_QUEDA_GRANDE:
        transporte.transformar[f"proposicoes-{ano}.csv"] = trocar_orgao


def queda_pequena(transporte):
    """Tirando as de 2015, o estoque cai de 122 para 111 (-9,02%), dentro do limite de 20%."""
    transporte.transformar[f"proposicoes-{ANO_QUEDA_PEQUENA}.csv"] = trocar_orgao


def test_estoque_bruto_das_fixtures():
    """Conferência dos números acima contra a função de produção (aviso de recaptura)."""

    def bruto(anos):
        return sum(
            contar_estoque_bruto(
                FIXTURES / f"proposicoes-{ano}.csv", ("PL", "PLP"), ("CE", "CREDN")
            )
            for ano in anos
        )

    assert bruto(range(2003, 2027)) == BRUTO
    assert BRUTO - bruto(ANOS_QUEDA_GRANDE) == BRUTO_QUEDA_GRANDE
    assert BRUTO - bruto((ANO_QUEDA_PEQUENA,)) == BRUTO_QUEDA_PEQUENA


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
    queda_grande(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    status_novo = conferir_falha_com_dados_bons_intactos(
        caminhos, dia1, capsys, codigo, "estoque_implausivel", f"{BRUTO} → {BRUTO_QUEDA_GRANDE}"
    )
    assert "-35,25%" in status_novo["falha"]["motivo"]
    assert dia1["status"]["ultimo_retrato_bom"]["estoque_bruto"] == BRUTO


def test_variacao_dentro_do_limite_grava_normalmente(caminhos, dia1):
    transporte = TransporteFalso()
    queda_pequena(transporte)

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    assert codigo == 0
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "ok"
    assert status_novo["ultimo_retrato_bom"]["estoque_bruto"] == BRUTO_QUEDA_PEQUENA
    assert status_novo["variacao_aceita"] is None


def test_variacao_da_lista_filtrada_nao_e_criterio_de_plausibilidade(caminhos, dia1):
    transporte = TransporteFalso()
    sem_autores_do_novo_em_2022(transporte)

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    assert codigo == 0
    # A lista filtrada encolhe (sem `autoria NOVO` em 2022), mas o estoque bruto não muda.
    novo = ler(caminhos["status"])["ultimo_retrato_bom"]
    assert 0 < novo["total_itens"] < dia1["status"]["ultimo_retrato_bom"]["total_itens"]
    assert novo["estoque_bruto"] == BRUTO


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
    assert ler(caminhos["status"])["ultimo_retrato_bom"]["estoque_bruto"] == BRUTO

    transporte = TransporteFalso()
    queda_grande(transporte)
    codigo = executar_main(caminhos, transporte, Relogio(agora + timedelta(hours=3)))

    status_novo = ler(caminhos["status"])
    assert codigo == 1
    assert status_novo["falha"]["categoria"] == "estoque_implausivel"
    assert f"{BRUTO} → {BRUTO_QUEDA_GRANDE}" in status_novo["falha"]["motivo"]


def conferir_sem_base(caminhos, dia1, capsys, codigo, estoque_de_hoje):
    erro = capsys.readouterr().err
    assert codigo == 1
    assert erro.startswith("FALHA [sem_base_de_comparacao]: "), erro
    assert f"estoque bruto de hoje: {estoque_de_hoje}" in erro
    assert caminhos["atual"].read_bytes() == dia1["atual"]  # idêntico byte a byte
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "falha"
    assert status_novo["falha"]["categoria"] == "sem_base_de_comparacao"
    retrato = status_novo["ultimo_retrato_bom"]
    assert retrato["gerado_em"] == dia1["status"]["ultimo_retrato_bom"]["gerado_em"]
    assert retrato["estoque_bruto"] is None  # sem base, não há número a manter
    return status_novo


def test_sem_status_com_atual_a_execucao_falha_sem_base_de_comparacao(caminhos, dia1, capsys):
    caminhos["status"].unlink()
    transporte = TransporteFalso()
    queda_grande(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]))

    status_novo = conferir_sem_base(caminhos, dia1, capsys, codigo, BRUTO_QUEDA_GRANDE)
    assert status_novo["tentativas"] == 1


def test_status_que_nao_descreve_o_atual_tambem_falha_sem_base_de_comparacao(
    caminhos, dia1, capsys
):
    outro = ler(caminhos["status"])
    outro["ultimo_retrato_bom"]["gerado_em"] = "2026-10-17T03:00:00-03:00"
    caminhos["status"].write_text(serializar(outro), encoding="utf-8")
    capsys.readouterr()

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]))

    conferir_sem_base(caminhos, dia1, capsys, codigo, BRUTO)


def test_status_corrompido_com_atual_falha_sem_base_de_comparacao(caminhos, dia1, capsys):
    caminhos["status"].write_text("{ não é json", encoding="utf-8")
    capsys.readouterr()

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]))

    conferir_sem_base(caminhos, dia1, capsys, codigo, BRUTO)


def test_sem_base_de_comparacao_nao_repete(caminhos, dia1):
    caminhos["config"].write_text(CONFIG_BASE, encoding="utf-8")  # 4 tentativas permitidas
    caminhos["status"].unlink()
    dormidas = Dormidas()
    transporte = TransporteIntermitente([])

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]), dormidas)

    assert codigo == 1
    assert transporte.coletas == 1
    assert dormidas.pedidos == []


def test_sem_atual_o_primeiro_dia_continua_passando_mesmo_com_um_status_solto(caminhos, dia1):
    caminhos["atual"].unlink()  # só o status ficou: não há retrato anterior para comparar

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]))

    assert codigo == 0
    assert ler(caminhos["status"])["variacao_aceita"] is None


def test_confirmacao_aceita_a_falta_de_base_e_registra(caminhos, dia1, capsys):
    caminhos["status"].unlink()
    transporte = TransporteFalso()
    queda_grande(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]), aceitar=True)

    assert codigo == 0
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "ok"
    assert status_novo["variacao_aceita"] == {
        "estoque_anterior": None,
        "estoque_novo": BRUTO_QUEDA_GRANDE,
        "variacao_percentual": None,
    }
    assert status_novo["ultimo_retrato_bom"]["estoque_bruto"] == BRUTO_QUEDA_GRANDE
    assert main(["mensagem", "--status", str(caminhos["status"])]) == 0
    assert capsys.readouterr().out.endswith(
        "dados: 2026-10-18 · ok · aceito sem base de comparação "
        f"(estoque bruto {BRUTO_QUEDA_GRANDE})\n"
    )


def test_a_confirmacao_nao_libera_estoque_vazio_nem_outras_falhas_sem_base(caminhos, dia1, capsys):
    caminhos["status"].unlink()
    transporte = TransporteFalso()
    falha_api(transporte, dia1["agora2"])

    assert executar_main(caminhos, transporte, Relogio(dia1["agora2"]), aceitar=True) == 1
    assert ler(caminhos["status"])["falha"]["categoria"] == "api_deputados"

    caminhos["config"].write_text(
        'comissoes = ["CXYZ"]\nano_minimo = 2003\n[execucao]\ntentativas = 1\n', encoding="utf-8"
    )
    capsys.readouterr()
    assert executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]), aceitar=True) == 1
    assert ler(caminhos["status"])["falha"]["categoria"] == "estoque_vazio"
    assert caminhos["atual"].read_bytes() == dia1["atual"]


def test_no_dia_seguinte_a_um_aceito_sem_base_a_base_e_o_estoque_aceito(caminhos, dia1, agora):
    caminhos["status"].unlink()
    aceito = TransporteFalso()
    queda_grande(aceito)
    assert executar_main(caminhos, aceito, Relogio(dia1["agora2"]), aceitar=True) == 0

    mesmo = TransporteFalso()
    queda_grande(mesmo)
    assert executar_main(caminhos, mesmo, Relogio(agora + timedelta(hours=3))) == 0
    assert ler(caminhos["status"])["variacao_aceita"] is None

    voltou = TransporteFalso()  # estoque de volta a 7: +40% sobre a base aceita (5)
    assert executar_main(caminhos, voltou, Relogio(agora + timedelta(hours=4))) == 1
    assert ler(caminhos["status"])["falha"]["categoria"] == "estoque_implausivel"


def test_confirmacao_manual_aceita_a_variacao_e_registra(caminhos, dia1, capsys):
    transporte = TransporteFalso()
    queda_grande(transporte)
    capsys.readouterr()

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]), aceitar=True)

    assert codigo == 0
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "ok"
    assert status_novo["variacao_aceita"] == {
        "estoque_anterior": BRUTO,
        "estoque_novo": BRUTO_QUEDA_GRANDE,
        "variacao_percentual": -35.2,
    }
    assert status_novo["ultimo_retrato_bom"]["estoque_bruto"] == BRUTO_QUEDA_GRANDE
    assert main(["mensagem", "--status", str(caminhos["status"])]) == 0
    assert capsys.readouterr().out.endswith(
        "dados: 2026-10-18 · ok · variação aceita manualmente "
        f"({BRUTO} → {BRUTO_QUEDA_GRANDE}, -35,2%)\n"
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
    queda_grande(aceita)
    assert executar_main(caminhos, aceita, Relogio(dia1["agora2"]), aceitar=True) == 0

    mesmo_estoque = TransporteFalso()
    queda_grande(mesmo_estoque)
    assert executar_main(caminhos, mesmo_estoque, Relogio(agora + timedelta(hours=3))) == 0
    assert ler(caminhos["status"])["variacao_aceita"] is None  # sem resto da aceitação

    voltou = TransporteFalso()  # estoque de volta a 7: +40% sobre a base aceita (5)
    codigo = executar_main(caminhos, voltou, Relogio(agora + timedelta(hours=4)))

    assert codigo == 1
    status_novo = ler(caminhos["status"])
    assert status_novo["falha"]["categoria"] == "estoque_implausivel"
    assert f"{BRUTO_QUEDA_GRANDE} → {BRUTO}" in status_novo["falha"]["motivo"]


# --- US4: novas tentativas ------------------------------------------------------------------------


class TransporteIntermitente(TransporteFalso):
    """Falha as primeiras coletas com as falhas dadas (uma por coleta), depois funciona.

    A falha sai no primeiro download da coleta, para chegar à execução diária com a categoria
    exata (a API de deputados reembrulha qualquer erro como `api_deputados`).
    """

    def __init__(self, falhas):
        super().__init__()
        self.falhas = list(falhas)
        self.coletas = 0
        self._falha_da_coleta = None

    def obter_json(self, url):
        # A lista de deputados do NOVO é a primeira chamada de cada coleta.
        if url.endswith("siglaPartido=NOVO&itens=100"):
            self.coletas += 1
            self._falha_da_coleta = self.falhas.pop(0) if self.falhas else None
        return super().obter_json(url)

    def baixar(self, url, destino):
        if self._falha_da_coleta is not None:
            falha, self._falha_da_coleta = self._falha_da_coleta, None
            raise falha
        return super().baixar(url, destino)


def passageira(categoria=FONTE_INDISPONIVEL, motivo="proposicoes-2024.csv: HTTP 503"):
    return FalhaDeColeta(categoria, motivo)


def test_falha_passageira_seguida_de_sucesso_termina_ok_com_duas_tentativas(
    caminhos, agora, capsys
):
    dormidas = Dormidas()
    transporte = TransporteIntermitente([passageira()])

    codigo = executar_main(caminhos, transporte, Relogio(agora), dormidas)

    assert codigo == 0
    assert dormidas.pedidos == [1800]  # 30 minutos
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "ok"
    assert status_novo["tentativas"] == 2
    assert status_novo["falha"] is None
    assert "tentativas 2" in capsys.readouterr().out


def test_duas_falhas_repetiveis_e_sucesso_na_terceira(caminhos, agora):
    dormidas = Dormidas()
    transporte = TransporteIntermitente(
        [passageira(), passageira("arquivos_desatualizados", "a Câmara não atualizou")]
    )

    codigo = executar_main(caminhos, transporte, Relogio(agora), dormidas)

    assert codigo == 0
    assert dormidas.pedidos == [1800, 1800]
    assert ler(caminhos["status"])["tentativas"] == 3


def test_quatro_falhas_repetiveis_esgotam_as_tentativas(caminhos, agora, capsys):
    dormidas = Dormidas()
    ultimas = [passageira(motivo=f"tentativa {n}") for n in range(1, 5)]
    transporte = TransporteIntermitente(ultimas)

    codigo = executar_main(caminhos, transporte, Relogio(agora), dormidas)

    assert codigo == 1
    assert transporte.coletas == 4
    assert dormidas.pedidos == [1800, 1800, 1800]  # nenhuma espera depois da última
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "falha"
    assert status_novo["tentativas"] == 4
    assert status_novo["falha"] == {
        "categoria": "fonte_indisponivel",
        "motivo": "tentativa 4",
    }
    erro = capsys.readouterr().err
    assert erro.count("TENTATIVA ") == 3
    assert (
        "TENTATIVA 1 de 4 falhou [fonte_indisponivel]: tentativa 1; nova tentativa em 30 minutos"
        in erro
    )
    assert "FALHA [fonte_indisponivel]: tentativa 4" in erro
    assert not caminhos["atual"].exists()


@pytest.mark.parametrize("categoria", REPETIVEIS)
def test_cada_categoria_repetivel_repete(caminhos, agora, categoria):
    dormidas = Dormidas()
    transporte = TransporteIntermitente([passageira(categoria, "x")])

    assert executar_main(caminhos, transporte, Relogio(agora), dormidas) == 0

    assert dormidas.pedidos == [1800]
    assert ler(caminhos["status"])["tentativas"] == 2


def test_so_as_quatro_categorias_da_spec_sao_repetiveis():
    assert set(REPETIVEIS) == {
        "fonte_indisponivel",
        "arquivos_desatualizados",
        "arquivo_incompleto",
        "api_deputados",
    }


@pytest.mark.parametrize(
    "categoria", ["formato_alterado", "estoque_vazio", "estoque_implausivel", "configuracao"]
)
def test_categorias_nao_repetiveis_falham_de_imediato(caminhos, agora, categoria):
    dormidas = Dormidas()
    transporte = TransporteIntermitente([passageira(categoria, "x"), passageira(categoria, "x")])

    codigo = executar_main(caminhos, transporte, Relogio(agora), dormidas)

    assert codigo == 1
    assert dormidas.pedidos == []
    assert transporte.coletas == 1
    assert ler(caminhos["status"])["tentativas"] == 1


def test_formato_alterado_real_nao_repete(caminhos, agora):
    dormidas = Dormidas()
    transporte = TransporteFalso()
    falha_formato(transporte, agora)

    codigo = executar_main(caminhos, transporte, Relogio(agora), dormidas)

    assert codigo == 1
    assert dormidas.pedidos == []
    assert ler(caminhos["status"])["tentativas"] == 1


def test_estoque_implausivel_real_nao_repete(caminhos, dia1):
    caminhos["config"].write_text(CONFIG_BASE, encoding="utf-8")  # 4 tentativas permitidas
    dormidas = Dormidas()
    transporte = TransporteFalso()
    queda_grande(transporte)

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]), dormidas)

    assert codigo == 1
    assert dormidas.pedidos == []
    assert ler(caminhos["status"])["tentativas"] == 1


def test_configuracao_invalida_nao_repete_e_nao_coleta(caminhos, agora):
    caminhos["config"].write_text("comissoes = []\nano_minimo = 2003\n", encoding="utf-8")
    dormidas = Dormidas()
    transporte = TransporteIntermitente([])

    assert executar_main(caminhos, transporte, Relogio(agora), dormidas) == 1

    assert dormidas.pedidos == []
    assert transporte.coletas == 0
    assert ler(caminhos["status"])["tentativas"] == 0


def test_falha_interna_nao_repete(caminhos, agora):
    class Quebra(TransporteIntermitente):
        def obter_json(self, url):
            self.coletas += 1
            raise KeyError("itens")

    dormidas = Dormidas()
    transporte = Quebra([])

    assert executar_main(caminhos, transporte, Relogio(agora), dormidas) == 1

    assert dormidas.pedidos == []
    assert transporte.coletas == 1
    assert ler(caminhos["status"])["falha"]["categoria"] == "interna"


def test_tentativas_e_espera_vem_da_configuracao(caminhos, agora):
    caminhos["config"].write_text(
        CONFIG_BASE + "[execucao]\ntentativas = 2\nespera_minutos = 5\n", encoding="utf-8"
    )
    dormidas = Dormidas()
    transporte = TransporteIntermitente([passageira(), passageira(), passageira()])

    codigo = executar_main(caminhos, transporte, Relogio(agora), dormidas)

    assert codigo == 1
    assert transporte.coletas == 2
    assert dormidas.pedidos == [300]
    assert ler(caminhos["status"])["tentativas"] == 2


def test_o_relogio_e_lido_de_novo_a_cada_tentativa(caminhos, agora):
    relogio = Relogio(agora, passo=timedelta(minutes=30))
    transporte = TransporteIntermitente([passageira()])

    assert executar_main(caminhos, transporte, relogio, Dormidas()) == 0

    gerado_em = datetime.fromisoformat(ler(caminhos["atual"])["meta"]["gerado_em"])
    assert gerado_em > agora + timedelta(minutes=30)  # da 2ª tentativa, não da 1ª


def test_a_confirmacao_de_variacao_nao_gasta_nem_pula_tentativas(caminhos, dia1):
    caminhos["config"].write_text(CONFIG_BASE, encoding="utf-8")  # 4 tentativas permitidas
    dormidas = Dormidas()
    transporte = TransporteIntermitente([passageira()])
    queda_grande(transporte)

    codigo = executar_main(caminhos, transporte, Relogio(dia1["agora2"]), dormidas, aceitar=True)

    assert codigo == 0
    assert ler(caminhos["status"])["tentativas"] == 2
    assert ler(caminhos["status"])["variacao_aceita"]["estoque_novo"] == BRUTO_QUEDA_GRANDE


# --- US5: reexecução no mesmo dia ----------------------------------------------------------------


def frescos(transporte, momento):
    """Todos os arquivos do lote 'gerados' uma hora antes de `momento` (para testar outros dias)."""
    for ano in range(2003, 2027):
        for nome in (f"proposicoes-{ano}.csv", f"proposicoesAutores-{ano}.csv"):
            transporte.last_modified[nome] = momento - timedelta(hours=1)


def test_duas_execucoes_no_mesmo_dia_dao_a_mesma_lista_e_ambas_gravam(caminhos, agora):
    assert executar_main(caminhos, TransporteFalso(), Relogio(agora)) == 0
    primeiro_atual, primeiro_status = ler(caminhos["atual"]), ler(caminhos["status"])

    segunda = agora + timedelta(hours=2)
    assert executar_main(caminhos, TransporteFalso(), Relogio(segunda)) == 0
    segundo_atual, segundo_status = ler(caminhos["atual"]), ler(caminhos["status"])

    assert segundo_atual["itens"] == primeiro_atual["itens"]  # conteúdo e ordem, mesmo dia
    diferenca = {
        chave
        for chave in primeiro_atual["meta"]
        if primeiro_atual["meta"][chave] != segundo_atual["meta"][chave]
    }
    assert diferenca == {"gerado_em"}
    assert segundo_status["verificado_em"] == segunda.isoformat(timespec="seconds")
    assert segundo_status["verificado_em"] != primeiro_status["verificado_em"]
    assert segundo_status["data_referencia"] == primeiro_status["data_referencia"]
    assert segundo_status["ultimo_retrato_bom"]["gerado_em"] == segundo_atual["meta"]["gerado_em"]


def test_execucao_de_sucesso_depois_de_uma_falha_do_mesmo_dia_grava(caminhos, agora):
    falhou = TransporteFalso()
    falha_api(falhou, agora)
    assert executar_main(caminhos, falhou, Relogio(agora)) == 1
    assert not caminhos["atual"].exists()

    assert executar_main(caminhos, TransporteFalso(), Relogio(agora + timedelta(hours=1))) == 0

    assert caminhos["atual"].exists()
    assert ler(caminhos["status"])["resultado"] == "ok"


@pytest.mark.xfail(
    strict=True,
    reason="MUD, Fase 4 (T024): roda dois dias seguidos e precisa da comparação com o anterior",
)
def test_a_data_de_referencia_muda_na_virada_do_dia_de_brasilia(caminhos):
    antes = datetime(2026, 10, 18, 23, 50, tzinfo=FUSO)
    depois = datetime(2026, 10, 19, 0, 10, tzinfo=FUSO)
    for momento, esperado in ((antes, "2026-10-18"), (depois, "2026-10-19")):
        transporte = TransporteFalso()
        frescos(transporte, momento)

        assert executar_main(caminhos, transporte, Relogio(momento)) == 0

        assert ler(caminhos["status"])["data_referencia"] == esperado


# --- Revisão: SIGTERM, anotação do Actions, retorno do par ---------------------------------------


def test_sigterm_no_meio_da_espera_grava_o_status_de_falha(caminhos, agora):
    import os
    import signal

    def dormir_e_ser_interrompido(segundos):
        os.kill(os.getpid(), signal.SIGTERM)  # o `timeout` do workflow estourou

    antes = signal.getsignal(signal.SIGTERM)
    transporte = TransporteIntermitente([passageira()])

    codigo = executar_main(caminhos, transporte, Relogio(agora), dormir_e_ser_interrompido)

    assert codigo == 1
    status_novo = ler(caminhos["status"])
    assert status_novo["resultado"] == "falha"
    assert status_novo["falha"]["categoria"] == "interna"
    assert "SIGTERM" in status_novo["falha"]["motivo"]
    assert status_novo["tentativas"] == 1
    assert not caminhos["atual"].exists()
    assert signal.getsignal(signal.SIGTERM) == antes  # o tratador não vaza para fora do main


def test_no_actions_o_aviso_de_sem_base_vira_anotacao(caminhos, agora, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    assert executar_main(caminhos, TransporteFalso(), Relogio(agora)) == 0

    saida = capsys.readouterr()
    assert "::warning title=Coleta diária::sem base para comparar a variação" in saida.out
    assert "AVISO: sem base para comparar a variação" in saida.err


def test_fora_do_actions_o_aviso_nao_gera_anotacao(caminhos, agora, capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    assert executar_main(caminhos, TransporteFalso(), Relogio(agora)) == 0

    assert "::warning" not in capsys.readouterr().out


def test_se_a_troca_do_status_falha_o_atual_volta_ao_que_era_e_o_status_fica_coerente(
    caminhos, dia1, capsys, monkeypatch
):
    import os

    original = os.replace
    falhas = []

    def falso(origem, destino):
        if Path(destino) == caminhos["status"] and not falhas:
            falhas.append(destino)
            raise OSError("falha simulada na troca do status")
        return original(origem, destino)

    monkeypatch.setattr(os, "replace", falso)
    capsys.readouterr()

    codigo = executar_main(caminhos, TransporteFalso(), Relogio(dia1["agora2"]))

    status_novo = conferir_falha_com_dados_bons_intactos(
        caminhos, dia1, capsys, codigo, "interna", "falha simulada"
    )
    assert status_novo["tentativas"] == 1


# --- MUD: retrato anterior, rotação e arquivo de mudanças -----------------------------------------


def arquivo_do_dia(caminhos, nome):
    return ler(caminhos["mudancas"] / nome)


def test_primeiro_dia_grava_a_linha_de_base_e_nao_cria_anterior(caminhos, transporte, agora):
    assert executar_main(caminhos, transporte, Relogio(agora)) == 0

    assert not caminhos["anterior"].exists()
    assert [p.name for p in caminhos["mudancas"].iterdir()] == ["2026-10-18.json"]
    arquivo = arquivo_do_dia(caminhos, "2026-10-18.json")
    total = ler(caminhos["atual"])["meta"]["total_itens"]
    assert arquivo["meta"]["linha_de_base"] == {"motivo": "primeiro retrato", "total_itens": total}
    assert arquivo["meta"]["retrato_anterior"] is None
    assert arquivo["eventos"] == [] and arquivo["ressalvas"] == []
    assert ler(caminhos["atual"])["meta"]["versao_formato"] == 3


def test_atual_de_dia_anterior_em_formato_antigo_rotaciona_e_vira_linha_de_base(
    caminhos, transporte, agora
):
    assert executar_main(caminhos, transporte, Relogio(agora)) == 0
    velho = ler(caminhos["atual"])
    velho["meta"]["versao_formato"] = 2  # o formato de antes da MUD
    texto_velho = (json.dumps(velho, ensure_ascii=False, indent=2) + "\n  \n").encode("utf-8")
    caminhos["atual"].write_bytes(texto_velho)

    assert executar_main(caminhos, transporte, Relogio(agora + timedelta(days=1))) == 0

    assert caminhos["anterior"].read_bytes() == texto_velho  # a cópia é o texto original
    arquivo = arquivo_do_dia(caminhos, "2026-10-19.json")
    assert arquivo["meta"]["linha_de_base"]["motivo"] == "formato anterior incompatível"
    assert arquivo["meta"]["retrato_anterior"] == {
        "dia": "2026-10-18",
        "dados_camara_em": velho["meta"]["dados_camara_em"],
    }
    assert arquivo["eventos"] == []
    assert ler(caminhos["atual"])["meta"]["versao_formato"] == 3
    assert sorted(p.name for p in caminhos["mudancas"].iterdir()) == [
        "2026-10-18.json",
        "2026-10-19.json",
    ]


def test_a_data_do_arquivo_e_a_da_execucao_em_brasilia(caminhos, transporte):
    # 02:00 UTC de 19/10 ainda é 23:00 de 18/10 em Brasília; o lote (de 18/10) está fresco.
    from datetime import UTC

    assert (
        executar_main(caminhos, transporte, Relogio(datetime(2026, 10, 19, 2, 0, tzinfo=UTC))) == 0
    )

    assert [p.name for p in caminhos["mudancas"].iterdir()] == ["2026-10-18.json"]
    assert arquivo_do_dia(caminhos, "2026-10-18.json")["meta"]["data"] == "2026-10-18"


def test_falha_da_coleta_nao_cria_arquivo_de_mudancas(caminhos, transporte, agora, capsys):
    caminhos["config"].write_text(CONFIG_SEM_REPETICAO, encoding="utf-8")
    falha_fonte(transporte, agora)

    assert executar_main(caminhos, transporte, Relogio(agora)) == 1

    assert [p.name for p in caminhos["atual"].parent.iterdir()] == ["status.json"]
    assert not caminhos["mudancas"].exists()
    assert ler(caminhos["status"])["resultado"] == "falha"


def test_sem_as_opcoes_o_anterior_e_as_mudancas_ficam_ao_lado_do_atual(
    caminhos, transporte, agora, tmp_path
):
    argumentos = [
        "executar",
        "--config",
        str(caminhos["config"]),
        "--atual",
        str(caminhos["atual"]),
        "--status",
        str(caminhos["status"]),
    ]
    codigo = main(argumentos, transporte=transporte, relogio=Relogio(agora), dormir=Dormidas())

    assert codigo == 0
    assert (tmp_path / "data" / "mudancas" / "2026-10-18.json").exists()
    assert not (Path.cwd() / "data" / "mudancas" / "2026-10-18.json").exists()
