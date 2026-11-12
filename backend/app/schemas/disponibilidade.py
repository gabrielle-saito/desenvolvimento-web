from datetime import datetime

from app.schemas.comum import Saida
from app.schemas.reserva import ReservaResumo
from app.schemas.sala import SalaLeitura


class SalaDisponibilidade(Saida):
    sala: SalaLeitura
    livre: bool
    reservas_conflitantes: list[ReservaResumo]


class Disponibilidade(Saida):
    inicio: datetime
    fim: datetime
    total_livres: int
    # Preenchida quando nenhuma sala está livre (caso de uso 2).
    mensagem: str | None
    salas: list[SalaDisponibilidade]
