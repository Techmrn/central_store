import uuid
import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.financial_year import FinancialYear
from app.crud.asset import create_asset

from app.crud.category import create_category
from app.crud.financial_year import create_financial_year
from app.crud.item import create_item
from app.crud.office import create_office
from app.crud.opening_stock import create_opening_stock
from app.crud.unserviceable import (
    create_unserviceable_material,
    get_unserviceable_register_report,
    transition_asset_unserviceable_status,
    update_unserviceable_material_status,
)
from app.models.enums import (
    AssetMovementType,
    AssetStatus,
    Category_Type,
    UnserviceableStatus,
)
from app.schemas.asset import AssetCreate
from app.schemas.category import CategoryCreate
from app.schemas.financial_year import FinancialYearCreate
from app.schemas.item import ItemCreate
from app.schemas.office import OfficeCreate
from app.schemas.opening_stock import OpeningStockCreate
from app.schemas.unserviceable import (
    AssetUnserviceableUpdate,
    UnserviceableMaterialCreate,
    UnserviceableMaterialStatusUpdate,
)
from app.services.stock_service import (
    get_item_stock,
    get_item_unserviceable_stock,
    get_item_usable_stock,
    validate_stock_availability,
)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from app.models.office import OfficeType

from app.crud.unit import create_unit
from app.schemas.unit import UnitCreate

@pytest.fixture
def setup_unserviceable_data(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    # Setup Office
    office = create_office(db_session, OfficeCreate(name=f"Central Store Test Office {uid}", code=f"CST{uid}", office_type=OfficeType.BRANCH))

    # Setup Unit
    unit = create_unit(db_session, UnitCreate(name=f"Liters {uid}", symbol=f"L{uid}"))

    # Setup Financial Year
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    if not fy:
        fy = create_financial_year(
            db_session,
            FinancialYearCreate(
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
                is_active=True,
            ),
        )


    # Setup Categories
    mat_cat = create_category(db_session, CategoryCreate(name=f"Raw Material {uid}", code=f"RM{uid}", type=Category_Type.MATERIAL))
    asset_cat = create_category(db_session, CategoryCreate(name=f"IT Equipment {uid}", code=f"IT{uid}", type=Category_Type.ASSET))

    # Setup Items
    oil_item = create_item(
        db_session,
        ItemCreate(name=f"Lubricating Oil {uid}", code=f"OIL-{uid}", category_id=mat_cat.id, unit_id=unit.id),
    )
    pc_item = create_item(
        db_session,
        ItemCreate(name=f"Desktop Computer {uid}", code=f"PC-{uid}", category_id=asset_cat.id, unit_id=unit.id),
    )


    return {
        "office": office,
        "fy": fy,
        "mat_cat": mat_cat,
        "asset_cat": asset_cat,
        "unit": unit,
        "oil_item": oil_item,
        "pc_item": pc_item,
    }


def test_material_unserviceable_usable_stock_flow(db_session: Session, setup_unserviceable_data):
    data = setup_unserviceable_data
    oil_item = data["oil_item"]
    office = data["office"]
    fy = data["fy"]

    # 1. Opening Stock = 100
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=oil_item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # Verify initial stock
    assert get_item_stock(db_session, oil_item.id, office.id, fy.id) == 100.0
    assert get_item_unserviceable_stock(db_session, oil_item.id, office.id, fy.id) == 0.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy.id) == 100.0

    # 2. Mark 15 units as UNSERVICEABLE (creates ADJUSTMENT_OUT = 15)
    un_mat = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=oil_item.id,
            office_id=office.id,
            quantity=15.0,
            reason="Leaking drum",
            remarks="Stored in Bay B",
        ),
    )
    assert un_mat.status == UnserviceableStatus.UNSERVICEABLE
    assert get_item_stock(db_session, oil_item.id, office.id, fy.id) == 85.0
    assert get_item_unserviceable_stock(db_session, oil_item.id, office.id, fy.id) == 15.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy.id) == 85.0

    # 3. Stock availability check: 85 permitted, 86 rejected
    assert validate_stock_availability(db_session, oil_item.id, office.id, 85.0, fy.id) is True
    with pytest.raises(ValueError, match="Insufficient stock"):
        validate_stock_availability(db_session, oil_item.id, office.id, 86.0, fy.id)

    # 4. Repair 5 units out of 15 (creates ADJUSTMENT_IN = 5)
    update_unserviceable_material_status(
        db_session,
        unserviceable_id=un_mat.id,
        update_data=UnserviceableMaterialStatusUpdate(
            status=UnserviceableStatus.REPAIRED,
            quantity=5.0,
            remarks="5 units sealed and restored",
        ),
    )
    # 85 + 5 = 90 stock, remaining active unserviceable = 10
    assert get_item_stock(db_session, oil_item.id, office.id, fy.id) == 90.0
    assert get_item_unserviceable_stock(db_session, oil_item.id, office.id, fy.id) == 10.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy.id) == 90.0

    # 5. Condemn and Dispose another batch
    un_mat2 = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=oil_item.id,
            office_id=office.id,
            quantity=10.0,
            reason="Expired chemical component",
        ),
    )
    # Stock drops from 90 to 80
    assert get_item_stock(db_session, oil_item.id, office.id, fy.id) == 80.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy.id) == 80.0

    # Transition to CONDEMNED (no stock movement)
    update_unserviceable_material_status(
        db_session,
        unserviceable_id=un_mat2.id,
        update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.CONDEMNED),
    )
    assert get_item_stock(db_session, oil_item.id, office.id, fy.id) == 80.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy.id) == 80.0

    # Transition to DISPOSED (no second stock movement)
    update_unserviceable_material_status(
        db_session,
        unserviceable_id=un_mat2.id,
        update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.DISPOSED),
    )
    assert get_item_stock(db_session, oil_item.id, office.id, fy.id) == 80.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy.id) == 80.0

    # 6. Verify Unserviceable Register report
    report = get_unserviceable_register_report(db_session, office_id=office.id, asset_or_material="MATERIAL")
    assert report["total"] >= 2


def test_asset_lifecycle_and_issue_protection(db_session: Session, setup_unserviceable_data):
    data = setup_unserviceable_data
    pc_item = data["pc_item"]
    office = data["office"]
    uid = uuid.uuid4().hex[:6]

    # 1. Create Asset IN_STORE
    asset = create_asset(
        db_session,
        AssetCreate(
            asset_no=f"PC-{uid}",
            item_id=pc_item.id,
            serial_no=f"SN-{uid}",
            office_id=office.id,
        ),
    )
    assert asset.status == AssetStatus.IN_STORE

    # 2. Asset becomes DAMAGED
    asset = transition_asset_unserviceable_status(
        db_session,
        asset_id=asset.id,
        update_data=AssetUnserviceableUpdate(
            status=AssetStatus.DAMAGED,
            reason="Motherboard short circuit",
        ),
    )
    assert asset.status == AssetStatus.DAMAGED
    assert asset.movements[-1].movement_type == AssetMovementType.UNSERVICEABLE

    # 3. Verify asset appears in Unserviceable Register
    report = get_unserviceable_register_report(db_session, office_id=office.id, asset_or_material="ASSET")
    assert report["total"] >= 1
    asset_entry = next((item for item in report["items"] if item.asset_no == asset.asset_no), None)
    assert asset_entry is not None
    assert asset_entry.status == "DAMAGED"

    # 4. Move DAMAGED -> UNDER_REPAIR
    asset = transition_asset_unserviceable_status(
        db_session,
        asset_id=asset.id,
        update_data=AssetUnserviceableUpdate(
            status=AssetStatus.UNDER_REPAIR,
            reason="Sent to vendor for repair",
        ),
    )
    assert asset.status == AssetStatus.UNDER_REPAIR
    assert asset.movements[-1].movement_type == AssetMovementType.REPAIR

    # 5. Return to service UNDER_REPAIR -> IN_STORE
    asset = transition_asset_unserviceable_status(
        db_session,
        asset_id=asset.id,
        update_data=AssetUnserviceableUpdate(
            status=AssetStatus.IN_STORE,
            reason="Repair completed successfully",
        ),
    )
    assert asset.status == AssetStatus.IN_STORE
    assert asset.movements[-1].movement_type == AssetMovementType.RETURN


    # 6. Condemnation flow: IN_STORE -> DAMAGED -> CONDEMNED -> E_WASTE -> DISPOSED
    asset = transition_asset_unserviceable_status(
        db_session,
        asset_id=asset.id,
        update_data=AssetUnserviceableUpdate(status=AssetStatus.DAMAGED, reason="Fire damage"),
    )
    asset = transition_asset_unserviceable_status(
        db_session,
        asset_id=asset.id,
        update_data=AssetUnserviceableUpdate(status=AssetStatus.CONDEMNED, reason="Beyond economical repair"),
    )
    assert asset.status == AssetStatus.CONDEMNED

    asset = transition_asset_unserviceable_status(
        db_session,
        asset_id=asset.id,
        update_data=AssetUnserviceableUpdate(status=AssetStatus.E_WASTE, reason="Transferred to E-Waste store"),
    )
    assert asset.status == AssetStatus.E_WASTE

    asset = transition_asset_unserviceable_status(
        db_session,
        asset_id=asset.id,
        update_data=AssetUnserviceableUpdate(status=AssetStatus.DISPOSED, reason="Recycled via authorized vendor"),
    )
    assert asset.status == AssetStatus.DISPOSED

    # 7. Reject invalid transition DISPOSED -> IN_STORE
    with pytest.raises(ValueError, match="Invalid asset status transition"):
        transition_asset_unserviceable_status(
            db_session,
            asset_id=asset.id,
            update_data=AssetUnserviceableUpdate(status=AssetStatus.IN_STORE, reason="Attempt restore"),
        )


def test_financial_year_unserviceable_carry_over(db_session: Session, setup_unserviceable_data):
    data = setup_unserviceable_data
    office = data["office"]
    fy1 = data["fy"]
    uid = uuid.uuid4().hex[:6]

    oil_item = create_item(
        db_session,
        ItemCreate(
            name=f"Carry Over Oil {uid}",
            code=f"CO-OIL-{uid}",
            category_id=data["mat_cat"].id,
            unit_id=data["unit"].id,
        ),
    )

    # Opening stock FY 1 = 100
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy1.id,
            item_id=oil_item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )


    # Mark 15 unserviceable
    create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy1.id,
            item_id=oil_item.id,
            office_id=office.id,
            quantity=15.0,
            reason="Worn out",
        ),
    )

    # Next Financial Year 2040-2041
    fy2 = db_session.query(FinancialYear).filter(FinancialYear.start_date == date(2040, 4, 1)).first()
    if not fy2:
        fy2 = FinancialYear(
            year_name="2040-41",
            start_date=date(2040, 4, 1),
            end_date=date(2041, 3, 31),
            is_current=True,
            is_closed=False,
        )
        db_session.add(fy2)
        db_session.commit()
        db_session.refresh(fy2)

    # Carry forward opening stock
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy2.id,
            item_id=oil_item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # In FY1, stock is 85 and active unserviceable is 15
    assert get_item_stock(db_session, oil_item.id, office.id, fy1.id) == 85.0
    assert get_item_unserviceable_stock(db_session, oil_item.id, office.id, fy1.id) == 15.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy1.id) == 85.0

    # In FY2, stock is 100, usable stock is 100, and unserviceable is 0 (isolated)
    assert get_item_stock(db_session, oil_item.id, office.id, fy2.id) == 100.0
    assert get_item_usable_stock(db_session, oil_item.id, office.id, fy2.id) == 100.0
    assert get_item_unserviceable_stock(db_session, oil_item.id, office.id, fy2.id) == 0.0


