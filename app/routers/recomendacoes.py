from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LivroEstante, StatusLeitura, Usuario
from app.schemas.catalogo import Recomendacoes
from app.services.generos import GENERO_PADRAO, assunto_open_library
from app.services.open_library import OpenLibraryClient, get_open_library
from app.services.seguranca import get_usuario_atual

router = APIRouter(prefix="/recomendacoes", tags=["Recomendações"])

GENERO_INICIAL = "Ficção"


def _peso(livro: LivroEstante) -> int:
    """Livros favoritos, lidos ou bem avaliados pesam mais na escolha do gênero."""
    peso = 1
    if livro.favorito:
        peso += 2
    if livro.status == StatusLeitura.lido:
        peso += 1
    if livro.nota and livro.nota >= 4:
        peso += livro.nota - 2
    if livro.status == StatusLeitura.abandonado or (livro.nota and livro.nota <= 2):
        peso = 0
    return peso


@router.get(
    "",
    response_model=Recomendacoes,
    summary="Recomenda livros com base no gosto do usuário",
    description=(
        "Descobre o gênero preferido do usuário (favoritos, livros lidos e notas altas pesam mais) "
        "e busca na Open Library livros populares desse gênero que ainda não estão na estante."
    ),
)
async def recomendar(
    limite: int = Query(default=10, ge=1, le=30),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
    open_library: OpenLibraryClient = Depends(get_open_library),
):
    livros = db.scalars(select(LivroEstante).where(LivroEstante.usuario_id == usuario.id)).all()

    pontuacao: Counter[str] = Counter()
    for livro in livros:
        if livro.genero != GENERO_PADRAO:
            pontuacao[livro.genero] += _peso(livro)

    if +pontuacao:
        genero = pontuacao.most_common(1)[0][0]
        motivo = f"Você demonstrou interesse por livros de {genero}."
    else:
        genero = GENERO_INICIAL
        motivo = "Adicione e avalie livros para receber recomendações personalizadas."

    ja_na_estante = {livro.livro_ref for livro in livros}
    sugestoes = await open_library.livros_por_assunto(
        assunto_open_library(genero), limite + len(ja_na_estante)
    )
    return Recomendacoes(
        genero_base=genero,
        motivo=motivo,
        livros=[s for s in sugestoes if s.livro_ref not in ja_na_estante][:limite],
    )
