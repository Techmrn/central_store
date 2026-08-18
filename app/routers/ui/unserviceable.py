from typing import Optional, Union
from fastapi import APIRouter, Depends, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.financial_year import get_all_financial_years
from app.crud.office import get_all_offices_dropdown
from app.crud.section import get_all_sections_dropdown
from app.crud.unserviceable import (
    create_unserviceable_material,
    get_unserviceable_register_report,
    update_unserviceable_material_status,
)
from app.dependencies.ui_auth import get_current_user_ui
from app.models.category import Category
from app.models.enums import Category_Type, UnserviceableStatus
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.opening_stock import OpeningStock
from app.models.section import Section
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.schemas.unserviceable import (
    UnserviceableMaterialCreate,
    UnserviceableMaterialStatusUpdate,
)
from app.services.stock_service import get_item_usable_stock

router = APIRouter(
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


def get_available_material_items_for_office(
    db: Session,
    office_id: int,
    financial_year_id: int,
):
    """Retrieve items having positive usable stock for the given office and financial year."""
    op_item_ids = (
        db.query(OpeningStock.item_id)
        .filter(
            OpeningStock.office_id == office_id,
            OpeningStock.financial_year_id == financial_year_id,
            OpeningStock.is_active == True,
        )
    )
    sm_item_ids = (
        db.query(StockMovement.item_id)
        .filter(
            StockMovement.office_id == office_id,
            StockMovement.financial_year_id == financial_year_id,
            StockMovement.is_active == True,
        )
    )
    all_ids = set(r[0] for r in op_item_ids.all()).union(r[0] for r in sm_item_ids.all())
    if not all_ids:
        return []

    items = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .filter(
            Item.id.in_(all_ids),
            Item.is_active == True,
            Category.is_active == True,
            Category.type != Category_Type.ASSET,
        )
        .order_by(Item.name)
        .all()
    )

    available_items = []
    for item in items:
        stock = get_item_usable_stock(
            db,
            item_id=item.id,
            office_id=office_id,
            financial_year_id=financial_year_id,
        )
        if stock > 0:
            available_items.append({
                "id": item.id,
                "name": item.name,
                "code": item.code,
                "unit_symbol": item.unit.symbol if item.unit else "",
                "available_stock": stock,
            })
    return available_items


@router.get("/unserviceable-register", response_class=HTMLResponse)
@router.get("/unserviceable-register/", response_class=HTMLResponse)
def get_unserviceable_register_ui(
    request: Request,
    page: int = Query(1, ge=1),
    financial_year_id: Optional[str] = None,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    item_id: Optional[str] = None,
    category_id: Optional[str] = None,
    asset_or_material: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    fy_id = parse_int(financial_year_id)
    s_id = parse_int(section_id)
    i_id = parse_int(item_id)
    c_id = parse_int(category_id)

    # Server-side office scoping: for ordinary users, lock to assigned office
    if current_user and current_user.office_id:
        o_id = current_user.office_id
    else:
        o_id = parse_int(office_id)

    data = get_unserviceable_register_report(
        db=db,
        financial_year_id=fy_id,
        office_id=o_id,
        section_id=s_id,
        item_id=i_id,
        category_id=c_id,
        asset_or_material=asset_or_material,
        status_filter=status_filter,
        search=search,
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    sections = (
        db.query(Section)
        .filter(Section.office_id == o_id, Section.is_active == True)
        .order_by(Section.name)
        .all()
        if o_id
        else get_all_sections_dropdown(db)
    )
    financial_years = get_all_financial_years(db)
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.name).all()
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
            "categories": categories,
            "dropdown_items": items,
            "asset_or_material": asset_or_material or "",
            "status_filter": status_filter or "",
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "item_id_filter": i_id,
            "category_id_filter": c_id,
            "financial_year_id_filter": fy_id,
            "search": search or "",
            "success": success,
            "error": error,
        },
    )


@router.get("/unserviceable-material/items-stock")
def get_material_items_stock_api(
    financial_year_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    """Return positive-stock items for current user's office in given financial year."""
    user_office_id = current_user.office_id if (current_user and current_user.office_id) else None
    if not user_office_id:
        return JSONResponse(content=[])

    items = get_available_material_items_for_office(
        db=db,
        office_id=user_office_id,
        financial_year_id=financial_year_id,
    )
    return JSONResponse(content=items)


@router.get("/unserviceable-material/new", response_class=HTMLResponse)
def get_new_unserviceable_material_form(
    request: Request,
    financial_year_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    user_office_id = current_user.office_id if (current_user and current_user.office_id) else None

    open_fys = (
        db.query(FinancialYear)
        .filter(FinancialYear.is_closed == False)
        .order_by(FinancialYear.start_date.desc())
        .all()
    )

    selected_fy_id = financial_year_id
    if not selected_fy_id:
        current_fy = next((f for f in open_fys if f.is_current), open_fys[0] if open_fys else None)
        selected_fy_id = current_fy.id if current_fy else None

    sections = []
    if user_office_id:
        sections = (
            db.query(Section)
            .filter(Section.office_id == user_office_id, Section.is_active == True)
            .order_by(Section.name)
            .all()
        )

    available_items = []
    if user_office_id and selected_fy_id:
        available_items = get_available_material_items_for_office(
            db=db,
            office_id=user_office_id,
            financial_year_id=selected_fy_id,
        )

    return templates.TemplateResponse(
        request=request,
        name="unserviceable_register/entry_form.html",
        context={
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "financial_years": open_fys,
            "selected_fy_id": selected_fy_id,
            "sections": sections,
            "available_items": available_items,
            "error": None,
            "form_data": {},
        },
    )


@router.post("/unserviceable-material/new", response_class=HTMLResponse)
def post_new_unserviceable_material(
    request: Request,
    financial_year_id: int = Form(...),
    item_id: int = Form(...),
    quantity: float = Form(...),
    reason: str = Form(...),
    section_id: Optional[str] = Form(None),
    reference_no: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    user_office_id = current_user.office_id if (current_user and current_user.office_id) else None
    if not user_office_id:
        raise ValueError("User must have an assigned office.")

    parsed_sec_id = parse_int(section_id)

    try:
        data = UnserviceableMaterialCreate(
            financial_year_id=financial_year_id,
            item_id=item_id,
            office_id=user_office_id,
            section_id=parsed_sec_id,
            quantity=quantity,
            reason=reason.strip(),
            reference_no=reference_no.strip() if reference_no else None,
            remarks=remarks.strip() if remarks else None,
        )
        create_unserviceable_material(
            db=db,
            data=data,
            user_id=current_user.id if current_user else None,
            office_id=user_office_id,
        )
        return RedirectResponse(
            url="/unserviceable-register?success=Unserviceable+material+recorded+successfully.",
            status_code=303,
        )
    except ValueError as e:
        open_fys = (
            db.query(FinancialYear)
            .filter(FinancialYear.is_closed == False)
            .order_by(FinancialYear.start_date.desc())
            .all()
        )
        sections = (
            db.query(Section)
            .filter(Section.office_id == user_office_id, Section.is_active == True)
            .order_by(Section.name)
            .all()
        )
        available_items = get_available_material_items_for_office(
            db=db,
            office_id=user_office_id,
            financial_year_id=financial_year_id,
        )
        return templates.TemplateResponse(
            request=request,
            name="unserviceable_register/entry_form.html",
            context={
                "request": request,
                "user": current_user,
                "current_user": current_user,
                "financial_years": open_fys,
                "selected_fy_id": financial_year_id,
                "sections": sections,
                "available_items": available_items,
                "error": str(e),
                "form_data": {
                    "financial_year_id": financial_year_id,
                    "item_id": item_id,
                    "section_id": parsed_sec_id,
                    "quantity": quantity,
                    "reason": reason,
                    "reference_no": reference_no,
                    "remarks": remarks,
                },
            },
        )


@router.post("/unserviceable-material/{unserviceable_id}/status")
def post_unserviceable_material_status(
    unserviceable_id: int,
    status: UnserviceableStatus = Form(...),
    quantity: Optional[float] = Form(None),
    remarks: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    user_office_id = current_user.office_id if (current_user and current_user.office_id) else None
    try:
        update_data = UnserviceableMaterialStatusUpdate(
            status=status,
            quantity=quantity,
            remarks=remarks.strip() if remarks else None,
        )
        update_unserviceable_material_status(
            db=db,
            unserviceable_id=unserviceable_id,
            update_data=update_data,
            user_id=current_user.id if current_user else None,
            office_id=user_office_id,
        )
        return RedirectResponse(
            url=f"/unserviceable-register?success=Record+status+updated+to+{status.value}.",
            status_code=303,
        )
    except ValueError as e:
        import urllib.parse
        err_msg = urllib.parse.quote(str(e))
        return RedirectResponse(
            url=f"/unserviceable-register?error={err_msg}",
            status_code=303,
        )


