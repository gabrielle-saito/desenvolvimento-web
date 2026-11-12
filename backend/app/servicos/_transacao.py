"""Tradução de erros do banco em exceções de domínio, num lugar só."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.dominio.excecoes import ConflitoDeHorario, JaExiste, VersaoDesatualizada
from app.repositorios.erros import EXCLUSION_VIOLATION, UNIQUE_VIOLATION, sqlstate


@contextmanager
def traduzindo_erros_do_banco(
    db: Session, *, mensagem_duplicado: str = "Registro duplicado."
) -> Iterator[None]:
    """Use em volta do flush/commit:

        with traduzindo_erros_do_banco(db):
            db.commit()

    - 23P01 (constraint de exclusão)  -> ConflitoDeHorario
    - 23505 (unique)                  -> JaExiste
    - StaleDataError (version_id_col) -> VersaoDesatualizada
    Qualquer outro erro sobe como está (é bug, não regra de negócio).
    """
    try:
        yield
    except IntegrityError as exc:
        db.rollback()
        codigo = sqlstate(exc)
        if codigo == EXCLUSION_VIOLATION:
            raise ConflitoDeHorario() from None
        if codigo == UNIQUE_VIOLATION:
            raise JaExiste(mensagem_duplicado) from None
        raise
    except StaleDataError:
        db.rollback()
        raise VersaoDesatualizada() from None
