"""Enumerações do domínio.

StrEnum: cada membro É uma string ("admin" == Papel.ADMIN), então o valor
viaja sem conversão para o banco, para o JSON e para os logs.
"""

from enum import StrEnum


class Papel(StrEnum):
    """Papéis do RBAC, do menor para o maior poder."""

    COLABORADOR = "colaborador"  # reserva e mexe só nas próprias reservas
    RESPONSAVEL = "responsavel"  # responsável pelas salas: mexe em qualquer reserva
    ADMIN = "admin"  # tudo do responsável + cadastra salas e usuários


class StatusReserva(StrEnum):
    # Cancelar NÃO apaga a linha: muda o status. O histórico fica.
    ATIVA = "ativa"
    CANCELADA = "cancelada"
