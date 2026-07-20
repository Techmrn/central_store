from alembic.util import status
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.category import (
    create_category,
    get_all_categories,
    get_category_by_id,
    update_category,
    delete_category,
)

from app.schemas.category import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)

router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)

@router.post("/", response_model=CategoryRead)
def add_category(category: CategoryCreate, db : Session = Depends(get_db)):
    try:
        return create_category(db, category)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

@router.get("/",response_model=list[CategoryRead],)
def list_categories(db: Session = Depends(get_db),):

    return get_all_categories(db)

@router.get("/{category_id}",response_model=CategoryRead,)
def read_category(category_id: int, db: Session = Depends(get_db),):

    category_db = get_category_by_id(db,category_id,)

    if not category_db:
        raise HTTPException(
            status_code=404,
            detail="Category not found",)

    return category_db

@router.put("/{category_id}", response_model=CategoryRead)
def edit_category(category_id: int, category: CategoryUpdate, db: Session = Depends(get_db)):

    result = update_category(db, category_id, category)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )
    if result is False:
        raise HTTPException(
            status_code=409,
            detail="Category already exists"
        )
    return result

@router.delete("/{category_id}")
def remove_category(category_id: int, db: Session = Depends(get_db)):

    result = delete_category(db, category_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No such Category"
        )
    
    return {
        "Message": "Category deleted successfully.."
    }








