from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas.auth import Token, UsuarioCriar, UsuarioResposta
from app.services.seguranca import (
    criar_token,
    gerar_hash_senha,
    get_usuario_atual,
    verificar_senha,
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/registro",
    response_model=UsuarioResposta,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma conta de usuário",
)
def registrar(dados: UsuarioCriar, db: Session = Depends(get_db)):
    email = dados.email.lower()
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está cadastrado.")

    usuario = Usuario(nome=dados.nome, email=email, senha_hash=gerar_hash_senha(dados.senha))
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post(
    "/login",
    response_model=Token,
    summary="Autentica e retorna um token JWT",
    description=(
        "Informe o **e-mail** no campo `username` e a senha em `password`. "
        "No Swagger, use o botão **Authorize** para fazer login uma única vez."
    ),
)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.scalar(select(Usuario).where(Usuario.email == form.username.lower()))
    if usuario is None or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=criar_token(usuario.id))


@router.get("/me", response_model=UsuarioResposta, summary="Dados do usuário autenticado")
def usuario_logado(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario
