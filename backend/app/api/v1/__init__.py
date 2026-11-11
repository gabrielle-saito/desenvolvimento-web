"""API versão 1. Tudo aqui fica sob o prefixo /v1.

Uma mudança que quebre clientes (renomear campo, mudar formato) vira /v2,
convivendo com a /v1 enquanto os clientes migram (ver ADR-002).
"""

from fastapi import APIRouter

from app.api.v1 import auditoria, auth, disponibilidade, reservas, salas, usuarios

router = APIRouter(prefix="/v1")
router.include_router(auth.router)
router.include_router(usuarios.router)
router.include_router(salas.router)
router.include_router(disponibilidade.router)
router.include_router(reservas.router)
router.include_router(auditoria.router)
