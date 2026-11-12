"""cria eventos_auditoria (append-only)

Revision ID: d4f6b8c0e234
Revises: c3e5a7b9d123
Create Date: 2026-11-11 23:33:00

Trilha de auditoria: só recebe INSERT. Um trigger recusa UPDATE e DELETE,
então o histórico não pode ser reescrito nem por um bug do código.
(TRUNCATE não dispara esses triggers: é como os testes limpam o banco de
TESTE entre um caso e outro.)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4f6b8c0e234"
down_revision: Union[str, Sequence[str], None] = "c3e5a7b9d123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eventos_auditoria",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=60), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("entidade", sa.String(length=40), nullable=False),
        sa.Column("entidade_id", sa.Integer(), nullable=False),
        sa.Column("dados", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_eventos_auditoria"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["users.id"], name="fk_eventos_auditoria_usuario_id_users"
        ),
    )
    op.create_index(
        "ix_eventos_auditoria_entidade",
        "eventos_auditoria",
        ["entidade", "entidade_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION eventos_auditoria_somente_insert() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'eventos_auditoria é append-only: % não é permitido', TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_eventos_auditoria_somente_insert
          BEFORE UPDATE OR DELETE ON eventos_auditoria
          FOR EACH ROW EXECUTE FUNCTION eventos_auditoria_somente_insert()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER tg_eventos_auditoria_somente_insert ON eventos_auditoria")
    op.execute("DROP FUNCTION eventos_auditoria_somente_insert()")
    op.drop_index("ix_eventos_auditoria_entidade", table_name="eventos_auditoria")
    op.drop_table("eventos_auditoria")
