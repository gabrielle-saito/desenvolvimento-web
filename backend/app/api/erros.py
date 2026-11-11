"""Erros em Problem Details (RFC 9457), num formato só para a API inteira.

Content-Type: application/problem+json
{
  "type": "/problemas/conflito-de-horario",   <- identifica o TIPO de problema
  "title": "Conflito de horário",              <- resumo fixo do tipo
  "status": 409,
  "detail": "Sala ocupada nesse horário...",   <- explicação DESTA ocorrência
  "instance": "/v1/reservas"                   <- onde aconteceu
}

Aqui é o ÚNICO lugar que sabe que ConflitoDeHorario vira 409. As rotas não
têm try/except: a exceção de domínio sobe e um destes handlers responde.
"""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.dominio.excecoes import (
    AcessoNegado,
    Conflito,
    ConflitoDeHorario,
    JaExiste,
    NaoEncontrado,
    OperacaoProibida,
    PeriodoInvalido,
    ReservaNaoAlteravel,
    SalaInativa,
    VersaoDesatualizada,
)

MEDIA_TYPE_PROBLEMA = "application/problem+json"


def resposta_problema(
    request: Request,
    status: int,
    detail: str,
    *,
    tipo: str = "about:blank",
    title: str | None = None,
    headers: dict[str, str] | None = None,
    **extensoes: Any,
) -> JSONResponse:
    corpo = {
        "type": tipo,
        # Com type "about:blank" a RFC pede que o title seja a frase do status.
        "title": title or HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        **extensoes,
    }
    return JSONResponse(corpo, status_code=status, media_type=MEDIA_TYPE_PROBLEMA, headers=headers)


# ------------------------------------------------- famílias de exceção de domínio
def tratar_nao_encontrado(request: Request, exc: NaoEncontrado) -> JSONResponse:
    return resposta_problema(
        request, 404, exc.mensagem, tipo="/problemas/nao-encontrado", title="Não encontrado"
    )


def tratar_acesso_negado(request: Request, exc: AcessoNegado) -> JSONResponse:
    return resposta_problema(
        request, 403, exc.mensagem, tipo="/problemas/acesso-negado", title="Acesso negado"
    )


def tratar_periodo_invalido(request: Request, exc: PeriodoInvalido) -> JSONResponse:
    return resposta_problema(
        request, 422, exc.mensagem, tipo="/problemas/periodo-invalido", title="Período inválido"
    )


# type e title de cada conflito (409). A ordem importa: a primeira classe que
# combinar com a exceção (isinstance) vence.
_CONFLITOS: list[tuple[type[Conflito], str, str]] = [
    (ConflitoDeHorario, "conflito-de-horario", "Conflito de horário"),
    (VersaoDesatualizada, "versao-desatualizada", "Versão desatualizada"),
    (ReservaNaoAlteravel, "reserva-nao-alteravel", "Reserva não pode ser alterada"),
    (SalaInativa, "sala-inativa", "Sala inativa"),
    (JaExiste, "ja-existe", "Registro duplicado"),
    (OperacaoProibida, "operacao-proibida", "Operação não permitida"),
]


def tratar_conflito(request: Request, exc: Conflito) -> JSONResponse:
    slug, title = next(
        ((s, t) for classe, s, t in _CONFLITOS if isinstance(exc, classe)),
        ("conflito", "Conflito"),
    )
    extensoes: dict[str, Any] = {}
    if isinstance(exc, ConflitoDeHorario):
        extensoes["reservas_conflitantes"] = exc.reservas_conflitantes
    if isinstance(exc, VersaoDesatualizada):
        extensoes["versao_atual"] = exc.versao_atual
    return resposta_problema(
        request, 409, exc.mensagem, tipo=f"/problemas/{slug}", title=title, **extensoes
    )


# ------------------------------------------------------- erros do framework
# Mensagens do Pydantic traduzidas para os casos mais comuns.
_MENSAGENS = {
    "missing": "Campo obrigatório.",
    "extra_forbidden": "Campo não permitido.",
    "timezone_aware": "Informe a data com fuso horário (ex.: 2030-01-31T14:00:00-03:00).",
    "datetime_from_date_parsing": "Data/hora inválida. Use ISO 8601 com fuso horário.",
    "datetime_parsing": "Data/hora inválida. Use ISO 8601 com fuso horário.",
    "datetime_type": "Data/hora inválida. Use ISO 8601 com fuso horário.",
    "int_parsing": "Informe um número inteiro.",
    "string_too_short": "Não pode ficar vazio.",
}


def tratar_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
    erros = exc.errors()
    # JSON quebrado não é "dado inválido", é "corpo ilegível": 400.
    if any(e.get("type") == "json_invalid" for e in erros):
        return resposta_problema(
            request,
            400,
            "O corpo da requisição não é um JSON válido.",
            tipo="/problemas/corpo-ilegivel",
            title="Corpo ilegível",
        )
    lista = []
    for e in erros:
        loc = [str(p) for p in e.get("loc", ())]
        # ("body", "inicio") -> local "body", campo "inicio"
        local, caminho = (loc[0], loc[1:]) if loc else ("", [])
        lista.append(
            {
                "campo": ".".join(caminho) or local,
                "local": local,
                "mensagem": _MENSAGENS.get(e.get("type", ""), e.get("msg", "Valor inválido.")),
            }
        )
    return resposta_problema(
        request,
        422,
        "Um ou mais campos são inválidos.",
        tipo="/problemas/validacao",
        title="Dados inválidos",
        erros=lista,
    )


def tratar_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    if exc.status_code == 404 and detail == "Not Found":
        detail = "Recurso não encontrado."
    elif exc.status_code == 405:
        detail = "Método não permitido para esta rota."
    return resposta_problema(request, exc.status_code, detail, headers=exc.headers)


def tratar_inesperado(request: Request, exc: Exception) -> JSONResponse:
    """500: o cliente recebe uma mensagem genérica, SEM stack trace (que
    revelaria detalhes internos). O detalhe completo vai para o log."""
    return resposta_problema(
        request, 500, "Erro interno inesperado. Tente novamente mais tarde."
    )


def registrar_handlers(app: FastAPI) -> None:
    """Um handler por família de exceção de domínio + os do framework."""
    app.add_exception_handler(NaoEncontrado, tratar_nao_encontrado)
    app.add_exception_handler(AcessoNegado, tratar_acesso_negado)
    app.add_exception_handler(PeriodoInvalido, tratar_periodo_invalido)
    app.add_exception_handler(Conflito, tratar_conflito)
    app.add_exception_handler(RequestValidationError, tratar_validacao)
    app.add_exception_handler(StarletteHTTPException, tratar_http)
    app.add_exception_handler(Exception, tratar_inesperado)
