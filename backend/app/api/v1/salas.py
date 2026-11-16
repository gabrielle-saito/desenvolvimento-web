"""Salas (caso de uso 6): o "catálogo" do sistema, com busca, filtros e
paginação. Leitura: qualquer usuário logado. Escrita: admin."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import CurrentUser, DbSession, UsuarioAdmin
from app.api.paginacao import DESCRICAO_TOTAL, HEADER_TOTAL, informar_total
from app.models.sala import Sala
from app.schemas.sala import SalaAtualizar, SalaCriar, SalaLeitura
from app.servicos import salas as servico

router = APIRouter(prefix="/salas", tags=["salas"])


@router.get(
    "",
    response_model=list[SalaLeitura],
    responses={200: {"headers": {HEADER_TOTAL: DESCRICAO_TOTAL}}},
)
def listar_salas(
    response: Response,
    db: DbSession,
    usuario: CurrentUser,
    busca: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Parte do nome ou da localização (sem diferenciar maiúsculas)",
            examples=["azul"],
        ),
    ] = None,
    ativas: bool | None = Query(default=None, description="true = só ativas; false = só inativas"),
    capacidade_minima: Annotated[
        int | None, Query(gt=0, description="Só salas para pelo menos N pessoas", examples=[6])
    ] = None,
    recurso: Annotated[
        list[int],
        Query(
            description="Id de recurso. Repita para exigir vários: ?recurso=1&recurso=3",
            examples=[[1]],
        ),
    ] = [],  # noqa: B006 (o FastAPI cria uma lista nova a cada requisição)
    limit: int = Query(default=50, ge=1, le=100, description="Itens por página"),
    offset: int = Query(default=0, ge=0, description="Quantos itens pular (página × limit)"),
) -> list[Sala]:
    """Lista as salas em ordem alfabética. O total (sem paginação) vem no
    cabeçalho **X-Total-Count**."""
    salas, total = servico.listar(
        db,
        busca=busca,
        ativas=ativas,
        capacidade_minima=capacidade_minima,
        recurso_ids=recurso,
        limit=limit,
        offset=offset,
    )
    informar_total(response, total)
    return salas


@router.post("", response_model=SalaLeitura, status_code=status.HTTP_201_CREATED)
def criar_sala(
    payload: SalaCriar, request: Request, response: Response, db: DbSession, admin: UsuarioAdmin
) -> Sala:
    sala = servico.criar(db, admin, **payload.model_dump())
    response.headers["Location"] = request.app.url_path_for("obter_sala", sala_id=sala.id)
    return sala


@router.get("/{sala_id}", response_model=SalaLeitura)
def obter_sala(sala_id: int, db: DbSession, usuario: CurrentUser) -> Sala:
    return servico.obter(db, sala_id)


@router.patch("/{sala_id}", response_model=SalaLeitura)
def atualizar_sala(
    sala_id: int, payload: SalaAtualizar, db: DbSession, admin: UsuarioAdmin
) -> Sala:
    return servico.atualizar(db, admin, sala_id, payload.model_dump(exclude_unset=True))


@router.delete(
    "/{sala_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
def desativar_sala(sala_id: int, db: DbSession, admin: UsuarioAdmin) -> Response:
    """**Soft delete:** a sala é desativada, não apagada. As reservas que ela
    já tem continuam no histórico; ela só sai do catálogo e não aceita
    reservas novas. Para reativar: `PATCH` com `{"ativa": true}`.
    Idempotente: repetir o DELETE responde 204 de novo."""
    servico.desativar(db, admin, sala_id)
    # 204 = sem corpo e sem content-type (um JSON vazio quebraria o cliente).
    return Response(status_code=status.HTTP_204_NO_CONTENT)
