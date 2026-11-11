"""Ajuste do documento OpenAPI gerado pelo FastAPI.

O FastAPI documenta toda resposta como application/json. Os nossos ERROS
saem como application/problem+json (RFC 9457), então movemos o schema das
respostas 4xx para esse media type: o contrato descreve o que a API faz.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

PROBLEM_JSON = "application/problem+json"


def instalar_openapi(app: FastAPI) -> None:
    def gerar() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        doc = get_openapi(
            title=app.title, version=app.version, description=app.description, routes=app.routes
        )
        for operacoes in doc.get("paths", {}).values():
            for operacao in operacoes.values():
                for status, resposta in operacao.get("responses", {}).items():
                    conteudo = resposta.get("content", {})
                    if status.startswith("4") and PROBLEM_JSON in conteudo:
                        schema = conteudo.pop("application/json", {}).get("schema")
                        if schema:
                            conteudo[PROBLEM_JSON] = {"schema": schema}
        app.openapi_schema = doc
        return doc

    app.openapi = gerar  # type: ignore[method-assign]
