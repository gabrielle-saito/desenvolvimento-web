"""Gestão de usuários (caso de uso 7). Somente admin."""

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import DbSession, UsuarioAdmin
from app.models.user import User
from app.schemas.usuario import UsuarioAtualizar, UsuarioCriar, UsuarioLeitura
from app.servicos import usuarios as servico

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioLeitura])
def listar_usuarios(
    db: DbSession,
    admin: UsuarioAdmin,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[User]:
    return servico.listar(db, limit=limit, offset=offset)


@router.post("", response_model=UsuarioLeitura, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    payload: UsuarioCriar, request: Request, response: Response, db: DbSession, admin: UsuarioAdmin
) -> User:
    usuario = servico.criar(db, admin, **payload.model_dump())
    # 201 Created + Location: onde o recurso novo pode ser lido.
    response.headers["Location"] = request.app.url_path_for("obter_usuario", usuario_id=usuario.id)
    return usuario


@router.get("/{usuario_id}", response_model=UsuarioLeitura)
def obter_usuario(usuario_id: int, db: DbSession, admin: UsuarioAdmin) -> User:
    return servico.obter(db, usuario_id)


@router.patch("/{usuario_id}", response_model=UsuarioLeitura)
def atualizar_usuario(
    usuario_id: int, payload: UsuarioAtualizar, db: DbSession, admin: UsuarioAdmin
) -> User:
    # exclude_unset: só os campos que o cliente realmente enviou.
    return servico.atualizar(db, admin, usuario_id, payload.model_dump(exclude_unset=True))
