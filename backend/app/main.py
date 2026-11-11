from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.routes import auth, items
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

# CORS restrito: lista explícita de origens, nunca "*" junto com credenciais.
# Lembre: CORS protege o USUÁRIO no navegador; não impede curl nem Postman.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(items.router)


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
