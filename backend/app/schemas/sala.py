from datetime import datetime

from pydantic import ConfigDict, Field

from app.schemas.comum import Entrada, Saida
from app.schemas.recurso import RecursoResumo


class SalaCriar(Entrada):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Sala Azul",
                    "capacidade": 6,
                    "localizacao": "2º andar",
                    "descricao": "Boa para reuniões de time",
                    "recurso_ids": [1, 2],
                }
            ]
        }
    )

    nome: str = Field(min_length=1, max_length=120)
    capacidade: int = Field(gt=0, le=10_000)
    localizacao: str | None = Field(default=None, max_length=200)
    descricao: str | None = Field(default=None, max_length=2000)
    # Ids dos recursos da sala (relação N:N). Ver GET /v1/recursos.
    recurso_ids: list[int] = Field(default_factory=list, max_length=50)


class SalaAtualizar(Entrada):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"capacidade": 8, "recurso_ids": [1, 3]}, {"ativa": False}]}
    )

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    capacidade: int | None = Field(default=None, gt=0, le=10_000)
    localizacao: str | None = Field(default=None, max_length=200)
    descricao: str | None = Field(default=None, max_length=2000)
    # ativa=false desativa a sala (não apaga, não cancela reservas existentes).
    ativa: bool | None = None
    # Se enviado, SUBSTITUI a lista inteira de recursos da sala ([] = nenhum).
    recurso_ids: list[int] | None = Field(default=None, max_length=50)


class SalaLeitura(Saida):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "nome": "Sala Azul",
                    "capacidade": 6,
                    "localizacao": "2º andar",
                    "descricao": "Boa para reuniões de time",
                    "ativa": True,
                    "criado_em": "2026-11-16T17:00:00Z",
                    "recursos": [{"id": 1, "nome": "Projetor"}, {"id": 2, "nome": "TV"}],
                }
            ]
        }
    )

    id: int
    nome: str
    capacidade: int
    localizacao: str | None
    descricao: str | None
    ativa: bool
    criado_em: datetime
    recursos: list[RecursoResumo]


class SalaResumo(Saida):
    id: int
    nome: str
