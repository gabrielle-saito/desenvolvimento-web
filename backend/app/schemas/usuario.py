from datetime import datetime

from pydantic import ConfigDict, EmailStr, Field, field_validator

from app.dominio.enums import Papel
from app.schemas.comum import Entrada, Saida


def _normalizar_email(v: str) -> str:
    # "Ana@Exemplo.com" e "ana@exemplo.com" são a mesma pessoa.
    return v.strip().lower()


class UsuarioCriar(Entrada):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "carla@veritas.com",
                    "nome": "Carla Souza",
                    "senha": "uma-senha-forte",
                    "papel": "responsavel",
                }
            ]
        }
    )

    email: EmailStr
    nome: str = Field(min_length=1, max_length=120)
    # max_length também importa: hash de senhas gigantes custa CPU (negação de serviço).
    senha: str = Field(min_length=8, max_length=128)
    papel: Papel = Papel.COLABORADOR

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return _normalizar_email(v)


class UsuarioRegistro(Entrada):
    """Cadastro público. Sem campo "papel": quem se cadastra é colaborador
    (e extra="forbid" recusa com 422 quem tentar mandar "papel": "admin")."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "daniel@veritas.com", "nome": "Daniel Lima", "senha": "uma-senha-forte"}
            ]
        }
    )

    email: EmailStr
    nome: str = Field(min_length=1, max_length=120)
    senha: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return _normalizar_email(v)


class UsuarioAtualizar(Entrada):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"papel": "responsavel"}, {"is_active": False}]}
    )

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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}]
        }
    )

    access_token: str
    token_type: str = "bearer"
