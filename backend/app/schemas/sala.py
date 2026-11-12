from datetime import datetime

from pydantic import Field

from app.schemas.comum import Entrada, Saida


class SalaCriar(Entrada):
    nome: str = Field(min_length=1, max_length=120)
    capacidade: int = Field(gt=0, le=10_000)
    localizacao: str | None = Field(default=None, max_length=200)
    descricao: str | None = Field(default=None, max_length=2000)


class SalaAtualizar(Entrada):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    capacidade: int | None = Field(default=None, gt=0, le=10_000)
    localizacao: str | None = Field(default=None, max_length=200)
    descricao: str | None = Field(default=None, max_length=2000)
    # ativa=false desativa a sala (não apaga, não cancela reservas existentes).
    ativa: bool | None = None


class SalaLeitura(Saida):
    id: int
    nome: str
    capacidade: int
    localizacao: str | None
    descricao: str | None
    ativa: bool
    criado_em: datetime


class SalaResumo(Saida):
    id: int
    nome: str
