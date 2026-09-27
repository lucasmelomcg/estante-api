from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsuarioCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=100, examples=["Ana Leitora"])
    email: str = Field(
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        examples=["ana@email.com"],
    )
    senha: str = Field(min_length=8, max_length=72, examples=["senhaSegura123"])


class UsuarioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    criado_em: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
