"""Uma árvore mínima do HTML gerado, para os testes conferirem estrutura e texto sem regex."""

import re
from html.parser import HTMLParser

VAZIOS = {"meta", "link", "br", "input", "img", "hr"}


class No:
    def __init__(self, tag: str, attrs: dict[str, str | None], pai: "No | None" = None):
        self.tag = tag
        self.attrs = attrs
        self.pai = pai
        self.filhos: list[No | str] = []

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    @property
    def texto(self) -> str:
        """O texto de dentro, sem as tags, com espaços normalizados."""
        partes = [f if isinstance(f, str) else f.texto for f in self.filhos]
        return re.sub(r"\s+", " ", " ".join(partes)).strip()

    def percorrer(self):
        yield self
        for filho in self.filhos:
            if isinstance(filho, No):
                yield from filho.percorrer()

    def achar(self, tag=None, id=None, classe=None, **atributos) -> list["No"]:
        achados = []
        for no in self.percorrer():
            if tag is not None and no.tag != tag:
                continue
            if id is not None and no.attrs.get("id") != id:
                continue
            if classe is not None and classe not in no.classes:
                continue
            if any(no.attrs.get(k.replace("_", "-")) != v for k, v in atributos.items()):
                continue
            achados.append(no)
        return achados

    def um(self, **filtros) -> "No":
        achados = self.achar(**filtros)
        assert len(achados) == 1, (filtros, len(achados))
        return achados[0]

    def tem_atributo(self, nome: str) -> bool:
        return nome in self.attrs


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = No("#documento", {})
        self.atual = self.raiz

    def handle_starttag(self, tag, attrs):
        no = No(tag, dict(attrs), self.atual)
        self.atual.filhos.append(no)
        if tag not in VAZIOS:
            self.atual = no

    def handle_endtag(self, tag):
        if tag in VAZIOS:
            return
        no = self.atual
        while no is not self.raiz and no.tag != tag:
            no = no.pai
        self.atual = no.pai if no is not self.raiz else self.raiz

    def handle_data(self, dados):
        self.atual.filhos.append(dados)


def parse(html: str) -> No:
    parser = _Parser()
    parser.feed(html)
    parser.close()
    return parser.raiz
