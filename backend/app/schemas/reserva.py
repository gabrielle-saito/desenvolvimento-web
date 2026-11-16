from datetime import datetime

from pydantic import ConfigDict, Field, model_validator

from app.dominio.enums import StatusReserva
from app.schemas.comum import DataHoraComFuso, Entrada, Saida
from app.schemas.sala import SalaResumo
from app.schemas.usuario import UsuarioResumo


class ReservaCriar(Entrada):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sala_id": 1,
                    "inicio": "2030-03-10T14:00:00-03:00",
                    "fim": "2030-03-10T15:00:00-03:00",
                    "finalidade": "Planejamento da sprint",
                }
            ]
        }
    )

    # Sem usuario_id: o dono vem do token (e extra="forbid" recusa o campo).
    sala_id: int = Field(gt=0)
    inicio: DataHoraComFuso
    fim: DataHoraComFuso
    finalidade: str = Field(min_length=1, max_length=500)


class ReservaAtualizar(Entrada):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "versao": 1,
                    "inicio": "2030-03-10T15:00:00-03:00",
                    "fim": "2030-03-10T16:00:00-03:00",
                }
            ]
        }
    )

    # OBRIGATÓRIA: a versão que o cliente leu (locking otimista).
    versao: int = Field(ge=1)
    sala_id: int | None = Field(default=None, gt=0)
    inicio: DataHoraComFuso | None = None
    fim: DataHoraComFuso | None = None
    finalidade: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def sem_nulos_explicitos(self) -> "ReservaAtualizar":
        # PATCH com "inicio": null não faz sentido (a coluna é obrigatória):
        # omita o campo para não alterá-lo.
        for campo in ("sala_id", "inicio", "fim", "finalidade"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"'{campo}' não pode ser nulo; omita o campo para não alterá-lo")
        return self


class ReservaLeitura(Saida):
    id: int
    sala_id: int
    sala: SalaResumo
    usuario_id: int
    usuario: UsuarioResumo
    inicio: datetime
    fim: datetime
    finalidade: str
    status: StatusReserva
    versao: int
    criado_em: datetime
    atualizado_em: datetime
    cancelado_em: datetime | None
    cancelado_por_id: int | None


class ReservaResumo(Saida):
    id: int
    inicio: datetime
    fim: datetime
    finalidade: str
    usuario: UsuarioResumo
