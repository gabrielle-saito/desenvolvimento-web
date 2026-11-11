"""Reservas (casos de uso 1, 3, 4, 5 e 8).

Rotas só traduzem HTTP <-> serviço. Não há try/except aqui: as exceções de
domínio sobem e os handlers de app/api/erros.py respondem (409, 403, ...).
Rotas literais vêm ANTES das rotas com parâmetro.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.dominio.enums import StatusReserva
from app.models.reserva import Reserva
from app.schemas.comum import DataHoraComFuso
from app.schemas.reserva import ReservaAtualizar, ReservaCriar, ReservaLeitura
from app.servicos import reservas as servico

router = APIRouter(prefix="/reservas", tags=["reservas"])


@router.get("", response_model=list[ReservaLeitura])
def listar_reservas(
    db: DbSession,
    usuario: CurrentUser,
    sala_id: int | None = Query(default=None, gt=0),
    de: Annotated[DataHoraComFuso | None, Query(description="início da janela (com fuso)")] = None,
    ate: Annotated[DataHoraComFuso | None, Query(description="fim da janela (com fuso)")] = None,
    minhas: bool = Query(default=False, description="true = só as reservas do usuário logado"),
    status_reserva: StatusReserva | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Reserva]:
    """Agenda: todos os papéis veem todas as reservas, ordenadas por início.
    Lista vazia = não há reservas para o período (o front mostra a mensagem)."""
    return servico.listar(
        db,
        usuario,
        sala_id=sala_id,
        de=de,
        ate=ate,
        minhas=minhas,
        status=status_reserva,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ReservaLeitura, status_code=status.HTTP_201_CREATED)
def criar_reserva(
    payload: ReservaCriar, request: Request, response: Response, db: DbSession, usuario: CurrentUser
) -> Reserva:
    reserva = servico.criar(db, usuario, **payload.model_dump())
    response.headers["Location"] = request.app.url_path_for("obter_reserva", reserva_id=reserva.id)
    return reserva


@router.get("/{reserva_id}", response_model=ReservaLeitura)
def obter_reserva(reserva_id: int, db: DbSession, usuario: CurrentUser) -> Reserva:
    return servico.obter(db, reserva_id)


@router.patch("/{reserva_id}", response_model=ReservaLeitura)
def editar_reserva(
    reserva_id: int, payload: ReservaAtualizar, db: DbSession, usuario: CurrentUser
) -> Reserva:
    alteracoes = payload.model_dump(exclude_unset=True)
    versao = alteracoes.pop("versao")
    return servico.editar(db, usuario, reserva_id, versao=versao, alteracoes=alteracoes)


@router.post("/{reserva_id}/cancelamento", response_model=ReservaLeitura)
def cancelar_reserva(reserva_id: int, db: DbSession, usuario: CurrentUser) -> Reserva:
    """Cancelar é uma MUDANÇA DE ESTADO (POST num sub-recurso), não DELETE:
    a reserva continua existindo, com status "cancelada", para o histórico."""
    return servico.cancelar(db, usuario, reserva_id)
