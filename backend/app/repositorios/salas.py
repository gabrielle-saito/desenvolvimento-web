from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sala import Sala


def buscar(db: Session, sala_id: int) -> Sala | None:
    return db.get(Sala, sala_id)


def listar(
    db: Session,
    *,
    ativas: bool | None = None,
    capacidade_minima: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Sala]:
    stmt = select(Sala).order_by(Sala.nome)
    if ativas is not None:
        stmt = stmt.where(Sala.ativa.is_(ativas))
    if capacidade_minima is not None:
        stmt = stmt.where(Sala.capacidade >= capacidade_minima)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt.offset(offset)))


def adicionar(db: Session, sala: Sala) -> None:
    db.add(sala)
