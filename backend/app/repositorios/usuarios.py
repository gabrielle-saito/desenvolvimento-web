from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def buscar(db: Session, usuario_id: int) -> User | None:
    return db.get(User, usuario_id)


def buscar_por_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def listar(db: Session, *, limit: int, offset: int) -> list[User]:
    stmt = select(User).order_by(User.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def adicionar(db: Session, usuario: User) -> None:
    db.add(usuario)
