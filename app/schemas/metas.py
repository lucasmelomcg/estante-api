"""Formatos da API de Metas de Leitura, reexpostos pela Estante API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MetaAtualizar(BaseModel):
    meta_livros: int = Field(ge=1, le=1000, examples=[24])
    meta_paginas: int | None = Field(default=None, ge=1, le=1_000_000, examples=[6000])


class MetaCriar(MetaAtualizar):
    ano: int = Field(ge=2000, le=2100, examples=[2026])


class MetaResposta(MetaCriar):
    id: int
    criada_em: datetime
    atualizada_em: datetime


class SituacaoMeta(str, Enum):
    meta_batida = "meta_batida"
    adiantado = "adiantado"
    no_ritmo = "no_ritmo"
    atrasado = "atrasado"
    nao_iniciada = "nao_iniciada"


class ProgressoMeta(BaseModel):
    meta_livros: int
    meta_paginas: int | None
    progresso_livros_percentual: float
    progresso_paginas_percentual: float | None
    livros_restantes: int
    livros_esperados_ate_hoje: float
    ritmo_necessario_livros_por_mes: float
    situacao: SituacaoMeta


class ResumoMes(BaseModel):
    mes: int
    livros: int
    paginas: int


class ResumoGenero(BaseModel):
    genero: str
    livros: int


class Estatisticas(BaseModel):
    ano: int
    livros_concluidos: int
    paginas_lidas: int
    media_nota: float | None
    sequencia_atual_dias: int
    maior_sequencia_dias: int
    meta: ProgressoMeta | None
    por_mes: list[ResumoMes]
    por_genero: list[ResumoGenero]
