"""Trilha de auditoria.

registrar() é chamado pelos serviços ANTES do commit, na MESMA transação da
alteração: ou a alteração e o evento são gravados juntos, ou nenhum dos dois.
Nunca existe "reserva cancelada sem evento" nem "evento de algo que não
aconteceu".
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.infra.request_id import request_id_atual
from app.models.evento_auditoria import EventoAuditoria
from app.models.reserva import Reserva
from app.models.sala import Sala
from app.models.user import User
from app.repositorios import auditoria as repo_auditoria


def _json(valor: Any) -> Any:
    # JSONB não aceita datetime: guarda em ISO 8601 (com fuso).
    return valor.isoformat() if isinstance(valor, datetime) else valor


def instantaneo_reserva(r: Reserva) -> dict[str, Any]:
    campos = ("sala_id", "usuario_id", "inicio", "fim", "finalidade", "status", "versao")
    return {c: _json(getattr(r, c)) for c in campos}


def instantaneo_sala(s: Sala) -> dict[str, Any]:
    campos = ("nome", "capacidade", "localizacao", "descricao", "ativa")
    return {c: getattr(s, c) for c in campos}


def instantaneo_usuario(u: User) -> dict[str, Any]:
    # Nunca o hash da senha.
    campos = ("email", "nome", "papel", "is_active")
    return {c: getattr(u, c) for c in campos}


def registrar(
    db: Session,
    *,
    tipo: str,
    ator_id: int | None,
    entidade: str,
    entidade_id: int,
    antes: dict[str, Any] | None = None,
    depois: dict[str, Any] | None = None,
    **extras: Any,
) -> None:
    """Adiciona o evento à sessão. Quem faz o commit é o serviço chamador."""
    repo_auditoria.adicionar(
        db,
        EventoAuditoria(
            tipo=tipo,
            usuario_id=ator_id,
            entidade=entidade,
            entidade_id=entidade_id,
            dados={"antes": antes, "depois": depois, **extras},
            request_id=request_id_atual(),
        ),
    )


def listar(
    db: Session, *, entidade: str | None, entidade_id: int | None, limit: int, offset: int
) -> list[EventoAuditoria]:
    return repo_auditoria.listar(
        db, entidade=entidade, entidade_id=entidade_id, limit=limit, offset=offset
    )
