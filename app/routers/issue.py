from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.issue import (
    create_issue,
    delete_issue,
    get_all_issues,
    get_issue_by_id,
    update_issue,
)
from app.dependencies.permissions import require_permission
from app.models.enums import TransactionStatus
from app.schemas.common import PaginatedResponse
from app.schemas.issue import (
    IssueCreate,
    IssueRead,
    IssueUpdate,
)
from app.services.posting_service import post_issue

router = APIRouter(
    prefix="/issues",
    tags=["Issues"],
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
    response_model=IssueRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Issue Document",
)
def add_issue(
    issue: IssueCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ISSUE_CREATE")),
):
    try:
        return create_issue(db=db, issue_in=issue, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/",
    response_model=PaginatedResponse[IssueRead],
    summary="Get All Issues",
)
def get_issues(
    search: str = "",
    issue_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    transaction_status: Optional[TransactionStatus] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ISSUE_VIEW")),
):
    return get_all_issues(
        db=db,
        search=search,
        issue_no=issue_no,
        financial_year_id=financial_year_id,
        office_id=office_id,
        section_id=section_id,
        status=transaction_status,
        page=page,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueRead,
    summary="Get Issue By ID",
)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ISSUE_VIEW")),
):
    issue = get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found.")
    return issue


@router.put(
    "/{issue_id}",
    response_model=IssueRead,
    summary="Update Issue Document",
)
def edit_issue(
    issue_id: int,
    issue: IssueUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ISSUE_UPDATE")),
):
    try:
        return update_issue(db=db, issue_id=issue_id, issue_in=issue)
    except ValueError as e:
        _handle_value_error(e)


@router.delete(
    "/{issue_id}",
    response_model=IssueRead,
    summary="Delete Issue Document",
)
def remove_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ISSUE_DELETE")),
):
    try:
        issue = delete_issue(db, issue_id)
        if not issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found.")
        return issue
    except ValueError as e:
        _handle_value_error(e)


@router.post(
    "/{issue_id}/post",
    response_model=IssueRead,
    summary="Post Issue Document",
)
def post_issue_endpoint(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ISSUE_POST")),
):
    try:
        return post_issue(db=db, issue_id=issue_id, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)
