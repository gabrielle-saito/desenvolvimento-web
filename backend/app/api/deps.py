"""Dependências injetadas nas rotas com Depends()."""

from collections.abc import Iterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},  # exigido pela RFC 6750 no 401
    )
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
