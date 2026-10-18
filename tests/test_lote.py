import csv
from datetime import UTC, datetime, timedelta

import pytest

from conftest import FIXTURES
from monitor_comissoes.erros import ARQUIVO_INCOMPLETO, FORMATO_ALTERADO, FalhaDeColeta
from monitor_comissoes.lote import (
    AUTORES_COLUNAS,
    PROPOSICOES_COLUNAS,
    PROPOSICOES_DATAS,
    Lote,
    baixar_lote,
    ler_apensacao,
    ler_autores,
    ler_proposicoes,
    validar_arquivo,
    verificar_frescor,
)

URL_BASE = "https://dadosabertos.camara.leg.br"

# Cabeçalho sintético mínimo: as colunas que a coleta usa, mais uma que ela ignora.
CABECALHO = (*PROPOSICOES_COLUNAS, "keywords")


def linha(**valores):
    base = {
        "id": "10",
        "siglaTipo": "PL",
        "numero": "1",
        "ano": "2020",
        "ementa": "Ementa",
        "dataApresentacao": "2020-03-02T10:00:00",
        "uriPropPrincipal": "",
        "ultimoStatus_dataHora": "2024-05-06T07:08:09",
        "ultimoStatus_siglaOrgao": "CE",
        "ultimoStatus_descricaoSituacao": "Aguardando Parecer",
        "keywords": "k",
    }
    base.update(valores)
    return [base[c] for c in CABECALHO]


def escrever(tmp_path, linhas, cabecalho=CABECALHO, *, final="\r\n", bom=True):
    """CSV sintético no formato da fonte: BOM, ';', campos entre aspas, CRLF entre linhas."""
    caminho = tmp_path / "proposicoes-2020.csv"
    with open(caminho, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        w.writerow(cabecalho)
        w.writerows(linhas)
    if final == "":
        caminho.write_bytes(caminho.read_bytes().rstrip(b"\r\n"))
    return caminho


# --- leitura real -------------------------------------------------------------------------


def test_le_proposicao_real_com_todos_os_campos():
    pid = 2211957  # PL 4047/2019
    achadas = list(ler_proposicoes(FIXTURES / "proposicoes-2019.csv", ids={pid}))

    assert len(achadas) == 1
    p = achadas[0]
    assert (p.id, p.tipo, p.numero, p.ano) == (pid, "PL", 4047, 2019)
    assert p.id_principal == 1579135
    assert p.orgao == "CE"
    assert p.situacao == "Tramitando em Conjunto"
    assert p.ultimo_status_em == datetime(2026, 4, 15, 12, 22)
    assert p.data_apresentacao.year == 2019


def test_apensacao_real_so_traz_linhas_com_principal():
    pares = dict(ler_apensacao(FIXTURES / "proposicoes-2019.csv"))

    assert pares[2211957] == 1579135
    assert all(isinstance(k, int) and isinstance(v, int) for k, v in pares.items())


def test_le_autor_real():
    autores = list(ler_autores(FIXTURES / "proposicoesAutores-2022.csv", ids={2331032}))

    assert [(a.nome, a.partido_na_data, a.ordem) for a in autores] == [
        ("Lucas Gonzalez", "NOVO", 1)
    ]
    assert autores[0].id_deputado == 204523


def test_valida_arquivos_reais_e_conta_linhas():
    assert validar_arquivo(FIXTURES / "proposicoes-2019.csv", PROPOSICOES_COLUNAS) >= 2
    assert validar_arquivo(FIXTURES / "proposicoesAutores-2019.csv", AUTORES_COLUNAS) >= 2


# --- formato (sintético) ------------------------------------------------------------------


def test_le_bom_aspas_e_quebra_de_linha_dentro_do_campo(tmp_path):
    caminho = escrever(tmp_path, [linha(ementa='Linha 1\nLinha 2 com "aspas"; e ponto e vírgula')])

    [p] = list(ler_proposicoes(caminho))

    assert p.ementa == 'Linha 1\nLinha 2 com "aspas"; e ponto e vírgula'


def test_campo_muito_longo_e_aceito(tmp_path):
    caminho = escrever(tmp_path, [linha(ementa="x" * 500_000)])

    assert validar_arquivo(caminho, PROPOSICOES_COLUNAS) == 1
    assert len(next(ler_proposicoes(caminho)).ementa) == 500_000


def test_orgao_e_situacao_vazios_sao_aceitos(tmp_path):
    caminho = escrever(
        tmp_path, [linha(ultimoStatus_siglaOrgao="", ultimoStatus_descricaoSituacao="")]
    )

    [p] = list(ler_proposicoes(caminho))

    assert (p.orgao, p.situacao) == ("", "")


def test_coluna_ausente_nomeia_a_coluna(tmp_path):
    sem = [c for c in CABECALHO if c != "ultimoStatus_dataHora"]
    caminho = escrever(
        tmp_path, [[v for c, v in zip(CABECALHO, linha(), strict=True) if c in sem]], sem
    )

    with pytest.raises(FalhaDeColeta) as erro:
        validar_arquivo(caminho, PROPOSICOES_COLUNAS)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "ultimoStatus_dataHora" in erro.value.motivo


def test_linha_com_colunas_faltando_e_arquivo_incompleto(tmp_path):
    caminho = escrever(tmp_path, [linha(), linha(id="11")[:5]])

    with pytest.raises(FalhaDeColeta) as erro:
        validar_arquivo(caminho, PROPOSICOES_COLUNAS)

    assert erro.value.categoria == ARQUIVO_INCOMPLETO


def test_fim_de_arquivo_dentro_de_campo_entre_aspas_e_incompleto(tmp_path):
    caminho = escrever(tmp_path, [linha()])
    caminho.write_bytes(caminho.read_bytes() + b'"12";"PL";"2";"2020";"ementa cortada')

    with pytest.raises(FalhaDeColeta) as erro:
        validar_arquivo(caminho, PROPOSICOES_COLUNAS)

    assert erro.value.categoria == ARQUIVO_INCOMPLETO


def test_arquivo_so_com_cabecalho_e_incompleto(tmp_path):
    caminho = escrever(tmp_path, [])

    with pytest.raises(FalhaDeColeta) as erro:
        validar_arquivo(caminho, PROPOSICOES_COLUNAS)

    assert erro.value.categoria == ARQUIVO_INCOMPLETO


def test_arquivo_totalmente_vazio_e_incompleto(tmp_path):
    caminho = tmp_path / "proposicoes-2020.csv"
    caminho.write_bytes(b"")

    with pytest.raises(FalhaDeColeta) as erro:
        validar_arquivo(caminho, PROPOSICOES_COLUNAS)

    assert erro.value.categoria == ARQUIVO_INCOMPLETO


@pytest.mark.parametrize("coluna", ["dataApresentacao", "ultimoStatus_dataHora"])
@pytest.mark.parametrize("valor", ["17/10/2026", "2026-10-17", "2026-10-17 10:00:00", ""])
def test_data_fora_do_formato_e_formato_alterado(tmp_path, coluna, valor):
    caminho = escrever(tmp_path, [linha(**{coluna: valor})])

    with pytest.raises(FalhaDeColeta) as erro:
        list(ler_proposicoes(caminho))

    assert erro.value.categoria == FORMATO_ALTERADO
    assert coluna in erro.value.motivo


@pytest.mark.parametrize("coluna", PROPOSICOES_DATAS)
@pytest.mark.parametrize("valor", ["17/10/2026", "2026-10-17", "", "ontem"])
def test_validacao_confere_o_formato_das_datas_em_todas_as_linhas(tmp_path, coluna, valor):
    # A linha ruim é a segunda e nenhuma leitura posterior a consumiria.
    caminho = escrever(tmp_path, [linha(), linha(id="11", **{coluna: valor})])

    with pytest.raises(FalhaDeColeta) as erro:
        validar_arquivo(caminho, PROPOSICOES_COLUNAS, PROPOSICOES_DATAS)

    assert erro.value.categoria == FORMATO_ALTERADO
    assert coluna in erro.value.motivo
    assert "linha 3" in erro.value.motivo


def test_validacao_aceita_datas_bem_formadas(tmp_path):
    caminho = escrever(tmp_path, [linha(), linha(id="11")])

    assert validar_arquivo(caminho, PROPOSICOES_COLUNAS, PROPOSICOES_DATAS) == 2


def test_id_nao_numerico_e_formato_alterado(tmp_path):
    caminho = escrever(tmp_path, [linha(id="abc")])

    with pytest.raises(FalhaDeColeta) as erro:
        list(ler_proposicoes(caminho))

    assert erro.value.categoria == FORMATO_ALTERADO
    assert "id" in erro.value.motivo


# --- download do lote ---------------------------------------------------------------------


def test_baixa_os_dois_arquivos_de_cada_ano_do_intervalo(tmp_path, transporte):
    lote = baixar_lote(transporte, URL_BASE, 2022, 2024, tmp_path)

    assert lote.anos == (2022, 2023, 2024)
    assert sorted(transporte.arquivos_pedidos()) == sorted(
        f"{tipo}-{ano}.csv"
        for ano in (2022, 2023, 2024)
        for tipo in ("proposicoes", "proposicoesAutores")
    )
    assert lote.proposicoes(2023).exists() and lote.autores(2023).exists()


def test_last_modified_minimo_e_o_mais_antigo(tmp_path, transporte):
    transporte.last_modified["proposicoes-2023.csv"] = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)

    lote = baixar_lote(transporte, URL_BASE, 2022, 2024, tmp_path)

    assert lote.last_modified_min == datetime(2026, 10, 1, 3, 0, tzinfo=UTC)


def test_arquivo_invalido_interrompe_o_download_do_lote(tmp_path, transporte):
    transporte.transformar["proposicoes-2023.csv"] = lambda corpo: corpo.split(b"\r\n")[0]

    with pytest.raises(FalhaDeColeta) as erro:
        baixar_lote(transporte, URL_BASE, 2022, 2024, tmp_path)

    assert erro.value.categoria == ARQUIVO_INCOMPLETO
    assert "proposicoes-2023.csv" in erro.value.motivo


# --- frescor e consistência entre os arquivos do lote --------------------------------------

MINIMO = datetime(2026, 10, 17, 4, 30, tzinfo=UTC)
AGORA_UTC = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def lote_com(minimo, maximo, tmp_path):
    return Lote(
        diretorio=tmp_path, anos=(2020,), last_modified_min=minimo, last_modified_max=maximo
    )


def test_last_modified_maximo_e_o_mais_recente(tmp_path, transporte):
    # Depois de todos os Last-Modified das fixtures (18/10/2026, entre 04:33 e 05:21 UTC).
    transporte.last_modified["proposicoes-2023.csv"] = datetime(2026, 10, 18, 9, 0, tzinfo=UTC)

    lote = baixar_lote(transporte, URL_BASE, 2022, 2024, tmp_path)

    assert lote.last_modified_max == datetime(2026, 10, 18, 9, 0, tzinfo=UTC)
    assert lote.last_modified_max >= lote.last_modified_min


def test_diferenca_de_exatamente_6_horas_entre_os_arquivos_e_aceita(tmp_path):
    verificar_frescor(lote_com(MINIMO, MINIMO + timedelta(hours=6), tmp_path), AGORA_UTC)


def test_mais_de_6_horas_entre_os_arquivos_falha_com_mensagem_clara(tmp_path):
    lote = lote_com(MINIMO, MINIMO + timedelta(hours=6, seconds=1), tmp_path)

    with pytest.raises(FalhaDeColeta) as erro:
        verificar_frescor(lote, AGORA_UTC)

    assert erro.value.categoria == "arquivos_desatualizados"
    assert "momentos diferentes" in erro.value.motivo
    assert "6 horas" in erro.value.motivo


def test_idade_maxima_continua_valendo_com_arquivos_consistentes(tmp_path):
    velho = AGORA_UTC - timedelta(hours=36, minutes=1)

    with pytest.raises(FalhaDeColeta) as erro:
        verificar_frescor(lote_com(velho, velho, tmp_path), AGORA_UTC)

    assert "a Câmara não atualizou os arquivos" in erro.value.motivo
