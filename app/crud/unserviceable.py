from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.asset import Asset
from app.models.asset_movement import AssetMovement
from app.models.category import Category
from app.models.enums import AssetMovementType, AssetStatus, Category_Type, MovementType, UnserviceableStatus
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.office import Office
from app.models.section import Section
from app.models.stock_movement import StockMovement
from app.models.unserviceable_material import UnserviceableMaterial
from app.schemas.unserviceable import (
    AssetUnserviceableUpdate,
    UnserviceableMaterialCreate,
    UnserviceableMaterialStatusUpdate,
    UnserviceableRegisterItem,
)
from app.services.scope_service import get_stock_office_id
from app.services.stock_service import get_item_usable_stock, validate_stock_availability

ALLOWED_MATERIAL_TRANSITIONS = {
    UnserviceableStatus.UNSERVICEABLE: {
        UnserviceableStatus.UNDER_REPAIR,
        UnserviceableStatus.REPAIRED,
        UnserviceableStatus.CONDEMNED,
        UnserviceableStatus.DISPOSED,
    },
    UnserviceableStatus.UNDER_REPAIR: {
        UnserviceableStatus.REPAIRED,
        UnserviceableStatus.CONDEMNED,
        UnserviceableStatus.DISPOSED,
    },
    UnserviceableStatus.REPAIRED: set(),
    UnserviceableStatus.CONDEMNED: {
        UnserviceableStatus.DISPOSED,
    },
    UnserviceableStatus.DISPOSED: set(),
}

ALLOWED_ASSET_TRANSITIONS = {
    AssetStatus.IN_STORE: {AssetStatus.DAMAGED, AssetStatus.UNDER_REPAIR, AssetStatus.CONDEMNED, AssetStatus.ISSUED},
    AssetStatus.ISSUED: {AssetStatus.DAMAGED, AssetStatus.UNDER_REPAIR, AssetStatus.IN_STORE},
    AssetStatus.DAMAGED: {AssetStatus.UNDER_REPAIR, AssetStatus.IN_STORE, AssetStatus.CONDEMNED},
    AssetStatus.UNDER_REPAIR: {AssetStatus.IN_STORE, AssetStatus.ISSUED, AssetStatus.CONDEMNED},
    AssetStatus.CONDEMNED: {AssetStatus.E_WASTE, AssetStatus.DISPOSED},
    AssetStatus.E_WASTE: {AssetStatus.DISPOSED},
    AssetStatus.DISPOSED: set(),  # Terminal state
}


def create_unserviceable_material(
    db: Session,
    data: UnserviceableMaterialCreate,
    user_id: Optional[int] = None,
    office_id: Optional[int] = None,
) -> UnserviceableMaterial:
    # 1. Authoritative Office validation
    target_office_id = office_id if office_id is not None else data.office_id
    if office_id is not None and data.office_id != office_id:
        raise ValueError(f"Office mismatch: requested office {data.office_id} does not match authorized office {office_id}.")

    # Validate Item
    item = db.query(Item).filter(Item.id == data.item_id, Item.is_active == True).first()
    if not item:
        raise ValueError(f"Item ID {data.item_id} not found.")

    # Validate Office
    office = db.query(Office).filter(Office.id == target_office_id, Office.is_active == True).first()
    if not office:
        raise ValueError(f"Office ID {target_office_id} not found.")

    # Validate Financial Year
    fy = db.query(FinancialYear).filter(FinancialYear.id == data.financial_year_id).first()
    if not fy:
        raise ValueError(f"Financial Year ID {data.financial_year_id} not found.")
    if fy.is_closed:
        raise ValueError(f"Financial Year {fy.year_name} is closed.")

    # Validate Section
    if data.section_id:
        section = db.query(Section).filter(Section.id == data.section_id, Section.is_active == True).first()
        if not section or section.office_id != target_office_id:
            raise ValueError(f"Invalid section ID {data.section_id} for office ID {target_office_id}.")

    # Validate quantity
    if data.quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")

    # 2. Validate against available usable stock in this FY and Office
    validate_stock_availability(
        db=db,
        item_id=data.item_id,
        office_id=target_office_id,
        required_qty=data.quantity,
        financial_year_id=data.financial_year_id,
    )

    try:
        rec = UnserviceableMaterial(
            financial_year_id=data.financial_year_id,
            item_id=data.item_id,
            office_id=target_office_id,
            section_id=data.section_id,
            quantity=data.quantity,
            reason=data.reason,
            status=UnserviceableStatus.UNSERVICEABLE,
            reference_no=data.reference_no,
            remarks=data.remarks,
            reported_by_id=user_id,
        )
        db.add(rec)
        db.flush()

        sm = StockMovement(
            financial_year_id=rec.financial_year_id,
            item_id=rec.item_id,
            office_id=get_stock_office_id(db, rec.office_id),
            section_id=rec.section_id,
            movement_type=MovementType.ADJUSTMENT_OUT,
            quantity_in=0.0,
            quantity_out=rec.quantity,
            reference_type="UNSERVICEABLE",
            reference_id=rec.id,
            reference_no=rec.reference_no or f"UNS-{rec.id}",
            remarks=rec.reason,
        )
        db.add(sm)
        db.commit()
        db.refresh(rec)
        return rec
    except Exception:
        db.rollback()
        raise


def update_unserviceable_material_status(
    db: Session,
    unserviceable_id: int,
    update_data: UnserviceableMaterialStatusUpdate,
    user_id: Optional[int] = None,
    office_id: Optional[int] = None,
) -> UnserviceableMaterial:
    query = db.query(UnserviceableMaterial).filter(
        UnserviceableMaterial.id == unserviceable_id,
        UnserviceableMaterial.is_active == True,
    )
    if office_id is not None:
        query = query.filter(UnserviceableMaterial.office_id == office_id)

    rec = query.first()
    if not rec:
        raise ValueError(f"Unserviceable material record ID {unserviceable_id} not found.")

    target_status = update_data.status
    current_status = rec.status

    allowed_targets = ALLOWED_MATERIAL_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_targets:
        raise ValueError(f"Invalid status transition from {current_status.value} to {target_status.value}.")

    affect_qty = update_data.quantity if update_data.quantity is not None else float(rec.quantity)
    if affect_qty <= 0:
        raise ValueError("Quantity must be greater than 0.")
    if affect_qty > float(rec.quantity):
        raise ValueError(f"Quantity ({affect_qty}) cannot exceed current unserviceable record quantity ({rec.quantity}).")

    try:
        # If partial quantity status change
        if affect_qty < float(rec.quantity):
            rec.quantity = float(rec.quantity) - affect_qty
            new_rec = UnserviceableMaterial(
                financial_year_id=rec.financial_year_id,
                item_id=rec.item_id,
                office_id=rec.office_id,
                section_id=rec.section_id,
                quantity=affect_qty,
                reason=rec.reason,
                status=target_status,
                reference_no=rec.reference_no,
                remarks=update_data.remarks or rec.remarks,
                reported_by_id=user_id or rec.reported_by_id,
            )
            db.add(new_rec)
            db.flush()
            target_obj = new_rec
        else:
            rec.status = target_status
            if update_data.remarks:
                rec.remarks = update_data.remarks
            db.flush()
            target_obj = rec

        # When transitioning to REPAIRED -> create ADJUSTMENT_IN with idempotency check
        if target_status == UnserviceableStatus.REPAIRED:
            existing_sm = db.query(StockMovement).filter(
                StockMovement.reference_type == "UNSERVICEABLE_REPAIR_RETURN",
                StockMovement.reference_id == target_obj.id,
                StockMovement.is_active == True,
            ).first()
            if existing_sm:
                raise ValueError(f"Repair return movement already recorded for unserviceable material ID {target_obj.id}.")

            sm = StockMovement(
                financial_year_id=target_obj.financial_year_id,
                item_id=target_obj.item_id,
                office_id=get_stock_office_id(db, target_obj.office_id),
                section_id=target_obj.section_id,
                movement_type=MovementType.ADJUSTMENT_IN,
                quantity_in=affect_qty,
                quantity_out=0.0,
                reference_type="UNSERVICEABLE_REPAIR_RETURN",
                reference_id=target_obj.id,
                reference_no=target_obj.reference_no or f"UNS-REPAIR-{target_obj.id}",
                remarks=f"Repaired material restored to stock: {target_obj.reason}",
            )
            db.add(sm)

        # For UNDER_REPAIR, CONDEMNED, DISPOSED -> NO stock movements

        db.commit()
        db.refresh(target_obj)
        return target_obj
    except Exception:
        db.rollback()
        raise


def transition_asset_unserviceable_status(
    db: Session,
    asset_id: int,
    update_data: AssetUnserviceableUpdate,
    user_id: Optional[int] = None,
    office_id: Optional[int] = None,
) -> Asset:
    query = db.query(Asset).filter(Asset.id == asset_id, Asset.is_active == True)
    if office_id is not None:
        query = query.filter(Asset.office_id == office_id)

    asset = query.first()
    if not asset:
        raise ValueError(f"Asset ID {asset_id} not found.")

    current_status = asset.status
    target_status = update_data.status

    if target_status not in ALLOWED_ASSET_TRANSITIONS.get(current_status, set()):
        raise ValueError(
            f"Invalid asset status transition from '{current_status.value}' to '{target_status.value}'."
        )

    # Determine AssetMovementType
    if target_status == AssetStatus.DAMAGED:
        mv_type = AssetMovementType.UNSERVICEABLE
    elif target_status == AssetStatus.UNDER_REPAIR:
        mv_type = AssetMovementType.REPAIR
    elif target_status in (AssetStatus.IN_STORE, AssetStatus.ISSUED):
        mv_type = AssetMovementType.RETURN
    elif target_status == AssetStatus.CONDEMNED:
        mv_type = AssetMovementType.CONDEMNATION
    else:
        mv_type = AssetMovementType.DISPOSAL

    from_office_id = asset.office_id
    from_section_id = asset.section_id

    # Update asset status
    asset.status = target_status
    if update_data.remarks:
        asset.remarks = update_data.remarks

    # Create AssetMovement audit log
    am = AssetMovement(
        asset_id=asset.id,
        movement_type=mv_type,
        from_office_id=from_office_id,
        from_section_id=from_section_id,
        to_office_id=from_office_id,
        to_section_id=from_section_id,
        reference_document=f"STATUS_CHANGE_{target_status.value}",
        movement_date=func.now(),
        remarks=f"Reason: {update_data.reason}. Remarks: {update_data.remarks or ''}",
    )
    db.add(am)
    db.commit()
    db.refresh(asset)
    return asset


def get_unserviceable_register_report(
    db: Session,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    item_id: Optional[int] = None,
    category_id: Optional[int] = None,
    asset_or_material: Optional[str] = None,  # "ASSET" or "MATERIAL"
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
):
    results = []
    clean_type = (asset_or_material or "").strip().upper()
    clean_status = (status_filter or "").strip().upper()
    clean_search = (search or "").strip()

    valid_asset_statuses = {s.value for s in AssetStatus}
    valid_material_statuses = {s.value for s in UnserviceableStatus}

    # 1. Unserviceable Assets Query
    include_assets = clean_type in ("", "ALL", "ASSET")
    if include_assets and (not clean_status or clean_status in valid_asset_statuses):
        asset_query = (
            db.query(Asset, Item, Category, Office, Section)
            .join(Item, Asset.item_id == Item.id)
            .join(Category, Item.category_id == Category.id)
            .join(Office, Asset.office_id == Office.id)
            .outerjoin(Section, Asset.section_id == Section.id)
            .filter(
                Asset.is_active == True,
                Asset.status.in_([
                    AssetStatus.DAMAGED,
                    AssetStatus.UNDER_REPAIR,
                    AssetStatus.CONDEMNED,
                    AssetStatus.E_WASTE,
                    AssetStatus.DISPOSED,
                ]),
            )
        )

        if office_id is not None:
            asset_query = asset_query.filter(Asset.office_id == office_id)
        if section_id is not None:
            asset_query = asset_query.filter(Asset.section_id == section_id)
        if item_id is not None:
            asset_query = asset_query.filter(Asset.item_id == item_id)
        if category_id is not None:
            asset_query = asset_query.filter(Item.category_id == category_id)
        if clean_status:
            asset_query = asset_query.filter(Asset.status == clean_status)

        if clean_search:
            asset_query = asset_query.filter(
                or_(
                    Item.name.ilike(f"%{clean_search}%"),
                    Item.code.ilike(f"%{clean_search}%"),
                    Category.name.ilike(f"%{clean_search}%"),
                    Asset.asset_no.ilike(f"%{clean_search}%"),
                    Asset.serial_no.ilike(f"%{clean_search}%"),
                    Asset.remarks.ilike(f"%{clean_search}%"),
                )
            )

        for asset, item, category, office, section in asset_query.all():
            make_val = asset.asset_detail.make if asset.asset_detail else None
            model_val = asset.asset_detail.model if asset.asset_detail else None

            # Find latest movement for date / reason
            latest_mv = (
                db.query(AssetMovement)
                .filter(AssetMovement.asset_id == asset.id)
                .order_by(AssetMovement.id.desc())
                .first()
            )
            date_rep = latest_mv.movement_date if latest_mv else asset.created_at
            reason_str = latest_mv.remarks if (latest_mv and latest_mv.remarks) else (asset.remarks or asset.status.value)

            results.append(
                UnserviceableRegisterItem(
                    id=asset.id,
                    register_type="ASSET",
                    asset_id=asset.id,
                    asset_no=asset.asset_no,
                    serial_no=asset.serial_no,
                    make=make_val,
                    model=model_val,
                    item_id=item.id,
                    item_name=item.name,
                    item_code=item.code,
                    category_name=category.name,
                    unit_name=item.unit.name if item.unit else None,
                    office_id=office.id,
                    office_name=office.name,
                    section_id=section.id if section else None,
                    section_name=section.name if section else None,
                    quantity=1.0,
                    status=asset.status.value,
                    date_reported=date_rep,
                    reason=reason_str,
                    remarks=asset.remarks,
                    reference_no=asset.asset_no,
                    reported_by_name=None,
                )
            )

    # 2. Unserviceable Materials Query
    include_materials = clean_type in ("", "ALL", "MATERIAL")
    if include_materials and (not clean_status or clean_status in valid_material_statuses):
        mat_query = (
            db.query(UnserviceableMaterial, Item, Category, Office, Section)
            .join(Item, UnserviceableMaterial.item_id == Item.id)
            .join(Category, Item.category_id == Category.id)
            .join(Office, UnserviceableMaterial.office_id == Office.id)
            .outerjoin(Section, UnserviceableMaterial.section_id == Section.id)
            .filter(UnserviceableMaterial.is_active == True)
        )

        if financial_year_id is not None:
            mat_query = mat_query.filter(UnserviceableMaterial.financial_year_id == financial_year_id)
        if office_id is not None:
            mat_query = mat_query.filter(UnserviceableMaterial.office_id == office_id)
        if section_id is not None:
            mat_query = mat_query.filter(UnserviceableMaterial.section_id == section_id)
        if item_id is not None:
            mat_query = mat_query.filter(UnserviceableMaterial.item_id == item_id)
        if category_id is not None:
            mat_query = mat_query.filter(Item.category_id == category_id)
        if clean_status:
            mat_query = mat_query.filter(UnserviceableMaterial.status == clean_status)

        if clean_search:
            mat_query = mat_query.filter(
                or_(
                    Item.name.ilike(f"%{clean_search}%"),
                    Item.code.ilike(f"%{clean_search}%"),
                    Category.name.ilike(f"%{clean_search}%"),
                    UnserviceableMaterial.reference_no.ilike(f"%{clean_search}%"),
                    UnserviceableMaterial.reason.ilike(f"%{clean_search}%"),
                    UnserviceableMaterial.remarks.ilike(f"%{clean_search}%"),
                )
            )

        for mat, item, category, office, section in mat_query.all():
            user_name = mat.reported_by.full_name if mat.reported_by else None
            results.append(
                UnserviceableRegisterItem(
                    id=mat.id,
                    register_type="MATERIAL",
                    asset_id=None,
                    asset_no=None,
                    serial_no=None,
                    make=None,
                    model=None,
                    item_id=item.id,
                    item_name=item.name,
                    item_code=item.code,
                    category_name=category.name,
                    unit_name=item.unit.name if item.unit else None,
                    office_id=office.id,
                    office_name=office.name,
                    section_id=section.id if section else None,
                    section_name=section.name if section else None,
                    quantity=float(mat.quantity),
                    status=mat.status.value,
                    date_reported=mat.date_reported,
                    reason=mat.reason,
                    remarks=mat.remarks,
                    reference_no=mat.reference_no,
                    reported_by_name=user_name,
                )
            )

    # Sort results by date_reported descending
    results.sort(key=lambda x: x.date_reported, reverse=True)

    # Manual pagination over combined list
    page_size = 25
    total_count = len(results)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = results[start:end]

    return {
        "items": page_items,
        "total": total_count,
        "page": page,
        "size": page_size,
        "pages": total_pages,
    }
