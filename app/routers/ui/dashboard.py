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

router = APIRouter(tags=["Dashboard UI"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    # Fetch operational metrics
    total_items = db.query(func.count(Item.id)).filter(Item.is_active == True).scalar() or 0
    pending_indents_count = db.query(func.count(Indent.id)).filter(
        Indent.is_active == True,
        Indent.status.in_([
            IndentStatus.DRAFT,
            IndentStatus.SUBMITTED,
            IndentStatus.PROCESSING,
        ])
    ).scalar() or 0

    actionable_indents_count = db.query(func.count(Indent.id)).filter(
        Indent.is_active == True,
        Indent.status.in_([
            IndentStatus.SUBMITTED,
            IndentStatus.PROCESSING,
        ])
    ).scalar() or 0

    total_issues = db.query(func.count(Issue.id)).filter(Issue.is_active == True).scalar() or 0
    total_assets = db.query(func.count(Asset.id)).filter(Asset.is_active == True).scalar() or 0
    unserviceable_count = db.query(func.count(UnserviceableMaterial.id)).filter(UnserviceableMaterial.is_active == True).scalar() or 0

    recent_issues = (
        db.query(Issue)
        .options(joinedload(Issue.office), joinedload(Issue.indent))
        .filter(Issue.is_active == True)
        .order_by(Issue.created_at.desc())
        .limit(5)
        .all()
    )

    recent_indents = (
        db.query(Indent)
        .options(joinedload(Indent.office))
        .filter(Indent.is_active == True)
        .order_by(Indent.created_at.desc())
        .limit(5)
        .all()
    )

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