from collections.abc import Sequence

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.recurso import sala_recursos
from app.models.sala import Sala


def buscar(db: Session, sala_id: int) -> Sala | None:
    return db.get(Sala, sala_id)


def _filtrado(
    *,
    busca: str | None,
    ativas: bool | None,
    capacidade_minima: int | None,
    recurso_ids: Sequence[int],
) -> Select[tuple[Sala]]:
    stmt = select(Sala)
    if busca:
        # Busca por parte do nome OU da localização, sem diferenciar
        # maiúsculas. autoescape: "%" e "_" digitados contam como texto,
        # não como curinga do LIKE. (O valor vai como parâmetro: sem injeção.)
        stmt = stmt.where(
            or_(
                Sala.nome.icontains(busca, autoescape=True),
                Sala.localizacao.icontains(busca, autoescape=True),
            )
        )
    if ativas is not None:
        stmt = stmt.where(Sala.ativa.is_(ativas))
    if capacidade_minima is not None:
        stmt = stmt.where(Sala.capacidade >= capacidade_minima)
    # Vários recursos = a sala precisa ter TODOS ("projetor E videoconferência").
    for recurso_id in set(recurso_ids):
        stmt = stmt.where(
            exists().where(
                sala_recursos.c.sala_id == Sala.id, sala_recursos.c.recurso_id == recurso_id
            )
        )
    return stmt


def listar(
    db: Session,
    *,
    busca: str | None = None,
    ativas: bool | None = None,
    capacidade_minima: int | None = None,
    recurso_ids: Sequence[int] = (),
    limit: int | None = None,
    offset: int = 0,
) -> list[Sala]:
    stmt = _filtrado(
        busca=busca, ativas=ativas, capacidade_minima=capacidade_minima, recurso_ids=recurso_ids
    ).order_by(Sala.nome)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt.offset(offset)))


def contar(
    db: Session,
    *,
    busca: str | None = None,
    ativas: bool | None = None,
    capacidade_minima: int | None = None,
    recurso_ids: Sequence[int] = (),
) -> int:
    """Total de salas que passam nos filtros (sem limit/offset): é o que a
    tela precisa para montar a paginação ("página 2 de 4")."""
    stmt = _filtrado(
        busca=busca, ativas=ativas, capacidade_minima=capacidade_minima, recurso_ids=recurso_ids
    )
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def adicionar(db: Session, sala: Sala) -> None:
    db.add(sala)
