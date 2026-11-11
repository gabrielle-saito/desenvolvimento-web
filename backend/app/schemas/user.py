from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    nome: str = Field(min_length=1, max_length=120)
    # max_length também importa: hash de senhas gigantes custa CPU (negação de serviço).
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        # "Ana@Exemplo.com" e "ana@exemplo.com" são a mesma pessoa.
        return v.strip().lower()


class UserRead(BaseModel):
    """Saída: repare que NÃO existe campo de senha aqui."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nome: str
    papel: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
