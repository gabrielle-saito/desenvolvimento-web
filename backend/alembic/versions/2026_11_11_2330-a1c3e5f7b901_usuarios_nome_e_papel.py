"""usuarios: nome e papel (RBAC)

Revision ID: a1c3e5f7b901
Revises: 071990882b0f
Create Date: 2026-11-11 23:30:00

Escrita à mão. O autogenerate criava "nome" direto como NOT NULL sem valor
padrão, o que FALHA se a tabela já tiver usuários (as linhas antigas
ficariam sem nome). Aqui fazemos em 3 passos: cria aceitando NULL, preenche
(backfill) e só então torna obrigatória.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c3e5f7b901"
down_revision: Union[str, Sequence[str], None] = "071990882b0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- nome ---
    # 1) Cria aceitando NULL, para não falhar com as linhas existentes.
    op.add_column("users", sa.Column("nome", sa.String(length=120), nullable=True))
    # 2) Backfill: usa a parte do e-mail antes do "@" como nome provisório
    #    (o admin pode corrigir depois pelo PATCH /v1/usuarios/{id}).
    op.execute("UPDATE users SET nome = split_part(email, '@', 1) WHERE nome IS NULL")
    # 3) Agora sim, obrigatória.
    op.alter_column("users", "nome", nullable=False)

    # --- papel ---
    # server_default: as linhas existentes recebem "colaborador" na hora,
    # então a coluna já nasce NOT NULL sem quebrar nada. Papel com MENOS
    # poder como padrão: promover a admin é decisão explícita.
    op.add_column(
        "users",
        sa.Column(
            "papel",
            sa.String(length=20),
            server_default="colaborador",
            nullable=False,
        ),
    )
    # CHECK com nome explícito: o banco recusa qualquer papel fora da lista.
    op.create_check_constraint(
        "ck_users_papel", "users", "papel IN ('colaborador', 'responsavel', 'admin')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_papel", "users", type_="check")
    op.drop_column("users", "papel")
    op.drop_column("users", "nome")
