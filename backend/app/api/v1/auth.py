"""Autenticação. O antigo POST /auth/register (público) foi REMOVIDO:
num sistema interno de empresa, quem cria usuários é o admin
(POST /v1/usuarios)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.usuario import Token, UsuarioMe
from app.servicos import auth as servico_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """Recebe application/x-www-form-urlencoded com os campos
    "username" (o e-mail) e "password" — é o formato do padrão OAuth2."""
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
