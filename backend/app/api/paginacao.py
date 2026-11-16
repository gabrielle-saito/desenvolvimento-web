"""Paginação das listagens.

O corpo continua sendo a LISTA (os clientes atuais não quebram) e o total vem
no cabeçalho X-Total-Count. Com ele e o limit/offset, a tela monta
"Página 2 de 4" e sabe se existe próxima página.
"""

from fastapi import Response

HEADER_TOTAL = "X-Total-Count"

DESCRICAO_TOTAL = {
    "description": "Total de itens que passam nos filtros (para a paginação)",
    "schema": {"type": "integer", "example": 15},
}


def informar_total(response: Response, total: int) -> None:
    response.headers[HEADER_TOTAL] = str(total)
