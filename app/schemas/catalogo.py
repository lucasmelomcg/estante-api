from pydantic import BaseModel


class LivroCatalogo(BaseModel):
    """Livro retornado pela Open Library, já normalizado para o formato da Estante."""

    livro_ref: str
    titulo: str
    autores: list[str]
    ano_publicacao: int | None = None
    total_paginas: int | None = None
    capa_url: str | None = None
    genero: str
    assuntos: list[str] = []


class LivroCatalogoDetalhe(LivroCatalogo):
    descricao: str | None = None


class ResultadoBusca(BaseModel):
    termo: str
    total: int
    pagina: int
    limite: int
    livros: list[LivroCatalogo]


class Recomendacoes(BaseModel):
    genero_base: str
    motivo: str
    livros: list[LivroCatalogo]
