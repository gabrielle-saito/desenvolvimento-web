"""Logs estruturados em JSON no stdout (Twelve-Factor, fator XI).

Uma linha JSON por evento, por exemplo:
{"event": "reserva.criada", "reserva_id": 7, "sala_id": 2, "usuario_id": 3,
 "request_id": "4f1c...", "level": "info", "timestamp": "2030-01-31T17:00:00.123Z"}

- "event" é um FATO no passado, com nome estável (reserva.criada,
  auth.login_falhou...): dá para contar, filtrar e alertar por ele.
- request_id entra sozinho em toda linha via merge_contextvars (o middleware
  liga o id ao contexto da requisição).
- Nada de print(): print não tem nível, nem horário, nem request_id.
"""

import logging
import sys

import structlog


def configurar_logging(nivel: int = logging.INFO) -> None:
    # Bibliotecas que usam o logging padrão (uvicorn, sqlalchemy) também
    # saem no stdout, uma linha por mensagem.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=nivel)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # traz o request_id
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            # Exceção vira estrutura no JSON (só no LOG; nunca na resposta HTTP).
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(nivel),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
