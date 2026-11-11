"""adiciona dono aos items

Revision ID: 071990882b0f
Revises: 71dc08c733c6
Create Date: 2026-10-08 15:27:38.086686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '071990882b0f'
down_revision: Union[str, Sequence[str], None] = '71dc08c733c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Ajustada à mão: o autogenerate criava owner_id direto como NOT NULL,
    o que falha se a tabela já tiver itens (eles não têm dono).
    """
    # 1) Cria a coluna aceitando NULL, para não falhar com as linhas existentes.
    op.add_column("items", sa.Column("owner_id", sa.Integer(), nullable=True))

    # 2) Itens criados antes da autenticação não têm dono. No laboratório,
    #    apagamos. Em produção NUNCA se apaga dado assim: faz-se um "backfill",
    #    atribuindo cada linha a um dono real antes do passo 3.
    op.execute("DELETE FROM items WHERE owner_id IS NULL")

    # 3) Agora sim, torna a coluna obrigatória.
    op.alter_column("items", "owner_id", nullable=False)

    op.create_index(op.f("ix_items_owner_id"), "items", ["owner_id"], unique=False)
    # Constraint com NOME explícito: o downgrade precisa do nome para removê-la.
    op.create_foreign_key(
        "fk_items_owner_id_users", "items", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_items_owner_id_users", "items", type_="foreignkey")
    op.drop_index(op.f("ix_items_owner_id"), table_name="items")
    op.drop_column("items", "owner_id")
