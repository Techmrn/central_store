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
from app.models.stock_return import StockReturn
from app.models.user import User

from app.crud.financial_year import get_all_financial_years, get_current_financial_year
from app.crud.office import get_all_offices_dropdown
from app.crud.section import get_all_sections
from app.crud.stock_return import (
    create_return,
    delete_return,
    get_all_returns,
    get_return_by_id,
    update_return,
)
from app.schemas.stock_return import StockReturnCreate, StockReturnLineCreate, StockReturnUpdate
from app.services.posting_service import post_return

router = APIRouter(
    prefix="/stock-returns",
    tags=["Stock Returns UI"],
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
# 1. Stock Returns Register / List
# ---------------------------------------------------------
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_returns_ui(
    request: Request,
    search: str = "",
    return_no: Optional[str] = None,
    financial_year_id: Optional[str] = None,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
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
    s_id = _parse_int(section_id)
    f_date = _parse_date(from_date)
    t_date = _parse_date(to_date)

    status_enum = None
    if transaction_status and transaction_status.strip():
        try:
            status_enum = TransactionStatus(transaction_status.strip())
        except ValueError:
            status_enum = None

    returns_page = get_all_returns(
        db=db,
        search=search or "",
        return_no=return_no.strip() if return_no else None,
        financial_year_id=fy_id,
        office_id=o_id,
        section_id=s_id,
        status=status_enum,
        from_date=f_date,
        to_date=t_date,
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    financial_years = get_all_financial_years(db)
    sections = get_all_sections(db)

    for r in returns_page.get("items", []):
        r.calculated_total_quantity = sum(float(l.quantity) for l in r.lines)

    return templates.TemplateResponse(
        request=request,
        name="stock_returns/list.html",
        context={
            "request": request,
            "page_title": "Stock Returns Register",
            "current_user": current_user,
            "user": current_user,
            "returns": returns_page.get("items", []),
            "total": returns_page.get("total_records", 0),
            "page": returns_page.get("current_page", 1),
            "total_pages": returns_page.get("total_pages", 1),
            "search": search,
            "return_no_filter": return_no or "",
            "financial_year_id_filter": fy_id,
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "transaction_status_filter": transaction_status or "",
            "from_date_filter": from_date or "",
            "to_date_filter": to_date or "",
            "offices": offices,
            "sections": sections,
            "financial_years": financial_years,
            "transaction_statuses": [s.value for s in TransactionStatus],
            "success": success,
            "error": error,
        },
    )


# ---------------------------------------------------------
# 2. New Stock Return Form
# ---------------------------------------------------------
@router.get("/new", response_class=HTMLResponse)
@router.get("/create", response_class=HTMLResponse)
def new_return_form_ui(
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

    return templates.TemplateResponse(
        request=request,
        name="stock_returns/create.html",
        context={
            "request": request,
            "page_title": "Record Stock Return",
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
# 3. Create Stock Return Submission (Draft or Post)
# ---------------------------------------------------------
@router.post("/new", response_class=HTMLResponse)
@router.post("/create", response_class=HTMLResponse)
async def submit_new_return_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    form_data = await request.form()

    return_date_raw = form_data.get("return_date")
    office_id_raw = form_data.get("office_id")
    section_id_raw = form_data.get("section_id")
    financial_year_id_raw = form_data.get("financial_year_id")
    remarks = str(form_data.get("remarks", "")).strip() or None
    action_type = str(form_data.get("action_type", "save_draft")).strip().lower()

    try:
        return_date = date.fromisoformat(return_date_raw) if return_date_raw else date.today()
        office_id = int(office_id_raw)
    except (ValueError, TypeError) as e:
        return RedirectResponse(
            url=f"/stock-returns/new?error=Invalid+form+data:+{e}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    section_id = _parse_int(section_id_raw)

    fy_id = _parse_int(financial_year_id_raw)
    if not fy_id:
        current_fy = get_current_financial_year(db)
        if not current_fy:
            current_fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
        if not current_fy:
            return RedirectResponse(
                url="/stock-returns/new?error=No+active+financial+year+found.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        fy_id = current_fy.id

    item_ids = form_data.getlist("item_id[]")
    quantities = form_data.getlist("quantity[]")
    line_remarks_list = form_data.getlist("line_remarks[]")

    if not item_ids:
        return RedirectResponse(
            url="/stock-returns/new?error=At+least+one+item+line+is+required.",
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
                url="/stock-returns/new?error=Quantity+must+be+greater+than+zero+for+all+items.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        l_remarks = str(line_remarks_list[i]).strip() if i < len(line_remarks_list) else None

        lines_create.append(
            StockReturnLineCreate(
                item_id=item_id,
                quantity=qty,
                remarks=l_remarks or None,
            )
        )

    if not lines_create:
        return RedirectResponse(
            url="/stock-returns/new?error=No+valid+item+lines+provided.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        stock_return = create_return(
            db=db,
            return_in=StockReturnCreate(
                financial_year_id=fy_id,
                office_id=office_id,
                section_id=section_id,
                return_date=return_date,
                remarks=remarks,
                lines=lines_create,
            ),
            user_id=current_user.id,
        )

        if action_type == "post":
            post_return(db=db, return_id=stock_return.id, user_id=current_user.id)
            return RedirectResponse(
                url=f"/stock-returns/view/{stock_return.id}?success=Stock+Return+{stock_return.return_no}+posted+to+stock+successfully.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            return RedirectResponse(
                url=f"/stock-returns/view/{stock_return.id}?success=Stock+Return+{stock_return.return_no}+saved+as+Draft.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    except ValueError as e:
        return RedirectResponse(
            url=f"/stock-returns/new?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 4. View Stock Return Details
# ---------------------------------------------------------
@router.get("/view/{return_id}", response_class=HTMLResponse)
def view_return_details_ui(
    return_id: int,
    request: Request,
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_return = get_return_by_id(db, return_id)
    if not stock_return:
        raise HTTPException(status_code=404, detail="Stock Return not found.")

    total_items = len(stock_return.lines)
    total_quantity = sum(float(l.quantity) for l in stock_return.lines)

    return templates.TemplateResponse(
        request=request,
        name="stock_returns/view.html",
        context={
            "request": request,
            "page_title": f"Stock Return - {stock_return.return_no}",
            "current_user": current_user,
            "user": current_user,
            "return_doc": stock_return,
            "total_items": total_items,
            "total_quantity": total_quantity,
            "success": success,
            "error": error,
        },
    )


# ---------------------------------------------------------
# 5. Edit Draft Return Form
# ---------------------------------------------------------
@router.get("/edit/{return_id}", response_class=HTMLResponse)
def edit_return_form_ui(
    return_id: int,
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_return = get_return_by_id(db, return_id)
    if not stock_return:
        raise HTTPException(status_code=404, detail="Stock Return not found.")

    if stock_return.status == TransactionStatus.POSTED:
        return RedirectResponse(
            url=f"/stock-returns/view/{stock_return.id}?error=Posted+returns+are+read-only+and+cannot+be+edited.",
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

    return templates.TemplateResponse(
        request=request,
        name="stock_returns/edit.html",
        context={
            "request": request,
            "page_title": f"Edit Stock Return - {stock_return.return_no}",
            "current_user": current_user,
            "user": current_user,
            "return_doc": stock_return,
            "offices": offices,
            "sections": sections,
            "items": items,
            "today_date": date.today().isoformat(),
            "error": error,
            "success": success,
        },
    )


# ---------------------------------------------------------
# 6. Update Draft Return Submission
# ---------------------------------------------------------
@router.post("/edit/{return_id}", response_class=HTMLResponse)
async def update_return_ui(
    return_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_return = get_return_by_id(db, return_id)
    if not stock_return:
        raise HTTPException(status_code=404, detail="Stock Return not found.")

    if stock_return.status == TransactionStatus.POSTED:
        return RedirectResponse(
            url=f"/stock-returns/view/{stock_return.id}?error=Posted+returns+are+read-only+and+cannot+be+edited.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    form_data = await request.form()

    return_date_raw = form_data.get("return_date")
    section_id_raw = form_data.get("section_id")
    remarks = str(form_data.get("remarks", "")).strip() or None
    action_type = str(form_data.get("action_type", "save_draft")).strip().lower()

    try:
        return_date = date.fromisoformat(return_date_raw) if return_date_raw else stock_return.return_date
    except (ValueError, TypeError) as e:
        return RedirectResponse(
            url=f"/stock-returns/edit/{return_id}?error=Invalid+date:+{e}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    section_id = _parse_int(section_id_raw)

    item_ids = form_data.getlist("item_id[]")
    quantities = form_data.getlist("quantity[]")
    line_remarks_list = form_data.getlist("line_remarks[]")

    if not item_ids:
        return RedirectResponse(
            url=f"/stock-returns/edit/{return_id}?error=At+least+one+item+line+is+required.",
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
                url=f"/stock-returns/edit/{return_id}?error=Quantity+must+be+greater+than+zero.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        l_remarks = str(line_remarks_list[i]).strip() if i < len(line_remarks_list) else None

        lines_update.append(
            StockReturnLineCreate(
                item_id=item_id,
                quantity=qty,
                remarks=l_remarks or None,
            )
        )

    if not lines_update:
        return RedirectResponse(
            url=f"/stock-returns/edit/{return_id}?error=No+valid+item+lines+provided.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        updated_return = update_return(
            db=db,
            return_id=return_id,
            return_in=StockReturnUpdate(
                return_date=return_date,
                section_id=section_id,
                remarks=remarks,
                lines=lines_update,
            ),
        )

        if action_type == "post":
            post_return(db=db, return_id=updated_return.id, user_id=current_user.id)
            return RedirectResponse(
                url=f"/stock-returns/view/{updated_return.id}?success=Stock+Return+{updated_return.return_no}+posted+to+stock+successfully.",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            return RedirectResponse(
                url=f"/stock-returns/view/{updated_return.id}?success=Stock+Return+{updated_return.return_no}+draft+updated+successfully.",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    except ValueError as e:
        return RedirectResponse(
            url=f"/stock-returns/edit/{return_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 7. Post Draft Return to Stock
# ---------------------------------------------------------
@router.post("/post/{return_id}", response_class=HTMLResponse)
@router.post("/{return_id}/post", response_class=HTMLResponse)
def post_return_ui(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        stock_return = post_return(db=db, return_id=return_id, user_id=current_user.id)
        return RedirectResponse(
            url=f"/stock-returns/view/{stock_return.id}?success=Stock+Return+{stock_return.return_no}+posted+to+stock+successfully.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/stock-returns/view/{return_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 8. Delete Draft Return
# ---------------------------------------------------------
@router.post("/delete/{return_id}", response_class=HTMLResponse)
@router.post("/{return_id}/delete", response_class=HTMLResponse)
def delete_return_ui(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        stock_return = delete_return(db=db, return_id=return_id)
        if not stock_return:
            raise HTTPException(status_code=404, detail="Stock Return not found.")
        return RedirectResponse(
            url="/stock-returns?success=Stock+Return+draft+deleted+successfully.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/stock-returns/view/{return_id}?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# ---------------------------------------------------------
# 9. Printable Stock Return Slip
# ---------------------------------------------------------
@router.get("/print/{return_id}", response_class=HTMLResponse)
def print_return_slip_ui(
    return_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    stock_return = get_return_by_id(db, return_id)
    if not stock_return:
        raise HTTPException(status_code=404, detail="Stock Return not found.")

    total_items = len(stock_return.lines)
    total_quantity = sum(float(l.quantity) for l in stock_return.lines)

    return templates.TemplateResponse(
        request=request,
        name="stock_returns/print.html",
        context={
            "request": request,
            "page_title": f"Return Slip - {stock_return.return_no}",
            "current_user": current_user,
            "user": current_user,
            "return_doc": stock_return,
            "total_items": total_items,
            "total_quantity": total_quantity,
        },
    )
