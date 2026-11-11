"""Schemas Pydantic: o contrato da API.

Separe ENTRADA de SAÍDA. O cliente nunca envia id nem created_at;
o modelo do banco nunca vaza direto para a resposta.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ItemUpdate(BaseModel):
    # Todos opcionais: PATCH altera só o que foi enviado.
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lê atributos do objeto ORM

    id: int
    title: str
    description: str | None
    created_at: datetime
    owner_id: int
