import math
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.core.constants import PAGE_SIZE
from app.dependencies.ui_auth import get_current_user_ui
from app.models.user import User
from app.models.enums import IndentStatus, RequestSource, Category_Type, DestinationType, AssetStatus, FulfillmentType
from app.models.category import Category
from app.models.item import Item
from app.models.indent import Indent
from app.models.issue import Issue
from app.models.financial_year import FinancialYear
from app.models.asset import Asset

from app.crud.indent import (
    close_indent,
    create_indent,
    get_all_indents,
    get_indent_by_id,
    update_indent,
)
from app.crud.issue import create_issue
from app.crud.item import create_temporary_item
from app.crud.category import get_category_lookup
from app.crud.unit import get_unit_lookup
from app.crud.office import get_all_offices_dropdown
from app.crud.section import get_all_sections_dropdown
from app.crud.financial_year import get_all_financial_years, get_current_financial_year
from app.services.posting_service import post_issue

from app.schemas.indent import IndentCreate, IndentLineCreate, IndentUpdate, IndentLineUpdate
from app.schemas.issue import IssueCreate, IssueLineCreate
from app.services.scope_service import get_stock_office_id
from app.services.stock_service import (
    get_available_asset_count,
    get_item_stock,
    get_item_unserviceable_stock,
    get_item_usable_stock,
)

router = APIRouter(
    prefix="/indents",
    tags=["Indents UI"],
)


def parse_int(val: Optional[object]) -> Optional[int]:
    if val is None or val == "" or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_indents_ui(
    request: Request,
    search: str = "",
    indent_no: Optional[str] = None,
    financial_year_id: Optional[str] = None,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    indent_status: Optional[str] = None,
    request_source: Optional[str] = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    fy_id = parse_int(financial_year_id)
    o_id = parse_int(office_id)
    s_id = parse_int(section_id)

    status_enum = None
    if indent_status and indent_status.strip():
        try:
            status_enum = IndentStatus(indent_status.strip())
        except ValueError:
            status_enum = None

    src_enum = None
    if request_source and request_source.strip():
        try:
            src_enum = RequestSource(request_source.strip())
        except ValueError:
            src_enum = None

    indents_page = get_all_indents(
        db=db,
        search=search or "",
        indent_no=indent_no.strip() if indent_no else None,
        financial_year_id=fy_id,
        office_id=o_id,
        section_id=s_id,
        status=status_enum,
        request_source=src_enum,
        page=page,
    )


    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    financial_years = get_all_financial_years(db)

    return templates.TemplateResponse(
        request=request,
        name="indents/list.html",
        context={
            "request": request,
            "page_title": "Physical Indent Register",
            "current_user": current_user,
            "user": current_user,
            "indents": indents_page.get("items", []),
            "total": indents_page.get("total_records", 0),
            "page": indents_page.get("current_page", 1),
            "total_pages": indents_page.get("total_pages", 1),
            "search": search,
            "indent_no_filter": indent_no or "",
            "financial_year_id_filter": financial_year_id,
            "office_id_filter": office_id,
            "section_id_filter": section_id,
            "indent_status_filter": indent_status.value if indent_status else "",
            "request_source_filter": request_source.value if request_source else "",
            "offices": offices,
            "sections": sections,
            "financial_years": financial_years,
            "indent_statuses": [s.value for s in IndentStatus],
            "request_sources": [r.value for r in RequestSource],
        },
    )


@router.post("/quick-create-item")
async def quick_create_indent_item_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    """Create a temporary MATERIAL Item while recording a physical Indent."""
    try:
        data = await request.json()
        name = str(data.get("name", "")).strip()
        code = str(data.get("code", "")).strip() or None
        category_id = int(data.get("category_id"))
        unit_id = int(data.get("unit_id"))
        specification = str(data.get("specification", "")).strip() or None
        remarks = str(data.get("remarks", "")).strip() or None
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid temporary item details."}

    try:
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True,
        ).first()
        if not category:
            return {"success": False, "error": "Category not found."}
        if category.type != Category_Type.MATERIAL:
            return {
                "success": False,
                "error": "Temporary/Petty Purchase Items must use a MATERIAL category.",
            }

        item = create_temporary_item(
            db=db,
            name=name,
            category_id=category_id,
            unit_id=unit_id,
            code=code,
            specification=specification,
            remarks=remarks,
        )
        return {
            "success": True,
            "item": {
                "id": item.id,
                "name": item.name,
                "code": item.code,
                "unit_symbol": item.unit.symbol if item.unit else "",
                "physical_stock": 0,
                "unserviceable_stock": 0,
                "usable_stock": 0,
                "is_asset": False,
                "is_temporary": True,
                "category_name": item.category.name if item.category else "",
            },
        }
    except ValueError as exc:
        return {"success": False, "error": str(exc)}


@router.get("/entry", response_class=HTMLResponse)
@router.get("/record", response_class=HTMLResponse)
def record_physical_indent_ui(
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    offices = get_all_offices_dropdown(db)
    categories = [c for c in get_category_lookup(db) if c.type == Category_Type.MATERIAL]
    units = get_unit_lookup(db)

    return templates.TemplateResponse(
        request=request,
        name="indents/entry.html",
        context={
            "request": request,
            "page_title": "Record Physical Indent",
            "current_user": current_user,
            "user": current_user,
            "offices": offices,
            "categories": categories,
            "units": units,
            "today_date": date.today().isoformat(),
            "error": error,
            "success": success,
        },
    )


@router.post("/entry", response_class=HTMLResponse)
async def submit_physical_indent_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    """
    V1 Physical Indent submission — single-step, no Save/Draft.
    Zero-issued lines are stored on the Indent but create no Issue/StockMovement.
    An all-zero Indent is still closed successfully.
    """
    form_data = await request.form()

    indent_no = str(form_data.get("indent_no", "")).strip()
    indent_date_raw = form_data.get("indent_date")
    office_id_raw = form_data.get("office_id")
    section_id_raw = form_data.get("section_id")
    reference_no = str(form_data.get("reference_no", "")).strip() or None
    remarks = str(form_data.get("remarks", "")).strip() or None

    if not indent_no:
        return RedirectResponse(
            url="/indents/entry?error=Printed+Indent+Number+is+required.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        indent_date = date.fromisoformat(indent_date_raw) if indent_date_raw else date.today()
        office_id = int(office_id_raw)
        section_id = int(section_id_raw) if section_id_raw and str(section_id_raw).isdigit() else None
    except (ValueError, TypeError) as e:
        return RedirectResponse(
            url=f"/indents/entry?error=Invalid+form+data:+{e}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Current Financial Year
    fy = get_current_financial_year(db)
    if not fy:
        fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        if not fy:
            return RedirectResponse(
                url="/indents/entry?error=No+active+financial+year+found.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    # Duplicate check for printed Indent No
    existing = (
        db.query(Indent)
        .filter(
            Indent.office_id == office_id,
            Indent.financial_year_id == fy.id,
            func.lower(Indent.indent_no) == indent_no.lower(),
            Indent.is_active == True,
        )
        .first()
    )

    if existing:
        if existing.status == IndentStatus.CLOSED:
            return RedirectResponse(
                url=f"/indents/entry?error=Indent+{indent_no}+has+already+been+completed+and+closed.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            return RedirectResponse(
                url=f"/indents/view/{existing.id}?error=Indent+{indent_no}+already+exists.+Redirected+to+existing+record.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    # Extract lines
    item_ids = form_data.getlist("item_id[]")
    requested_qtys = form_data.getlist("requested_qty[]")
    issued_qtys = form_data.getlist("issued_qty[]")
    line_remarks_list = form_data.getlist("line_remarks[]")

    if not item_ids:
        return RedirectResponse(
            url="/indents/entry?error=At+least+one+item+line+is+required.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    lines_create = []

    for i in range(len(item_ids)):
        if not item_ids[i] or not item_ids[i].isdigit():
            continue

        item_id = int(item_ids[i])
        try:
            req_qty = float(requested_qtys[i]) if i < len(requested_qtys) and requested_qtys[i] else 0.0
        except ValueError:
            req_qty = 0.0

        try:
            iss_qty_raw = issued_qtys[i] if i < len(issued_qtys) else ""
            iss_qty = float(iss_qty_raw) if iss_qty_raw else 0.0
        except ValueError:
            iss_qty = 0.0

        if req_qty <= 0:
            return RedirectResponse(
                url="/indents/entry?error=Requested+quantity+must+be+greater+than+0.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        if iss_qty < 0:
            return RedirectResponse(
                url="/indents/entry?error=Issued+quantity+cannot+be+negative.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        if iss_qty > req_qty:
            return RedirectResponse(
                url=f"/indents/entry?error=Issued+quantity+({iss_qty})+cannot+exceed+requested+quantity+({req_qty}).",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        l_remarks = str(line_remarks_list[i]).strip() if i < len(line_remarks_list) else None

        lines_create.append(
            IndentLineCreate(
                item_id=item_id,
                requested_quantity=req_qty,
                issued_quantity=iss_qty,
                remarks=l_remarks or None,
            )
        )

    if not lines_create:
        return RedirectResponse(
            url="/indents/entry?error=No+valid+item+lines+provided.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        # Create Indent (always — even all-zero)
        indent = create_indent(
            db=db,
            indent_in=IndentCreate(
                indent_no=indent_no,
                indent_date=indent_date,
                received_date=indent_date,
                financial_year_id=fy.id,
                office_id=office_id,
                section_id=section_id,
                request_source=RequestSource.PHYSICAL,
                reference_no=reference_no,
                remarks=remarks,
                lines=lines_create,
            ),
            user_id=current_user.id,
        )

        # The Indent is the request document. Do not silently create an Issue
        # or auto-select arbitrary Assets here. The Issue screen is the final
        # allocation/posting step and can select exact physical Assets.
        return RedirectResponse(
            url=f"/issues/create?indent_id={indent.id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except ValueError as e:
        return RedirectResponse(
            url=f"/indents/entry?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.get("/receipt/{indent_id}", response_class=HTMLResponse)
def view_indent_receipt_ui(
    indent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    indent = get_indent_by_id(db, indent_id)
    if not indent:
        raise HTTPException(status_code=404, detail="Indent not found")

    issue = db.query(Issue).filter(Issue.indent_id == indent_id, Issue.is_active == True).first()

    return templates.TemplateResponse(
        request=request,
        name="indents/receipt.html",
        context={
            "request": request,
            "page_title": f"Receipt - Indent #{indent.indent_no}",
            "current_user": current_user,
            "user": current_user,
            "indent": indent,
            "issue": issue,
        },
    )


@router.get("/view/{indent_id}", response_class=HTMLResponse)
@router.get("/{indent_id}", response_class=HTMLResponse)
def view_indent_detail_ui(
    indent_id: int,
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    indent = get_indent_by_id(db, indent_id)
    if not indent:
        raise HTTPException(status_code=404, detail="Indent not found")

    enriched_lines = []
    has_asset_item = False

    for line in indent.lines:
        if not line.is_active:
            continue

        is_asset = bool(
            line.item
            and line.item.category
            and line.item.category.type == Category_Type.ASSET
        )

        if is_asset:
            has_asset_item = True
            usable = get_available_asset_count(
                db, item_id=line.item_id, office_id=indent.office_id
            )
            physical = usable
            unserviceable = 0.0
        else:
            usable = get_item_usable_stock(
                db, item_id=line.item_id, office_id=indent.office_id,
                financial_year_id=indent.financial_year_id
            )
            physical = get_item_stock(
                db, item_id=line.item_id, office_id=indent.office_id,
                financial_year_id=indent.financial_year_id
            )
            unserviceable = get_item_unserviceable_stock(
                db, item_id=line.item_id, office_id=indent.office_id,
                financial_year_id=indent.financial_year_id
            )

        enriched_lines.append({
            "line": line,
            "usable_stock": usable,
            "physical_stock": physical,
            "unserviceable_stock": unserviceable,
            "is_asset": is_asset,
        })

    return templates.TemplateResponse(
        request=request,
        name="indents/detail.html",
        context={
            "request": request,
            "page_title": f"Indent #{indent.indent_no}",
            "current_user": current_user,
            "user": current_user,
            "indent": indent,
            "enriched_lines": enriched_lines,
            "has_asset_item": has_asset_item,
            "error": error,
            "success": success,
        },
    )


@router.post("/{indent_id}/process", response_class=HTMLResponse)
async def process_indent_ui(
    indent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    """
    Save storekeeper processing quantities on the Indent and hand off to the
    Issue screen for final allocation/posting. Asset lines are never assigned
    automatically; exact physical Assets must be selected in Issue creation.
    """
    indent = get_indent_by_id(db, indent_id)
    if not indent:
        raise HTTPException(status_code=404, detail="Indent not found")
    if indent.status == IndentStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot process a closed Indent.")

    form_data = await request.form()
    line_updates = []

    for line in indent.lines:
        if not line.is_active:
            continue

        issued_key = f"issued_qty_{line.id}"
        remarks_key = f"remarks_{line.id}"
        fulfillment_key = f"fulfillment_{line.id}"
        if issued_key not in form_data:
            continue

        try:
            issued_qty = float(form_data[issued_key])
        except (TypeError, ValueError):
            issued_qty = 0.0

        if issued_qty < 0:
            return RedirectResponse(
                url=f"/indents/view/{indent_id}?error=Issued+quantity+cannot+be+negative+for+{line.item.name}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        if issued_qty > line.requested_quantity:
            return RedirectResponse(
                url=f"/indents/view/{indent_id}?error=Issued+quantity+cannot+exceed+requested+({line.requested_quantity})+for+{line.item.name}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        remarks_val = str(form_data.get(remarks_key, "")).strip()
        fulfillment_raw = str(form_data.get(fulfillment_key, line.fulfillment_type.value)).strip()
        try:
            fulfillment = FulfillmentType(fulfillment_raw)
        except ValueError:
            fulfillment = line.fulfillment_type

        # Initial petty-purchase implementation is for material lines only.
        is_asset = bool(line.item and line.item.category and line.item.category.type == Category_Type.ASSET)
        if is_asset and fulfillment == FulfillmentType.PETTY_PURCHASE:
            return RedirectResponse(
                url=f"/indents/view/{indent_id}?error=Asset+item+{line.item.name}+cannot+be+fulfilled+through+Petty+Purchase.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        line_updates.append(
            IndentLineUpdate(
                id=line.id,
                issued_quantity=issued_qty,
                fulfillment_type=fulfillment,
                remarks=remarks_val or None,
            )
        )

    try:
        if line_updates:
            update_indent(
                db=db,
                indent_id=indent_id,
                indent_in=IndentUpdate(
                    lines=line_updates,
                    status=IndentStatus.PROCESSING,
                ),
                user_id=current_user.id,
            )

        return RedirectResponse(
            url=f"/issues/create?indent_id={indent_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/indents/view/{indent_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/{indent_id}/close", response_class=HTMLResponse)
def close_indent_ui(
    indent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        close_indent(db=db, indent_id=indent_id, user_id=current_user.id)
        return RedirectResponse(
            url=f"/indents/view/{indent_id}?success=Indent+closed+successfully",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/indents/view/{indent_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
