"""Caso de uso: consultar disponibilidade das salas num período."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.dominio.reservas import validar_periodo_de_consulta
from app.models.reserva import Reserva
from app.models.sala import Sala
from app.repositorios import reservas as repo_reservas
from app.repositorios import salas as repo_salas


@dataclass
class SituacaoSala:
    sala: Sala
    reservas_conflitantes: list[Reserva] = field(default_factory=list)

    @property
    def livre(self) -> bool:
        return not self.reservas_conflitantes


def consultar(
    db: Session, *, inicio: datetime, fim: datetime, capacidade_minima: int | None
) -> list[SituacaoSala]:
    """Cada sala ATIVA (com a capacidade pedida) e as reservas que a ocupam
    no período. Duas consultas no total, independente do número de salas."""
    validar_periodo_de_consulta(inicio, fim)
    salas = repo_salas.listar(db, ativas=True, capacidade_minima=capacidade_minima)
    ocupadas = repo_reservas.ativas_que_conflitam(db, [s.id for s in salas], inicio, fim)

    por_sala: dict[int, SituacaoSala] = {s.id: SituacaoSala(sala=s) for s in salas}
    for reserva in ocupadas:
        por_sala[reserva.sala_id].reservas_conflitantes.append(reserva)
    return list(por_sala.values())
