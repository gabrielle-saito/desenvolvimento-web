from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Item(Base):
    """Entidade genérica do projeto. Cada grupo pode renomeá-la
    (Safra, Inventario, ...) e acrescentar colunas."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    # server_default: quem preenche a data é o banco, não o Python.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Dono do item. index=True: toda listagem filtra por esta coluna.
    # ondelete="CASCADE": apagar o usuário apaga os itens dele.
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
