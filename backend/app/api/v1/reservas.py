"""Reservas (casos de uso 1, 3, 4, 5 e 8).

Rotas só traduzem HTTP <-> serviço. Não há try/except aqui: as exceções de
domínio sobem e os handlers de app/api/erros.py respondem (409, 403, ...).
Rotas literais vêm ANTES das rotas com parâmetro.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.api.paginacao import DESCRICAO_TOTAL, HEADER_TOTAL, informar_total
from app.dominio.enums import StatusReserva
from app.schemas.comum import DataHoraComFuso
from app.schemas.reserva import (
    ReservaAtualizar,
    ReservaCriar,
    ReservaLeitura,
    reserva_para,
)
from app.servicos import reservas as servico

router = APIRouter(prefix="/reservas", tags=["reservas"])


@router.get(
    "",
    response_model=list[ReservaLeitura],
    responses={200: {"headers": {HEADER_TOTAL: DESCRICAO_TOTAL}}},
)
def listar_reservas(
    response: Response,
    db: DbSession,
    usuario: CurrentUser,
    sala_id: int | None = Query(default=None, gt=0),
    de: Annotated[DataHoraComFuso | None, Query(description="início da janela (com fuso)")] = None,
    ate: Annotated[DataHoraComFuso | None, Query(description="fim da janela (com fuso)")] = None,
    minhas: bool = Query(default=False, description="true = só as reservas do usuário logado"),
    status_reserva: StatusReserva | None = Query(default=None, alias="status"),
    busca: str | None = Query(
        default=None, min_length=1, max_length=100, description="Parte da finalidade",
        examples=["daily"],
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ReservaLeitura]:
    """Agenda, ordenada por início.

    - **Responsável e admin:** todas as reservas, completas.
    - **Colaborador:** as próprias, completas; das outras pessoas, só as
      ativas e só a ocupação (sala e horário). Quem reservou e a finalidade
      vêm nulos, com `detalhes_ocultos: true`. A `busca` e `status=cancelada`
      procuram só nas próprias.

    Lista vazia = não há reservas para o período (o front mostra a mensagem).
    O total (sem paginação) vem no cabeçalho **X-Total-Count**."""
    reservas, total = servico.listar(
        db,
        usuario,
        sala_id=sala_id,
        de=de,
        ate=ate,
        minhas=minhas,
        status=status_reserva,
        busca=busca,
        limit=limit,
        offset=offset,
    )
    informar_total(response, total)
    return [reserva_para(r, usuario) for r in reservas]


@router.post("", response_model=ReservaLeitura, status_code=status.HTTP_201_CREATED)
def criar_reserva(
    payload: ReservaCriar, request: Request, response: Response, db: DbSession, usuario: CurrentUser
) -> ReservaLeitura:
    reserva = servico.criar(db, usuario, **payload.model_dump())
    response.headers["Location"] = request.app.url_path_for("obter_reserva", reserva_id=reserva.id)
    return reserva_para(reserva, usuario)


@router.get("/{reserva_id}", response_model=ReservaLeitura)
def obter_reserva(reserva_id: int, db: DbSession, usuario: CurrentUser) -> ReservaLeitura:
    """Colaborador só abre as próprias: reserva de outra pessoa responde 404."""
    return reserva_para(servico.obter_para(db, usuario, reserva_id), usuario)


@router.patch("/{reserva_id}", response_model=ReservaLeitura)
def editar_reserva(
    reserva_id: int, payload: ReservaAtualizar, db: DbSession, usuario: CurrentUser
) -> ReservaLeitura:
    alteracoes = payload.model_dump(exclude_unset=True)
    versao = alteracoes.pop("versao")
    reserva = servico.editar(db, usuario, reserva_id, versao=versao, alteracoes=alteracoes)
    return reserva_para(reserva, usuario)


@router.post("/{reserva_id}/cancelamento", response_model=ReservaLeitura)
def cancelar_reserva(reserva_id: int, db: DbSession, usuario: CurrentUser) -> ReservaLeitura:
    """Cancelar é uma MUDANÇA DE ESTADO (POST num sub-recurso), não DELETE:
    a reserva continua existindo, com status "cancelada", para o histórico."""
    return reserva_para(servico.cancelar(db, usuario, reserva_id), usuario)
