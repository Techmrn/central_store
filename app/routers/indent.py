from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.indent import (
    close_indent,
    create_indent,
    delete_indent,
    get_all_indents,
    get_indent_by_id,
    update_indent,
)
from app.dependencies.permissions import require_permission
from app.models.enums import IndentStatus, RequestSource
from app.schemas.common import PaginatedResponse
from app.schemas.indent import (
    IndentCloseResponse,
    IndentCreate,
    IndentRead,
    IndentUpdate,
)

router = APIRouter(
    prefix="/indents",
    tags=["Indents"],
)


def _handle_value_error(e: ValueError):
    msg = str(e)
    if "already exists" in msg.lower():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )
    elif "not found" in msg.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


@router.post(
    "/",
    response_model=IndentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Indent",
)
def add_indent(
    indent: IndentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("INDENT_CREATE")),
):
    try:
        return create_indent(
            db=db,
            indent_in=indent,
            user_id=current_user.id,
        )
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/",
    response_model=PaginatedResponse[IndentRead],
    summary="Get All Indents",
)
def get_indents(
    search: str = "",
    indent_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    indent_status: Optional[IndentStatus] = None,
    request_source: Optional[RequestSource] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("INDENT_VIEW")),
):
    return get_all_indents(
        db=db,
        search=search,
        indent_no=indent_no,
        financial_year_id=financial_year_id,
        office_id=office_id,
        section_id=section_id,
        status=indent_status,
        request_source=request_source,
        page=page,
    )


@router.get(
    "/{indent_id}",
    response_model=IndentRead,
    summary="Get Indent By ID",
)
def get_indent(
    indent_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("INDENT_VIEW")),
):
    indent = get_indent_by_id(db, indent_id)
    if indent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Indent not found.",
        )
    return indent


@router.put(
    "/{indent_id}",
    response_model=IndentRead,
    summary="Update Indent / Process Issued Quantities",
)
def edit_indent(
    indent_id: int,
    indent: IndentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("INDENT_UPDATE")),
):
    try:
        return update_indent(
            db=db,
            indent_id=indent_id,
            indent_in=indent,
            user_id=current_user.id,
        )
    except ValueError as e:
        _handle_value_error(e)


@router.delete(
    "/{indent_id}",
    response_model=IndentRead,
    summary="Delete Indent",
)
def remove_indent(
    indent_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("INDENT_DELETE")),
):
    try:
        indent = delete_indent(db, indent_id)
        if indent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Indent not found.",
            )
        return indent
    except ValueError as e:
        _handle_value_error(e)


@router.post(
    "/{indent_id}/close",
    response_model=IndentCloseResponse,
    summary="Close Indent",
)
def close_indent_endpoint(
    indent_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("INDENT_CLOSE")),
):
    try:
        indent = close_indent(
            db=db,
            indent_id=indent_id,
            user_id=current_user.id,
        )
        return IndentCloseResponse(
            id=indent.id,
            indent_no=indent.indent_no,
            status=indent.status,
            closed_by_id=indent.closed_by_id,
            closed_at=indent.closed_at,
            message="Indent closed successfully.",
        )
    except ValueError as e:
        _handle_value_error(e)
