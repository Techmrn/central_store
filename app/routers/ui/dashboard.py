from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.db import get_db
from app.core.templates import templates
from app.dependencies.ui_auth import get_current_user_ui
from app.models.user import User
from app.models.item import Item
from app.models.indent import Indent
from app.models.issue import Issue
from app.models.asset import Asset
from app.models.unserviceable_material import UnserviceableMaterial
from app.models.enums import IndentStatus, TransactionStatus
from app.services.scope_service import (
    get_authorized_view_office_ids,
    is_department_wide_viewer,
    is_central_store_user,
)

router = APIRouter(tags=["Dashboard UI"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    # Fetch operational metrics scoped to authorized offices
    view_office_ids = get_authorized_view_office_ids(db, current_user)

    total_items = db.query(func.count(Item.id)).filter(Item.is_active == True).scalar() or 0

    indents_q = db.query(Indent).filter(Indent.is_active == True)
    if view_office_ids is not None:
        indents_q = indents_q.filter(Indent.office_id.in_(view_office_ids))

    pending_indents_count = indents_q.filter(
        Indent.status.in_([
            IndentStatus.DRAFT,
            IndentStatus.SUBMITTED,
            IndentStatus.PROCESSING,
        ])
    ).count()

    actionable_indents_count = indents_q.filter(
        Indent.status.in_([
            IndentStatus.SUBMITTED,
            IndentStatus.PROCESSING,
        ])
    ).count()

    issues_q = db.query(Issue).filter(Issue.is_active == True)
    if view_office_ids is not None:
        issues_q = issues_q.filter(Issue.office_id.in_(view_office_ids))
    total_issues = issues_q.count()

    assets_q = db.query(Asset).filter(Asset.is_active == True)
    if view_office_ids is not None:
        assets_q = assets_q.filter(Asset.office_id.in_(view_office_ids))
    total_assets = assets_q.count()

    unserv_q = db.query(UnserviceableMaterial).filter(UnserviceableMaterial.is_active == True)
    if view_office_ids is not None:
        unserv_q = unserv_q.filter(UnserviceableMaterial.office_id.in_(view_office_ids))
    unserviceable_count = unserv_q.count()

    recent_issues_q = (
        db.query(Issue)
        .options(joinedload(Issue.office), joinedload(Issue.indent))
        .filter(Issue.is_active == True)
    )
    if view_office_ids is not None:
        recent_issues_q = recent_issues_q.filter(Issue.office_id.in_(view_office_ids))
    recent_issues = recent_issues_q.order_by(Issue.created_at.desc()).limit(5).all()

    recent_indents_q = (
        db.query(Indent)
        .options(joinedload(Indent.office))
        .filter(Indent.is_active == True)
    )
    if view_office_ids is not None:
        recent_indents_q = recent_indents_q.filter(Indent.office_id.in_(view_office_ids))
    recent_indents = recent_indents_q.order_by(Indent.created_at.desc()).limit(5).all()

    return templates.TemplateResponse(
        request=request,
        name="dashboard/home.html",
        context={
            "request": request,
            "page_title": "Storekeeper Dashboard",
            "current_user": current_user,
            "total_items": total_items,
            "pending_indents_count": pending_indents_count,
            "actionable_indents_count": actionable_indents_count,
            "total_issues": total_issues,
            "total_assets": total_assets,
            "unserviceable_count": unserviceable_count,
            "recent_issues": recent_issues,
            "recent_indents": recent_indents,
        },
    )


@router.get("/", response_class=HTMLResponse)
def root_redirect():
    return RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_303_SEE_OTHER,
    )