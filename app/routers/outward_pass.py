from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.outward_pass import (
    create_outward_pass,
    get_all_outward_passes,
    get_outward_pass_by_id,
    get_outward_pass_by_issue_id,
)
from app.dependencies.permissions import require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.outward_pass import (
    OutwardPassCreate,
    OutwardPassRead,
)

router = APIRouter(
    prefix="/outward-passes",
    tags=["Outward Passes"],
)


def _handle_value_error(e: ValueError):
    msg = str(e)
    if "already exists" in msg.lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
    elif "not found" in msg.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post(
    "/",
    response_model=OutwardPassRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Outward Pass",
)
def add_outward_pass(
    pass_in: OutwardPassCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OUTWARD_PASS_CREATE")),
):
    try:
        return create_outward_pass(db=db, pass_in=pass_in, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/",
    response_model=PaginatedResponse[OutwardPassRead],
    summary="Get All Outward Passes",
)
def get_outward_passes(
    search: str = "",
    pass_no: Optional[str] = None,
    issue_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OUTWARD_PASS_VIEW")),
):
    return get_all_outward_passes(
        db=db,
        search=search,
        pass_no=pass_no,
        issue_id=issue_id,
        page=page,
    )


@router.get(
    "/{pass_id}",
    response_model=OutwardPassRead,
    summary="Get Outward Pass By ID",
)
def get_outward_pass(
    pass_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OUTWARD_PASS_VIEW")),
):
    op = get_outward_pass_by_id(db, pass_id)
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outward Pass not found.")
    return op


@router.get(
    "/issue/{issue_id}",
    response_model=OutwardPassRead,
    summary="Get Outward Pass By Issue ID",
)
def get_outward_pass_by_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OUTWARD_PASS_VIEW")),
):
    op = get_outward_pass_by_issue_id(db, issue_id)
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outward Pass for this issue not found.")
    return op
