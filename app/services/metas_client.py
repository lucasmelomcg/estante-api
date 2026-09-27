"""Cliente HTTP da API secundária (Metas de Leitura API)."""

import logging
from datetime import date
from typing import Any

import httpx
from fastapi import status

from app.config import get_settings
from app.excecoes import ErroServicoExterno

logger = logging.getLogger(__name__)


class MetasClient:
    def __init__(self, base_url: str, api_key: str, timeout: float):
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout

    async def _requisitar(
        self,
        metodo: str,
        caminho: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"X-API-Key": self._api_key},
            ) as cliente:
                resposta = await cliente.request(metodo, caminho, json=json, params=params)
        except httpx.HTTPError as erro:
            logger.warning("Falha ao acessar a API de metas: %s", erro)
            raise ErroServicoExterno(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "O serviço de metas de leitura está indisponível no momento.",
            ) from erro

        if resposta.status_code == status.HTTP_204_NO_CONTENT:
            return None
        if resposta.is_error:
            try:
                detalhe = resposta.json().get("detail", "Erro na API de metas.")
            except ValueError:
                detalhe = "Erro na API de metas."
            if resposta.status_code >= 500 or resposta.status_code == 401:
                logger.error("API de metas respondeu %s: %s", resposta.status_code, detalhe)
                raise ErroServicoExterno(
                    status.HTTP_502_BAD_GATEWAY, "Erro ao comunicar com o serviço de metas."
                )
            raise ErroServicoExterno(resposta.status_code, detalhe)
        return resposta.json()

    # Leituras concluídas e sessões (chamadas automaticamente pela estante)

    async def registrar_leitura(
        self,
        usuario_id: int,
        livro_ref: str,
        titulo: str,
        genero: str,
        paginas: int | None,
        nota: int | None,
        data_conclusao: date,
    ) -> dict:
        return await self._requisitar(
            "POST",
            "/leituras",
            json={
                "usuario_id": usuario_id,
                "livro_ref": livro_ref,
                "titulo": titulo,
                "genero": genero,
                "paginas": paginas,
                "nota": nota,
                "data_conclusao": data_conclusao.isoformat(),
            },
        )

    async def remover_leitura(self, usuario_id: int, livro_ref: str) -> None:
        try:
            await self._requisitar("DELETE", f"/leituras/{usuario_id}/{livro_ref}")
        except ErroServicoExterno as erro:
            if erro.status_code != status.HTTP_404_NOT_FOUND:
                raise

    async def registrar_sessao(self, usuario_id: int, livro_ref: str, paginas_lidas: int) -> dict:
        return await self._requisitar(
            "POST",
            "/sessoes",
            json={"usuario_id": usuario_id, "livro_ref": livro_ref, "paginas_lidas": paginas_lidas},
        )

    async def remover_sessoes(self, usuario_id: int, livro_ref: str) -> None:
        await self._requisitar("DELETE", f"/sessoes/{usuario_id}/{livro_ref}")

    # Metas e estatísticas (repassadas pelas rotas /metas e /estatisticas)

    async def criar_meta(
        self, usuario_id: int, ano: int, meta_livros: int, meta_paginas: int | None
    ) -> dict:
        return await self._requisitar(
            "POST",
            "/metas",
            json={
                "usuario_id": usuario_id,
                "ano": ano,
                "meta_livros": meta_livros,
                "meta_paginas": meta_paginas,
            },
        )

    async def obter_meta(self, usuario_id: int, ano: int) -> dict:
        return await self._requisitar("GET", f"/metas/{usuario_id}/{ano}")

    async def atualizar_meta(
        self, usuario_id: int, ano: int, meta_livros: int, meta_paginas: int | None
    ) -> dict:
        return await self._requisitar(
            "PUT",
            f"/metas/{usuario_id}/{ano}",
            json={"meta_livros": meta_livros, "meta_paginas": meta_paginas},
        )

    async def remover_meta(self, usuario_id: int, ano: int) -> None:
        await self._requisitar("DELETE", f"/metas/{usuario_id}/{ano}")

    async def estatisticas(self, usuario_id: int, ano: int) -> dict:
        return await self._requisitar("GET", f"/estatisticas/{usuario_id}", params={"ano": ano})


def get_metas_client() -> MetasClient:
    settings = get_settings()
    return MetasClient(
        settings.metas_api_url, settings.metas_api_key, settings.http_timeout_segundos
    )
