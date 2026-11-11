"""Leitura dos códigos de erro do PostgreSQL (SQLSTATE).

Cada violação de constraint tem um código padronizado. Olhar o código é mais
robusto do que procurar texto na mensagem de erro (que muda com o idioma).
"""

from sqlalchemy.exc import DBAPIError

UNIQUE_VIOLATION = "23505"  # UNIQUE (nome de sala, e-mail)
EXCLUSION_VIOLATION = "23P01"  # EXCLUDE (sobreposição de reservas)


def sqlstate(exc: DBAPIError) -> str | None:
    # exc.orig é o erro original do driver (psycopg), que traz o SQLSTATE.
    return getattr(exc.orig, "sqlstate", None)
