from datetime import date
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.dependencies.ui_auth import get_current_user_ui
from app.models.enums import TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.office import Office
from app.models.receipt import Receipt
from app.models.section import Section
from app.models.user import User

from app.crud.financial_year import get_all_financial_years, get_current_financial_year
from app.crud.office import get_all_offices, get_all_offices_dropdown
from app.crud.section import get_all_sections
from app.crud.category import get_category_lookup
from app.crud.unit import get_unit_lookup
from app.crud.item import create_temporary_item, get_item_by_id as get_crud_item
from app.crud.receipt import (
    create_receipt,
    delete_receipt,
    get_all_receipts,
    get_receipt_by_id,
    update_receipt,
)
from app.schemas.receipt import ReceiptCreate, ReceiptLineCreate, ReceiptUpdate
from app.services.posting_service import post_receipt

router = APIRouter(
    prefix="/receipts",
    tags=["Receipts UI"],
)


def _parse_int(val: Optional[object]) -> Optional[int]:
    if val is None or val == "" or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_date(val: Optional[object]) -> Optional[date]:
    if val is None or val == "" or str(val).strip() == "":
        return None
    try:
        return date.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------
# 1. Receipts Register / List
# ---------------------------------------------------------
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_receipts_ui(
    request: Request,
    search: str = "",
    receipt_no: Optional[str] = None,
    financial_year_id: Optional[str] = None,
    office_id: Optional[str] = None,
    transaction_status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    fy_id = _parse_int(financial_year_id)
    o_id = _parse_int(office_id)
    f_date = _parse_date(from_date)
    t_date = _parse_date(to_date)

    status_enum = None
    if transaction_status and transaction_status.strip():
        try:
            status_enum = TransactionStatus(transaction_status.strip())
        except ValueError:
            status_enum = None

    receipts_page = get_all_receipts(
        db=db,
        search=search or "",
        receipt_no=receipt_no.strip() if receipt_no else None,
        financial_year_id=fy_id,
        office_id=o_id,
        status=status_enum,
        from_date=f_date,
        to_date=t_date,
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    financial_years = get_all_financial_years(db)

    # Compute totals for items on current page for quick summary
    for r in receipts_page.get("items", []):
        r.calculated_total_quantity = sum(float(l.quantity) for l in r.lines)
        r.calculated_total_value = sum(float(l.quantity) * float(l.unit_price or 0.0) for l in r.lines)

    return templates.TemplateResponse(
        request=request,
        name="receipts/list.html",
        context={
            "request": request,
            "page_title": "Goods Receipts Register",
            "current_user": current_user,
            "user": current_user,
            "receipts": receipts_page.get("items", []),
            "total": receipts_page.get("total_records", 0),
            "page": receipts_page.get("current_page", 1),
            "total_pages": receipts_page.get("total_pages", 1),
            "search": search,
            "receipt_no_filter": receipt_no or "",
            "financial_year_id_filter": fy_id,
            "office_id_filter": o_id,
            "transaction_status_filter": transaction_status or "",
            "from_date_filter": from_date or "",
            "to_date_filter": to_date or "",
            "offices": offices,
            "financial_years": financial_years,
            "transaction_statuses": [s.value for s in TransactionStatus],
            "success": success,
            "error": error,
        },
    )


# ---------------------------------------------------------
# 2. New Goods Receipt Form
# ---------------------------------------------------------
@router.get("/new", response_class=HTMLResponse)
@router.get("/create", response_class=HTMLResponse)
def new_receipt_form_ui(
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    financial_years = get_all_financial_years(db)
    current_fy = get_current_financial_year(db)
    if not current_fy and financial_years:
        current_fy = financial_years[0]

    offices = get_all_offices_dropdown(db)
    categories = get_category_lookup(db)
    units = get_unit_lookup(db)

    # Active items from Item Master (both catalogue and temporary)
    items = (
        db.query(Item)
        .filter(Item.is_active == True)
        .order_by(Item.is_temporary.asc(), Item.name.asc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="receipts/create.html",
        context={
            "request": request,
            "page_title": "New Goods Receipt",
            "current_user": current_user,
            "user": current_user,
            "financial_years": financial_years,
            "current_fy": current_fy,
            "offices": offices,
            "items": items,
            "categories": categories,
            "units": units,
            "today_date": date.today().isoformat(),
            "error": error,
            "success": success,
        },
    )


# ---------------------------------------------------------
# 3. Create Local Purchase / Temporary Item on the Fly
# ---------------------------------------------------------
@router.post("/quick-create-item")
async def quick_create_item_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        data = await request.json()
    except Exception:
        data = dict(await request.form())

    name = str(data.get("name", "")).strip()
    category_id_raw = data.get("category_id")
    unit_id_raw = data.get("unit_id")
    code = str(data.get("code", "")).strip() or None
    specification = str(data.get("specification", "")).strip() or None
    remarks = str(data.get("remarks", "")).strip() or None

    if not name:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Item name is required."},
        )

    try:
        category_id = int(category_id_raw)
        unit_id = int(unit_id_raw)
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Category and Unit must be selected."},
        )

    try:
        item = create_temporary_item(
            db=db,
            name=name,
            category_id=category_id,
            unit_id=unit_id,
            code=code,
            specification=specification,
            remarks=remarks,
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "item": {
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "category_name": item.category.name if item.category else "",
                    "unit_name": item.unit.name if item.unit else "Nos",
                    "is_temporary": True,
                },
            },
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)},
        )


# ---------------------------------------------------------
# 4. Create Goods Receipt Submission (Draft or Post)
# ---------------------------------------------------------
@router.post("/new", response_class=HTMLResponse)
@router.post("/create", response_class=HTMLResponse)
async def submit_new_receipt_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    form_data = await request.form()

    receipt_date_raw = form_data.get("receipt_date")
    office_id_raw = form_data.get("office_id")
    financial_year_id_raw = form_data.get("financial_year_id")
    supplier_name = str(form_data.get("supplier_name", "")).strip() or None
    reference_no = str(form_data.get("reference_no", "")).strip() or None
    remarks = str(form_data.get("remarks", "")).strip() or None
    action_type = str(form_data.get("action_type", "save_draft")).strip().lower()

    try:
        receipt_date = date.fromisoformat(receipt_date_raw) if receipt_date_raw else date.today()
        office_id = int(office_id_raw)
    except (ValueError, TypeError) as e:
        return RedirectResponse(
            url=f"/receipts/new?error=Invalid+form+data:+{e}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Financial year
    fy_id = _parse_int(financial_year_id_raw)
    if not fy_id:
        current_fy = get_current_financial_year(db)
        if not current_fy:
            current_fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        if not current_fy:
            return RedirectResponse(
                url="/receipts/new?error=No+active+financial+year+found.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        fy_id = current_fy.id

    # Line items
    item_ids = form_data.getlist("item_id[]")
    quantities = form_data.getlist("quantity[]")
    unit_prices = form_data.getlist("unit_price[]")
    line_remarks_list = form_data.getlist("line_remarks[]")

    if not item_ids:
        return RedirectResponse(
            url="/receipts/new?error=At+least+one+item+line+is+required.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    lines_create = []
    for i in range(len(item_ids)):
        if not item_ids[i] or not str(item_ids[i]).isdigit():
            continue

        item_id = int(item_ids[i])
        try:
            qty = float(quantities[i]) if i < len(quantities) and quantities[i] else 0.0
        except ValueError:
            qty = 0.0

        try:
            rate_raw = unit_prices[i] if i < len(unit_prices) else ""
            rate = float(rate_raw) if rate_raw and str(rate_raw).strip() != "" else None
        except ValueError:
            rate = None

        if qty <= 0:
            return RedirectResponse(
                url="/receipts/new?error=Quantity+must+be+greater+than+zero+for+all+line+items.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        if rate is not None and rate < 0:
            return RedirectResponse(
                url="/receipts/new?error=Unit+rate+cannot+be+negative.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        l_remarks = str(line_remarks_list[i]).strip() if i < len(line_remarks_list) else None

        lines_create.append(
            ReceiptLineCreate(
                item_id=item_id,
                quantity=qty,
                unit_price=rate,
                remarks=l_remarks or None,
            )
        )

    if not lines_create:
        return RedirectResponse(
            url="/receipts/new?error=No+valid+item+lines+provided.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        receipt = create_receipt(
            db=db,
            receipt_in=ReceiptCreate(
                financial_year_id=fy_id,
                office_id=office_id,
                section_id=None,  # Standard: Receipts arrive into Main Office Store
                receipt_date=receipt_date,
                supplier_name=supplier_name,
                reference_no=reference_no,
                remarks=remarks,
                lines=lines_create,
            ),
            user_id=current_user.id,
        )

        if action_type == "post":
            post_receipt(db=db, receipt_id=receipt.id, user_id=current_user.id)
            return RedirectResponse(
                url=f"/receipts/view/{receipt.id}?success=Goods+Receipt+{receipt.receipt_no}+successfully+created+and+posted+to+stock.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            return RedirectResponse(
                url=f"/receipts/view/{receipt.id}?success=Goods+Receipt+{receipt.receipt_no}+saved+as+Draft.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    except ValueError as e:
        return RedirectResponse(
            url=f"/receipts/new?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 5. View Goods Receipt Details
# ---------------------------------------------------------
@router.get("/view/{receipt_id}", response_class=HTMLResponse)
def view_receipt_details_ui(
    receipt_id: int,
    request: Request,
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    receipt = get_receipt_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Goods Receipt not found.")

    total_items = len(receipt.lines)
    total_quantity = sum(float(l.quantity) for l in receipt.lines)
    total_value = sum(float(l.quantity) * float(l.unit_price or 0.0) for l in receipt.lines)

    return templates.TemplateResponse(
        request=request,
        name="receipts/view.html",
        context={
            "request": request,
            "page_title": f"Goods Receipt - {receipt.receipt_no}",
            "current_user": current_user,
            "user": current_user,
            "receipt": receipt,
            "total_items": total_items,
            "total_quantity": total_quantity,
            "total_value": total_value,
            "success": success,
            "error": error,
        },
    )


# ---------------------------------------------------------
# 6. Edit Draft Receipt Form
# ---------------------------------------------------------
@router.get("/edit/{receipt_id}", response_class=HTMLResponse)
def edit_receipt_form_ui(
    receipt_id: int,
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    receipt = get_receipt_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Goods Receipt not found.")

    if receipt.status == TransactionStatus.POSTED:
        return RedirectResponse(
            url=f"/receipts/view/{receipt.id}?error=Posted+Receipts+are+read-only+and+cannot+be+edited.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    offices = get_all_offices_dropdown(db)
    categories = get_category_lookup(db)
    units = get_unit_lookup(db)

    items = (
        db.query(Item)
        .filter(Item.is_active == True)
        .order_by(Item.is_temporary.asc(), Item.name.asc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="receipts/edit.html",
        context={
            "request": request,
            "page_title": f"Edit Receipt - {receipt.receipt_no}",
            "current_user": current_user,
            "user": current_user,
            "receipt": receipt,
            "offices": offices,
            "items": items,
            "categories": categories,
            "units": units,
            "today_date": date.today().isoformat(),
            "error": error,
            "success": success,
        },
    )


# ---------------------------------------------------------
# 7. Update Draft Receipt Submission
# ---------------------------------------------------------
@router.post("/edit/{receipt_id}", response_class=HTMLResponse)
async def update_receipt_ui(
    receipt_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    receipt = get_receipt_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Goods Receipt not found.")

    if receipt.status == TransactionStatus.POSTED:
        return RedirectResponse(
            url=f"/receipts/view/{receipt.id}?error=Posted+Receipts+are+read-only+and+cannot+be+edited.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    form_data = await request.form()

    receipt_date_raw = form_data.get("receipt_date")
    supplier_name = str(form_data.get("supplier_name", "")).strip() or None
    reference_no = str(form_data.get("reference_no", "")).strip() or None
    remarks = str(form_data.get("remarks", "")).strip() or None
    action_type = str(form_data.get("action_type", "save_draft")).strip().lower()

    try:
        receipt_date = date.fromisoformat(receipt_date_raw) if receipt_date_raw else receipt.receipt_date
    except (ValueError, TypeError) as e:
        return RedirectResponse(
            url=f"/receipts/edit/{receipt_id}?error=Invalid+form+data:+{e}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    item_ids = form_data.getlist("item_id[]")
    quantities = form_data.getlist("quantity[]")
    unit_prices = form_data.getlist("unit_price[]")
    line_remarks_list = form_data.getlist("line_remarks[]")

    if not item_ids:
        return RedirectResponse(
            url=f"/receipts/edit/{receipt_id}?error=At+least+one+item+line+is+required.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    lines_update = []
    for i in range(len(item_ids)):
        if not item_ids[i] or not str(item_ids[i]).isdigit():
            continue

        item_id = int(item_ids[i])
        try:
            qty = float(quantities[i]) if i < len(quantities) and quantities[i] else 0.0
        except ValueError:
            qty = 0.0

        try:
            rate_raw = unit_prices[i] if i < len(unit_prices) else ""
            rate = float(rate_raw) if rate_raw and str(rate_raw).strip() != "" else None
        except ValueError:
            rate = None

        if qty <= 0:
            return RedirectResponse(
                url=f"/receipts/edit/{receipt_id}?error=Quantity+must+be+greater+than+zero+for+all+lines.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        if rate is not None and rate < 0:
            return RedirectResponse(
                url=f"/receipts/edit/{receipt_id}?error=Unit+rate+cannot+be+negative.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        l_remarks = str(line_remarks_list[i]).strip() if i < len(line_remarks_list) else None

        lines_update.append(
            ReceiptLineCreate(
                item_id=item_id,
                quantity=qty,
                unit_price=rate,
                remarks=l_remarks or None,
            )
        )

    if not lines_update:
        return RedirectResponse(
            url=f"/receipts/edit/{receipt_id}?error=No+valid+item+lines+provided.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        updated_receipt = update_receipt(
            db=db,
            receipt_id=receipt_id,
            receipt_in=ReceiptUpdate(
                receipt_date=receipt_date,
                section_id=None,  # Main Store
                supplier_name=supplier_name,
                reference_no=reference_no,
                remarks=remarks,
                lines=lines_update,
            ),
        )

        if action_type == "post":
            post_receipt(db=db, receipt_id=updated_receipt.id, user_id=current_user.id)
            return RedirectResponse(
                url=f"/receipts/view/{updated_receipt.id}?success=Goods+Receipt+{updated_receipt.receipt_no}+updated+and+posted+to+stock.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            return RedirectResponse(
                url=f"/receipts/view/{updated_receipt.id}?success=Goods+Receipt+{updated_receipt.receipt_no}+draft+updated+successfully.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    except ValueError as e:
        return RedirectResponse(
            url=f"/receipts/edit/{receipt_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 8. Post Draft Receipt to Stock
# ---------------------------------------------------------
@router.post("/post/{receipt_id}", response_class=HTMLResponse)
@router.post("/{receipt_id}/post", response_class=HTMLResponse)
def post_receipt_ui(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        receipt = post_receipt(db=db, receipt_id=receipt_id, user_id=current_user.id)
        return RedirectResponse(
            url=f"/receipts/view/{receipt.id}?success=Goods+Receipt+{receipt.receipt_no}+successfully+posted+to+stock.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/receipts/view/{receipt_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 9. Delete Draft Receipt
# ---------------------------------------------------------
@router.post("/delete/{receipt_id}", response_class=HTMLResponse)
@router.post("/{receipt_id}/delete", response_class=HTMLResponse)
def delete_receipt_ui(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        receipt = delete_receipt(db=db, receipt_id=receipt_id)
        if not receipt:
            raise HTTPException(status_code=404, detail="Goods Receipt not found.")
        return RedirectResponse(
            url="/receipts?success=Receipt+draft+deleted+successfully.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/receipts/view/{receipt_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 10. Printable Goods Receipt Note (GRN)
# ---------------------------------------------------------
@router.get("/print/{receipt_id}", response_class=HTMLResponse)
def print_receipt_grn_ui(
    receipt_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    receipt = get_receipt_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Goods Receipt not found.")

    total_items = len(receipt.lines)
    total_quantity = sum(float(l.quantity) for l in receipt.lines)
    total_value = sum(float(l.quantity) * float(l.unit_price or 0.0) for l in receipt.lines)

    return templates.TemplateResponse(
        request=request,
        name="receipts/print.html",
        context={
            "request": request,
            "page_title": f"GRN - {receipt.receipt_no}",
            "current_user": current_user,
            "user": current_user,
            "receipt": receipt,
            "total_items": total_items,
            "total_quantity": total_quantity,
            "total_value": total_value,
        },
    )
