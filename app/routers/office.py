from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.crud.office import (
    create_office,
    get_all_offices,
    get_office_by_id,
    update_office,
    delete_office
)

from app.schemas.office import (
    OfficeCreate,
    OfficeRead,
    OfficeUpdate,
)

router = APIRouter(
    prefix="/offices",
    tags=["Offices"],
)

@router.post(
    "/",
    response_model=OfficeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Office"
    )
def add_office(office: OfficeCreate, db: Session = Depends(get_db)):
    try:
        return create_office(db, office)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

@router.get(
    "/",
    response_model=list[OfficeRead],
    summary="Get All Offices"
)
def list_offices(db: Session = Depends(get_db)):
    return get_all_offices(db)


@router.get(
    "/{office_id}",
    response_model=OfficeRead,
    summary="Get Office By ID"
)
def get_office(office_id: int, db: Session = Depends(get_db)):
    office_db = get_office_by_id(db, office_id)
    if not office_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found",
        ) 
    return office_db

@router.put(
    "/{office_id}",
    response_model=OfficeRead,
    summary="Update Office"
)
def edit_office(office_id: int, office: OfficeUpdate, db: Session = Depends(get_db)):

    try:
        result = update_office(db, office_id, office)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Office not found",
            )
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    
@router.delete(
    "/{office_id}",
    summary="Delete Office"
)

def remove_office(office_id: int, db: Session = Depends(get_db)):

    result = delete_office(db, office_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found",
        )
    
    return{
        "success": True,
        "message": "Office deleted successfully.",
    }