from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.unserviceable import get_unserviceable_register_report
from app.dependencies.ui_auth import get_current_user_ui
from app.models.user import User

router = APIRouter(
    prefix="/unserviceable-register",
    tags=["Unserviceable Register UI"],
)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def get_unserviceable_register_ui(
    request: Request,
    page: int = 1,
    asset_or_material: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    data = get_unserviceable_register_report(
        db=db,
        asset_or_material=asset_or_material,
        status_filter=status_filter,
        page=page,
    )

    return templates.TemplateResponse(
        "unserviceable_register/list.html",
        {
            "request": request,
            "user": current_user,
            "items": data["items"],
            "total": data["total"],
            "page": data["page"],
            "pages": data["pages"],
            "asset_or_material": asset_or_material or "",
            "status_filter": status_filter or "",
        },
    )
