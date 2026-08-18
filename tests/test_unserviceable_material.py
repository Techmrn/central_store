import uuid
import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.crud.category import create_category
from app.crud.financial_year import create_financial_year
from app.crud.item import create_item
from app.crud.office import create_office
from app.crud.opening_stock import create_opening_stock
from app.crud.section import create_section
from app.crud.unit import create_unit
from app.crud.unserviceable import (
    create_unserviceable_material,
    get_unserviceable_register_report,
    update_unserviceable_material_status,
)
from app.models.enums import (
    Category_Type,
    MovementType,
    UnserviceableStatus,
)
from app.models.financial_year import FinancialYear
from app.models.office import OfficeType
from app.models.stock_movement import StockMovement
from app.models.unserviceable_material import UnserviceableMaterial
from app.models.user import User
from app.schemas.category import CategoryCreate
from app.schemas.financial_year import FinancialYearCreate
from app.schemas.item import ItemCreate
from app.schemas.office import OfficeCreate
from app.schemas.opening_stock import OpeningStockCreate
from app.schemas.sections import SectionCreate
from app.schemas.unit import UnitCreate
from app.schemas.unserviceable import (
    UnserviceableMaterialCreate,
    UnserviceableMaterialStatusUpdate,
)
from app.services.stock_service import (
    get_item_stock,
    get_item_unserviceable_stock,
    get_item_usable_stock,
)
from app.routers.ui.unserviceable import get_available_material_items_for_office, get_unserviceable_register_ui


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_test_fy(db: Session, start_year: int, is_current: bool = False, is_closed: bool = False):
    year_name = f"{start_year}-{str(start_year + 1)[-2:]}"
    fy = db.query(FinancialYear).filter(FinancialYear.year_name == year_name).first()
    if not fy:
        fy = FinancialYear(
            year_name=year_name,
            start_date=date(start_year, 4, 1),
            end_date=date(start_year + 1, 3, 31),
            is_current=is_current,
            is_closed=is_closed,
        )
        db.add(fy)
        db.commit()
        db.refresh(fy)
    else:
        fy.is_closed = is_closed
        if is_current:
            fy.is_current = True
        db.commit()
        db.refresh(fy)
    return fy


@pytest.fixture
def fixture_setup(db_session: Session):
    uid = uuid.uuid4().hex[:6]

    # Offices
    office_a = create_office(db_session, OfficeCreate(name=f"Office A {uid}", code=f"OA{uid}", office_type=OfficeType.GCP))
    office_b = create_office(db_session, OfficeCreate(name=f"Office B {uid}", code=f"OB{uid}", office_type=OfficeType.GCP))

    # Sections
    sec_a = create_section(db_session, SectionCreate(name=f"Sec A {uid}", code=f"SA{uid}", office_id=office_a.id))
    sec_b = create_section(db_session, SectionCreate(name=f"Sec B {uid}", code=f"SB{uid}", office_id=office_b.id))

    # Unit & Categories
    unit = create_unit(db_session, UnitCreate(name=f"Pieces {uid}", symbol=f"PCS{uid}"))
    cat = create_category(db_session, CategoryCreate(name=f"Consumables {uid}", code=f"CON{uid}", type=Category_Type.MATERIAL))

    # Items
    item_x = create_item(db_session, ItemCreate(name=f"Item X {uid}", code=f"IX-{uid}", category_id=cat.id, unit_id=unit.id))
    item_y = create_item(db_session, ItemCreate(name=f"Item Y {uid}", code=f"IY-{uid}", category_id=cat.id, unit_id=unit.id))

    # Financial Years
    fy1 = get_or_create_test_fy(db_session, 2035, is_current=False, is_closed=False)
    fy2 = get_or_create_test_fy(db_session, 2036, is_current=True, is_closed=False)

    return {
        "office_a": office_a,
        "office_b": office_b,
        "sec_a": sec_a,
        "sec_b": sec_b,
        "unit": unit,
        "cat": cat,
        "item_x": item_x,
        "item_y": item_y,
        "fy1": fy1,
        "fy2": fy2,
        "uid": uid,
    }


# -------------------------------------------------------------------------
# Test 1 — Financial-year stock isolation
# -------------------------------------------------------------------------
def test_1_financial_year_stock_isolation(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy1 = f["fy1"]
    fy2 = f["fy2"]

    # FY1 = 100
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy1.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # FY2 = 20
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy2.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("20.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy1.id) == 100.0
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy2.id) == 20.0


# -------------------------------------------------------------------------
# Test 2 — Office stock isolation
# -------------------------------------------------------------------------
def test_2_office_stock_isolation(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office_a = f["office_a"]
    office_b = f["office_b"]
    fy = f["fy2"]

    # Office A = 100, Office B = 5
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office_a.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office_b.id,
            quantity=Decimal("5.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    assert get_item_stock(db_session, item_id=item.id, office_id=office_b.id, financial_year_id=fy.id) == 5.0
    assert get_item_stock(db_session, item_id=item.id, office_id=office_a.id, financial_year_id=fy.id) == 100.0


# -------------------------------------------------------------------------
# Test 3 — Unserviceable entry creates ADJUSTMENT_OUT
# -------------------------------------------------------------------------
def test_3_unserviceable_entry_creates_adjustment_out(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    un_mat = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=10.0,
            reason="Damaged seal",
        ),
        office_id=office.id,
    )

    assert un_mat.quantity == 10.0
    assert un_mat.status == UnserviceableStatus.UNSERVICEABLE

    # Check exactly one StockMovement ADJUSTMENT_OUT
    movements = db_session.query(StockMovement).filter(
        StockMovement.reference_type == "UNSERVICEABLE",
        StockMovement.reference_id == un_mat.id,
        StockMovement.is_active == True,
    ).all()
    assert len(movements) == 1
    sm = movements[0]
    assert sm.movement_type == MovementType.ADJUSTMENT_OUT
    assert float(sm.quantity_out) == 10.0
    assert sm.office_id == office.id
    assert sm.financial_year_id == fy.id

    # Stock becomes 90
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 90.0


# -------------------------------------------------------------------------
# Test 4 — Previous FY stock cannot authorize current FY unserviceable entry
# -------------------------------------------------------------------------
def test_4_previous_fy_stock_cannot_authorize_current_fy(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy1 = f["fy1"]
    fy2 = f["fy2"]

    # FY1 stock = 100, FY2 stock = 0
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy1.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy2.id) == 0.0

    # Attempt FY2 unserviceable = 1 must fail
    with pytest.raises(ValueError, match="Insufficient stock"):
        create_unserviceable_material(
            db_session,
            UnserviceableMaterialCreate(
                financial_year_id=fy2.id,
                item_id=item.id,
                office_id=office.id,
                quantity=1.0,
                reason="Attempting cross-FY stock declaration",
            ),
            office_id=office.id,
        )


# -------------------------------------------------------------------------
# Test 5 — Usable stock is not double-subtracted
# -------------------------------------------------------------------------
def test_5_usable_stock_is_not_double_subtracted(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=10.0,
            reason="Expired batch",
        ),
        office_id=office.id,
    )

    current_stock = get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id)
    usable_stock = get_item_usable_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id)
    unserviceable_qty = get_item_unserviceable_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id)

    assert current_stock == 90.0
    assert usable_stock == 90.0
    assert unserviceable_qty == 10.0


# -------------------------------------------------------------------------
# Test 6 — Disposal creates no second stock adjustment
# -------------------------------------------------------------------------
def test_6_disposal_creates_no_second_stock_adjustment(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    un_mat = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=10.0,
            reason="Chemical degradation",
        ),
        office_id=office.id,
    )

    # Transition to DISPOSED
    update_unserviceable_material_status(
        db_session,
        unserviceable_id=un_mat.id,
        update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.DISPOSED),
        office_id=office.id,
    )

    # Verify no DISPOSAL reference movement exists for this unserviceable material
    disp_movements = db_session.query(StockMovement).filter(
        StockMovement.reference_type == "DISPOSAL",
        StockMovement.reference_id == un_mat.id,
        StockMovement.is_active == True,
    ).all()
    assert len(disp_movements) == 0

    # Stock remains 90
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 90.0
    assert get_item_usable_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 90.0


# -------------------------------------------------------------------------
# Test 7 — Repair return creates ADJUSTMENT_IN
# -------------------------------------------------------------------------
def test_7_repair_return_creates_adjustment_in(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    un_mat = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=10.0,
            reason="Defective valve",
        ),
        office_id=office.id,
    )
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 90.0

    # Repair 5
    target_rec = update_unserviceable_material_status(
        db_session,
        unserviceable_id=un_mat.id,
        update_data=UnserviceableMaterialStatusUpdate(
            status=UnserviceableStatus.REPAIRED,
            quantity=5.0,
            remarks="Valves replaced and tested",
        ),
        office_id=office.id,
    )

    repair_movements = db_session.query(StockMovement).filter(
        StockMovement.reference_type == "UNSERVICEABLE_REPAIR_RETURN",
        StockMovement.reference_id == target_rec.id,
        StockMovement.is_active == True,
    ).all()
    assert len(repair_movements) == 1
    rm = repair_movements[0]
    assert rm.movement_type == MovementType.ADJUSTMENT_IN
    assert float(rm.quantity_in) == 5.0

    # Stock becomes 95
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 95.0


# -------------------------------------------------------------------------
# Test 8 — Repair return is idempotent
# -------------------------------------------------------------------------
def test_8_repair_return_is_idempotent(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    un_mat = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=10.0,
            reason="Minor defects",
        ),
        office_id=office.id,
    )

    # Transition full quantity to REPAIRED
    target_rec = update_unserviceable_material_status(
        db_session,
        unserviceable_id=un_mat.id,
        update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.REPAIRED),
        office_id=office.id,
    )
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 100.0

    # Attempting status transition from terminal REPAIRED state is rejected
    with pytest.raises(ValueError, match="Invalid status transition"):
        update_unserviceable_material_status(
            db_session,
            unserviceable_id=target_rec.id,
            update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.REPAIRED),
            office_id=office.id,
        )

    # Stock remains 100, not double-restored
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 100.0


# -------------------------------------------------------------------------
# Test 9 — Partial disposal creates no additional stock deduction
# -------------------------------------------------------------------------
def test_9_partial_disposal_creates_no_additional_stock_deduction(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    un_mat = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=10.0,
            reason="Unusable batch",
        ),
        office_id=office.id,
    )
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 90.0

    # Dispose partial 5
    disp_rec = update_unserviceable_material_status(
        db_session,
        unserviceable_id=un_mat.id,
        update_data=UnserviceableMaterialStatusUpdate(
            status=UnserviceableStatus.DISPOSED,
            quantity=5.0,
            remarks="5 scrapped",
        ),
        office_id=office.id,
    )

    # Verify 5 remains unserviceable and 5 becomes disposed
    db_session.refresh(un_mat)
    assert float(un_mat.quantity) == 5.0
    assert un_mat.status == UnserviceableStatus.UNSERVICEABLE
    assert float(disp_rec.quantity) == 5.0
    assert disp_rec.status == UnserviceableStatus.DISPOSED

    # No additional movements created, stock stays 90
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy.id) == 90.0


# -------------------------------------------------------------------------
# Test 10 — Office security (cross-office rejection & tampering)
# -------------------------------------------------------------------------
def test_10_office_security(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office_a = f["office_a"]
    office_b = f["office_b"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office_b.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # User from Office A tries to declare material for Office B
    with pytest.raises(ValueError, match="Office mismatch"):
        create_unserviceable_material(
            db_session,
            UnserviceableMaterialCreate(
                financial_year_id=fy.id,
                item_id=item.id,
                office_id=office_b.id,
                quantity=5.0,
                reason="Unauthorized attempt",
            ),
            office_id=office_a.id,
        )

    # Create unserviceable in Office B
    un_b = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office_b.id,
            quantity=5.0,
            reason="Office B unserviceable",
        ),
        office_id=office_b.id,
    )

    # User from Office A tries to update status of Office B record
    with pytest.raises(ValueError, match="not found"):
        update_unserviceable_material_status(
            db_session,
            unserviceable_id=un_b.id,
            update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.UNDER_REPAIR),
            office_id=office_a.id,
        )


# -------------------------------------------------------------------------
# Test 11 — Office-scoped item dropdown
# -------------------------------------------------------------------------
def test_11_office_scoped_item_dropdown(db_session: Session, fixture_setup):
    f = fixture_setup
    item_x = f["item_x"]
    item_y = f["item_y"]
    office_a = f["office_a"]
    office_b = f["office_b"]
    fy = f["fy2"]

    # Office A has Item X = 50
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item_x.id,
            office_id=office_a.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # Office B has Item Y = 100
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item_y.id,
            office_id=office_b.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # Fetch available items for Office A
    items_a = get_available_material_items_for_office(
        db=db_session,
        office_id=office_a.id,
        financial_year_id=fy.id,
    )
    ids_a = [itm["id"] for itm in items_a]

    assert item_x.id in ids_a
    assert item_y.id not in ids_a


# -------------------------------------------------------------------------
# Test 12 — Section security (cross-office section rejection)
# -------------------------------------------------------------------------
def test_12_section_security(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office_a = f["office_a"]
    sec_b = f["sec_b"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office_a.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # User from Office A specifies section belonging to Office B
    with pytest.raises(ValueError, match="Invalid section ID"):
        create_unserviceable_material(
            db_session,
            UnserviceableMaterialCreate(
                financial_year_id=fy.id,
                item_id=item.id,
                office_id=office_a.id,
                section_id=sec_b.id,
                quantity=5.0,
                reason="Cross-office section attack",
            ),
            office_id=office_a.id,
        )


# -------------------------------------------------------------------------
# Additional Edge Case Assertions (Closed FY, Nonexistent FY, Invalid Quantities)
# -------------------------------------------------------------------------
def test_edge_cases_and_validations(db_session: Session, fixture_setup):
    f = fixture_setup
    item = f["item_x"]
    office = f["office_a"]
    fy = f["fy2"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # Closed FY validation
    closed_fy = get_or_create_test_fy(db_session, 2018, is_current=False, is_closed=True)
    with pytest.raises(ValueError, match="closed"):
        create_unserviceable_material(
            db_session,
            UnserviceableMaterialCreate(
                financial_year_id=closed_fy.id,
                item_id=item.id,
                office_id=office.id,
                quantity=1.0,
                reason="Closed FY attempt",
            ),
            office_id=office.id,
        )

    # Nonexistent FY
    with pytest.raises(ValueError, match="Financial Year ID 999999 not found"):
        create_unserviceable_material(
            db_session,
            UnserviceableMaterialCreate(
                financial_year_id=999999,
                item_id=item.id,
                office_id=office.id,
                quantity=1.0,
                reason="Invalid FY",
            ),
            office_id=office.id,
        )

    # Zero/negative quantity validation
    with pytest.raises(ValueError, match="Quantity"):
        create_unserviceable_material(
            db_session,
            UnserviceableMaterialCreate.model_construct(
                financial_year_id=fy.id,
                item_id=item.id,
                office_id=office.id,
                quantity=-5.0,
                reason="Negative qty",
            ),
            office_id=office.id,
        )

    # Quantity exceeding stock
    with pytest.raises(ValueError, match="Insufficient stock"):
        create_unserviceable_material(
            db_session,
            UnserviceableMaterialCreate(
                financial_year_id=fy.id,
                item_id=item.id,
                office_id=office.id,
                quantity=100.0,
                reason="Too much qty",
            ),
            office_id=office.id,
        )


# -------------------------------------------------------------------------
# Test Search & UI Filters in Unserviceable Register Report
# -------------------------------------------------------------------------
def test_unserviceable_register_search_and_filters(db_session: Session, fixture_setup):
    f = fixture_setup
    item_x = f["item_x"]
    item_y = f["item_y"]
    office = f["office_a"]
    fy = f["fy2"]
    uid = f["uid"]

    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item_x.id,
            office_id=office.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item_y.id,
            office_id=office.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    un_x = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item_x.id,
            office_id=office.id,
            quantity=5.0,
            reason=f"DefectAlpha_{uid}",
            reference_no=f"REF-ALPHA-{uid}",
            remarks=f"InspectionNotes_{uid}",
        ),
        office_id=office.id,
    )

    un_y = create_unserviceable_material(
        db_session,
        UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item_y.id,
            office_id=office.id,
            quantity=8.0,
            reason=f"DefectBeta_{uid}",
            reference_no=f"REF-BETA-{uid}",
        ),
        office_id=office.id,
    )

    # 1. Search by item code / name
    rep_search_x = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        search=item_x.code,
    )
    ids_found = [r.id for r in rep_search_x["items"] if r.register_type == "MATERIAL"]
    assert un_x.id in ids_found
    assert un_y.id not in ids_found

    # 2. Search by reference no
    rep_search_ref = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        search=f"REF-BETA-{uid}",
    )
    ids_found_ref = [r.id for r in rep_search_ref["items"] if r.register_type == "MATERIAL"]
    assert un_y.id in ids_found_ref
    assert un_x.id not in ids_found_ref

    # 3. Search by reason
    rep_search_reason = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        search=f"DefectAlpha_{uid}",
    )
    ids_found_reason = [r.id for r in rep_search_reason["items"] if r.register_type == "MATERIAL"]
    assert un_x.id in ids_found_reason

    # 4. Filter by asset_or_material = "" (All Types)
    rep_all_types = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        asset_or_material="",
    )
    ids_all = [r.id for r in rep_all_types["items"] if r.register_type == "MATERIAL"]
    assert un_x.id in ids_all
    assert un_y.id in ids_all

    # 5. Filter by asset_or_material = "MATERIAL"
    rep_mat_only = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        asset_or_material="MATERIAL",
    )
    assert all(r.register_type == "MATERIAL" for r in rep_mat_only["items"])

    # 6. Filter by asset_or_material = "ASSET"
    rep_asset_only = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        asset_or_material="ASSET",
    )
    assert all(r.register_type == "ASSET" for r in rep_asset_only["items"])

    # 7. Filter by specific item_id
    rep_item_y = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        item_id=item_y.id,
    )
    ids_item_y = [r.id for r in rep_item_y["items"] if r.register_type == "MATERIAL"]
    assert un_y.id in ids_item_y
    assert un_x.id not in ids_item_y

    # 8. Filter by status_filter
    rep_status_uns = get_unserviceable_register_report(
        db_session,
        office_id=office.id,
        financial_year_id=fy.id,
        status_filter="UNSERVICEABLE",
    )
    ids_uns = [r.id for r in rep_status_uns["items"] if r.register_type == "MATERIAL"]
    assert un_x.id in ids_uns
    assert un_y.id in ids_uns

