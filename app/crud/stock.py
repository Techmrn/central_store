from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.asset import Asset
from app.models.category import Category
from app.models.enums import AssetStatus, Category_Type, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.issue import Issue, IssueLine
from app.models.item import Item
from app.models.office import Office
from app.models.section import Section
from app.models.stock_movement import StockMovement
from app.models.unit import Unit
from app.schemas.stock import (
    AssetRegisterItem,
    DistributionRegisterItem,
    ItemTransactionRegisterItem,
    StockBalanceRead,
)
from app.services.stock_service import get_item_stock


def get_stock_balances(
    db: Session,
    search: str = "",
    category_id: Optional[int] = None,
    office_id: Optional[int] = None,
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
    page: int = 1,
):
    """
    Item Transaction Register showing historical movement history and running stock balance for an item.
    """
    query = (
        db.query(StockMovement, FinancialYear)
        .join(FinancialYear, StockMovement.financial_year_id == FinancialYear.id)
        .filter(
            StockMovement.item_id == item_id,
            StockMovement.is_active == True,
        )
    )

    if office_id is not None:
        query = query.filter(StockMovement.office_id == office_id)

    query = query.order_by(StockMovement.movement_date.asc(), StockMovement.id.asc())
    pagination = get_pagination_result(query, page)

    running_balance = 0.0
    items = []
    for sm, fy in pagination["items"]:
        running_balance += (sm.quantity_in - sm.quantity_out)
        items.append(
            ItemTransactionRegisterItem(
                movement_id=sm.id,
                movement_date=sm.movement_date,
                financial_year_code=fy.year_name,
                reference_type=sm.reference_type,
                reference_no=sm.reference_no,
                movement_type=sm.movement_type,
                quantity_in=sm.quantity_in,
                quantity_out=sm.quantity_out,
                running_balance=round(running_balance, 2),
                remarks=sm.remarks,
            )
        )

    pagination["items"] = items
    return pagination


def get_asset_register_report(
    db: Session,
    item_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status: Optional[AssetStatus] = None,
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
    page: int = 1,
):
    return get_asset_register_report(
        db=db,
        office_id=office_id,
        status=AssetStatus.E_WASTE,
        page=page,
    )
