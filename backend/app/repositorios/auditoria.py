from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evento_auditoria import EventoAuditoria


def adicionar(db: Session, evento: EventoAuditoria) -> None:
    # Só existe "adicionar": a tabela é append-only (não há atualizar/remover).
    db.add(evento)


def listar(
    db: Session,
    *,
    entidade: str | None = None,
    entidade_id: int | None = None,
    limit: int,
    offset: int,
) -> list[EventoAuditoria]:
    stmt = select(EventoAuditoria)
    if entidade is not None:
        stmt = stmt.where(EventoAuditoria.entidade == entidade)
    if entidade_id is not None:
        stmt = stmt.where(EventoAuditoria.entidade_id == entidade_id)
    # Mais recentes primeiro: é o que se quer ver numa trilha de auditoria.
    stmt = stmt.order_by(EventoAuditoria.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))
