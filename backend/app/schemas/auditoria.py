from datetime import datetime
from typing import Any

from app.schemas.comum import Saida


class EventoLeitura(Saida):
    id: int
    tipo: str
    usuario_id: int | None
    entidade: str
    entidade_id: int
    dados: dict[str, Any]
    request_id: str | None
    criado_em: datetime
