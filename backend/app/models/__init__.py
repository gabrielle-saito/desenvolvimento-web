# Importe AQUI todo modelo novo. O Alembic só "enxerga" tabelas cujos modelos
# foram importados — esquecer esta linha gera uma migration vazia.
from app.models.evento_auditoria import EventoAuditoria
from app.models.recurso import Recurso, sala_recursos
from app.models.reserva import Reserva
from app.models.sala import Sala
from app.models.user import User

__all__ = ["EventoAuditoria", "Recurso", "Reserva", "Sala", "User", "sala_recursos"]
