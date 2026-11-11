"""Consultar disponibilidade (caso de uso 2)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.comum import DataHoraComFuso
from app.schemas.disponibilidade import Disponibilidade, SalaDisponibilidade
from app.schemas.reserva import ReservaResumo
from app.schemas.sala import SalaLeitura
from app.servicos import disponibilidade as servico

router = APIRouter(prefix="/disponibilidade", tags=["disponibilidade"])


@router.get("", response_model=Disponibilidade)
def consultar_disponibilidade(
    db: DbSession,
    usuario: CurrentUser,
    # Annotated (e não "= Query(...)"): assim o validador que converte para
    # UTC, declarado em DataHoraComFuso, também roda nos parâmetros de query.
    inicio: Annotated[
        DataHoraComFuso, Query(description="ISO 8601 com fuso, ex.: 2030-01-31T14:00:00-03:00")
    ],
    fim: Annotated[DataHoraComFuso, Query()],
    capacidade_minima: int | None = Query(default=None, ge=1),
) -> Disponibilidade:
    situacoes = servico.consultar(db, inicio=inicio, fim=fim, capacidade_minima=capacidade_minima)
    total_livres = sum(1 for s in situacoes if s.livre)
    mensagem = None
    if total_livres == 0:
        mensagem = (
            "Nenhuma sala disponível nesse período. Tente outro horário"
            + (" ou uma capacidade menor." if capacidade_minima else ".")
        )
    return Disponibilidade(
        inicio=inicio,
        fim=fim,
        total_livres=total_livres,
        mensagem=mensagem,
        salas=[
            SalaDisponibilidade(
                sala=SalaLeitura.model_validate(s.sala),
                livre=s.livre,
                reservas_conflitantes=[
                    ReservaResumo.model_validate(r) for r in s.reservas_conflitantes
                ],
            )
            for s in situacoes
        ],
    )
