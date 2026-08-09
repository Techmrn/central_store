from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.common import PaginatedResponse

from app.dependencies.permissions import require_permission

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
    tags=["Categories"],
)


# ---------------------------------------------------------------
# Create
# ---------------------------------------------------------------

@router.post(
    "/",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Category",
)
def add_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("CATEGORY_CREATE")),
):
    try:
        return create_category(db, category)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


# ---------------------------------------------------------------
# Read All
# ---------------------------------------------------------------

@router.get(
    "/",
    response_model=PaginatedResponse[CategoryRead],
    summary="Get All Categories",
)
def list_categories(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("CATEGORY_VIEW")),
):
    return get_all_categories(db)


# ---------------------------------------------------------------
# Read One
# ---------------------------------------------------------------

@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Get Category By ID",
)
def read_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("CATEGORY_VIEW")),
):

    category_db = get_category_by_id(db, category_id)

    if category_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    return category_db


# ---------------------------------------------------------------
# Update
# ---------------------------------------------------------------

@router.put(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Update Category",
)
def edit_category(
    category_id: int,
    category: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("CATEGORY_UPDATE")),
):

    try:

        result = update_category(
            db=db,
            category_id=category_id,
            category=category,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


# ---------------------------------------------------------------
# Delete
# ---------------------------------------------------------------

@router.delete(
    "/{category_id}",
    summary="Delete Category",
)
def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("CATEGORY_DELETE")),
):

    result = delete_category(db, category_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    return {
        "success": True,
        "message": "Category deleted successfully.",
    }