from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> User:
    user = User(email=payload.email, nome=payload.nome, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Quem garante a unicidade é a constraint do banco. Checar antes com
        # um SELECT não basta: duas requisições simultâneas passariam juntas.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado") from None
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> Token:
    """Recebe application/x-www-form-urlencoded com os campos
    "username" (o e-mail) e "password" — é o formato do padrão OAuth2."""
    email = form.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    # Verifica a senha MESMO se o usuário não existir (tempo de resposta parecido).
    hashed = user.hashed_password if user else DUMMY_HASH
    password_ok = verify_password(form.password, hashed)

    if user is None or not password_ok or not user.is_active:
        # Mesma mensagem para "e-mail não existe" e "senha errada":
        # não ajudamos ninguém a descobrir quais e-mails estão cadastrados.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser) -> User:
    return current_user
