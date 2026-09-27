from datetime import date

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.models import Usuario
from app.schemas.metas import Estatisticas, MetaAtualizar, MetaCriar, MetaResposta
from app.services.metas_client import MetasClient, get_metas_client
from app.services.seguranca import get_usuario_atual

router = APIRouter(tags=["Metas e estatísticas"])

ANO = Path(ge=2000, le=2100, examples=[2026])


@router.post(
    "/metas",
    response_model=MetaResposta,
    status_code=status.HTTP_201_CREATED,
    summary="Define a meta de leitura do ano",
)
async def criar_meta(
    dados: MetaCriar,
    usuario: Usuario = Depends(get_usuario_atual),
    metas: MetasClient = Depends(get_metas_client),
):
    return await metas.criar_meta(usuario.id, dados.ano, dados.meta_livros, dados.meta_paginas)


@router.get("/metas/{ano}", response_model=MetaResposta, summary="Consulta a meta de um ano")
async def obter_meta(
    ano: int = ANO,
    usuario: Usuario = Depends(get_usuario_atual),
    metas: MetasClient = Depends(get_metas_client),
):
    return await metas.obter_meta(usuario.id, ano)


@router.put("/metas/{ano}", response_model=MetaResposta, summary="Altera a meta de um ano")
async def atualizar_meta(
    dados: MetaAtualizar,
    ano: int = ANO,
    usuario: Usuario = Depends(get_usuario_atual),
    metas: MetasClient = Depends(get_metas_client),
):
    return await metas.atualizar_meta(usuario.id, ano, dados.meta_livros, dados.meta_paginas)


@router.delete(
    "/metas/{ano}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a meta de um ano"
)
async def remover_meta(
    ano: int = ANO,
    usuario: Usuario = Depends(get_usuario_atual),
    metas: MetasClient = Depends(get_metas_client),
):
    await metas.remover_meta(usuario.id, ano)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/estatisticas",
    response_model=Estatisticas,
    summary="Estatísticas de leitura e progresso da meta",
    description=(
        "Livros concluídos, páginas lidas, livros por mês e por gênero, média das notas, "
        "sequência de dias lendo e situação da meta (calculados pela API de metas)."
    ),
)
async def estatisticas(
    ano: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    usuario: Usuario = Depends(get_usuario_atual),
    metas: MetasClient = Depends(get_metas_client),
):
    return await metas.estatisticas(usuario.id, ano)
