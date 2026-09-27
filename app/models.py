from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class StatusLeitura(str, Enum):
    quero_ler = "quero_ler"
    lendo = "lendo"
    lido = "lido"
    abandonado = "abandonado"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    livros: Mapped[list["LivroEstante"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class LivroEstante(Base):
    """Um livro na estante de um usuário, com os dados copiados da Open Library."""

    __tablename__ = "livros_estante"
    __table_args__ = (UniqueConstraint("usuario_id", "livro_ref"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)

    livro_ref: Mapped[str] = mapped_column(String(50))
    titulo: Mapped[str] = mapped_column(String(300))
    autores: Mapped[str] = mapped_column(String(500), default="")
    ano_publicacao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_paginas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capa_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    genero: Mapped[str] = mapped_column(String(50), default="Outros")

    status: Mapped[StatusLeitura] = mapped_column(
        SqlEnum(StatusLeitura, native_enum=False), default=StatusLeitura.quero_ler
    )
    pagina_atual: Mapped[int] = mapped_column(Integer, default=0)
    nota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resenha: Mapped[str | None] = mapped_column(Text, nullable=True)
    favorito: Mapped[bool] = mapped_column(Boolean, default=False)

    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora, onupdate=_agora
    )
    concluido_em: Mapped[date | None] = mapped_column(Date, nullable=True)

    usuario: Mapped[Usuario] = relationship(back_populates="livros")
