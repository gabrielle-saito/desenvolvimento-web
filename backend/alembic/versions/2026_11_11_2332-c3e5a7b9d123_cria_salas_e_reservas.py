"""cria salas e reservas, com a constraint contra reserva dupla

Revision ID: c3e5a7b9d123
Revises: b2d4f6a8c012
Create Date: 2026-11-11 23:32:00

Escrita à mão a partir do rascunho do autogenerate, que:
  - não criava a extensão btree_gist (sem ela a constraint de exclusão falha);
  - repetia o CHECK de status duas vezes;
  - deixava FKs e UNIQUE sem nome (o downgrade precisa do nome para remover).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3e5a7b9d123"
down_revision: Union[str, Sequence[str], None] = "b2d4f6a8c012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "salas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("capacidade", sa.Integer(), nullable=False),
        sa.Column("localizacao", sa.String(length=200), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ativa", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_salas"),
        # Nome único garantido pelo BANCO (mesmo raciocínio do e-mail).
        sa.UniqueConstraint("nome", name="uq_salas_nome"),
        sa.CheckConstraint("capacidade > 0", name="ck_salas_capacidade_positiva"),
    )

    op.create_table(
        "reservas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sala_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalidade", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ativa", nullable=False),
        sa.Column("versao", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_por_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_reservas"),
        sa.ForeignKeyConstraint(["sala_id"], ["salas.id"], name="fk_reservas_sala_id_salas"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["users.id"], name="fk_reservas_usuario_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["cancelado_por_id"], ["users.id"], name="fk_reservas_cancelado_por_id_users"
        ),
        sa.CheckConstraint("fim > inicio", name="ck_reservas_fim_depois_do_inicio"),
        sa.CheckConstraint("status IN ('ativa', 'cancelada')", name="ck_reservas_status"),
        sa.CheckConstraint("versao >= 1", name="ck_reservas_versao_positiva"),
    )
    op.create_index("ix_reservas_sala_id", "reservas", ["sala_id"], unique=False)
    op.create_index("ix_reservas_usuario_id", "reservas", ["usuario_id"], unique=False)

    # ------------------------------------------------------------------
    # GARANTIA CONTRA RESERVA DUPLA
    # ------------------------------------------------------------------
    # Checar com SELECT antes de inserir NÃO basta: duas requisições
    # simultâneas fazem o SELECT ao mesmo tempo, as duas veem a sala livre e as
    # duas inserem. Quem impede de verdade é o banco, com uma constraint de
    # EXCLUSÃO: "não podem existir duas linhas com a mesma sala (=) cujos
    # períodos se sobrepõem (&&)".
    #
    # - btree_gist: o índice GiST não sabe comparar inteiros com "=" sem ela.
    # - tstzrange(inicio, fim, '[)'): intervalo semiaberto, inclui o início e
    #   exclui o fim. Assim 10h-11h e 11h-12h NÃO conflitam (reservas encostadas).
    # - WHERE status = 'ativa': reserva cancelada libera o horário.
    # Violação -> erro SQLSTATE 23P01 (exclusion_violation), que o serviço
    # converte na exceção de domínio ConflitoDeHorario (HTTP 409).
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE reservas
          ADD CONSTRAINT ex_reservas_sala_sem_sobreposicao
          EXCLUDE USING gist (
            sala_id WITH =,
            tstzrange(inicio, fim, '[)') WITH &&
          )
          WHERE (status = 'ativa')
        """
    )


def downgrade() -> None:
    # Ordem inversa: constraint -> índices -> reservas (depende de salas) -> salas.
    op.execute("ALTER TABLE reservas DROP CONSTRAINT ex_reservas_sala_sem_sobreposicao")
    op.drop_index("ix_reservas_usuario_id", table_name="reservas")
    op.drop_index("ix_reservas_sala_id", table_name="reservas")
    op.drop_table("reservas")
    op.drop_table("salas")
    # A extensão é removida por último e só se nada mais a usar.
    # Sem CASCADE de propósito: se outra tabela depender dela, o downgrade
    # falha em vez de apagar coisa alheia em silêncio.
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
