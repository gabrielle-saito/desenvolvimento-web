"""cria recursos e sala_recursos (relação N:N sala <-> recurso)

Revision ID: e5a7c9d1f345
Revises: d4f6b8c0e234
Create Date: 2026-11-16 17:00:00

Recurso = equipamento/característica de uma sala (projetor, TV,
videoconferência). sala_recursos liga as duas tabelas:
  - PK composta (sala_id, recurso_id): a mesma ligação não se repete;
  - apagar a sala apaga as ligações dela (CASCADE);
  - recurso em uso não pode ser apagado (RESTRICT): é desativado.
Escrita a partir do rascunho do autogenerate, dando nome à PK (o downgrade
e o "alembic check" ficam previsíveis).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5a7c9d1f345"
down_revision: Union[str, Sequence[str], None] = "d4f6b8c0e234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recursos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=80), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recursos"),
        sa.UniqueConstraint("nome", name="uq_recursos_nome"),
    )
    op.create_table(
        "sala_recursos",
        sa.Column("sala_id", sa.Integer(), nullable=False),
        sa.Column("recurso_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sala_id"], ["salas.id"], name="fk_sala_recursos_sala_id_salas", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["recurso_id"],
            ["recursos.id"],
            name="fk_sala_recursos_recurso_id_recursos",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("sala_id", "recurso_id", name="pk_sala_recursos"),
    )
    op.create_index("ix_sala_recursos_recurso_id", "sala_recursos", ["recurso_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sala_recursos_recurso_id", table_name="sala_recursos")
    op.drop_table("sala_recursos")
    op.drop_table("recursos")
