from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.dominio.enums import StatusReserva


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (
        CheckConstraint("fim > inicio", name="ck_reservas_fim_depois_do_inicio"),
        # GARANTIA CONTRA RESERVA DUPLA (o coração do sistema).
        # "Não pode existir duas linhas com a MESMA sala (=) cujos períodos se
        # SOBREPÕEM (&&)", considerando só as reservas ativas.
        # '[)' = intervalo semiaberto: 10h-11h e 11h-12h NÃO se sobrepõem.
        # Quem cria de verdade é a migration (escrita à mão); declarar aqui
        # serve para o autogenerate não achar que ela sobrou e tentar removê-la.
        ExcludeConstraint(
            ("sala_id", "="),
            (text("tstzrange(inicio, fim, '[)')"), "&&"),
            name="ex_reservas_sala_sem_sobreposicao",
            using="gist",
            where=text("status = 'ativa'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # ondelete RESTRICT (padrão): não se apaga sala/usuário que tem reservas.
    sala_id: Mapped[int] = mapped_column(
        ForeignKey("salas.id", name="fk_reservas_sala_id_salas"), index=True
    )
    # Dono da reserva: vem SEMPRE do token, nunca do corpo da requisição.
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_reservas_usuario_id_users"), index=True
    )
    # timestamptz: o PostgreSQL guarda em UTC e converte na leitura.
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finalidade: Mapped[str] = mapped_column(String(500))
    status: Mapped[StatusReserva] = mapped_column(
        Enum(
            StatusReserva,
            native_enum=False,
            create_constraint=True,
            length=20,
            name="ck_reservas_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        server_default=StatusReserva.ATIVA.value,
    )
    # Locking otimista: cada UPDATE faz "... WHERE id = :id AND versao = :lida"
    # e incrementa a versão (ver __mapper_args__). Se outra pessoa salvou antes,
    # o UPDATE não acha a linha e o SQLAlchemy levanta StaleDataError.
    versao: Mapped[int] = mapped_column(Integer, server_default="1")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_reservas_cancelado_por_id_users")
    )

    __mapper_args__ = {"version_id_col": versao}
