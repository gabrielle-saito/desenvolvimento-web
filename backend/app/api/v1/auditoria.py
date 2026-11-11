"""Trilha de auditoria (somente leitura). Responsável ou admin."""

from fastapi import APIRouter, Query

from app.api.deps import DbSession, UsuarioResponsavel
from app.models.evento_auditoria import EventoAuditoria
from app.schemas.auditoria import EventoLeitura
from app.servicos import auditoria as servico

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("", response_model=list[EventoLeitura])
def listar_eventos(
    db: DbSession,
    usuario: UsuarioResponsavel,
    entidade: str | None = Query(default=None, max_length=40, examples=["reserva"]),
    entidade_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[EventoAuditoria]:
    return servico.listar(
        db, entidade=entidade, entidade_id=entidade_id, limit=limit, offset=offset
    )
