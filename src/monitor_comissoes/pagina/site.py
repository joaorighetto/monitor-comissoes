"""O conjunto de arquivos da página e sua gravação (PAG, R9; contracts/site.md).

O site inteiro é montado na memória como `{caminho relativo: bytes}`. A gravação prepara todos os
arquivos como temporários e só então os troca: um erro na preparação não deixa nenhum arquivo novo.
Um erro durante a troca (raro: disco cheio, permissão) pode deixar parte dos arquivos novos e parte
dos antigos na pasta; no workflow isso não chega ao leitor, porque a falha impede o upload.
"""

import os
from pathlib import Path, PurePosixPath

from ..erros import FalhaDePagina
from . import html, tabela
from .modelo import Pagina

ESTATICO = Path(__file__).parent / "estatico"
# O que `estatico/` publica. O `LEIAME.md` é só documentação do repositório.
PUBLICADOS = ("estilo.css", "pagina.js")


FONTES_ESPERADAS = 4  # Schibsted Grotesk (variável) e IBM Plex Mono 400, 500 e 600


def copiar_estaticos() -> dict[str, bytes]:
    """O CSS, o JS e as fontes do DS, lidos de `estatico/`.

    Falta de um arquivo publicado ou de alguma fonte é falha: uma página sem estilo ou sem fonte
    nunca pode ser publicada como se estivesse completa (constituição, III).
    """
    arquivos = {}
    for nome in PUBLICADOS:
        caminho = ESTATICO / nome
        if not caminho.is_file():
            raise FalhaDePagina(f"arquivo estático {caminho} não existe")
        arquivos[nome] = caminho.read_bytes()
    fontes = sorted((ESTATICO / "fontes").glob("*.woff2"))
    if len(fontes) != FONTES_ESPERADAS:
        raise FalhaDePagina(
            f"{ESTATICO / 'fontes'}: esperadas {FONTES_ESPERADAS} fontes .woff2, "
            f"encontradas {len(fontes)}"
        )
    for fonte in fontes:
        arquivos[f"fontes/{fonte.name}"] = fonte.read_bytes()
    return arquivos


def montar(pagina: Pagina, atual: bytes, itens: list[dict]) -> dict[str, bytes]:
    """Todos os arquivos do site, na memória: `{caminho relativo: bytes}`.

    `atual` são os bytes do `atual.json` como estão no disco (a cópia é byte a byte) e `itens` os
    itens do retrato, na ordem da lista, para o CSV.
    """
    arquivos = copiar_estaticos()
    arquivos["index.html"] = html.renderizar(pagina).encode("utf-8")
    arquivos["atual.json"] = atual
    arquivos["itens.csv"] = tabela.renderizar(itens)
    return arquivos


def _caminho_seguro(nome: str) -> PurePosixPath:
    caminho = PurePosixPath(nome)
    if not nome or caminho.is_absolute() or ".." in caminho.parts or "\\" in nome:
        raise FalhaDePagina(f"caminho de saída inválido: {nome!r}")
    return caminho


def _falha_de_gravacao(caminho: Path, erro: OSError) -> FalhaDePagina:
    return FalhaDePagina(f"não foi possível gravar {caminho}: {erro.strerror or erro}")


def gravar(arquivos: dict[str, bytes], saida: Path) -> None:
    """Grava cada arquivo em `saida`, que é criada se não existir.

    Sobrescreve os arquivos de nome fixo e não apaga os outros da pasta.
    """
    if not arquivos:
        raise FalhaDePagina("nenhum arquivo para gravar")
    saida = Path(saida)
    destinos = {nome: saida.joinpath(*_caminho_seguro(nome).parts) for nome in arquivos}

    temporarios: list[tuple[Path, Path]] = []
    try:
        for nome, destino in destinos.items():
            try:
                destino.parent.mkdir(parents=True, exist_ok=True)
                temporario = destino.with_name(destino.name + ".tmp")
                temporario.write_bytes(arquivos[nome])
            except OSError as erro:
                raise _falha_de_gravacao(destino, erro) from erro
            temporarios.append((temporario, destino))
        for temporario, destino in temporarios:
            try:
                os.replace(temporario, destino)
            except OSError as erro:
                raise _falha_de_gravacao(destino, erro) from erro
    finally:
        for temporario, _ in temporarios:
            temporario.unlink(missing_ok=True)
