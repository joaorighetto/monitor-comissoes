"""data/status.json: conteúdo, invariantes, base de comparação e mensagem do commit (AGE)."""

import json
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from monitor_comissoes import status as status_modulo
from monitor_comissoes.saida import serializar
from monitor_comissoes.status import (
    base_de_comparacao,
    gravar_par,
    gravar_status,
    gravar_todos,
    ler_status,
    mensagem_commit,
    montar_status,
    retrato_do_atual,
)

BRASILIA = timezone(timedelta(hours=-3))
VERIFICADO = datetime(2026, 10, 19, 3, 41, 12, tzinfo=BRASILIA)
RETRATO = {
    "gerado_em": "2026-10-19T03:41:10-03:00",
    "dados_camara_em": "2026-10-19T04:33:58+00:00",
    "total_itens": 23,
    "estoque_bruto": 1531,
}
FALHA = {"categoria": "arquivos_desatualizados", "motivo": "a Câmara não atualizou os arquivos"}
CAMPOS = [
    "versao_formato",
    "resultado",
    "verificado_em",
    "data_referencia",
    "tentativas",
    "falha",
    "variacao_aceita",
    "ultimo_retrato_bom",
]


def sucesso(**mudancas):
    dados = dict(
        resultado="ok",
        verificado_em=VERIFICADO,
        tentativas=2,
        falha=None,
        variacao_aceita=None,
        retrato=RETRATO,
    )
    dados.update(mudancas)
    return montar_status(**dados)


def falha(**mudancas):
    dados = dict(
        resultado="falha",
        verificado_em=VERIFICADO,
        tentativas=4,
        falha=FALHA,
        variacao_aceita=None,
        retrato=RETRATO,
    )
    dados.update(mudancas)
    return montar_status(**dados)


def escrever_atual(caminho, meta):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({"meta": meta, "itens": []}), encoding="utf-8")


META_ATUAL = {
    "gerado_em": RETRATO["gerado_em"],
    "dados_camara_em": RETRATO["dados_camara_em"],
    "total_itens": 23,
}


# (a) e (b) conteúdo ---------------------------------------------------------------------------


def test_status_de_sucesso_tem_os_campos_do_contrato_na_ordem_fixa():
    status = sucesso()

    assert list(status) == CAMPOS
    assert status["versao_formato"] == 1
    assert status["resultado"] == "ok"
    assert status["verificado_em"] == "2026-10-19T03:41:12-03:00"
    assert status["data_referencia"] == "2026-10-19"
    assert status["tentativas"] == 2
    assert status["falha"] is None
    assert status["variacao_aceita"] is None
    assert list(status["ultimo_retrato_bom"]) == [
        "gerado_em",
        "dados_camara_em",
        "total_itens",
        "estoque_bruto",
    ]
    assert status["ultimo_retrato_bom"] == RETRATO


def test_status_de_falha_traz_categoria_motivo_e_o_retrato_mantido():
    status = falha()

    assert list(status) == CAMPOS
    assert status["resultado"] == "falha"
    assert status["falha"] == FALHA
    assert list(status["falha"]) == ["categoria", "motivo"]
    assert status["variacao_aceita"] is None
    assert status["ultimo_retrato_bom"] == RETRATO


def test_status_de_falha_sem_retrato_tem_ultimo_retrato_bom_nulo():
    assert falha(retrato=None)["ultimo_retrato_bom"] is None


def test_variacao_aceita_so_em_sucesso():
    aceita = {"estoque_anterior": 1531, "estoque_novo": 1100, "variacao_percentual": -28.2}

    assert sucesso(variacao_aceita=aceita)["variacao_aceita"] == aceita
    with pytest.raises(ValueError):
        falha(variacao_aceita=aceita)


def test_invariantes_do_montar_status():
    with pytest.raises(ValueError):
        sucesso(falha=FALHA)  # ok com falha
    with pytest.raises(ValueError):
        sucesso(retrato=None)  # ok sem retrato bom
    with pytest.raises(ValueError):
        falha(falha=None)  # falha sem falha


# (c) data de referência ---------------------------------------------------------------------


def test_data_referencia_e_a_data_de_brasilia_mesmo_perto_da_meia_noite():
    em_brasilia = datetime(2026, 10, 19, 23, 50, tzinfo=BRASILIA)
    em_utc = datetime(2026, 10, 20, 2, 50, tzinfo=UTC)  # o mesmo instante

    for momento in (em_brasilia, em_utc):
        status = sucesso(verificado_em=momento)
        assert status["verificado_em"] == "2026-10-19T23:50:00-03:00"
        assert status["data_referencia"] == "2026-10-19"


# (d) e (e) repetibilidade e ausência de resto ----------------------------------------------


def test_mesma_entrada_gera_texto_identico():
    assert serializar(sucesso()) == serializar(sucesso())
    assert serializar(falha()) == serializar(falha())


def test_sucesso_depois_de_falha_nao_carrega_resto_da_falha():
    depois = sucesso(verificado_em=VERIFICADO + timedelta(hours=2))

    assert depois["falha"] is None
    assert "arquivos_desatualizados" not in serializar(depois)


# (f) retrato do atual.json --------------------------------------------------------------------


def test_retrato_do_atual_le_o_meta(tmp_path):
    atual = tmp_path / "data" / "atual.json"
    escrever_atual(atual, {**META_ATUAL, "outro": "ignorado"})

    assert retrato_do_atual(atual) == META_ATUAL


@pytest.mark.parametrize(
    "conteudo",
    [
        None,  # arquivo ausente
        '{"sentinela": true}',
        "isto não é json",
        json.dumps({"meta": {**META_ATUAL, "total_itens": "23"}, "itens": []}),
        json.dumps({"meta": {k: v for k, v in META_ATUAL.items() if k != "gerado_em"}}),
    ],
)
def test_retrato_do_atual_sem_meta_valido_e_nulo_e_nao_altera_o_arquivo(tmp_path, conteudo):
    atual = tmp_path / "atual.json"
    if conteudo is not None:
        atual.write_text(conteudo, encoding="utf-8")

    assert retrato_do_atual(atual) is None
    if conteudo is not None:
        assert atual.read_text(encoding="utf-8") == conteudo


# (g) base de comparação -----------------------------------------------------------------------


def preparar_base(tmp_path, meta=META_ATUAL, status=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    atual, arquivo_status = tmp_path / "atual.json", tmp_path / "status.json"
    if meta is not None:
        escrever_atual(atual, meta)
    if status is not None:
        arquivo_status.write_text(serializar(status), encoding="utf-8")
    return atual, arquivo_status


def test_base_e_o_estoque_do_status_quando_o_gerado_em_confere(tmp_path):
    atual, status = preparar_base(tmp_path, status=sucesso())

    assert base_de_comparacao(atual, status) == 1531


def test_base_vale_tambem_depois_de_uma_falha_pois_o_retrato_e_o_mantido(tmp_path):
    atual, status = preparar_base(tmp_path, status=falha())

    assert base_de_comparacao(atual, status) == 1531


def test_base_e_nula_se_o_gerado_em_do_status_difere_do_atual(tmp_path):
    outro = {**RETRATO, "gerado_em": "2026-10-18T03:41:10-03:00"}
    atual, status = preparar_base(tmp_path, status=sucesso(retrato=outro))

    assert base_de_comparacao(atual, status) is None


def test_base_e_nula_sem_um_dos_arquivos_ou_com_status_invalido(tmp_path):
    atual, status = preparar_base(tmp_path / "a", status=None)
    assert base_de_comparacao(atual, status) is None  # só o atual

    atual, status = preparar_base(tmp_path / "b", meta=None, status=sucesso())
    assert base_de_comparacao(atual, status) is None  # só o status

    atual, status = preparar_base(tmp_path / "c")
    status.write_text("{ não é json", encoding="utf-8")
    assert base_de_comparacao(atual, status) is None  # status inválido


def test_base_e_nula_quando_o_status_nao_tem_estoque_bruto(tmp_path):
    sem_estoque = {**RETRATO, "estoque_bruto": None}
    atual, status = preparar_base(tmp_path, status=falha(retrato=sem_estoque))

    assert base_de_comparacao(atual, status) is None


# (h) ler status -------------------------------------------------------------------------------


def test_ler_status_devolve_o_documento_gravado(tmp_path):
    caminho = tmp_path / "data" / "status.json"
    gravar_status(sucesso(), caminho)

    assert ler_status(caminho) == sucesso()
    assert caminho.read_text(encoding="utf-8") == serializar(sucesso())


def test_ler_status_ausente_e_nulo(tmp_path):
    assert ler_status(tmp_path / "nao-existe.json") is None


@pytest.mark.parametrize(
    "conteudo",
    [
        "{ não é json",
        "[]",
        json.dumps({**sucesso(), "falha": FALHA}),  # ok com falha
        json.dumps({**sucesso(), "ultimo_retrato_bom": None}),  # ok sem retrato
        json.dumps({**falha(), "falha": None}),  # falha sem falha
        json.dumps({**falha(), "variacao_aceita": {"estoque_anterior": 1}}),
        json.dumps({k: v for k, v in sucesso().items() if k != "tentativas"}),
        json.dumps({**sucesso(), "resultado": "talvez"}),
    ],
)
def test_ler_status_invalido_levanta_erro_claro(tmp_path, conteudo):
    caminho = tmp_path / "status.json"
    caminho.write_text(conteudo, encoding="utf-8")

    with pytest.raises(ValueError, match="status"):
        ler_status(caminho)


# (i) mensagem do commit ---------------------------------------------------------------------


def test_mensagem_de_sucesso():
    assert mensagem_commit(sucesso()) == "dados: 2026-10-19 · ok · 23 itens · estoque bruto 1531"


def test_mensagem_de_sucesso_com_variacao_aceita():
    aceita = {"estoque_anterior": 1531, "estoque_novo": 1100, "variacao_percentual": -28.2}
    retrato = {**RETRATO, "estoque_bruto": 1100}
    status = sucesso(
        verificado_em=datetime(2027, 2, 1, 9, 12, tzinfo=BRASILIA),
        variacao_aceita=aceita,
        retrato=retrato,
    )

    assert mensagem_commit(status) == (
        "dados: 2027-02-01 · ok · variação aceita manualmente (1531 → 1100, -28,2%)"
    )


def test_mensagem_de_variacao_aceita_para_alta_traz_o_sinal_de_mais():
    aceita = {"estoque_anterior": 1000, "estoque_novo": 1250, "variacao_percentual": 25.0}
    status = sucesso(variacao_aceita=aceita)

    assert "(1000 → 1250, +25,0%)" in mensagem_commit(status)


def test_mensagem_de_falha():
    assert mensagem_commit(falha()) == "dados: 2026-10-19 · falha [arquivos_desatualizados]"


# (j) gravação do par -----------------------------------------------------------------------


def test_gravar_par_substitui_os_dois_destinos(tmp_path):
    atual, status = tmp_path / "data" / "atual.json", tmp_path / "data" / "status.json"

    gravar_par({"meta": {}, "itens": []}, atual, sucesso(), status)

    assert json.loads(atual.read_text(encoding="utf-8")) == {"meta": {}, "itens": []}
    assert ler_status(status) == sucesso()
    assert sorted(p.name for p in atual.parent.iterdir()) == ["atual.json", "status.json"]


def test_gravar_par_com_falha_ao_preparar_o_segundo_nao_troca_nenhum(tmp_path):
    atual, status = tmp_path / "atual.json", tmp_path / "status.json"
    atual.write_text('{"anterior": 1}\n', encoding="utf-8")
    status.write_text('{"anterior": 2}\n', encoding="utf-8")

    with pytest.raises(TypeError):  # um conjunto não é serializável em JSON
        gravar_par({"novo": 1}, atual, {"invalido": {1, 2}}, status)

    assert atual.read_text(encoding="utf-8") == '{"anterior": 1}\n'
    assert status.read_text(encoding="utf-8") == '{"anterior": 2}\n'
    assert sorted(p.name for p in tmp_path.iterdir()) == ["atual.json", "status.json"]


def test_gravar_status_sozinho_grava_so_o_status(tmp_path):
    status = tmp_path / "data" / "status.json"

    gravar_status(falha(), status)

    assert sorted(p.name for p in status.parent.iterdir()) == ["status.json"]


def falhar_troca_do(monkeypatch, destino_que_falha):
    original = os.replace

    def falso(origem, destino):
        if Path(destino) == destino_que_falha:
            raise OSError("falha simulada na troca")
        return original(origem, destino)

    monkeypatch.setattr(os, "replace", falso)


def test_gravar_par_restaura_o_primeiro_se_a_troca_do_segundo_falhar(tmp_path, monkeypatch):
    atual, status = tmp_path / "atual.json", tmp_path / "status.json"
    atual.write_text('{"anterior": 1}\n', encoding="utf-8")
    status.write_text('{"anterior": 2}\n', encoding="utf-8")
    falhar_troca_do(monkeypatch, status)

    with pytest.raises(OSError, match="falha simulada"):
        gravar_par({"novo": 1}, atual, sucesso(), status)

    assert atual.read_text(encoding="utf-8") == '{"anterior": 1}\n'
    assert status.read_text(encoding="utf-8") == '{"anterior": 2}\n'
    assert sorted(p.name for p in tmp_path.iterdir()) == ["atual.json", "status.json"]


def test_gravar_par_remove_o_primeiro_se_ele_nao_existia_e_a_troca_do_segundo_falhar(
    tmp_path, monkeypatch
):
    atual, status = tmp_path / "data" / "atual.json", tmp_path / "data" / "status.json"
    falhar_troca_do(monkeypatch, status)

    with pytest.raises(OSError, match="falha simulada"):
        gravar_par({"novo": 1}, atual, sucesso(), status)

    assert not atual.exists()
    assert not status.exists()
    assert list(atual.parent.iterdir()) == []


def test_gravar_par_com_dupla_falha_propaga_a_causa_original_com_nota(tmp_path, monkeypatch):
    atual, status = tmp_path / "atual.json", tmp_path / "status.json"
    atual.write_text('{"anterior": 1}\n', encoding="utf-8")
    falhar_troca_do(monkeypatch, status)

    def restauracao_quebrada(destino, anterior):
        raise OSError("restauração quebrada")

    monkeypatch.setattr("monitor_comissoes.status._restaurar", restauracao_quebrada)

    with pytest.raises(OSError, match="falha simulada") as erro:
        gravar_par({"novo": 1}, atual, sucesso(), status)

    assert any("restauração" in nota for nota in erro.value.__notes__)


# (k) gravação de N arquivos (MUD) ---------------------------------------------------------------


def quatro(tmp_path):
    return [tmp_path / "data" / nome for nome in ("a.json", "b.json", "mudancas/c.json", "d.json")]


def textos(destinos, rotulo):
    return [(f"{rotulo}-{d.name}\n", d) for d in destinos]


def conteudo(destinos):
    return {d.name: d.read_text(encoding="utf-8") if d.exists() else None for d in destinos}


def arquivos_da_pasta(pasta):
    return sorted(str(p.relative_to(pasta)) for p in pasta.rglob("*") if p.is_file())


def test_gravar_todos_substitui_todos_os_destinos_e_cria_pastas(tmp_path):
    destinos = quatro(tmp_path)
    destinos[0].parent.mkdir(parents=True)
    destinos[0].write_text("velho\n", encoding="utf-8")

    gravar_todos(textos(destinos, "novo"))

    assert conteudo(destinos) == {d.name: f"novo-{d.name}\n" for d in destinos}
    assert arquivos_da_pasta(tmp_path) == [
        "data/a.json",
        "data/b.json",
        "data/d.json",
        "data/mudancas/c.json",
    ]


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_gravar_todos_com_falha_ao_preparar_o_k_esimo_nao_troca_nenhum(tmp_path, monkeypatch, k):
    destinos = quatro(tmp_path)
    for d in destinos:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(f"velho-{d.name}\n", encoding="utf-8")
    antes = conteudo(destinos)
    original = status_modulo.escrever_temporario
    chamadas = []

    def falso(texto, destino):
        chamadas.append(destino)
        if len(chamadas) == k:
            raise OSError("disco cheio (simulado)")
        return original(texto, destino)

    monkeypatch.setattr(status_modulo, "escrever_temporario", falso)

    with pytest.raises(OSError, match="disco cheio"):
        gravar_todos(textos(destinos, "novo"))

    assert conteudo(destinos) == antes
    assert arquivos_da_pasta(tmp_path) == [
        "data/a.json",
        "data/b.json",
        "data/d.json",
        "data/mudancas/c.json",
    ]


@pytest.mark.parametrize("k", [2, 3, 4])
def test_gravar_todos_com_falha_na_troca_do_k_esimo_restaura_os_anteriores_em_ordem_inversa(
    tmp_path, monkeypatch, k
):
    destinos = quatro(tmp_path)
    for d in destinos:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(f"velho-{d.name}\n", encoding="utf-8")
    antes = conteudo(destinos)
    falhar_troca_do(monkeypatch, destinos[k - 1])
    restauradas = []
    original = status_modulo._restaurar

    def espiao(destino, anterior):
        restauradas.append(destino)
        return original(destino, anterior)

    monkeypatch.setattr(status_modulo, "_restaurar", espiao)

    with pytest.raises(OSError, match="falha simulada"):
        gravar_todos(textos(destinos, "novo"))

    assert conteudo(destinos) == antes
    assert restauradas == list(reversed(destinos[: k - 1]))
    assert len(arquivos_da_pasta(tmp_path)) == 4  # nenhum temporário sobra


@pytest.mark.parametrize("k", [2, 3, 4])
def test_gravar_todos_com_falha_ao_ler_o_conteudo_anterior_do_k_esimo_nao_troca_nenhum(
    tmp_path, monkeypatch, k
):
    destinos = quatro(tmp_path)
    for d in destinos:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(f"velho-{d.name}\n", encoding="utf-8")
    antes = conteudo(destinos)
    alvo = destinos[k - 1]
    original = Path.read_bytes

    def leitura_quebrada(self):
        if self == alvo:
            raise PermissionError("leitura negada (simulada)")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", leitura_quebrada)

    with pytest.raises(PermissionError, match="leitura negada"):
        gravar_todos(textos(destinos, "novo"))

    assert conteudo(destinos) == antes
    assert len(arquivos_da_pasta(tmp_path)) == 4  # nenhum temporário sobra


def test_gravar_todos_remove_os_que_nao_existiam_se_uma_troca_posterior_falhar(
    tmp_path, monkeypatch
):
    destinos = quatro(tmp_path)
    destinos[0].parent.mkdir(parents=True)
    destinos[0].write_text("velho\n", encoding="utf-8")  # só o primeiro existia
    falhar_troca_do(monkeypatch, destinos[3])

    with pytest.raises(OSError, match="falha simulada"):
        gravar_todos(textos(destinos, "novo"))

    assert destinos[0].read_text(encoding="utf-8") == "velho\n"
    assert arquivos_da_pasta(tmp_path) == ["data/a.json"]


def test_gravar_todos_com_falha_ao_restaurar_continua_restaurando_e_anota_a_causa(
    tmp_path, monkeypatch
):
    destinos = quatro(tmp_path)
    for d in destinos:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(f"velho-{d.name}\n", encoding="utf-8")
    falhar_troca_do(monkeypatch, destinos[3])
    tentativas = []
    original = status_modulo._restaurar

    def primeira_quebra(destino, anterior):
        tentativas.append(destino)
        if len(tentativas) == 1:
            raise OSError("restauração quebrada")
        return original(destino, anterior)

    monkeypatch.setattr(status_modulo, "_restaurar", primeira_quebra)

    with pytest.raises(OSError, match="falha simulada") as erro:
        gravar_todos(textos(destinos, "novo"))

    assert tentativas == list(reversed(destinos[:3]))  # as outras duas foram tentadas
    assert any("restauração" in nota for nota in erro.value.__notes__)
    assert destinos[0].read_text(encoding="utf-8") == "velho-a.json\n"
    assert destinos[1].read_text(encoding="utf-8") == "velho-b.json\n"


# --- Aceito sem base de comparação --------------------------------------------------------------

SEM_BASE = {"estoque_anterior": None, "estoque_novo": 1531, "variacao_percentual": None}


def test_variacao_aceita_sem_base_tem_o_numero_anterior_e_o_percentual_nulos():
    status = sucesso(variacao_aceita=SEM_BASE)

    assert status["variacao_aceita"] == SEM_BASE
    assert ler_status_de(status) == status


def ler_status_de(status):
    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "status.json"
        gravar_status(status, caminho)
        return ler_status(caminho)


@pytest.mark.parametrize(
    "invalida",
    [
        {"estoque_anterior": None, "estoque_novo": 1531, "variacao_percentual": -1.0},
        {"estoque_anterior": 1531, "estoque_novo": 1100, "variacao_percentual": None},
        {"estoque_anterior": None, "estoque_novo": None, "variacao_percentual": None},
        {"estoque_anterior": "1531", "estoque_novo": 1100, "variacao_percentual": -28.2},
    ],
)
def test_variacao_aceita_com_nulos_so_vale_os_dois_juntos_e_com_estoque_novo(invalida):
    with pytest.raises(ValueError, match="status"):
        sucesso(variacao_aceita=invalida)


def test_mensagem_do_aceito_sem_base_de_comparacao():
    assert mensagem_commit(sucesso(variacao_aceita=SEM_BASE)) == (
        "dados: 2026-10-19 · ok · aceito sem base de comparação (estoque bruto 1531)"
    )
