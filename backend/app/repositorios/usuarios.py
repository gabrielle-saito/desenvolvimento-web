from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.dominio.enums import Papel
from app.models.user import User


def buscar(db: Session, usuario_id: int) -> User | None:
    return db.get(User, usuario_id)


def buscar_por_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def _filtrado(
    *, busca: str | None, papel: Papel | None, ativos: bool | None
) -> Select[tuple[User]]:
    stmt = select(User)
    if busca:
        stmt = stmt.where(
            or_(
                User.nome.icontains(busca, autoescape=True),
                User.email.icontains(busca, autoescape=True),
            )
        )
    if papel is not None:
        stmt = stmt.where(User.papel == papel)
    if ativos is not None:
        stmt = stmt.where(User.is_active.is_(ativos))
    return stmt


def listar(
    db: Session,
    *,
    busca: str | None = None,
    papel: Papel | None = None,
    ativos: bool | None = None,
    limit: int,
    offset: int,
) -> list[User]:
    stmt = _filtrado(busca=busca, papel=papel, ativos=ativos)
    return list(db.scalars(stmt.order_by(User.id).limit(limit).offset(offset)))


def contar(
    db: Session, *, busca: str | None = None, papel: Papel | None = None, ativos: bool | None = None
) -> int:
    stmt = _filtrado(busca=busca, papel=papel, ativos=ativos)
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def adicionar(db: Session, usuario: User) -> None:
    db.add(usuario)
