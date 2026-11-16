"""Autenticação e cadastro público.

POST /v1/auth/registro: a própria pessoa cria a conta, SEMPRE como
colaborador. Papéis maiores (responsável, admin) só o admin concede, pelo
PATCH /v1/usuarios/{id}."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.usuario import Token, UsuarioMe, UsuarioRegistro
from app.servicos import auth as servico_auth
from app.servicos import usuarios as servico_usuarios

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", response_model=UsuarioMe, status_code=status.HTTP_201_CREATED)
def registrar(
    payload: UsuarioRegistro, request: Request, response: Response, db: DbSession
) -> User:
    """Cria a conta de quem está se cadastrando (público, sem token).
    Depois do cadastro, faça login em POST /v1/auth/login.
    E-mail já cadastrado: 409."""
    usuario = servico_usuarios.registrar(db, **payload.model_dump())
    response.headers["Location"] = request.app.url_path_for("me")
    return usuario


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """Recebe application/x-www-form-urlencoded com os campos
    "username" (o e-mail) e "password" — é o formato do padrão OAuth2.

    Exemplo (curl):
    `curl -X POST /v1/auth/login -d "username=ana@empresa.com&password=senha-demo-123"`

    Resposta: `{"access_token": "eyJ...", "token_type": "bearer"}`. Envie o
    token nas outras rotas no cabeçalho `Authorization: Bearer <token>`
    (no Swagger: botão **Authorize**)."""
    usuario = servico_auth.autenticar(db, form.username, form.password)
    if usuario is None:
        # Mesma mensagem para "e-mail não existe", "senha errada" e "conta
        # desativada": não ajudamos ninguém a descobrir quais e-mails existem.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(usuario.id)))


@router.get("/me", response_model=UsuarioMe)
def me(current_user: CurrentUser) -> User:
    return current_user
