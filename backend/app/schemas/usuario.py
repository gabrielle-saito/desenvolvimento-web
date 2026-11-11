from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.dominio.enums import Papel
from app.schemas.comum import Entrada, Saida


class UsuarioCriar(Entrada):
    email: EmailStr
    nome: str = Field(min_length=1, max_length=120)
    # max_length também importa: hash de senhas gigantes custa CPU (negação de serviço).
    senha: str = Field(min_length=8, max_length=128)
    papel: Papel = Papel.COLABORADOR

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        # "Ana@Exemplo.com" e "ana@exemplo.com" são a mesma pessoa.
        return v.strip().lower()


class UsuarioAtualizar(Entrada):
    # Todos opcionais: PATCH altera só o que foi enviado.
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    papel: Papel | None = None
    is_active: bool | None = None


class UsuarioLeitura(Saida):
    """Saída: repare que NÃO existe campo de senha aqui."""

    id: int
    email: EmailStr
    nome: str
    papel: Papel
    is_active: bool
    created_at: datetime


class UsuarioMe(Saida):
    id: int
    nome: str
    email: EmailStr
    papel: Papel


class UsuarioResumo(Saida):
    """O que a agenda mostra de quem reservou (sem e-mail)."""

    id: int
    nome: str


class Token(Saida):
    access_token: str
    token_type: str = "bearer"
