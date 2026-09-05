from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.core.db import get_db
from app.core.templates import templates
from app.dependencies.ui_auth import get_current_user_ui
from app.models.user import User
from app.models.enums import DestinationType, TransactionStatus, Category_Type, AssetStatus, FulfillmentType
from app.models.asset import Asset
from app.models.issue import Issue

from app.crud.issue import (
    create_issue,
    get_all_issues,
    get_issue_by_id,
    update_issue,
)
from app.crud.indent import get_indent_by_id
from app.crud.office import get_all_offices
from app.crud.section import get_all_sections
from app.crud.financial_year import get_all_financial_years
from app.crud.outward_pass import create_outward_pass, get_outward_pass_by_issue_id

from app.schemas.issue import IssueCreate, IssueLineCreate
from app.schemas.petty_purchase import PettyPurchaseCreate
from app.schemas.outward_pass import OutwardPassCreate
from app.services.document_number_service import generate_document_number
from app.services.posting_service import post_issue
from app.services.scope_service import get_stock_office_id
from app.services.stock_service import get_available_asset_count, get_item_usable_stock

router = APIRouter(
    prefix="/issues",
    tags=["Issues UI"],
)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def list_issues_ui(
    request: Request,
    search: str = "",
    issue_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    transaction_status: Optional[TransactionStatus] = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    issues_page = get_all_issues(
        db=db,
        search=search,
        issue_no=issue_no,
        financial_year_id=financial_year_id,
        office_id=office_id,
        section_id=section_id,
        status=transaction_status,
        page=page,
    )

    offices = get_all_offices(db)
    sections = get_all_sections(db)
    financial_years = get_all_financial_years(db)

    return templates.TemplateResponse(
        request=request,
        name="issues/list.html",
        context={
            "request": request,
            "page_title": "Issue Register",
            "current_user": current_user,
            "issues": issues_page.get("items", []),
            "total": issues_page.get("total_records", 0),
            "page": issues_page.get("current_page", 1),
            "total_pages": issues_page.get("total_pages", 1),
            "search": search,
            "issue_no_filter": issue_no or "",
            "financial_year_id_filter": financial_year_id,
            "office_id_filter": office_id,
            "section_id_filter": section_id,
            "transaction_status_filter": transaction_status.value if transaction_status else "",
            "offices": offices,
            "sections": sections,
            "financial_years": financial_years,
            "transaction_statuses": [s.value for s in TransactionStatus],
        },
    )


@router.get("/create", response_class=HTMLResponse)
def create_issue_form_ui(
    indent_id: int,
    request: Request,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    indent = get_indent_by_id(db, indent_id)
    if not indent:
        raise HTTPException(status_code=404, detail="Indent not found")

    proposed_issue_no = generate_document_number(
        db=db,
        model_class=Issue,
        number_field_name="issue_no",
        prefix="ISS",
        financial_year_id=indent.financial_year_id,
    )

    prepared_lines = []
    for line in indent.lines:
        if not line.is_active:
            continue

        # Effective issue quantity defaults to issued_quantity if set > 0, else requested_quantity
        default_qty = line.issued_quantity if (line.issued_quantity is not None and line.issued_quantity > 0) else line.requested_quantity
        
        store_office_id = get_stock_office_id(db, indent.office_id)
        is_asset = bool(
            line.item
            and line.item.category
            and line.item.category.type == Category_Type.ASSET
        )
        available_assets = []
        if is_asset:
            available_assets = db.query(Asset).filter(
                Asset.item_id == line.item_id,
                Asset.office_id == store_office_id,
                Asset.status == AssetStatus.IN_STORE,
                Asset.is_active == True,
            ).order_by(Asset.asset_no).all()
            usable = len(available_assets)
        else:
            usable = get_item_usable_stock(
                db,
                item_id=line.item_id,
                office_id=indent.office_id,
                financial_year_id=indent.financial_year_id,
            )

        prepared_lines.append({
            "line": line,
            "default_qty": default_qty,
            "usable_stock": usable,
            "is_asset": is_asset,
            "available_assets": available_assets,
        })

    return templates.TemplateResponse(
        request=request,
        name="issues/create.html",
        context={
            "request": request,
            "page_title": f"Create Issue for Indent {indent.indent_no}",
            "current_user": current_user,
            "indent": indent,
            "proposed_issue_no": proposed_issue_no,
            "today_date": date.today().isoformat(),
            "prepared_lines": prepared_lines,
            "destination_types": [d.value for d in DestinationType],
            "error": error,
        },
    )


@router.post("/create", response_class=HTMLResponse)
async def submit_create_issue_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    form_data = await request.form()

    try:
        indent_id = int(form_data.get("indent_id"))
        financial_year_id = int(form_data.get("financial_year_id"))
        office_id = int(form_data.get("office_id"))
        section_id_raw = form_data.get("section_id")
        section_id = int(section_id_raw) if section_id_raw and section_id_raw.isdigit() else None
        destination_type = DestinationType(form_data.get("destination_type", DestinationType.INTERNAL.value))
        reference_no = form_data.get("reference_no", "").strip() or None
        remarks = form_data.get("remarks", "").strip() or None
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid form parameters: {e}")

    indent = get_indent_by_id(db, indent_id)
    if not indent:
        raise HTTPException(status_code=404, detail="Indent not found")

    issue_lines = []
    for line in indent.lines:
        if not line.is_active:
            continue

        qty_key = f"qty_{line.id}"
        remarks_key = f"remarks_{line.id}"
        assets_key = f"assets_{line.id}"
        pp_date_key = f"pp_date_{line.id}"
        pp_supplier_key = f"pp_supplier_{line.id}"
        pp_ref_key = f"pp_ref_{line.id}"
        pp_rate_key = f"pp_rate_{line.id}"
        pp_remarks_key = f"pp_remarks_{line.id}"

        if qty_key in form_data:
            try:
                qty_val = float(form_data.get(qty_key))
            except ValueError:
                qty_val = 0.0

            if qty_val <= 0:
                # Zero issue line
                continue

            selected_asset_ids = []
            if line.item and line.item.category and line.item.category.type == Category_Type.ASSET:
                raw_assets = form_data.getlist(assets_key)
                selected_asset_ids = [int(a) for a in raw_assets if a.isdigit()]
                
                # Enforce selected asset count == issued quantity for assets
                if len(selected_asset_ids) != int(qty_val):
                    return RedirectResponse(
                        url=f"/issues/create?indent_id={indent_id}&error=Selected+asset+count+({len(selected_asset_ids)})+must+equal+issued+quantity+({int(qty_val)})+for+{line.item.name}",
                        status_code=status.HTTP_303_SEE_OTHER,
                    )

            line_remarks = form_data.get(remarks_key, "").strip() or None
            petty_purchase = None
            if line.fulfillment_type == FulfillmentType.PETTY_PURCHASE:
                from datetime import date as _date
                purchase_date_raw = str(form_data.get(pp_date_key, "")).strip()
                purchase_date = _date.fromisoformat(purchase_date_raw) if purchase_date_raw else _date.today()
                rate_raw = str(form_data.get(pp_rate_key, "")).strip()
                try:
                    rate_value = float(rate_raw) if rate_raw else None
                except ValueError:
                    return RedirectResponse(
                        url=f"/issues/create?indent_id={indent_id}&error=Invalid+unit+rate+for+{line.item.name}",
                        status_code=status.HTTP_303_SEE_OTHER,
                    )
                petty_purchase = PettyPurchaseCreate(
                    purchase_date=purchase_date,
                    supplier_name=str(form_data.get(pp_supplier_key, "")).strip() or None,
                    reference_no=str(form_data.get(pp_ref_key, "")).strip() or None,
                    unit_price=rate_value,
                    remarks=str(form_data.get(pp_remarks_key, "")).strip() or None,
                )

            issue_lines.append(
                IssueLineCreate(
                    item_id=line.item_id,
                    unit_id=line.item.unit_id if line.item else None,
                    quantity=qty_val,
                    remarks=line_remarks,
                    asset_ids=selected_asset_ids if selected_asset_ids else None,
                    petty_purchase=petty_purchase,
                )
            )

    if not issue_lines:
        return RedirectResponse(
            url=f"/issues/create?indent_id={indent_id}&error=At+least+one+item+must+have+issued+quantity+greater+than+0",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        issue = create_issue(
            db=db,
            issue_in=IssueCreate(
                financial_year_id=financial_year_id,
                indent_id=indent_id,
                office_id=office_id,
                section_id=section_id,
                destination_type=destination_type,
                issue_date=date.today(),
                reference_no=reference_no,
                remarks=remarks,
                lines=issue_lines,
            ),
            user_id=current_user.id,
        )
        return RedirectResponse(
            url=f"/issues/{issue.id}/review?success=Draft+Issue+created+successfully",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/issues/create?indent_id={indent_id}&error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.get("/view/{issue_id}", response_class=HTMLResponse)
@router.get("/{issue_id}", response_class=HTMLResponse)
@router.get("/{issue_id}/review", response_class=HTMLResponse)
def review_issue_ui(
    issue_id: int,
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    issue = get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    outward_pass = get_outward_pass_by_issue_id(db, issue.id)

    total_lines = len(issue.lines)
    total_qty = sum(l.quantity for l in issue.lines)

    return templates.TemplateResponse(
        request=request,
        name="issues/review.html",
        context={
            "request": request,
            "page_title": f"Review Issue {issue.issue_no}",
            "current_user": current_user,
            "issue": issue,
            "outward_pass": outward_pass,
            "total_lines": total_lines,
            "total_qty": total_qty,
            "is_external": issue.destination_type == DestinationType.EXTERNAL,
            "error": error,
            "success": success,
        },
    )


@router.post("/{issue_id}/post", response_class=HTMLResponse)
def post_issue_ui(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    try:
        posted = post_issue(db=db, issue_id=issue_id, user_id=current_user.id)
        return templates.TemplateResponse(
            request=request,
            name="issues/posted.html",
            context={
                "request": request,
                "page_title": f"Issue Posted - {posted.issue_no}",
                "current_user": current_user,
                "issue": posted,
            },
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/issues/{issue_id}/review?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/{issue_id}/outward-pass", response_class=HTMLResponse)
async def create_outward_pass_ui(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    form_data = await request.form()
    purpose = form_data.get("purpose", "").strip()
    recipient = form_data.get("recipient", "").strip()
    destination = form_data.get("destination", "").strip()
    vehicle = form_data.get("vehicle_details", "").strip() or None
    remarks = form_data.get("remarks", "").strip() or None

    try:
        create_outward_pass(
            db=db,
            pass_in=OutwardPassCreate(
                issue_id=issue_id,
                pass_date=date.today(),
                purpose=purpose,
                recipient_name=recipient,
                destination=destination,
                vehicle_details=vehicle,
                remarks=remarks,
            ),
            user_id=current_user.id,
        )
        return RedirectResponse(
            url=f"/issues/{issue_id}/review?success=Outward+Pass+generated+successfully",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/issues/{issue_id}/review?error={str(e).replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
