from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models import StatusLeitura

PADRAO_LIVRO_REF = r"^OL\d+W$"


class LivroEstanteCriar(BaseModel):
    livro_ref: str = Field(
        pattern=PADRAO_LIVRO_REF,
        description="Identificador da obra na Open Library (obtido em /catalogo/busca).",
        examples=["OL1003040W"],
    )
    status: StatusLeitura = StatusLeitura.quero_ler


class LivroEstanteAtualizar(BaseModel):
    """Todos os campos são opcionais: envie apenas o que deseja alterar."""

    status: StatusLeitura | None = None
    pagina_atual: int | None = Field(default=None, ge=0, examples=[120])
    nota: int | None = Field(default=None, ge=1, le=5, examples=[5])
    resenha: str | None = Field(default=None, max_length=2000)
    favorito: bool | None = None


class LivroEstanteResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    livro_ref: str
    titulo: str
    autores: str
    ano_publicacao: int | None
    total_paginas: int | None
    capa_url: str | None
    genero: str
    status: StatusLeitura
    pagina_atual: int
    nota: int | None
    resenha: str | None
    favorito: bool
    adicionado_em: datetime
    atualizado_em: datetime
    concluido_em: date | None

    @computed_field
    @property
    def progresso_percentual(self) -> float | None:
        if not self.total_paginas:
            return None
        return round(min(self.pagina_atual / self.total_paginas, 1) * 100, 1)


class PaginaLivros(BaseModel):
    itens: list[LivroEstanteResposta]
    total: int
    pagina: int
    tamanho: int
    total_paginas: int


class ResumoEstante(BaseModel):
    total: int
    quero_ler: int
    lendo: int
    lido: int
    abandonado: int
    favoritos: int


class OrdenacaoEstante(str, Enum):
    adicionado_em = "adicionado_em"
    atualizado_em = "atualizado_em"
    titulo = "titulo"
    nota = "nota"


class DirecaoOrdenacao(str, Enum):
    asc = "asc"
    desc = "desc"
