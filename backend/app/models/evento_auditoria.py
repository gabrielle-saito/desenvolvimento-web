from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventoAuditoria(Base):
    """Trilha de auditoria APPEND-ONLY: só INSERT, nunca UPDATE nem DELETE.

    A migration cria um trigger que recusa UPDATE/DELETE nesta tabela, então
    nem um bug no código consegue reescrever o histórico.
    """

    __tablename__ = "eventos_auditoria"
    __table_args__ = (
        # A consulta típica é "o histórico desta reserva": entidade + id.
        Index("ix_eventos_auditoria_entidade", "entidade", "entidade_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(60))  # fato: "reserva.criada"
    # Quem fez. Nulo só em eventos sem usuário logado (ex.: seed).
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_eventos_auditoria_usuario_id_users")
    )
    entidade: Mapped[str] = mapped_column(String(40))  # "reserva", "sala", ...
    entidade_id: Mapped[int] = mapped_column(Integer)
    # JSONB com {"antes": {...}, "depois": {...}}.
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Liga o evento à linha de log da mesma requisição.
    request_id: Mapped[str | None] = mapped_column(String(64))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
