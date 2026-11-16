from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.recurso import Recurso


def buscar(db: Session, recurso_id: int) -> Recurso | None:
    return db.get(Recurso, recurso_id)


def buscar_varios(db: Session, ids: Sequence[int]) -> list[Recurso]:
    if not ids:
        return []
    return list(db.scalars(select(Recurso).where(Recurso.id.in_(ids))))


def _filtrado(*, busca: str | None, ativos: bool | None) -> Select[tuple[Recurso]]:
    stmt = select(Recurso)
    if busca:
        stmt = stmt.where(Recurso.nome.icontains(busca, autoescape=True))
    if ativos is not None:
        stmt = stmt.where(Recurso.ativo.is_(ativos))
    return stmt


def listar(
    db: Session, *, busca: str | None = None, ativos: bool | None = None, limit: int, offset: int
) -> list[Recurso]:
    stmt = _filtrado(busca=busca, ativos=ativos).order_by(Recurso.nome)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def contar(db: Session, *, busca: str | None = None, ativos: bool | None = None) -> int:
    """Total que passa nos filtros (sem limit/offset), para a paginação."""
    stmt = _filtrado(busca=busca, ativos=ativos)
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def adicionar(db: Session, recurso: Recurso) -> None:
    db.add(recurso)
