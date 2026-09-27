"""Cliente da Open Library (https://openlibrary.org/developers/api).

Os dados da API externa são consumidos e convertidos para o formato da Estante;
o usuário nunca é redirecionado para o site da Open Library.
"""

import logging
from typing import Any

import httpx
from fastapi import status

from app.config import get_settings
from app.excecoes import ErroServicoExterno
from app.schemas.catalogo import LivroCatalogo, LivroCatalogoDetalhe, ResultadoBusca
from app.services.generos import inferir_genero

logger = logging.getLogger(__name__)

CAMPOS_BUSCA = "key,title,author_name,first_publish_year,number_of_pages_median,cover_i,subject"
URL_CAPAS = "https://covers.openlibrary.org/b/id/{capa_id}-M.jpg"
MAX_ASSUNTOS = 8


def _capa_url(capa_id: int | None) -> str | None:
    if not capa_id or capa_id < 0:
        return None
    return URL_CAPAS.format(capa_id=capa_id)


def _livro_ref(chave: str) -> str:
    """Converte "/works/OL1003040W" em "OL1003040W"."""
    return chave.rsplit("/", 1)[-1]


def _livro_da_busca(documento: dict[str, Any]) -> LivroCatalogo:
    assuntos = documento.get("subject") or []
    return LivroCatalogo(
        livro_ref=_livro_ref(documento["key"]),
        titulo=documento.get("title", "Sem título"),
        autores=documento.get("author_name") or [],
        ano_publicacao=documento.get("first_publish_year"),
        total_paginas=documento.get("number_of_pages_median"),
        capa_url=_capa_url(documento.get("cover_i")),
        genero=inferir_genero(assuntos),
        assuntos=assuntos[:MAX_ASSUNTOS],
    )


def _livro_do_assunto(obra: dict[str, Any]) -> LivroCatalogo:
    assuntos = obra.get("subject") or []
    return LivroCatalogo(
        livro_ref=_livro_ref(obra["key"]),
        titulo=obra.get("title", "Sem título"),
        autores=[autor["name"] for autor in obra.get("authors", []) if "name" in autor],
        ano_publicacao=obra.get("first_publish_year"),
        capa_url=_capa_url(obra.get("cover_id")),
        genero=inferir_genero(assuntos),
        assuntos=assuntos[:MAX_ASSUNTOS],
    )


def _extrair_descricao(obra: dict[str, Any]) -> str | None:
    descricao = obra.get("description")
    if isinstance(descricao, dict):
        return descricao.get("value")
    return descricao


class OpenLibraryClient:
    def __init__(self, base_url: str, timeout: float):
        self._base_url = base_url
        self._timeout = timeout

    async def _get(self, caminho: str, params: dict[str, Any] | None = None) -> dict | None:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": "EstanteDeLeitura/1.0 (projeto academico)"},
            ) as cliente:
                resposta = await cliente.get(caminho, params=params)
        except httpx.HTTPError as erro:
            logger.warning("Falha ao acessar a Open Library: %s", erro)
            raise ErroServicoExterno(
                status.HTTP_502_BAD_GATEWAY,
                "Não foi possível consultar a Open Library no momento. Tente novamente.",
            ) from erro

        if resposta.status_code == status.HTTP_404_NOT_FOUND:
            return None
        if resposta.is_error:
            logger.warning("Open Library respondeu %s em %s", resposta.status_code, caminho)
            raise ErroServicoExterno(
                status.HTTP_502_BAD_GATEWAY,
                "A Open Library retornou um erro. Tente novamente mais tarde.",
            )
        return resposta.json()

    async def buscar(self, termo: str, pagina: int, limite: int) -> ResultadoBusca:
        dados = await self._get(
            "/search.json",
            {"q": termo, "page": pagina, "limit": limite, "fields": CAMPOS_BUSCA},
        ) or {}
        return ResultadoBusca(
            termo=termo,
            total=dados.get("numFound", 0),
            pagina=pagina,
            limite=limite,
            livros=[_livro_da_busca(doc) for doc in dados.get("docs", []) if "key" in doc],
        )

    async def obter_livro(self, livro_ref: str) -> LivroCatalogoDetalhe | None:
        busca = await self._get(
            "/search.json",
            {"q": f"key:/works/{livro_ref}", "limit": 1, "fields": CAMPOS_BUSCA},
        )
        documentos = (busca or {}).get("docs", [])
        if not documentos:
            return None

        obra = await self._get(f"/works/{livro_ref}.json") or {}
        return LivroCatalogoDetalhe(
            **_livro_da_busca(documentos[0]).model_dump(),
            descricao=_extrair_descricao(obra),
        )

    async def livros_por_assunto(self, assunto: str, limite: int) -> list[LivroCatalogo]:
        dados = await self._get(f"/subjects/{assunto}.json", {"limit": limite}) or {}
        return [_livro_do_assunto(obra) for obra in dados.get("works", []) if "key" in obra]


def get_open_library() -> OpenLibraryClient:
    settings = get_settings()
    return OpenLibraryClient(settings.open_library_url, settings.http_timeout_segundos)
