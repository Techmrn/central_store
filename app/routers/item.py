from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.item import (
    create_item,
    get_all_items,
    get_item_by_id,
    update_item,
    delete_item,
)
from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemRead,
)

router = APIRouter(
    prefix="/items",
    tags=["Items"],
)

@router.post("/", response_model=ItemRead)
def add_item(item: ItemCreate, db: Session = Depends(get_db)):
    try:
        return create_item(db, item)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.get("/", response_model=list[ItemRead])
def get_items(
    db: Session = Depends(get_db),
):
    return get_all_items(db)


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = get_item_by_id(
        db,
        item_id,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found.",
        )

    return item


@router.put("/{item_id}", response_model=ItemRead)
def edit_item(
    item_id: int,
    item: ItemUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_item(
            db,
            item_id,
            item,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.delete("/{item_id}", response_model=ItemRead)
def remove_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = delete_item(
        db,
        item_id,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found.",
        )

    return item