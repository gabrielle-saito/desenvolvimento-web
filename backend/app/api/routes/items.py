"""CRUD de itens com autorização por dono.

Regra: cada usuário só vê e altera os PRÓPRIOS itens. A regra é aplicada
na consulta ao banco (WHERE owner_id = usuário atual), em um único lugar.
"""

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.item import Item
from app.models.user import User
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


def _get_own_item_or_404(db: DbSession, item_id: int, user: User) -> Item:
    """Busca pelo id E pelo dono. Item de outra pessoa responde 404, não 403:
    assim a API não confirma que aquele id existe."""
    item = db.scalar(select(Item).where(Item.id == item_id, Item.owner_id == user.id))
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado")
    return item


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: DbSession, current_user: CurrentUser) -> Item:
    # O dono vem do TOKEN, nunca do corpo da requisição: o cliente não escolhe
    # em nome de quem cria o item.
    item = Item(**payload.model_dump(), owner_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)  # traz id e created_at gerados pelo banco
    return item


@router.get("", response_model=list[ItemRead])
def list_items(
    db: DbSession,
    current_user: CurrentUser,
    # Limite máximo: ninguém consegue pedir 1 milhão de linhas de uma vez.
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Item]:
    stmt = (
        select(Item)
        .where(Item.owner_id == current_user.id)
        .order_by(Item.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: DbSession, current_user: CurrentUser) -> Item:
    return _get_own_item_or_404(db, item_id, current_user)


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int, payload: ItemUpdate, db: DbSession, current_user: CurrentUser
) -> Item:
    item = _get_own_item_or_404(db, item_id, current_user)
    # exclude_unset: só os campos que o cliente realmente enviou.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    item = _get_own_item_or_404(db, item_id, current_user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
