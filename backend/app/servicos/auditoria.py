from sqlalchemy.orm import Session

from app.models.evento_auditoria import EventoAuditoria
from app.repositorios import auditoria as repo_auditoria


def listar(
    db: Session, *, entidade: str | None, entidade_id: int | None, limit: int, offset: int
) -> list[EventoAuditoria]:
    return repo_auditoria.listar(
        db, entidade=entidade, entidade_id=entidade_id, limit=limit, offset=offset
    )
