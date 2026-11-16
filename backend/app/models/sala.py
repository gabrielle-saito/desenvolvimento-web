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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.recurso import Recurso, sala_recursos


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

    # N:N com recursos (pela tabela sala_recursos). selectin: os recursos de
    # todas as salas de uma listagem vêm numa consulta só (sem N+1).
    recursos: Mapped[list[Recurso]] = relationship(
        secondary=sala_recursos, lazy="selectin", order_by=Recurso.nome
    )
