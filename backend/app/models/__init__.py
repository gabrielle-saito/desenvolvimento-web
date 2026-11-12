# Importe AQUI todo modelo novo. O Alembic só "enxerga" tabelas cujos modelos
# foram importados — esquecer esta linha gera uma migration vazia.
from app.models.evento_auditoria import EventoAuditoria
from app.models.reserva import Reserva
from app.models.sala import Sala
from app.models.user import User

__all__ = ["EventoAuditoria", "Reserva", "Sala", "User"]
