from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, func, literal, select
from sqlalchemy.orm import Session

from app.dominio.enums import StatusReserva
from app.models.reserva import Reserva


def _sobrepoe(inicio: datetime, fim: datetime) -> ColumnElement[bool]:
    """tstzrange(inicio, fim, '[)') && tstzrange(:inicio, :fim, '[)').

    A MESMA expressão da constraint de exclusão: assim a checagem prévia e a
    garantia do banco concordam sobre o que é "sobrepor", e a consulta
    aproveita o índice GiST criado pela constraint.
    """
    periodo_reserva = func.tstzrange(Reserva.inicio, Reserva.fim, literal("[)"))
    periodo_pedido = func.tstzrange(inicio, fim, literal("[)"))
    return periodo_reserva.op("&&")(periodo_pedido)


def buscar(db: Session, reserva_id: int) -> Reserva | None:
    return db.get(Reserva, reserva_id)


def versao_atual(db: Session, reserva_id: int) -> int | None:
    return db.scalar(select(Reserva.versao).where(Reserva.id == reserva_id))


def listar(
    db: Session,
    *,
    sala_id: int | None = None,
    de: datetime | None = None,
    ate: datetime | None = None,
    usuario_id: int | None = None,
    status: StatusReserva | None = None,
    limit: int,
    offset: int,
) -> list[Reserva]:
    stmt = select(Reserva)
    if sala_id is not None:
        stmt = stmt.where(Reserva.sala_id == sala_id)
    # Filtro por período: traz toda reserva que TOCA a janela [de, ate),
    # inclusive as que começaram antes de "de" e ainda não terminaram.
    if de is not None:
        stmt = stmt.where(Reserva.fim > de)
    if ate is not None:
        stmt = stmt.where(Reserva.inicio < ate)
    if usuario_id is not None:
        stmt = stmt.where(Reserva.usuario_id == usuario_id)
    if status is not None:
        stmt = stmt.where(Reserva.status == status)
    stmt = stmt.order_by(Reserva.inicio, Reserva.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def ativas_que_conflitam(
    db: Session,
    sala_ids: Sequence[int],
    inicio: datetime,
    fim: datetime,
    ignorar_reserva_id: int | None = None,
) -> list[Reserva]:
    """Reservas ATIVAS das salas indicadas que se sobrepõem ao período."""
    if not sala_ids:
        return []
    stmt = select(Reserva).where(
        Reserva.sala_id.in_(sala_ids),
        Reserva.status == StatusReserva.ATIVA,
        _sobrepoe(inicio, fim),
    )
    if ignorar_reserva_id is not None:
        # Na edição, a própria reserva não conflita com ela mesma.
        stmt = stmt.where(Reserva.id != ignorar_reserva_id)
    return list(db.scalars(stmt.order_by(Reserva.inicio)))


def adicionar(db: Session, reserva: Reserva) -> None:
    db.add(reserva)
