"""Salas (caso de uso 6). Leitura: qualquer usuário logado. Escrita: admin."""

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import CurrentUser, DbSession, UsuarioAdmin
from app.models.sala import Sala
from app.schemas.sala import SalaAtualizar, SalaCriar, SalaLeitura
from app.servicos import salas as servico

router = APIRouter(prefix="/salas", tags=["salas"])


@router.get("", response_model=list[SalaLeitura])
def listar_salas(
    db: DbSession,
    usuario: CurrentUser,
    ativas: bool | None = Query(default=None, description="true = só ativas; false = só inativas"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Sala]:
    return servico.listar(db, ativas=ativas, limit=limit, offset=offset)


@router.post("", response_model=SalaLeitura, status_code=status.HTTP_201_CREATED)
def criar_sala(
    payload: SalaCriar, request: Request, response: Response, db: DbSession, admin: UsuarioAdmin
) -> Sala:
    sala = servico.criar(db, admin, **payload.model_dump())
    response.headers["Location"] = request.app.url_path_for("obter_sala", sala_id=sala.id)
    return sala


@router.get("/{sala_id}", response_model=SalaLeitura)
def obter_sala(sala_id: int, db: DbSession, usuario: CurrentUser) -> Sala:
    return servico.obter(db, sala_id)


@router.patch("/{sala_id}", response_model=SalaLeitura)
def atualizar_sala(
    sala_id: int, payload: SalaAtualizar, db: DbSession, admin: UsuarioAdmin
) -> Sala:
    return servico.atualizar(db, admin, sala_id, payload.model_dump(exclude_unset=True))
