from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _para_utc(valor: datetime) -> datetime:
    return valor.astimezone(UTC)


# AwareDatetime: data SEM fuso ("2030-01-01T10:00") é recusada com 422.
# Depois de validada, é convertida para UTC: é assim que guardamos.
DataHoraComFuso = Annotated[AwareDatetime, AfterValidator(_para_utc)]
