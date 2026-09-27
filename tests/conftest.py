import os
import tempfile

import pytest

_DB_TEMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_TEMP.name}"
os.environ["JWT_SECRET"] = "segredo-de-teste-com-pelo-menos-32-bytes"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.catalogo import (  # noqa: E402
    LivroCatalogo,
    LivroCatalogoDetalhe,
    ResultadoBusca,
)
from app.services.metas_client import get_metas_client  # noqa: E402
from app.services.open_library import get_open_library  # noqa: E402

LIVROS_FALSOS = {
    "OL1003040W": LivroCatalogoDetalhe(
        livro_ref="OL1003040W",
        titulo="Dom Casmurro",
        autores=["Machado de Assis"],
        ano_publicacao=1900,
        total_paginas=268,
        genero="Ficção",
        descricao="Bentinho e Capitu.",
    ),
    "OL27448W": LivroCatalogoDetalhe(
        livro_ref="OL27448W",
        titulo="The Lord of the Rings",
        autores=["J.R.R. Tolkien"],
        ano_publicacao=1954,
        total_paginas=1193,
        genero="Fantasia",
    ),
}


class OpenLibraryFalsa:
    async def buscar(self, termo, pagina, limite):
        livros = [
            LivroCatalogo(**livro.model_dump(exclude={"descricao"}))
            for livro in LIVROS_FALSOS.values()
            if termo.lower() in livro.titulo.lower()
        ]
        return ResultadoBusca(termo=termo, total=len(livros), pagina=pagina, limite=limite, livros=livros)

    async def obter_livro(self, livro_ref):
        return LIVROS_FALSOS.get(livro_ref)

    async def livros_por_assunto(self, assunto, limite):
        return [
            LivroCatalogo(livro_ref=f"OL{i}W", titulo=f"{assunto} {i}", autores=[], genero="Fantasia")
            for i in range(limite)
        ]


class MetasFalsa:
    """Registra as chamadas feitas para a API de metas."""

    def __init__(self):
        self.chamadas: list[tuple] = []

    async def registrar_leitura(self, **dados):
        self.chamadas.append(("registrar_leitura", dados["livro_ref"], dados["nota"]))

    async def remover_leitura(self, usuario_id, livro_ref):
        self.chamadas.append(("remover_leitura", livro_ref))

    async def registrar_sessao(self, usuario_id, livro_ref, paginas_lidas):
        self.chamadas.append(("registrar_sessao", livro_ref, paginas_lidas))

    async def remover_sessoes(self, usuario_id, livro_ref):
        self.chamadas.append(("remover_sessoes", livro_ref))

    async def criar_meta(self, usuario_id, ano, meta_livros, meta_paginas):
        self.chamadas.append(("criar_meta", ano, meta_livros))
        return {
            "id": 1,
            "usuario_id": usuario_id,
            "ano": ano,
            "meta_livros": meta_livros,
            "meta_paginas": meta_paginas,
            "criada_em": "2026-01-01T00:00:00Z",
            "atualizada_em": "2026-01-01T00:00:00Z",
        }


@pytest.fixture
def metas_falsa():
    return MetasFalsa()


@pytest.fixture
def client(metas_falsa):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_open_library] = OpenLibraryFalsa
    app.dependency_overrides[get_metas_client] = lambda: metas_falsa
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def autenticado(client):
    client.post(
        "/auth/registro",
        json={"nome": "Ana", "email": "ana@email.com", "senha": "senhaSegura123"},
    )
    token = client.post(
        "/auth/login", data={"username": "ana@email.com", "password": "senhaSegura123"}
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
