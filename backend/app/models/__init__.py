# Importe AQUI todo modelo novo. O Alembic só "enxerga" tabelas cujos modelos
# foram importados — esquecer esta linha gera uma migration vazia.
from app.models.item import Item
from app.models.user import User

__all__ = ["Item", "User"]
