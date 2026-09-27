import logging
import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.excecoes import ErroServicoExterno
from app.models import LivroEstante, StatusLeitura, Usuario
from app.schemas.estante import (
    DirecaoOrdenacao,
    LivroEstanteAtualizar,
    LivroEstanteCriar,
    LivroEstanteResposta,
    OrdenacaoEstante,
    PaginaLivros,
    ResumoEstante,
)
from app.services.metas_client import MetasClient, get_metas_client
from app.services.open_library import OpenLibraryClient, get_open_library
from app.services.seguranca import get_usuario_atual

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estante", tags=["Minha estante"])


def _buscar_livro(db: Session, usuario: Usuario, livro_id: int) -> LivroEstante:
    livro = db.scalar(
        select(LivroEstante).where(
            LivroEstante.id == livro_id, LivroEstante.usuario_id == usuario.id
        )
    )
    if livro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Livro não encontrado na sua estante.")
    return livro


async def _sincronizar(descricao: str, operacao) -> None:
    """Executa uma chamada à API de metas sem impedir a operação na estante.

    A estante continua funcionando mesmo se a API de metas estiver fora do ar;
    nesse caso a falha é registrada no log.
    """
    try:
        await operacao
    except ErroServicoExterno as erro:
        logger.warning("Não foi possível %s: %s", descricao, erro.detail)


async def _registrar_conclusao(metas: MetasClient, livro: LivroEstante) -> None:
    await _sincronizar(
        "registrar a conclusão do livro",
        metas.registrar_leitura(
            usuario_id=livro.usuario_id,
            livro_ref=livro.livro_ref,
            titulo=livro.titulo,
            genero=livro.genero,
            paginas=livro.total_paginas,
            nota=livro.nota,
            data_conclusao=livro.concluido_em or date.today(),
        ),
    )


@router.post(
    "",
    response_model=LivroEstanteResposta,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona um livro da Open Library à estante",
    description=(
        "Busca os dados do livro na Open Library (título, autores, páginas, capa e gênero) "
        "e o salva na estante. Se o status for `lido`, a conclusão é registrada na API de metas."
    ),
)
async def adicionar_livro(
    dados: LivroEstanteCriar,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
    open_library: OpenLibraryClient = Depends(get_open_library),
    metas: MetasClient = Depends(get_metas_client),
):
    ja_existe = db.scalar(
        select(LivroEstante.id).where(
            LivroEstante.usuario_id == usuario.id, LivroEstante.livro_ref == dados.livro_ref
        )
    )
    if ja_existe:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este livro já está na sua estante.")

    catalogo = await open_library.obter_livro(dados.livro_ref)
    if catalogo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Livro não encontrado na Open Library.")

    livro = LivroEstante(
        usuario_id=usuario.id,
        livro_ref=catalogo.livro_ref,
        titulo=catalogo.titulo,
        autores=", ".join(catalogo.autores),
        ano_publicacao=catalogo.ano_publicacao,
        total_paginas=catalogo.total_paginas,
        capa_url=catalogo.capa_url,
        genero=catalogo.genero,
        status=dados.status,
    )
    if dados.status == StatusLeitura.lido:
        livro.pagina_atual = livro.total_paginas or 0
        livro.concluido_em = date.today()

    db.add(livro)
    db.commit()
    db.refresh(livro)

    if livro.status == StatusLeitura.lido:
        await _registrar_conclusao(metas, livro)
    return livro


@router.get(
    "",
    response_model=PaginaLivros,
    summary="Lista os livros da estante com filtros, ordenação e paginação",
)
def listar_livros(
    status_leitura: StatusLeitura | None = Query(default=None, alias="status"),
    genero: str | None = Query(default=None, examples=["Fantasia"]),
    favorito: bool | None = Query(default=None),
    busca: str | None = Query(default=None, min_length=2, description="Trecho do título ou autor"),
    ordenar_por: OrdenacaoEstante = Query(default=OrdenacaoEstante.adicionado_em),
    ordem: DirecaoOrdenacao = Query(default=DirecaoOrdenacao.desc),
    pagina: int = Query(default=1, ge=1),
    tamanho: int = Query(default=10, ge=1, le=50),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    filtros = [LivroEstante.usuario_id == usuario.id]
    if status_leitura is not None:
        filtros.append(LivroEstante.status == status_leitura)
    if genero:
        filtros.append(func.lower(LivroEstante.genero) == genero.lower())
    if favorito is not None:
        filtros.append(LivroEstante.favorito == favorito)
    if busca:
        termo = f"%{busca}%"
        filtros.append(or_(LivroEstante.titulo.ilike(termo), LivroEstante.autores.ilike(termo)))

    total = db.scalar(select(func.count()).select_from(LivroEstante).where(*filtros))

    coluna = getattr(LivroEstante, ordenar_por.value)
    ordenacao = coluna.asc() if ordem == DirecaoOrdenacao.asc else coluna.desc()
    itens = db.scalars(
        select(LivroEstante)
        .where(*filtros)
        .order_by(ordenacao.nulls_last(), LivroEstante.id)
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    ).all()

    return PaginaLivros(
        itens=itens,
        total=total,
        pagina=pagina,
        tamanho=tamanho,
        total_paginas=math.ceil(total / tamanho) if total else 0,
    )


@router.get(
    "/resumo",
    response_model=ResumoEstante,
    summary="Quantidade de livros por status",
)
def resumo_estante(
    usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)
):
    contagem = dict(
        db.execute(
            select(LivroEstante.status, func.count())
            .where(LivroEstante.usuario_id == usuario.id)
            .group_by(LivroEstante.status)
        ).all()
    )
    favoritos = db.scalar(
        select(func.count())
        .select_from(LivroEstante)
        .where(LivroEstante.usuario_id == usuario.id, LivroEstante.favorito.is_(True))
    )
    return ResumoEstante(
        total=sum(contagem.values()),
        favoritos=favoritos,
        **{situacao.value: contagem.get(situacao, 0) for situacao in StatusLeitura},
    )


@router.get(
    "/{livro_id}",
    response_model=LivroEstanteResposta,
    summary="Detalhes de um livro da estante",
)
def obter_livro(
    livro_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    return _buscar_livro(db, usuario, livro_id)


@router.patch(
    "/{livro_id}",
    response_model=LivroEstanteResposta,
    summary="Atualiza status, progresso, nota, resenha ou favorito",
    description=(
        "Envie apenas os campos que deseja alterar. Regras aplicadas:\n\n"
        "* Avançar `pagina_atual` registra uma **sessão de leitura** na API de metas "
        "(e muda o status de `quero_ler` para `lendo`).\n"
        "* Mudar o status para `lido` completa as páginas e registra a **conclusão** na API de metas.\n"
        "* Tirar um livro do status `lido` remove a conclusão da API de metas."
    ),
)
async def atualizar_livro(
    livro_id: int,
    dados: LivroEstanteAtualizar,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
    metas: MetasClient = Depends(get_metas_client),
):
    livro = _buscar_livro(db, usuario, livro_id)
    alteracoes = dados.model_dump(exclude_unset=True)

    for campo in ("status", "pagina_atual", "favorito"):
        if campo in alteracoes and alteracoes[campo] is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"O campo '{campo}' não pode ser nulo."
            )

    status_anterior = livro.status
    pagina_anterior = livro.pagina_atual
    novo_status = alteracoes.get("status", livro.status)
    nova_pagina = alteracoes.get("pagina_atual", livro.pagina_atual)

    if livro.total_paginas and nova_pagina > livro.total_paginas:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Este livro tem apenas {livro.total_paginas} páginas.",
        )
    if (
        "status" not in alteracoes
        and nova_pagina > pagina_anterior
        and novo_status == StatusLeitura.quero_ler
    ):
        novo_status = StatusLeitura.lendo
    if novo_status == StatusLeitura.lido and livro.total_paginas:
        nova_pagina = livro.total_paginas

    livro.status = novo_status
    livro.pagina_atual = nova_pagina
    for campo in ("nota", "resenha", "favorito"):
        if campo in alteracoes:
            setattr(livro, campo, alteracoes[campo])

    if novo_status == StatusLeitura.lido:
        if status_anterior != StatusLeitura.lido:
            livro.concluido_em = date.today()
    else:
        livro.concluido_em = None

    db.commit()
    db.refresh(livro)

    paginas_lidas = nova_pagina - pagina_anterior
    if paginas_lidas > 0:
        await _sincronizar(
            "registrar a sessão de leitura",
            metas.registrar_sessao(usuario.id, livro.livro_ref, paginas_lidas),
        )
    if novo_status == StatusLeitura.lido:
        if status_anterior != StatusLeitura.lido or "nota" in alteracoes:
            await _registrar_conclusao(metas, livro)
    elif status_anterior == StatusLeitura.lido:
        await _sincronizar(
            "remover a conclusão do livro", metas.remover_leitura(usuario.id, livro.livro_ref)
        )

    return livro


@router.delete(
    "/{livro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um livro da estante",
    description="Também apaga a conclusão e as sessões de leitura do livro na API de metas.",
)
async def remover_livro(
    livro_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
    metas: MetasClient = Depends(get_metas_client),
):
    livro = _buscar_livro(db, usuario, livro_id)
    livro_ref = livro.livro_ref
    db.delete(livro)
    db.commit()

    await _sincronizar("remover a conclusão do livro", metas.remover_leitura(usuario.id, livro_ref))
    await _sincronizar("remover as sessões do livro", metas.remover_sessoes(usuario.id, livro_ref))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
