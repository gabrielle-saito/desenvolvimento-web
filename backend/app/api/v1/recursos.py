"""Recursos das salas (projetor, TV, videoconferência...).
Leitura: qualquer usuário logado (para filtrar o catálogo). Escrita: admin.
Não há DELETE: recurso é desativado (ativo=false), como as salas."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import CurrentUser, DbSession, UsuarioAdmin
from app.api.paginacao import DESCRICAO_TOTAL, HEADER_TOTAL, informar_total
from app.models.recurso import Recurso
from app.schemas.recurso import RecursoAtualizar, RecursoCriar, RecursoLeitura
from app.servicos import recursos as servico

router = APIRouter(prefix="/recursos", tags=["recursos"])


@router.get(
    "",
    response_model=list[RecursoLeitura],
    responses={200: {"headers": {HEADER_TOTAL: DESCRICAO_TOTAL}}},
)
def listar_recursos(
    response: Response,
    db: DbSession,
    usuario: CurrentUser,
    busca: Annotated[
        str | None, Query(min_length=1, max_length=80, description="Parte do nome", examples=["proj"])
    ] = None,
    ativos: bool | None = Query(default=None, description="true = só ativos; false = só inativos"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Recurso]:
    recursos, total = servico.listar(db, busca=busca, ativos=ativos, limit=limit, offset=offset)
    informar_total(response, total)
    return recursos


@router.post("", response_model=RecursoLeitura, status_code=status.HTTP_201_CREATED)
def criar_recurso(
    payload: RecursoCriar,
    request: Request,
    response: Response,
    db: DbSession,
    admin: UsuarioAdmin,
) -> Recurso:
    recurso = servico.criar(db, admin, **payload.model_dump())
    response.headers["Location"] = request.app.url_path_for("obter_recurso", recurso_id=recurso.id)
    return recurso


@router.get("/{recurso_id}", response_model=RecursoLeitura)
def obter_recurso(recurso_id: int, db: DbSession, usuario: CurrentUser) -> Recurso:
    return servico.obter(db, recurso_id)


@router.patch("/{recurso_id}", response_model=RecursoLeitura)
def atualizar_recurso(
    recurso_id: int, payload: RecursoAtualizar, db: DbSession, admin: UsuarioAdmin
) -> Recurso:
    return servico.atualizar(db, admin, recurso_id, payload.model_dump(exclude_unset=True))
