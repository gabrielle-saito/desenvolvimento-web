"""Formato de erro da API (RFC 9457), só para DOCUMENTAR no OpenAPI.
Quem monta a resposta de verdade é app/api/erros.py."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErroDeCampo(BaseModel):
    campo: str
    local: str
    mensagem: str


class Problema(BaseModel):
    # Extensões (erros, versao_atual, reservas_conflitantes, request_id) são
    # permitidas pela RFC: por isso extra="allow".
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "type": "/problemas/conflito-de-horario",
                "title": "Conflito de horário",
                "status": 409,
                "detail": "Sala ocupada nesse horário. Escolha outro horário ou outra sala.",
                "instance": "/v1/reservas",
                "reservas_conflitantes": [7],
            }
        },
    )

    type: str
    title: str
    status: int
    detail: str
    instance: str
    erros: list[ErroDeCampo] | None = None


def _resposta(descricao: str) -> dict[str, Any]:
    return {
        "description": descricao,
        "model": Problema,
        "content": {"application/problem+json": {}},
    }


RESPOSTAS_DE_ERRO: dict[int | str, dict[str, Any]] = {
    400: _resposta("Corpo ilegível (JSON inválido)"),
    401: _resposta("Sem token, token inválido/expirado ou usuário desativado"),
    403: _resposta("Papel insuficiente ou reserva de outra pessoa"),
    404: _resposta("Recurso não encontrado"),
    409: _resposta(
        "Conflito: horário ocupado, versão desatualizada, nome/e-mail duplicado, "
        "reserva cancelada/iniciada ou sala inativa"
    ),
    422: _resposta("Dados inválidos (lista em 'erros') ou período inválido"),
}
