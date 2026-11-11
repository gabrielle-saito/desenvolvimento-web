"""Dependências injetadas nas rotas com Depends()."""

from collections.abc import Callable, Iterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.dominio.enums import Papel
from app.dominio.excecoes import AcessoNegado
from app.dominio.permissoes import tem_papel_minimo
from app.models.user import User


def get_db() -> Iterator[Session]:
    """Uma sessão por requisição, sempre fechada no final (mesmo com erro)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]

# Lê o cabeçalho "Authorization: Bearer <token>". O tokenUrl só informa ao
# Swagger onde fazer login (botão "Authorize").
# auto_error=False: sem token, NÓS respondemos o 401 (com mensagem em português).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)], db: DbSession
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado: faça login para continuar.",
        headers={"WWW-Authenticate": "Bearer"},  # exigido pela RFC 6750 no 401
    )
    if not token:
        raise credentials_error
    try:
        user_id = int(decode_access_token(token))
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_error from None

    user = db.get(User, user_id)
    # Token válido de um usuário apagado ou desativado também é recusado.
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def exigir_papel(minimo: Papel) -> Callable[[User], User]:
    """Fábrica de dependência do RBAC: Depends(exigir_papel(Papel.ADMIN)).

    Sem token -> 401 (get_current_user). Com token, mas papel abaixo do
    mínimo -> 403 (AcessoNegado). A regra de hierarquia mora no domínio.
    """

    def dependencia(usuario: CurrentUser) -> User:
        if not tem_papel_minimo(usuario.papel, minimo):
            raise AcessoNegado(f"Esta ação exige o papel '{minimo.value}' ou superior.")
        return usuario

    return dependencia


UsuarioResponsavel = Annotated[User, Depends(exigir_papel(Papel.RESPONSAVEL))]
UsuarioAdmin = Annotated[User, Depends(exigir_papel(Papel.ADMIN))]
