from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.asset import Asset
from app.models.enums import (
    AssetStatus,
    Category_Type,
    MovementType,
    TransactionSource,
    TransactionStatus,
    UnserviceableStatus,
)

from app.models.category import Category
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.issue import Issue, IssueLine
from app.models.item import Item
from app.models.office import Office

from app.models.opening_stock import OpeningStock
from app.models.section import Section
from app.models.stock_movement import StockMovement
from app.models.unit import Unit
from app.models.unserviceable_material import UnserviceableMaterial
from app.schemas.stock import (
    AssetRegisterItem,
    DistributionRegisterItem,
    ItemTransactionRegisterItem,
    StockBalanceRead,
)
from app.services.stock_service import get_item_stock, get_item_unserviceable_stock, get_item_usable_stock



def get_stock_balances(
    db: Session,
    search: str = "",
    category_id: Optional[int] = None,
    office_id: Optional[int] = None,
    financial_year_id: Optional[int] = None,
    page: int = 1,
):
    query = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .outerjoin(Unit, Item.unit_id == Unit.id)
        .filter(
            Item.is_active == True,
            Category.is_active == True,
        )
    )

    if category_id is not None:
        query = query.filter(Item.category_id == category_id)

    if office_id is not None:
        op_item_ids = (
            db.query(OpeningStock.item_id)
            .filter(OpeningStock.office_id == office_id, OpeningStock.is_active == True)
        )
        sm_item_ids = (
            db.query(StockMovement.item_id)
            .filter(StockMovement.office_id == office_id, StockMovement.is_active == True)
        )
        if financial_year_id is not None:
            op_item_ids = op_item_ids.filter(OpeningStock.financial_year_id == financial_year_id)
            sm_item_ids = sm_item_ids.filter(StockMovement.financial_year_id == financial_year_id)

        all_ids = set(r[0] for r in op_item_ids.all()).union(r[0] for r in sm_item_ids.all())
        query = query.filter(Item.id.in_(all_ids if all_ids else [-1]))

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                Item.name.ilike(f"%{clean}%"),
                Item.code.ilike(f"%{clean}%"),
                Category.name.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(Item.name.asc())
    pagination = get_pagination_result(query, page)

    off_name = None
    if office_id:
        off = db.query(Office).filter(Office.id == office_id).first()
        if off:
            off_name = off.name

    result_items = []
    for item in pagination["items"]:
        balance = get_item_stock(db, item_id=item.id, office_id=office_id)
        unserviceable = get_item_unserviceable_stock(db, item_id=item.id, office_id=office_id)
        usable = get_item_usable_stock(db, item_id=item.id, office_id=office_id)
        result_items.append(
            StockBalanceRead(
                item_id=item.id,
                item_name=item.name,
                item_code=item.code,
                category_name=item.category.name if item.category else "",
                unit_name=item.unit.name if item.unit else None,
                office_id=office_id,
                office_name=off_name,
                current_stock=balance,
                unserviceable_stock=unserviceable,
                usable_stock=usable,
            )
        )

    pagination["items"] = result_items
    return pagination


def get_stock_ledger(
    db: Session,
    item_id: Optional[int] = None,
    office_id: Optional[int] = None,
    financial_year_id: Optional[int] = None,
    page: int = 1,
):
    query = db.query(StockMovement).filter(StockMovement.is_active == True)

    if item_id is not None:
        query = query.filter(StockMovement.item_id == item_id)

    if office_id is not None:
        query = query.filter(StockMovement.office_id == office_id)

    if financial_year_id is not None:
        query = query.filter(StockMovement.financial_year_id == financial_year_id)

    query = query.order_by(StockMovement.id.desc())
    return get_pagination_result(query, page)


def get_distribution_register(
    db: Session,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    item_id: Optional[int] = None,
    from_date: Optional[object] = None,
    to_date: Optional[object] = None,
    page: int = 1,
):
    """
    Distribution Register derived from posted Issue documents.
    """
    query = (
        db.query(IssueLine, Issue, Indent, Office, Section, Item, FinancialYear, Unit)
        .join(Issue, IssueLine.issue_id == Issue.id)
        .join(Indent, Issue.indent_id == Indent.id)
        .join(Office, Issue.office_id == Office.id)
        .outerjoin(Section, Issue.section_id == Section.id)
        .join(Item, IssueLine.item_id == Item.id)
        .join(FinancialYear, Issue.financial_year_id == FinancialYear.id)
        .outerjoin(Unit, IssueLine.unit_id == Unit.id)
        .filter(
            Issue.status == TransactionStatus.POSTED,
            Issue.is_active == True,
            IssueLine.is_active == True,
        )
    )

    if financial_year_id is not None:
        query = query.filter(Issue.financial_year_id == financial_year_id)

    if office_id is not None:
        query = query.filter(Issue.office_id == office_id)

    if section_id is not None:
        query = query.filter(Issue.section_id == section_id)

    if item_id is not None:
        query = query.filter(IssueLine.item_id == item_id)

    if from_date is not None:
        query = query.filter(Issue.issue_date >= from_date)

    if to_date is not None:
        query = query.filter(Issue.issue_date <= to_date)

    query = query.order_by(Issue.issue_date.desc(), Issue.id.desc())
    pagination = get_pagination_result(query, page)

    items = []
    for line, issue, indent, office, section, item, fy, unit in pagination["items"]:
        items.append(
            DistributionRegisterItem(
                issue_id=issue.id,
                issue_no=issue.issue_no,
                issue_date=issue.issue_date,
                financial_year_id=fy.id,
                financial_year_code=fy.year_name,
                office_id=office.id,
                office_name=office.name,
                section_id=section.id if section else None,
                section_name=section.name if section else None,
                indent_id=indent.id,
                indent_no=indent.indent_no,
                item_id=item.id,
                item_name=item.name,
                item_code=item.code,
                quantity=line.quantity,
                unit_name=unit.name if unit else None,
                remarks=line.remarks,
            )
        )

    pagination["items"] = items
    return pagination


def get_item_transaction_register(
    db: Session,
    item_id: int,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    financial_year_id: Optional[int] = None,
    page: int = 1,
):
    """
    Item Transaction Register showing movement history, running balance, indent number, and to office/section.
    Includes Opening Stock as initial movement.
    """
    # 1. Fetch any Opening Stock record for this item/office/FY
    op_query = (
        db.query(OpeningStock, FinancialYear, Office)
        .join(FinancialYear, OpeningStock.financial_year_id == FinancialYear.id)
        .join(Office, OpeningStock.office_id == Office.id)
        .filter(
            OpeningStock.item_id == item_id,
            OpeningStock.is_active == True,
        )
    )
    if office_id is not None:
        op_query = op_query.filter(OpeningStock.office_id == office_id)
    if financial_year_id is not None:
        op_query = op_query.filter(OpeningStock.financial_year_id == financial_year_id)

    op_records = op_query.all()

    # 2. Query StockMovement
    query = (
        db.query(StockMovement, FinancialYear, Office, Section)
        .join(FinancialYear, StockMovement.financial_year_id == FinancialYear.id)
        .join(Office, StockMovement.office_id == Office.id)
        .outerjoin(Section, StockMovement.section_id == Section.id)
        .filter(
            StockMovement.item_id == item_id,
            StockMovement.is_active == True,
            StockMovement.transaction_source != TransactionSource.HISTORICAL,
        )
    )

    if office_id is not None:
        query = query.filter(StockMovement.office_id == office_id)

    if section_id is not None:
        query = query.filter(StockMovement.section_id == section_id)

    if financial_year_id is not None:
        query = query.filter(StockMovement.financial_year_id == financial_year_id)

    query = query.order_by(StockMovement.movement_date.asc(), StockMovement.id.asc())

    rows = []
    has_opening_sm = any(sm.movement_type == MovementType.OPENING for sm, fy, off, sec in query.all())

    if not has_opening_sm and op_records:
        for op, fy, off in op_records:
            rows.append({
                "id": op.id,
                "date": op.created_at,
                "fy_code": fy.year_name,
                "indent_no": None,
                "ref_type": "OPENING",
                "ref_no": "OPENING-STOCK",
                "m_type": MovementType.OPENING,
                "qty_in": float(op.quantity),
                "qty_out": 0.0,
                "off_name": off.name if off else None,
                "sec_name": None,
                "remarks": op.remarks or "Opening Stock Balance",
            })

    sm_items = query.all()
    # Batch lookup indent numbers for issue movements
    issue_ids = [
        sm.reference_id
        for sm, fy, off, sec in sm_items
        if sm.reference_type == "ISSUE"
    ]
    issue_indent_map = {}
    if issue_ids:
        issue_rows = (
            db.query(Issue.id, Indent.indent_no, Section.name)
            .join(Indent, Issue.indent_id == Indent.id)
            .outerjoin(Section, Issue.section_id == Section.id)
            .filter(Issue.id.in_(issue_ids))
            .all()
        )
        for iss_id, ind_no, sec_name in issue_rows:
            issue_indent_map[iss_id] = (ind_no, sec_name)

    for sm, fy, off, sec in sm_items:
        indent_no = None
        sec_name = sec.name if sec else None
        if sm.reference_type == "ISSUE" and sm.reference_id in issue_indent_map:
            indent_no, iss_sec = issue_indent_map[sm.reference_id]
            if not sec_name:
                sec_name = iss_sec
        elif sm.reference_type == "INDENT":
            ind = db.query(Indent).filter(Indent.id == sm.reference_id).first()
            if ind:
                indent_no = ind.indent_no

        rows.append({
            "id": sm.id,
            "date": sm.movement_date,
            "fy_code": fy.year_name,
            "indent_no": indent_no,
            "ref_type": sm.reference_type,
            "ref_no": sm.reference_no,
            "m_type": sm.movement_type,
            "qty_in": float(sm.quantity_in),
            "qty_out": float(sm.quantity_out),
            "off_name": off.name if off else None,
            "sec_name": sec_name,
            "remarks": sm.remarks,
        })

    # Sort rows by date ascending
    rows.sort(key=lambda r: r["date"])

    running_balance = 0.0
    items = []
    for r in rows:
        running_balance += (r["qty_in"] - r["qty_out"])
        items.append(
            ItemTransactionRegisterItem(
                movement_id=r["id"],
                movement_date=r["date"],
                financial_year_code=r["fy_code"],
                indent_no=r["indent_no"],
                reference_type=r["ref_type"],
                reference_no=r["ref_no"],
                movement_type=r["m_type"],
                quantity_in=r["qty_in"],
                quantity_out=r["qty_out"],
                running_balance=round(running_balance, 2),
                office_name=r["off_name"],
                section_name=r["sec_name"],
                remarks=r["remarks"],
            )
        )

    # Paginate over items
    page_size = 25
    total_count = len(items)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": items[start:end],
        "total_records": total_count,
        "current_page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_asset_register_report(
    db: Session,
    item_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status: Optional[AssetStatus] = None,
    search: str = "",
    page: int = 1,
):
    query = (
        db.query(Asset, Item, Category, Office, Section)
        .join(Item, Asset.item_id == Item.id)
        .join(Category, Item.category_id == Category.id)
        .join(Office, Asset.office_id == Office.id)
        .outerjoin(Section, Asset.section_id == Section.id)
        .filter(Asset.is_active == True)
    )

    if item_id is not None:
        query = query.filter(Asset.item_id == item_id)

    if office_id is not None:
        query = query.filter(Asset.office_id == office_id)

    if section_id is not None:
        query = query.filter(Asset.section_id == section_id)

    if status is not None:
        query = query.filter(Asset.status == status)

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                Asset.asset_no.ilike(f"%{clean}%"),
                Asset.serial_no.ilike(f"%{clean}%"),
                Item.name.ilike(f"%{clean}%"),
                Item.code.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(Asset.id.desc())
    pagination = get_pagination_result(query, page)

    items = []
    for asset, item, category, office, section in pagination["items"]:
        make_val = asset.asset_detail.make if asset.asset_detail else None
        model_val = asset.asset_detail.model if asset.asset_detail else None

        items.append(
            AssetRegisterItem(
                asset_id=asset.id,
                asset_no=asset.asset_no,
                item_id=item.id,
                item_name=item.name,
                category_name=category.name,
                serial_no=asset.serial_no,
                make=make_val,
                model=model_val,
                office_id=office.id,
                office_name=office.name,
                section_id=section.id if section else None,
                section_name=section.name if section else None,
                status=asset.status,
                remarks=asset.remarks,
            )
        )

    pagination["items"] = items
    return pagination


def get_computer_register_report(
    db: Session,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    search: str = "",
    page: int = 1,
):
    query = (
        db.query(Asset, Item, Category, Office, Section)
        .join(Item, Asset.item_id == Item.id)
        .join(Category, Item.category_id == Category.id)
        .join(Office, Asset.office_id == Office.id)
        .outerjoin(Section, Asset.section_id == Section.id)
        .filter(
            Asset.is_active == True,
            Category.type == Category_Type.ASSET,
            or_(
                Item.name.ilike("%computer%"),
                Item.name.ilike("%desktop%"),
                Item.name.ilike("%laptop%"),
                Item.name.ilike("%pc%"),
                Category.name.ilike("%computer%"),
                Category.name.ilike("%it%"),
            ),
        )
    )

    if office_id is not None:
        query = query.filter(Asset.office_id == office_id)

    if section_id is not None:
        query = query.filter(Asset.section_id == section_id)

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                Asset.asset_no.ilike(f"%{clean}%"),
                Asset.serial_no.ilike(f"%{clean}%"),
                Item.name.ilike(f"%{clean}%"),
                Item.code.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(Asset.id.desc())
    pagination = get_pagination_result(query, page)

    items = []
    for asset, item, category, office, section in pagination["items"]:
        make_val = asset.asset_detail.make if asset.asset_detail else None
        model_val = asset.asset_detail.model if asset.asset_detail else None

        items.append(
            AssetRegisterItem(
                asset_id=asset.id,
                asset_no=asset.asset_no,
                item_id=item.id,
                item_name=item.name,
                category_name=category.name,
                serial_no=asset.serial_no,
                make=make_val,
                model=model_val,
                office_id=office.id,
                office_name=office.name,
                section_id=section.id if section else None,
                section_name=section.name if section else None,
                status=asset.status,
                remarks=asset.remarks,
            )
        )

    pagination["items"] = items
    return pagination


def get_ewaste_register_report(
    db: Session,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    search: str = "",
    page: int = 1,
):
    return get_asset_register_report(
        db=db,
        office_id=office_id,
        section_id=section_id,
        status=AssetStatus.E_WASTE,
        search=search,
        page=page,
    )


def get_office_stock_items(
    db: Session,
    office_id: int,
    financial_year_id: Optional[int] = None,
):
    """
    Return all Items that have a stock identity for the given office/FY.
    Calculates live physical/unserviceable/usable stock figures efficiently in batch.
    """
    from app.models.enums import Category_Type, MovementType, TransactionSource, UnserviceableStatus, AssetStatus
    from app.models.unit import Unit
    from app.models.asset import Asset

    # 1. Opening stock batch map
    op_query = (
        db.query(OpeningStock.item_id, func.coalesce(func.sum(OpeningStock.quantity), 0))
        .filter(OpeningStock.office_id == office_id, OpeningStock.is_active == True)
    )
    if financial_year_id is not None:
        op_query = op_query.filter(OpeningStock.financial_year_id == financial_year_id)
    op_map = dict(op_query.group_by(OpeningStock.item_id).all())

    # 2. Movement stock batch map
    sm_query = (
        db.query(
            StockMovement.item_id,
            func.coalesce(func.sum(StockMovement.quantity_in - StockMovement.quantity_out), 0)
        )
        .filter(
            StockMovement.office_id == office_id,
            StockMovement.is_active == True,
            StockMovement.transaction_source != TransactionSource.HISTORICAL,
        )
    )
    if financial_year_id is not None:
        sm_query = sm_query.filter(StockMovement.financial_year_id == financial_year_id)
    sm_map = dict(sm_query.group_by(StockMovement.item_id).all())

    # Items that have an explicit OPENING StockMovement
    opening_sm_items = set(
        row[0]
        for row in db.query(StockMovement.item_id)
        .filter(
            StockMovement.office_id == office_id,
            StockMovement.movement_type == MovementType.OPENING,
            StockMovement.is_active == True,
        )
        .distinct()
        .all()
    )

    # 3. Unserviceable materials batch map
    unserv_mat_map = dict(
        db.query(UnserviceableMaterial.item_id, func.coalesce(func.sum(UnserviceableMaterial.quantity), 0))
        .filter(
            UnserviceableMaterial.office_id == office_id,
            UnserviceableMaterial.is_active == True,
            UnserviceableMaterial.status.in_([UnserviceableStatus.UNSERVICEABLE, UnserviceableStatus.UNDER_REPAIR]),
        )
        .group_by(UnserviceableMaterial.item_id)
        .all()
    )

    # 4. Unserviceable assets batch map
    unserv_asset_map = dict(
        db.query(Asset.item_id, func.count(Asset.id))
        .filter(
            Asset.office_id == office_id,
            Asset.is_active == True,
            Asset.status.in_([
                AssetStatus.DAMAGED,
                AssetStatus.UNDER_REPAIR,
                AssetStatus.CONDEMNED,
                AssetStatus.E_WASTE,
                AssetStatus.DISPOSED,
            ]),
        )
        .group_by(Asset.item_id)
        .all()
    )

    all_item_ids = set(op_map.keys()) | set(sm_map.keys())
    if not all_item_ids:
        return []

    items = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .outerjoin(Unit, Item.unit_id == Unit.id)
        .filter(
            Item.id.in_(all_item_ids),
            Item.is_active == True,
            Category.is_active == True,
        )
        .order_by(Item.name)
        .all()
    )

    result = []
    for item in items:
        # Opening + movement (ignoring op model if OPENING movement exists)
        op_qty = 0.0 if item.id in opening_sm_items else float(op_map.get(item.id, 0.0))
        mv_qty = float(sm_map.get(item.id, 0.0))
        physical = round(op_qty + mv_qty, 2)

        # Unserviceable stock
        unserv = round(float(unserv_mat_map.get(item.id, 0.0)) + float(unserv_asset_map.get(item.id, 0.0)), 2)
        usable = round(max(0.0, physical - unserv), 2)

        is_asset = (
            item.category is not None
            and item.category.type == Category_Type.ASSET
        )
        result.append(
            {
                "id": item.id,
                "name": item.name,
                "code": item.code,
                "unit_symbol": item.unit.symbol if item.unit else "",
                "physical_stock": physical,
                "unserviceable_stock": unserv,
                "usable_stock": usable,
                "is_asset": is_asset,
            }
        )
    return result

