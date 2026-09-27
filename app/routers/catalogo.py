from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.schemas.catalogo import LivroCatalogo, LivroCatalogoDetalhe, ResultadoBusca
from app.schemas.estante import PADRAO_LIVRO_REF
from app.services.generos import assunto_open_library, nomes_generos
from app.services.open_library import OpenLibraryClient, get_open_library

router = APIRouter(prefix="/catalogo", tags=["Catálogo (Open Library)"])


@router.get(
    "/busca",
    response_model=ResultadoBusca,
    summary="Busca livros na Open Library",
    description="Pesquisa por título, autor ou ISBN. Use o `livro_ref` retornado para adicionar o livro à estante.",
)
async def buscar_livros(
    q: str = Query(min_length=2, max_length=200, description="Título, autor ou ISBN", examples=["dom casmurro"]),
    pagina: int = Query(default=1, ge=1, le=100),
    limite: int = Query(default=10, ge=1, le=50),
    open_library: OpenLibraryClient = Depends(get_open_library),
):
    return await open_library.buscar(q, pagina, limite)


@router.get(
    "/livros/{livro_ref}",
    response_model=LivroCatalogoDetalhe,
    summary="Detalhes de um livro da Open Library",
)
async def detalhar_livro(
    livro_ref: str = Path(pattern=PADRAO_LIVRO_REF, examples=["OL1003040W"]),
    open_library: OpenLibraryClient = Depends(get_open_library),
):
    livro = await open_library.obter_livro(livro_ref)
    if livro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Livro não encontrado na Open Library.")
    return livro


@router.get(
    "/generos",
    response_model=list[str],
    summary="Lista os gêneros usados para classificar os livros",
)
def listar_generos():
    return nomes_generos()


@router.get(
    "/generos/{genero}",
    response_model=list[LivroCatalogo],
    summary="Livros populares de um gênero",
)
async def livros_do_genero(
    genero: str = Path(examples=["Fantasia"]),
    limite: int = Query(default=10, ge=1, le=50),
    open_library: OpenLibraryClient = Depends(get_open_library),
):
    assunto = assunto_open_library(genero)
    if assunto is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Gênero desconhecido. Consulte GET /catalogo/generos.",
        )
    return await open_library.livros_por_assunto(assunto, limite)
