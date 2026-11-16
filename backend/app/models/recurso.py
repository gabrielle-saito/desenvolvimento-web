from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Tabela de associação da relação N:N sala <-> recurso: uma sala tem vários
# recursos (projetor, TV...) e um recurso existe em várias salas.
# - Apagar a SALA apaga as ligações dela (CASCADE): a ligação não tem sentido
#   sozinha. (Na prática salas não são apagadas, só desativadas.)
# - Apagar um RECURSO ligado a alguma sala é recusado (RESTRICT): recurso em
#   uso é desativado, não apagado.
sala_recursos = Table(
    "sala_recursos",
    Base.metadata,
    Column(
        "sala_id",
        ForeignKey("salas.id", ondelete="CASCADE", name="fk_sala_recursos_sala_id_salas"),
        primary_key=True,
    ),
    Column(
        "recurso_id",
        ForeignKey("recursos.id", ondelete="RESTRICT", name="fk_sala_recursos_recurso_id_recursos"),
        primary_key=True,
    ),
    # A PK (sala_id, recurso_id) já serve à busca "recursos da sala X". Este
    # índice serve ao filtro do catálogo: "salas que têm o recurso Y".
    Index("ix_sala_recursos_recurso_id", "recurso_id"),
)


class Recurso(Base):
    """Equipamento ou característica de uma sala (projetor, TV, videoconferência)."""

    __tablename__ = "recursos"
    __table_args__ = (UniqueConstraint("nome", name="uq_recursos_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    descricao: Mapped[str | None] = mapped_column(Text)
    # Desativar (ativo=false) em vez de apagar: as salas que já têm o recurso
    # continuam mostrando-o, mas ele deixa de ser oferecido em salas novas.
    ativo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
