from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.permissions import require_permission
from app.crud.item import (
    create_item,
    get_all_items,
    get_item_by_id,
    update_item,
    delete_item,
)

from app.schemas.common import PaginatedResponse
from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemRead,
)

router = APIRouter(
    prefix="/items",
    tags=["Items"],
)


@router.post(
    "/",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Item",
)
def add_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ITEM_CREATE")),
):
    try:
        return create_item(db, item)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[ItemRead],
    summary="Get All Items",
)
def get_items(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ITEM_VIEW")),
):
    return get_all_items(db)


@router.get(
    "/{item_id}",
    response_model=ItemRead,
    summary="Get Item By ID",
)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ITEM_VIEW")),
):
    item = get_item_by_id(
        db,
        item_id,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )

    return item


@router.put(
    "/{item_id}",
    response_model=ItemRead,
    summary="Update Item",
)
def edit_item(
    item_id: int,
    item: ItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ITEM_UPDATE")),
):
    try:
        return update_item(
            db,
            item_id,
            item,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{item_id}",
    response_model=ItemRead,
    summary="Delete Item",
)
def remove_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ITEM_DELETE")),
):
    item = delete_item(
        db,
        item_id,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )

    return item