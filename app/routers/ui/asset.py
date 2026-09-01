"""
UI Router — Asset Registration and Management
Routes:
    GET  /assets          → redirect to /asset-register (existing register)
    GET  /assets/new      → registration form
    POST /assets/new      → save new asset (atomic: Asset + AssetDetail + initial AssetMovement)
    GET  /assets/{id}     → detail page with lifetime movement history
    GET  /assets/{id}/edit → edit form (master + detail info only)
    POST /assets/{id}/edit → save edits (master + detail info only)
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.asset import (
    create_asset,
    get_all_assets,
    get_asset_by_id,
    get_asset_movements,
    update_asset,
)
from app.crud.office import get_all_offices_dropdown
from app.crud.section import get_all_sections_dropdown
from app.dependencies.ui_auth import get_current_user_ui
from app.models.asset import Asset
from app.models.asset_movement import AssetMovement
from app.models.category import Category
from app.models.enums import AssetStatus, Category_Type
from app.models.item import Item
from app.models.office import Office
from app.models.section import Section
from app.models.user import User
from app.schemas.asset import AssetCreate, AssetDetailCreate, AssetDetailUpdate, AssetUpdate
from app.services.scope_service import (
    can_transact_office,
    get_authorized_stock_office_ids,
    get_authorized_view_office_ids,
    is_central_store_user,
    is_department_wide_viewer,
    validate_office_access,
)

router = APIRouter(
    prefix="/assets",
    tags=["Assets UI"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_asset_items(db: Session):
    """Return active items whose category type is ASSET."""
    return (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .filter(
            Item.is_active == True,
            Category.is_active == True,
            Category.type == Category_Type.ASSET,
        )
        .order_by(Item.name)
        .all()
    )


def _can_manage_assets(user: User) -> bool:
    """Return True if user has ASSET_CREATE or ASSET_UPDATE in their perm_codes."""
    perm_codes = getattr(user, "perm_codes", set()) or set()
    return bool({"ASSET_CREATE", "ASSET_UPDATE"} & perm_codes)


def _require_asset_view(user: User):
    perm_codes = getattr(user, "perm_codes", set()) or set()
    if "ASSET_VIEW" not in perm_codes:
        raise HTTPException(status_code=403, detail="You do not have permission to view assets.")


def _require_asset_create(user: User):
    perm_codes = getattr(user, "perm_codes", set()) or set()
    if "ASSET_CREATE" not in perm_codes:
        raise HTTPException(status_code=403, detail="You do not have permission to register assets.")


def _require_asset_update(user: User):
    perm_codes = getattr(user, "perm_codes", set()) or set()
    if "ASSET_UPDATE" not in perm_codes:
        raise HTTPException(status_code=403, detail="You do not have permission to edit assets.")


def _parse_int(val) -> Optional[int]:
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_date(val) -> Optional[date]:
    if val is None or str(val).strip() == "":
        return None
    try:
        return date.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


def _get_office_id_for_asset(db: Session, user: User, form_office_id: Optional[int]) -> int:
    """
    Determine the asset office_id for the current user:
    - Branch users: forced to their own office_id (form value ignored for security)
    - Central Store / Dept-wide viewers: use the form-provided office_id (validated)

    Returns the resolved office_id or raises ValueError.
    """
    if is_department_wide_viewer(db, user) or is_central_store_user(db, user):
        if form_office_id is None:
            raise ValueError("Please select an office.")
        # Validate the office exists and is active
        office = db.query(Office).filter(
            Office.id == form_office_id,
            Office.is_active == True,
        ).first()
        if not office:
            raise ValueError("Selected office not found or is inactive.")
        return form_office_id
    else:
        # Branch / ordinary user — office is their own assigned office
        return user.office_id


# ---------------------------------------------------------------------------
# GET /assets  — redirect to existing Asset Register
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def asset_list_redirect(request: Request):
    return RedirectResponse(url="/asset-register", status_code=303)


# ---------------------------------------------------------------------------
# GET /assets/new  — Registration Form
# ---------------------------------------------------------------------------

@router.get("/new", response_class=HTMLResponse)
def new_asset_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    _require_asset_create(current_user)

    items = _get_asset_items(db)
    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)

    # Determine whether office field is free-choice or locked
    user_can_choose_office = (
        is_department_wide_viewer(db, current_user)
        or is_central_store_user(db, current_user)
    )

    return templates.TemplateResponse(
        request=request,
        name="assets/form.html",
        context={
            "request": request,
            "page_title": "Register Asset",
            "items": items,
            "offices": offices,
            "sections": sections,
            "asset_statuses": [s.value for s in AssetStatus],
            "current_user": current_user,
            "user_can_choose_office": user_can_choose_office,
            "is_edit": False,
            "asset": None,
            "error": None,
        },
    )


# ---------------------------------------------------------------------------
# POST /assets/new  — Save New Asset
# ---------------------------------------------------------------------------

@router.post("/new")
def save_new_asset(
    request: Request,
    asset_no: str = Form(...),
    item_id: int = Form(...),
    serial_no: str = Form(""),
    office_id: Optional[int] = Form(None),
    section_id: Optional[int] = Form(None),
    remarks: str = Form(""),
    # AssetDetail fields
    make: str = Form(""),
    model: str = Form(""),
    purchase_date: str = Form(""),
    purchase_reference: str = Form(""),
    purchase_value: str = Form(""),
    warranty_expiry_date: str = Form(""),
    technical_specifications: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    _require_asset_create(current_user)

    items = _get_asset_items(db)
    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    user_can_choose_office = (
        is_department_wide_viewer(db, current_user)
        or is_central_store_user(db, current_user)
    )

    def render_form(error_msg: str):
        return templates.TemplateResponse(
            request=request,
            name="assets/form.html",
            context={
                "request": request,
                "page_title": "Register Asset",
                "items": items,
                "offices": offices,
                "sections": sections,
                "asset_statuses": [s.value for s in AssetStatus],
                "current_user": current_user,
                "user_can_choose_office": user_can_choose_office,
                "is_edit": False,
                "error": error_msg,
                "form_data": {
                    "asset_no": asset_no,
                    "item_id": item_id,
                    "serial_no": serial_no,
                    "office_id": office_id,
                    "section_id": section_id,
                    "remarks": remarks,
                    "make": make,
                    "model": model,
                    "purchase_date": purchase_date,
                    "purchase_reference": purchase_reference,
                    "purchase_value": purchase_value,
                    "warranty_expiry_date": warranty_expiry_date,
                    "technical_specifications": technical_specifications,
                },
            },
        )

    try:
        resolved_office_id = _get_office_id_for_asset(db, current_user, office_id)

        # Build detail schema if any detail field provided
        purchase_value_parsed = None
        if purchase_value.strip():
            try:
                purchase_value_parsed = float(purchase_value.strip())
            except ValueError:
                return render_form("Purchase value must be a valid number.")

        detail = AssetDetailCreate(
            make=make.strip() or None,
            model=model.strip() or None,
            purchase_date=_parse_date(purchase_date),
            purchase_reference=purchase_reference.strip() or None,
            purchase_value=purchase_value_parsed,
            warranty_expiry_date=_parse_date(warranty_expiry_date),
            technical_specifications=technical_specifications.strip() or None,
        )

        asset_in = AssetCreate(
            asset_no=asset_no.strip(),
            item_id=item_id,
            serial_no=serial_no.strip() or None,
            office_id=resolved_office_id,
            section_id=section_id if section_id else None,
            status=AssetStatus.IN_STORE,
            remarks=remarks.strip() or None,
            detail=detail,
        )

        new_asset = create_asset(db=db, asset_in=asset_in)

        return RedirectResponse(
            url=f"/assets/{new_asset.id}?success=Asset+registered+successfully",
            status_code=303,
        )

    except ValueError as e:
        return render_form(str(e))


# ---------------------------------------------------------------------------
# GET /assets/{asset_id}  — Detail Page
# ---------------------------------------------------------------------------

@router.get("/{asset_id}", response_class=HTMLResponse)
def asset_detail(
    asset_id: int,
    request: Request,
    success: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    _require_asset_view(current_user)

    asset = get_asset_by_id(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")

    # Fetch full movement history (no pagination — lifetime record)
    movements = (
        db.query(AssetMovement)
        .filter(
            AssetMovement.asset_id == asset_id,
            AssetMovement.is_active == True,
        )
        .order_by(AssetMovement.movement_date.asc(), AssetMovement.id.asc())
        .all()
    )

    can_edit = "ASSET_UPDATE" in (getattr(current_user, "perm_codes", None) or set())

    return templates.TemplateResponse(
        request=request,
        name="assets/detail.html",
        context={
            "request": request,
            "page_title": f"Asset — {asset.asset_no}",
            "asset": asset,
            "movements": movements,
            "current_user": current_user,
            "can_edit": can_edit,
            "success": success,
            "error": error,
        },
    )


# ---------------------------------------------------------------------------
# GET /assets/{asset_id}/edit  — Edit Form (master + detail info only)
# ---------------------------------------------------------------------------

@router.get("/{asset_id}/edit", response_class=HTMLResponse)
def edit_asset_form(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    _require_asset_update(current_user)

    asset = get_asset_by_id(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")

    items = _get_asset_items(db)
    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    user_can_choose_office = (
        is_department_wide_viewer(db, current_user)
        or is_central_store_user(db, current_user)
    )

    return templates.TemplateResponse(
        request=request,
        name="assets/form.html",
        context={
            "request": request,
            "page_title": f"Edit Asset — {asset.asset_no}",
            "asset": asset,
            "asset_id": asset_id,
            "items": items,
            "offices": offices,
            "sections": sections,
            "asset_statuses": [s.value for s in AssetStatus],
            "current_user": current_user,
            "user_can_choose_office": user_can_choose_office,
            "is_edit": True,
            "error": None,
            "form_data": None,
        },
    )


# ---------------------------------------------------------------------------
# POST /assets/{asset_id}/edit  — Save Edits (master + detail info only)
# NOTE: office_id, section_id, status are intentionally NOT accepted here.
#       Location/status changes must go through AssetMovement.
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/edit")
def save_asset_edit(
    asset_id: int,
    request: Request,
    item_id: int = Form(...),
    serial_no: str = Form(""),
    remarks: str = Form(""),
    # AssetDetail fields
    make: str = Form(""),
    model: str = Form(""),
    purchase_date: str = Form(""),
    purchase_reference: str = Form(""),
    purchase_value: str = Form(""),
    warranty_expiry_date: str = Form(""),
    technical_specifications: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    _require_asset_update(current_user)

    existing = get_asset_by_id(db, asset_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Asset not found.")

    items = _get_asset_items(db)
    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    user_can_choose_office = (
        is_department_wide_viewer(db, current_user)
        or is_central_store_user(db, current_user)
    )

    def render_edit_form(error_msg: str):
        return templates.TemplateResponse(
            request=request,
            name="assets/form.html",
            context={
                "request": request,
                "page_title": f"Edit Asset — {existing.asset_no}",
                "asset": existing,
                "asset_id": asset_id,
                "items": items,
                "offices": offices,
                "sections": sections,
                "asset_statuses": [s.value for s in AssetStatus],
                "current_user": current_user,
                "user_can_choose_office": user_can_choose_office,
                "is_edit": True,
                "error": error_msg,
                "form_data": {
                    "item_id": item_id,
                    "serial_no": serial_no,
                    "remarks": remarks,
                    "make": make,
                    "model": model,
                    "purchase_date": purchase_date,
                    "purchase_reference": purchase_reference,
                    "purchase_value": purchase_value,
                    "warranty_expiry_date": warranty_expiry_date,
                    "technical_specifications": technical_specifications,
                },
            },
        )

    try:
        purchase_value_parsed = None
        if purchase_value.strip():
            try:
                purchase_value_parsed = float(purchase_value.strip())
            except ValueError:
                return render_edit_form("Purchase value must be a valid number.")

        detail_update = AssetDetailUpdate(
            make=make.strip() or None,
            model=model.strip() or None,
            purchase_date=_parse_date(purchase_date),
            purchase_reference=purchase_reference.strip() or None,
            purchase_value=purchase_value_parsed,
            warranty_expiry_date=_parse_date(warranty_expiry_date),
            technical_specifications=technical_specifications.strip() or None,
        )

        asset_update = AssetUpdate(
            item_id=item_id,
            serial_no=serial_no.strip() or None,
            remarks=remarks.strip() or None,
            detail=detail_update,
            # Intentionally omitting: asset_no, office_id, section_id, status
            # asset_no is treated as a stable identifier — not editable via UI
            # office/section/status changes must use AssetMovement
        )

        update_asset(db=db, asset_id=asset_id, asset_in=asset_update)

        return RedirectResponse(
            url=f"/assets/{asset_id}?success=Asset+updated+successfully",
            status_code=303,
        )

    except ValueError as e:
        return render_edit_form(str(e))
