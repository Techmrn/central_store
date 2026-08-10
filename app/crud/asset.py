from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.asset import Asset
from app.models.asset_detail import AssetDetail
from app.models.asset_movement import AssetMovement
from app.models.category import Category
from app.models.enums import AssetMovementType, AssetStatus, Category_Type
from app.models.item import Item
from app.models.office import Office
from app.models.section import Section
from app.schemas.asset import (
    AssetCreate,
    AssetDetailCreate,
    AssetDetailUpdate,
    AssetMovementCreate,
    AssetUpdate,
)


def _validate_item_for_asset(db: Session, item_id: int) -> Item:
    item = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .filter(
            Item.id == item_id,
            Item.is_active == True,
            Category.is_active == True,
        )
        .first()
    )

    if not item:
        raise ValueError("Item not found.")

    if item.category.type != Category_Type.ASSET:
        raise ValueError("Selected item does not belong to an Asset category.")

    return item


def _validate_office_and_section(
    db: Session,
    office_id: int,
    section_id: Optional[int] = None,
):
    office = (
        db.query(Office)
        .filter(
            Office.id == office_id,
            Office.is_active == True,
        )
        .first()
    )

    if not office:
        raise ValueError("Office not found.")

    if section_id is not None:
        section = (
            db.query(Section)
            .filter(
                Section.id == section_id,
                Section.is_active == True,
            )
            .first()
        )

        if not section:
            raise ValueError("Section not found.")

        if section.office_id != office_id:
            raise ValueError("The selected section does not belong to the specified office.")


def create_asset(db: Session, asset_in: AssetCreate) -> Asset:
    asset_no = asset_in.asset_no.strip().upper()
    serial_no = (
        asset_in.serial_no.strip()
        if asset_in.serial_no and asset_in.serial_no.strip()
        else None
    )

    # Validate Duplicate Asset No
    dup_asset_no = (
        db.query(Asset)
        .filter(
            func.upper(Asset.asset_no) == asset_no,
            Asset.is_active == True,
        )
        .first()
    )
    if dup_asset_no:
        raise ValueError("Asset with the same asset_no already exists.")

    # Validate Duplicate Serial No
    if serial_no:
        dup_serial = (
            db.query(Asset)
            .filter(
                Asset.serial_no == serial_no,
                Asset.is_active == True,
            )
            .first()
        )
        if dup_serial:
            raise ValueError("Asset with the same serial_no already exists.")

    # Validate Item Category
    _validate_item_for_asset(db, asset_in.item_id)

    # Validate Office & Section
    _validate_office_and_section(db, asset_in.office_id, asset_in.section_id)

    initial_status = asset_in.status or AssetStatus.IN_STORE

    db_asset = Asset(
        asset_no=asset_no,
        item_id=asset_in.item_id,
        serial_no=serial_no,
        office_id=asset_in.office_id,
        section_id=asset_in.section_id,
        status=initial_status,
        remarks=asset_in.remarks.strip() if asset_in.remarks else None,
    )

    if asset_in.detail:
        detail_data = asset_in.detail.model_dump(exclude_unset=True)
        db_asset.asset_detail = AssetDetail(**detail_data)

    # Automatic initial movement record
    initial_movement = AssetMovement(
        movement_type=AssetMovementType.RECEIPT,
        to_office_id=asset_in.office_id,
        to_section_id=asset_in.section_id,
        remarks="Initial Asset Registration",
    )
    db_asset.movements.append(initial_movement)

    db.add(db_asset)

    try:
        db.commit()
        db.refresh(db_asset)
        return db_asset
    except Exception:
        db.rollback()
        raise


def get_asset_by_id(db: Session, asset_id: int) -> Optional[Asset]:
    return (
        db.query(Asset)
        .filter(
            Asset.id == asset_id,
            Asset.is_active == True,
        )
        .first()
    )


def get_asset_by_asset_no(db: Session, asset_no: str) -> Optional[Asset]:
    clean_asset_no = asset_no.strip().upper()
    return (
        db.query(Asset)
        .filter(
            func.upper(Asset.asset_no) == clean_asset_no,
            Asset.is_active == True,
        )
        .first()
    )


def get_asset_by_serial_no(db: Session, serial_no: str) -> Optional[Asset]:
    clean_serial_no = serial_no.strip()
    return (
        db.query(Asset)
        .filter(
            Asset.serial_no == clean_serial_no,
            Asset.is_active == True,
        )
        .first()
    )


def get_all_assets(
    db: Session,
    search: str = "",
    item_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status: Optional[AssetStatus] = None,
    page: int = 1,
):
    query = (
        db.query(Asset)
        .join(Item, Asset.item_id == Item.id)
        .join(Office, Asset.office_id == Office.id)
        .filter(
            Asset.is_active == True,
            Item.is_active == True,
            Office.is_active == True,
        )
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
        clean_search = search.strip()
        query = query.filter(
            or_(
                Asset.asset_no.ilike(f"%{clean_search}%"),
                Asset.serial_no.ilike(f"%{clean_search}%"),
                Item.name.ilike(f"%{clean_search}%"),
                Office.name.ilike(f"%{clean_search}%"),
            )
        )

    query = query.order_by(Asset.asset_no)

    return get_pagination_result(query, page)


def update_asset(
    db: Session,
    asset_id: int,
    asset_in: AssetUpdate,
) -> Asset:
    db_asset = get_asset_by_id(db, asset_id)

    if not db_asset:
        raise ValueError("Asset not found.")

    # Determine office and section targets
    target_office_id = (
        asset_in.office_id if asset_in.office_id is not None else db_asset.office_id
    )
    target_section_id = (
        asset_in.section_id if asset_in.section_id is not None else db_asset.section_id
    )

    if asset_in.office_id is not None or asset_in.section_id is not None:
        _validate_office_and_section(db, target_office_id, target_section_id)
        db_asset.office_id = target_office_id
        db_asset.section_id = target_section_id

    if asset_in.asset_no is not None:
        clean_asset_no = asset_in.asset_no.strip().upper()
        existing = (
            db.query(Asset)
            .filter(
                func.upper(Asset.asset_no) == clean_asset_no,
                Asset.id != asset_id,
                Asset.is_active == True,
            )
            .first()
        )
        if existing:
            raise ValueError("Asset number already exists.")
        db_asset.asset_no = clean_asset_no

    if asset_in.serial_no is not None:
        clean_serial_no = (
            asset_in.serial_no.strip() if asset_in.serial_no.strip() else None
        )
        if clean_serial_no:
            existing = (
                db.query(Asset)
                .filter(
                    Asset.serial_no == clean_serial_no,
                    Asset.id != asset_id,
                    Asset.is_active == True,
                )
                .first()
            )
            if existing:
                raise ValueError("Serial number already exists.")
        db_asset.serial_no = clean_serial_no

    if asset_in.item_id is not None:
        _validate_item_for_asset(db, asset_in.item_id)
        db_asset.item_id = asset_in.item_id

    if asset_in.status is not None:
        db_asset.status = asset_in.status

    if asset_in.remarks is not None:
        db_asset.remarks = asset_in.remarks.strip() if asset_in.remarks else None

    if asset_in.is_active is not None:
        db_asset.is_active = asset_in.is_active

    # Handle nested detail updates
    if asset_in.detail is not None:
        detail_data = asset_in.detail.model_dump(exclude_unset=True)
        if db_asset.asset_detail:
            for key, val in detail_data.items():
                setattr(db_asset.asset_detail, key, val)
        else:
            db_asset.asset_detail = AssetDetail(**detail_data)

    try:
        db.commit()
        db.refresh(db_asset)
        return db_asset
    except Exception:
        db.rollback()
        raise


def delete_asset(db: Session, asset_id: int) -> Optional[Asset]:
    db_asset = get_asset_by_id(db, asset_id)

    if db_asset is None:
        return None

    db_asset.is_active = False

    try:
        db.commit()
        return db_asset
    except Exception:
        db.rollback()
        raise


def create_asset_movement(
    db: Session,
    movement_in: AssetMovementCreate,
    asset_id: Optional[int] = None,
) -> AssetMovement:
    target_asset_id = asset_id or movement_in.asset_id

    if not target_asset_id:
        raise ValueError("Asset ID is required for movement.")

    db_asset = get_asset_by_id(db, target_asset_id)
    if not db_asset:
        raise ValueError("Asset not found.")

    from_office_id = movement_in.from_office_id or db_asset.office_id
    from_section_id = movement_in.from_section_id or db_asset.section_id

    to_office_id = movement_in.to_office_id or db_asset.office_id
    to_section_id = movement_in.to_section_id

    # Validate destination office and section
    _validate_office_and_section(db, to_office_id, to_section_id)

    db_movement = AssetMovement(
        asset_id=target_asset_id,
        movement_type=movement_in.movement_type,
        from_office_id=from_office_id,
        from_section_id=from_section_id,
        to_office_id=to_office_id,
        to_section_id=to_section_id,
        reference_document=(
            movement_in.reference_document.strip()
            if movement_in.reference_document
            else None
        ),
        remarks=movement_in.remarks.strip() if movement_in.remarks else None,
    )

    # Update Asset current location
    db_asset.office_id = to_office_id
    db_asset.section_id = to_section_id

    # Update Asset status based on movement type or explicit status
    if movement_in.new_status:
        db_asset.status = movement_in.new_status
    elif movement_in.movement_type == AssetMovementType.ISSUE:
        db_asset.status = AssetStatus.ISSUED
    elif movement_in.movement_type == AssetMovementType.RETURN:
        db_asset.status = AssetStatus.IN_STORE

    db.add(db_movement)

    try:
        db.commit()
        db.refresh(db_movement)
        return db_movement
    except Exception:
        db.rollback()
        raise


def get_asset_movements(db: Session, asset_id: int, page: int = 1):
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset:
        raise ValueError("Asset not found.")

    query = (
        db.query(AssetMovement)
        .filter(
            AssetMovement.asset_id == asset_id,
            AssetMovement.is_active == True,
        )
        .order_by(AssetMovement.movement_date.desc(), AssetMovement.id.desc())
    )

    return get_pagination_result(query, page)
