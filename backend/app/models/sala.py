from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Sala(Base):
    __tablename__ = "salas"
    __table_args__ = (
        # Regra garantida pelo banco: nenhuma sala com capacidade 0 ou negativa,
        # mesmo que alguém insira direto pelo psql.
        CheckConstraint("capacidade > 0", name="ck_salas_capacidade_positiva"),
        # Nome único garantido pelo BANCO: dois cadastros simultâneos com o
        # mesmo nome -> só um passa (o outro vira 409).
        UniqueConstraint("nome", name="uq_salas_nome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    capacidade: Mapped[int] = mapped_column(Integer)
    localizacao: Mapped[str | None] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    # Desativar (ativa=false) em vez de apagar: as reservas antigas
    # continuam apontando para uma sala que existe.
    ativa: Mapped[bool] = mapped_column(Boolean, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
