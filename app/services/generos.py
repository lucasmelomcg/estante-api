"""Traduz os assuntos (subjects) da Open Library para gêneros em português."""

from dataclasses import dataclass

GENERO_PADRAO = "Outros"


@dataclass(frozen=True)
class Genero:
    nome: str
    assunto_open_library: str
    palavras_chave: tuple[str, ...]


# A ordem importa: os gêneros mais específicos vêm antes dos mais genéricos
# (ex.: "Fantasia" antes de "Ficção"), pois vence o primeiro que casar.
GENEROS: tuple[Genero, ...] = (
    Genero("Fantasia", "fantasy", ("fantasy", "magic", "wizards", "dragons")),
    Genero("Ficção científica", "science_fiction", ("science fiction", "dystopia", "space")),
    Genero("Terror", "horror", ("horror", "ghost", "vampire", "supernatural")),
    Genero(
        "Mistério e suspense",
        "mystery_and_detective_stories",
        ("mystery", "detective", "thriller", "suspense", "crime"),
    ),
    Genero("Romance", "romance", ("romance", "love stories")),
    Genero("Infantojuvenil", "juvenile_fiction", ("juvenile", "children", "young adult")),
    Genero("Poesia", "poetry", ("poetry", "poems")),
    Genero("Biografia", "biography", ("biography", "autobiography", "memoir")),
    Genero("Autoajuda", "self-help", ("self-help", "self-actualization", "success", "personal development")),
    Genero("Negócios", "business", ("business", "economics", "management", "finance")),
    Genero("Tecnologia", "computers", ("computer", "programming", "software", "technology")),
    Genero("Filosofia", "philosophy", ("philosophy",)),
    Genero("Ficção", "fiction", ("fiction", "novel", "literature")),
    Genero("História", "history", ("history", "historical")),
)

_POR_NOME = {genero.nome: genero for genero in GENEROS}


def inferir_genero(assuntos: list[str] | None) -> str:
    """Escolhe o gênero em português a partir da lista de assuntos de um livro."""
    assuntos_normalizados = [assunto.lower() for assunto in assuntos or []]
    for genero in GENEROS:
        for assunto in assuntos_normalizados:
            if any(palavra in assunto for palavra in genero.palavras_chave):
                return genero.nome
    return GENERO_PADRAO


def assunto_open_library(nome_genero: str) -> str | None:
    genero = _POR_NOME.get(nome_genero)
    return genero.assunto_open_library if genero else None


def nomes_generos() -> list[str]:
    return [genero.nome for genero in GENEROS] + [GENERO_PADRAO]
