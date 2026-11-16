from datetime import datetime

from pydantic import ConfigDict, Field

from app.schemas.comum import Entrada, Saida


class RecursoCriar(Entrada):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"nome": "Projetor", "descricao": "Projetor Full HD com entrada HDMI"}]
        }
    )

    nome: str = Field(min_length=1, max_length=80)
    descricao: str | None = Field(default=None, max_length=2000)


class RecursoAtualizar(Entrada):
    model_config = ConfigDict(json_schema_extra={"examples": [{"ativo": False}]})

    nome: str | None = Field(default=None, min_length=1, max_length=80)
    descricao: str | None = Field(default=None, max_length=2000)
    # ativo=false desativa o recurso (não apaga; as salas continuam com ele).
    ativo: bool | None = None


class RecursoLeitura(Saida):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "nome": "Projetor",
                    "descricao": "Projetor Full HD com entrada HDMI",
                    "ativo": True,
                    "criado_em": "2026-11-16T17:00:00Z",
                }
            ]
        }
    )

    id: int
    nome: str
    descricao: str | None
    ativo: bool
    criado_em: datetime


class RecursoResumo(Saida):
    id: int
    nome: str
