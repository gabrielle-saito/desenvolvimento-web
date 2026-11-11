from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import v1
from app.api.deps import DbSession
from app.api.erros import registrar_handlers
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Sistema web de reserva de salas da empresa (monolito modular).",
)

# Erros em Problem Details (RFC 9457): um handler por família de exceção.
registrar_handlers(app)

# CORS restrito: lista explícita de origens, nunca "*" junto com credenciais.
# Lembre: CORS protege o USUÁRIO no navegador; não impede curl nem Postman.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(v1.router)


@app.get("/health", tags=["infra"])
def health(db: DbSession) -> JSONResponse:
    """API de pé E banco respondendo. 503 se o banco estiver fora."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            {"status": "degraded", "database": "unreachable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse({"status": "ok", "database": "ok"})
