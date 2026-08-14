from typing import Optional, Union
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.financial_year import get_all_financial_years
from app.crud.office import get_all_offices_dropdown
from app.crud.section import get_all_sections_dropdown
from app.crud.unserviceable import get_unserviceable_register_report
from app.dependencies.ui_auth import get_current_user_ui
from app.models.item import Item
from app.models.user import User

router = APIRouter(
    prefix="/unserviceable-register",
    tags=["Unserviceable Register UI"],
)


def parse_int(val: Optional[Union[str, int]]) -> Optional[int]:
    """Safely parse query parameter to integer, treating empty strings as None."""
    if val is None or val == "" or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def get_unserviceable_register_ui(
    request: Request,
    page: int = Query(1, ge=1),
    financial_year_id: Optional[str] = None,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    item_id: Optional[str] = None,
    asset_or_material: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    fy_id = parse_int(financial_year_id)
    o_id = parse_int(office_id)
    s_id = parse_int(section_id)
    i_id = parse_int(item_id)

    data = get_unserviceable_register_report(
        db=db,
        financial_year_id=fy_id,
        office_id=o_id,
        section_id=s_id,
        item_id=i_id,
        asset_or_material=asset_or_material,
        status_filter=status_filter,
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    financial_years = get_all_financial_years(db)
    items = db.query(Item).filter(Item.is_active == True).order_by(Item.name).all()

    return templates.TemplateResponse(
        request=request,
        name="unserviceable_register/list.html",
        context={
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "items": data["items"],
            "total": data["total"],
            "page": data["page"],
            "pages": data["pages"],
            "offices": offices,
            "sections": sections,
            "financial_years": financial_years,
            "dropdown_items": items,
            "asset_or_material": asset_or_material or "",
            "status_filter": status_filter or "",
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "item_id_filter": i_id,
            "financial_year_id_filter": fy_id,
        },
    )


