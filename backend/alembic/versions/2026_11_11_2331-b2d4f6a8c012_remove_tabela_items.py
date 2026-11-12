"""remove a tabela items (entidade genérica da base)

Revision ID: b2d4f6a8c012
Revises: a1c3e5f7b901
Create Date: 2026-11-11 23:31:00

O sistema de reserva de salas não usa a entidade Item da base do
laboratório. ATENÇÃO: o downgrade recria a ESTRUTURA da tabela, mas os
dados apagados no upgrade não voltam (DROP TABLE não tem desfazer).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2d4f6a8c012"
down_revision: Union[str, Sequence[str], None] = "a1c3e5f7b901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ordem: primeiro o que depende (FK e índice), depois a tabela.
    op.drop_constraint("fk_items_owner_id_users", "items", type_="foreignkey")
    op.drop_index("ix_items_owner_id", table_name="items")
    op.drop_table("items")


def downgrade() -> None:
    # Recria exatamente o estado da revision 071990882b0f.
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_items_owner_id", "items", ["owner_id"], unique=False)
    op.create_foreign_key(
        "fk_items_owner_id_users", "items", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )
