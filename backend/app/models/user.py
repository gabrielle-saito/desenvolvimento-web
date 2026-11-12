from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.dominio.enums import Papel


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True: a garantia de e-mail único é do BANCO, não só do código.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(120))
    # Guardamos o HASH, nunca a senha. O nome da coluna deixa isso explícito.
    hashed_password: Mapped[str] = mapped_column(String(255))
    # native_enum=False: grava como VARCHAR + CHECK, e não como um tipo ENUM do
    # PostgreSQL (que é chato de alterar em migration). values_callable faz o
    # banco guardar o VALOR ("admin"), não o nome do membro ("ADMIN").
    papel: Mapped[Papel] = mapped_column(
        Enum(
            Papel,
            native_enum=False,
            create_constraint=True,
            length=20,
            name="ck_users_papel",
            values_callable=lambda e: [m.value for m in e],
        ),
        server_default=Papel.COLABORADOR.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
