"""Middleware de request_id: o fio que liga log, auditoria e resposta.

1. Lê o header X-Request-ID (se o cliente/proxy mandou um válido) ou gera
   um uuid4().hex.
2. Liga o id ao contexto dos logs (structlog contextvars): toda linha de log
   desta requisição sai com "request_id" sem ninguém precisar passá-lo.
3. Devolve o id no header X-Request-ID da resposta. Quando o usuário relata
   um erro, esse id leva direto às linhas de log e aos eventos de auditoria.

É um middleware ASGI "puro" (não BaseHTTPMiddleware): roda no mesmo contexto
da requisição, então o request_id continua visível nas rotas síncronas (que
rodam numa thread) e no handler de erro 500.
"""

import re
import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "X-Request-ID"
# Só aceita ids "bem comportados" vindos de fora: evita injeção de texto
# arbitrário (quebras de linha, JSON) nos logs.
_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

log = structlog.get_logger()


def request_id_atual() -> str | None:
    return structlog.contextvars.get_contextvars().get("request_id")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        recebido = dict(scope["headers"]).get(HEADER.lower().encode(), b"").decode("latin-1")
        request_id = recebido if _ID_VALIDO.match(recebido) else uuid.uuid4().hex

        # Limpa no INÍCIO (não no fim): assim o handler de erro 500, que roda
        # por fora deste middleware, ainda enxerga o request_id.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        status_code = 500  # se nada for enviado, foi erro inesperado
        inicio = time.perf_counter()

        async def send_com_header(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_com_header)
        finally:
            # Uma linha por requisição (substitui o access log do uvicorn).
            log.info(
                "http.requisicao",
                metodo=scope["method"],
                caminho=scope["path"],
                status=status_code,
                duracao_ms=round((time.perf_counter() - inicio) * 1000, 1),
            )
