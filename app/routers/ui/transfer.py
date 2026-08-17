from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.dependencies.ui_auth import get_current_user_ui
from app.models.enums import TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.office import Office
from app.models.section import Section
from app.models.stock_transfer import StockTransfer
from app.models.user import User

from app.crud.financial_year import get_all_financial_years, get_current_financial_year
from app.crud.office import get_all_offices_dropdown
from app.crud.section import get_all_sections
from app.crud.stock_transfer import (
    create_transfer,
    delete_transfer,
    get_all_transfers,
    get_transfer_by_id,
    update_transfer,
)
from app.schemas.stock_transfer import StockTransferCreate, StockTransferLineCreate, StockTransferUpdate
from app.services.posting_service import post_transfer
from app.services.stock_service import get_item_stock

router = APIRouter(
    prefix="/transfers",
    tags=["Stock Transfers UI"],
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
# 1. Stock Transfers Register / List
# ---------------------------------------------------------
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_transfers_ui(
    request: Request,
    search: str = "",
    transfer_no: Optional[str] = None,
    financial_year_id: Optional[str] = None,
    from_office_id: Optional[str] = None,
    to_office_id: Optional[str] = None,
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
    f_o_id = _parse_int(from_office_id)
    t_o_id = _parse_int(to_office_id)
    f_date = _parse_date(from_date)
    t_date = _parse_date(to_date)

    status_enum = None
    if transaction_status and transaction_status.strip():
        try:
            status_enum = TransactionStatus(transaction_status.strip())
        except ValueError:
            status_enum = None

    transfers_page = get_all_transfers(
        db=db,
        search=search or "",
        transfer_no=transfer_no.strip() if transfer_no else None,
        financial_year_id=fy_id,
        from_office_id=f_o_id,
        to_office_id=t_o_id,
        status=status_enum,
        from_date=f_date,
        to_date=t_date,
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    financial_years = get_all_financial_years(db)

    for t in transfers_page.get("items", []):
        t.calculated_total_quantity = sum(float(l.quantity) for l in t.lines)

    return templates.TemplateResponse(
        request=request,
        name="transfers/list.html",
        context={
            "request": request,
            "page_title": "Stock Transfers Register",
            "current_user": current_user,
            "user": current_user,
            "transfers": transfers_page.get("items", []),
            "total": transfers_page.get("total_records", 0),
            "page": transfers_page.get("current_page", 1),
            "total_pages": transfers_page.get("total_pages", 1),
            "search": search,
            "transfer_no_filter": transfer_no or "",
            "financial_year_id_filter": fy_id,
            "from_office_id_filter": f_o_id,
            "to_office_id_filter": t_o_id,
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
# 2. New Stock Transfer Form
# ---------------------------------------------------------
@router.get("/new", response_class=HTMLResponse)
@router.get("/create", response_class=HTMLResponse)
def new_transfer_form_ui(
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
    sections = get_all_sections(db)

    items = (
        db.query(Item)
        .filter(Item.is_active == True)
        .order_by(Item.name.asc())
        .all()
    )

    # Attach current stock to items for active store
    user_office_id = current_user.office_id if current_user.office_id else (offices[0].id if offices else 1)
    for it in items:
        it.current_stock_val = get_item_stock(db, item_id=it.id, office_id=user_office_id)

    return templates.TemplateResponse(
        request=request,
        name="transfers/create.html",
        context={
            "request": request,
            "page_title": "New Stock Transfer",
            "current_user": current_user,
            "user": current_user,
            "financial_years": financial_years,
            "current_fy": current_fy,
            "offices": offices,
            "sections": sections,
            "items": items,
            "today_date": date.today().isoformat(),
            "error": error,
            "success": success,
        },
    )


# ---------------------------------------------------------
# 3. Create Stock Transfer Submission (Draft or Post)
# ---------------------------------------------------------
@router.post("/new", response_class=HTMLResponse)
@router.post("/create", response_class=HTMLResponse)
async def submit_new_transfer_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    form_data = await request.form()

    transfer_date_raw = form_data.get("transfer_date")
    from_office_id_raw = form_data.get("from_office_id")
    to_office_id_raw = form_data.get("to_office_id")
    from_section_id_raw = form_data.get("from_section_id")
    to_section_id_raw = form_data.get("to_section_id")
    financial_year_id_raw = form_data.get("financial_year_id")
    remarks = str(form_data.get("remarks", "")).strip() or None
    action_type = str(form_data.get("action_type", "save_draft")).strip().lower()

    try:
        transfer_date = date.fromisoformat(transfer_date_raw) if transfer_date_raw else date.today()
        from_office_id = int(from_office_id_raw)
        to_office_id = int(to_office_id_raw)
    except (ValueError, TypeError) as e:
        return RedirectResponse(
            url=f"/transfers/new?error=Invalid+location+or+date:+{e}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    from_section_id = _parse_int(from_section_id_raw)
    to_section_id = _parse_int(to_section_id_raw)

    if from_office_id == to_office_id and from_section_id == to_section_id:
        return RedirectResponse(
            url="/transfers/new?error=Source+and+destination+stores+cannot+be+identical.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    fy_id = _parse_int(financial_year_id_raw)
    if not fy_id:
        current_fy = get_current_financial_year(db)
        if not current_fy:
            current_fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        if not current_fy:
            return RedirectResponse(
                url="/transfers/new?error=No+active+financial+year+found.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        fy_id = current_fy.id

    item_ids = form_data.getlist("item_id[]")
    quantities = form_data.getlist("quantity[]")
    line_remarks_list = form_data.getlist("line_remarks[]")

    if not item_ids:
        return RedirectResponse(
            url="/transfers/new?error=At+least+one+item+line+is+required.",
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

        if qty <= 0:
            return RedirectResponse(
                url="/transfers/new?error=Transfer+quantity+must+be+greater+than+zero.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        l_remarks = str(line_remarks_list[i]).strip() if i < len(line_remarks_list) else None

        lines_create.append(
            StockTransferLineCreate(
                item_id=item_id,
                quantity=qty,
                remarks=l_remarks or None,
            )
        )

    if not lines_create:
        return RedirectResponse(
            url="/transfers/new?error=No+valid+item+lines+provided.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        stock_transfer = create_transfer(
            db=db,
            transfer_in=StockTransferCreate(
                financial_year_id=fy_id,
                from_office_id=from_office_id,
                from_section_id=from_section_id,
                to_office_id=to_office_id,
                to_section_id=to_section_id,
                transfer_date=transfer_date,
                remarks=remarks,
                lines=lines_create,
            ),
            user_id=current_user.id,
        )

        if action_type == "post":
            post_transfer(db=db, transfer_id=stock_transfer.id, user_id=current_user.id)
            return RedirectResponse(
                url=f"/transfers/view/{stock_transfer.id}?success=Stock+Transfer+{stock_transfer.transfer_no}+posted+to+stock+successfully.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            return RedirectResponse(
                url=f"/transfers/view/{stock_transfer.id}?success=Stock+Transfer+{stock_transfer.transfer_no}+saved+as+Draft.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    except ValueError as e:
        return RedirectResponse(
            url=f"/transfers/new?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 4. View Stock Transfer Details
# ---------------------------------------------------------
@router.get("/view/{transfer_id}", response_class=HTMLResponse)
def view_transfer_details_ui(
    transfer_id: int,
    request: Request,
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_transfer = get_transfer_by_id(db, transfer_id)
    if not stock_transfer:
        raise HTTPException(status_code=404, detail="Stock Transfer not found.")

    total_items = len(stock_transfer.lines)
    total_quantity = sum(float(l.quantity) for l in stock_transfer.lines)

    return templates.TemplateResponse(
        request=request,
        name="transfers/view.html",
        context={
            "request": request,
            "page_title": f"Stock Transfer - {stock_transfer.transfer_no}",
            "current_user": current_user,
            "user": current_user,
            "transfer": stock_transfer,
            "total_items": total_items,
            "total_quantity": total_quantity,
            "success": success,
            "error": error,
        },
    )


# ---------------------------------------------------------
# 5. Edit Draft Transfer Form
# ---------------------------------------------------------
@router.get("/edit/{transfer_id}", response_class=HTMLResponse)
def edit_transfer_form_ui(
    transfer_id: int,
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_transfer = get_transfer_by_id(db, transfer_id)
    if not stock_transfer:
        raise HTTPException(status_code=404, detail="Stock Transfer not found.")

    if stock_transfer.status == TransactionStatus.POSTED:
        return RedirectResponse(
            url=f"/transfers/view/{stock_transfer.id}?error=Posted+transfers+are+read-only+and+cannot+be+edited.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    offices = get_all_offices_dropdown(db)
    sections = get_all_sections(db)
    items = (
        db.query(Item)
        .filter(Item.is_active == True)
        .order_by(Item.name.asc())
        .all()
    )

    for it in items:
        it.current_stock_val = get_item_stock(db, item_id=it.id, office_id=stock_transfer.from_office_id)

    return templates.TemplateResponse(
        request=request,
        name="transfers/edit.html",
        context={
            "request": request,
            "page_title": f"Edit Transfer - {stock_transfer.transfer_no}",
            "current_user": current_user,
            "user": current_user,
            "transfer": stock_transfer,
            "offices": offices,
            "sections": sections,
            "items": items,
            "today_date": date.today().isoformat(),
            "error": error,
            "success": success,
        },
    )


# ---------------------------------------------------------
# 6. Update Draft Transfer Submission
# ---------------------------------------------------------
@router.post("/edit/{transfer_id}", response_class=HTMLResponse)
async def update_transfer_ui(
    transfer_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_transfer = get_transfer_by_id(db, transfer_id)
    if not stock_transfer:
        raise HTTPException(status_code=404, detail="Stock Transfer not found.")

    if stock_transfer.status == TransactionStatus.POSTED:
        return RedirectResponse(
            url=f"/transfers/view/{stock_transfer.id}?error=Posted+transfers+are+read-only+and+cannot+be+edited.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    form_data = await request.form()

    transfer_date_raw = form_data.get("transfer_date")
    to_office_id_raw = form_data.get("to_office_id")
    from_section_id_raw = form_data.get("from_section_id")
    to_section_id_raw = form_data.get("to_section_id")
    remarks = str(form_data.get("remarks", "")).strip() or None
    action_type = str(form_data.get("action_type", "save_draft")).strip().lower()

    try:
        transfer_date = date.fromisoformat(transfer_date_raw) if transfer_date_raw else stock_transfer.transfer_date
        to_office_id = int(to_office_id_raw) if to_office_id_raw else stock_transfer.to_office_id
    except (ValueError, TypeError) as e:
        return RedirectResponse(
            url=f"/transfers/edit/{transfer_id}?error=Invalid+form+data:+{e}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    from_section_id = _parse_int(from_section_id_raw)
    to_section_id = _parse_int(to_section_id_raw)

    if stock_transfer.from_office_id == to_office_id and from_section_id == to_section_id:
        return RedirectResponse(
            url=f"/transfers/edit/{transfer_id}?error=Source+and+destination+stores+cannot+be+identical.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    item_ids = form_data.getlist("item_id[]")
    quantities = form_data.getlist("quantity[]")
    line_remarks_list = form_data.getlist("line_remarks[]")

    if not item_ids:
        return RedirectResponse(
            url=f"/transfers/edit/{transfer_id}?error=At+least+one+item+line+is+required.",
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

        if qty <= 0:
            return RedirectResponse(
                url=f"/transfers/edit/{transfer_id}?error=Quantity+must+be+greater+than+zero.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        l_remarks = str(line_remarks_list[i]).strip() if i < len(line_remarks_list) else None

        lines_update.append(
            StockTransferLineCreate(
                item_id=item_id,
                quantity=qty,
                remarks=l_remarks or None,
            )
        )

    if not lines_update:
        return RedirectResponse(
            url=f"/transfers/edit/{transfer_id}?error=No+valid+item+lines+provided.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        updated_transfer = update_transfer(
            db=db,
            transfer_id=transfer_id,
            transfer_in=StockTransferUpdate(
                transfer_date=transfer_date,
                to_office_id=to_office_id,
                from_section_id=from_section_id,
                to_section_id=to_section_id,
                remarks=remarks,
                lines=lines_update,
            ),
        )

        if action_type == "post":
            post_transfer(db=db, transfer_id=updated_transfer.id, user_id=current_user.id)
            return RedirectResponse(
                url=f"/transfers/view/{updated_transfer.id}?success=Stock+Transfer+{updated_transfer.transfer_no}+posted+to+stock+successfully.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            return RedirectResponse(
                url=f"/transfers/view/{updated_transfer.id}?success=Stock+Transfer+{updated_transfer.transfer_no}+draft+updated+successfully.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    except ValueError as e:
        return RedirectResponse(
            url=f"/transfers/edit/{transfer_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 7. Post Draft Transfer to Stock
# ---------------------------------------------------------
@router.post("/post/{transfer_id}", response_class=HTMLResponse)
@router.post("/{transfer_id}/post", response_class=HTMLResponse)
def post_transfer_ui(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        stock_transfer = post_transfer(db=db, transfer_id=transfer_id, user_id=current_user.id)
        return RedirectResponse(
            url=f"/transfers/view/{stock_transfer.id}?success=Stock+Transfer+{stock_transfer.transfer_no}+posted+to+stock+successfully.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/transfers/view/{transfer_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 8. Delete Draft Transfer
# ---------------------------------------------------------
@router.post("/delete/{transfer_id}", response_class=HTMLResponse)
@router.post("/{transfer_id}/delete", response_class=HTMLResponse)
def delete_transfer_ui(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        stock_transfer = delete_transfer(db=db, transfer_id=transfer_id)
        if not stock_transfer:
            raise HTTPException(status_code=404, detail="Stock Transfer not found.")
        return RedirectResponse(
            url="/transfers?success=Stock+Transfer+draft+deleted+successfully.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/transfers/view/{transfer_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 9. Printable Transfer Voucher / Gate Pass
# ---------------------------------------------------------
@router.get("/print/{transfer_id}", response_class=HTMLResponse)
def print_transfer_voucher_ui(
    transfer_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_transfer = get_transfer_by_id(db, transfer_id)
    if not stock_transfer:
        raise HTTPException(status_code=404, detail="Stock Transfer not found.")

    total_items = len(stock_transfer.lines)
    total_quantity = sum(float(l.quantity) for l in stock_transfer.lines)

    return templates.TemplateResponse(
        request=request,
        name="transfers/print.html",
        context={
            "request": request,
            "page_title": f"Transfer Voucher - {stock_transfer.transfer_no}",
            "current_user": current_user,
            "user": current_user,
            "transfer": stock_transfer,
            "total_items": total_items,
            "total_quantity": total_quantity,
        },
    )
