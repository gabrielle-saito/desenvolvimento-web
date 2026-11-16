"""chaves estrangeiras com ação de exclusão explícita (ON DELETE RESTRICT)

Revision ID: f7b9d1e3a456
Revises: e5a7c9d1f345
Create Date: 2026-11-16 21:00:00

As FKs de reservas e eventos_auditoria foram criadas sem ON DELETE, ou seja,
com o padrão do PostgreSQL (NO ACTION). O efeito era quase o mesmo, mas a
regra ficava implícita. Agora ela está escrita no banco:

  reservas.sala_id            -> salas.id  RESTRICT  (sala com reservas não é apagada)
  reservas.usuario_id         -> users.id  RESTRICT  (dono da reserva não é apagado)
  reservas.cancelado_por_id   -> users.id  RESTRICT  (quem cancelou não é apagado)
  eventos_auditoria.usuario_id -> users.id RESTRICT  (autor de evento não é apagado)

Salas e usuários não são apagados no sistema, são desativados (soft delete).
RESTRICT garante isso no banco, inclusive para quem acessar o SQL direto.
Diferença para NO ACTION: RESTRICT recusa na hora, sem esperar o fim da
instrução, e não pode ser adiado (DEFERRABLE).

Para trocar a ação de uma FK, o PostgreSQL exige apagar e recriar a
constraint. Os nomes continuam os mesmos.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f7b9d1e3a456"
down_revision: Union[str, Sequence[str], None] = "e5a7c9d1f345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (nome, tabela de origem, coluna, tabela referenciada)
FKS = [
    ("fk_reservas_sala_id_salas", "reservas", "sala_id", "salas"),
    ("fk_reservas_usuario_id_users", "reservas", "usuario_id", "users"),
    ("fk_reservas_cancelado_por_id_users", "reservas", "cancelado_por_id", "users"),
    ("fk_eventos_auditoria_usuario_id_users", "eventos_auditoria", "usuario_id", "users"),
]


def _recriar(ondelete: str | None) -> None:
    for nome, origem, coluna, destino in FKS:
        op.drop_constraint(nome, origem, type_="foreignkey")
        op.create_foreign_key(nome, origem, destino, [coluna], ["id"], ondelete=ondelete)


def upgrade() -> None:
    _recriar("RESTRICT")


def downgrade() -> None:
    _recriar(None)
