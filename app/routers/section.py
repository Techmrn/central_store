from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.crud.section import (
    create_section,
    get_all_sections,
    get_section_by_id,
    update_section,
    delete_section,
)

from app.schemas.sections import (
    SectionCreate,
    SectionRead,
    SectionUpdate,
)

router = APIRouter(
    prefix="/sections",
    tags=["Sections"],
)


@router.post(
    "/",
    response_model=SectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Section",
)
def add_section(
    section: SectionCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_section(db, section)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[SectionRead],
    summary="Get All Sections",
)
def list_sections(db: Session = Depends(get_db)):
    return get_all_sections(db)


@router.get(
    "/{section_id}",
    response_model=SectionRead,
    summary="Get Section By ID",
)
def get_section(
    section_id: int,
    db: Session = Depends(get_db),
):
    section_db = get_section_by_id(db, section_id)

    if not section_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found",
        )

    return section_db


@router.put(
    "/{section_id}",
    response_model=SectionRead,
    summary="Update Section",
)
def edit_section(
    section_id: int,
    section: SectionUpdate,
    db: Session = Depends(get_db),
):
    try:
        result = update_section(db, section_id, section)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found",
            )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{section_id}",
    summary="Delete Section",
)
def remove_section(
    section_id: int,
    db: Session = Depends(get_db),
):
    result = delete_section(db, section_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found",
        )

    return {
        "success": True,
        "message": "Section deleted successfully.",
    }