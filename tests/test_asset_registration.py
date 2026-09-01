"""
tests/test_asset_registration.py

Full test suite for:
  - Asset Registration (tests 1–10)
  - Opening Stock MATERIAL-only validation (tests 11–13)
  - Asset Scope (tests 14–20)
  - Asset history (tests 21–24)
  - Central Store specific (Tests A, B, C)

Follows the same conventions as test_business_rules.py:
  - Uses CRUD functions for office/section/FY creation
  - Directly uses model constructors for Unit, Category, Item, User, Role
  - Uses the correct field names from the actual SQLAlchemy models
"""

import uuid
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.enums import (
    AssetMovementType,
    AssetStatus,
    Category_Type,
)
from app.models.office import Office, OfficeType
from app.models.section import Section
from app.models.financial_year import FinancialYear
from app.models.category import Category
from app.models.unit import Unit
from app.models.item import Item
from app.models.asset import Asset
from app.models.asset_movement import AssetMovement
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole

from app.crud.asset import (
    create_asset,
    create_asset_movement,
    get_asset_by_id,
    get_all_assets,
)
from app.crud.opening_stock import create_opening_stock, update_opening_stock
from app.crud.office import create_office
from app.crud.section import create_section
from app.crud.financial_year import create_financial_year
from app.crud.unit import create_unit
from app.crud.category import create_category
from app.crud.item import create_item

from app.schemas.asset import (
    AssetCreate,
    AssetDetailCreate,
    AssetMovementCreate,
)
from app.schemas.sections import SectionCreate
from app.schemas.opening_stock import OpeningStockCreate, OpeningStockUpdate
from app.schemas.financial_year import FinancialYearCreate
from app.schemas.office import OfficeCreate
from app.schemas.unit import UnitCreate
from app.schemas.category import CategoryCreate
from app.schemas.item import ItemCreate

from app.services.scope_service import (
    can_transact_office,
    can_view_office,
    get_authorized_stock_office_ids,
    get_stock_office_id,
    is_central_store_user,
    is_department_wide_viewer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def asset_setup(db: Session):
    """
    Self-contained fixture set following test_business_rules.py conventions.
    All unique names to avoid collisions with existing seeded data.
    """
    uid = uuid.uuid4().hex[:6]  # 6 hex chars — safe for all code fields

    # ── Offices ────────────────────────────────────────────────────────────
    dir_office = create_office(
        db,
        OfficeCreate(
            name=f"Directorate {uid}",
            code=f"DI_{uid}",
            office_type=OfficeType.DIRECTORATE,
        ),
    )
    gcp_office = create_office(
        db,
        OfficeCreate(
            name=f"GCP {uid}",
            code=f"GC_{uid}",
            office_type=OfficeType.GCP,
        ),
    )
    branch_a = create_office(
        db,
        OfficeCreate(
            name=f"Branch A {uid}",
            code=f"BA_{uid}",
            office_type=OfficeType.BRANCH,
        ),
    )
    branch_b = create_office(
        db,
        OfficeCreate(
            name=f"Branch B {uid}",
            code=f"BB_{uid}",
            office_type=OfficeType.BRANCH,
        ),
    )

    # ── Sections (require code field) ──────────────────────────────────────
    gcp_section = create_section(
        db,
        SectionCreate(
            name=f"Pre-press {uid}",
            code=f"PP_{uid}",
            office_id=gcp_office.id,
        ),
    )
    branch_a_section = create_section(
        db,
        SectionCreate(
            name=f"Store A {uid}",
            code=f"SA_{uid}",
            office_id=branch_a.id,
        ),
    )
    other_section = create_section(
        db,
        SectionCreate(
            name=f"Store B {uid}",
            code=f"SB_{uid}",
            office_id=branch_b.id,
        ),
    )

    # ── Unit (name + symbol, no code) ──────────────────────────────────────
    unit = create_unit(db, UnitCreate(name=f"Piece {uid}", symbol=f"PC{uid}"))

    # ── Categories ─────────────────────────────────────────────────────────
    asset_cat = create_category(
        db,
        CategoryCreate(
            name=f"Computers {uid}",
            code=f"AC{uid}",
            type=Category_Type.ASSET,
        ),
    )
    material_cat = create_category(
        db,
        CategoryCreate(
            name=f"Stationery {uid}",
            code=f"MC{uid}",
            type=Category_Type.MATERIAL,
        ),
    )

    # ── Items ───────────────────────────────────────────────────────────────
    asset_item = create_item(
        db,
        ItemCreate(
            name=f"Desktop Computer {uid}",
            code=f"CP{uid}",
            category_id=asset_cat.id,
            unit_id=unit.id,
        ),
    )
    material_item = create_item(
        db,
        ItemCreate(
            name=f"A4 Paper {uid}",
            code=f"AP{uid}",
            category_id=material_cat.id,
            unit_id=unit.id,
        ),
    )

    # Inactive item — directly construct and persist
    inactive_item = Item(
        code=f"IN{uid}",
        name=f"Inactive Item {uid}",
        category_id=asset_cat.id,
        unit_id=unit.id,
        is_temporary=False,
        is_active=False,
    )
    db.add(inactive_item)
    db.flush()

    # ── Financial Year — get or create to handle existing FY with same name ─
    fy = create_financial_year(
        db,
        FinancialYearCreate(
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        ),
    )
    if not fy:
        # A FY with year_name "2024-25" already exists — reuse it
        from app.crud.financial_year import generate_year_name
        yn = generate_year_name(date(2024, 4, 1), date(2025, 3, 31))
        fy = db.query(FinancialYear).filter(FinancialYear.year_name == yn).first()
    if not fy:
        # Last-resort: any active FY
        fy = db.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    if not fy:
        raise RuntimeError("No financial year available for tests.")

    # ── Roles — reuse system roles if they exist ───────────────────────────
    def get_or_create_role(code, name):
        r = db.query(Role).filter(Role.code == code).first()
        if not r:
            r = Role(code=code, name=name)
            db.add(r)
            db.commit()
        return r

    sk_role  = get_or_create_role("STOREKEEPER", "Storekeeper")
    csk_role = get_or_create_role("CENTRAL_STORE_KEEPER", "Central Store Keeper")
    dir_role = get_or_create_role("DIRECTOR", "Director")

    # ── Users (code max 7 chars, field is password_hash) ──────────────────
    branch_sk = User(
        code=f"B{uid}",
        username=f"bsk{uid}",
        password_hash="hash",
        full_name=f"Branch SK {uid}",
        office_id=branch_a.id,
        is_active=True,
    )
    central_sk = User(
        code=f"C{uid}",
        username=f"csk{uid}",
        password_hash="hash",
        full_name=f"Central SK {uid}",
        office_id=gcp_office.id,
        is_active=True,
    )
    director_user = User(
        code=f"D{uid}",
        username=f"dir{uid}",
        password_hash="hash",
        full_name=f"Director {uid}",
        office_id=dir_office.id,
        is_active=True,
    )
    db.add_all([branch_sk, central_sk, director_user])
    db.flush()

    db.add_all([
        UserRole(user_id=branch_sk.id, role_id=sk_role.id),
        UserRole(user_id=central_sk.id, role_id=csk_role.id),
        UserRole(user_id=director_user.id, role_id=dir_role.id),
    ])
    db.commit()

    return {
        "uid": uid,
        "dir_office": dir_office,
        "gcp_office": gcp_office,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "gcp_section": gcp_section,
        "branch_a_section": branch_a_section,
        "other_section": other_section,
        "unit": unit,
        "asset_cat": asset_cat,
        "material_cat": material_cat,
        "asset_item": asset_item,
        "material_item": material_item,
        "inactive_item": inactive_item,
        "fy": fy,
        "branch_sk": branch_sk,
        "central_sk": central_sk,
        "director_user": director_user,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_asset(db, item, office_id, section_id=None):
    """Create a quick asset with a unique asset_no."""
    uid = uuid.uuid4().hex[:8]
    return create_asset(
        db,
        AssetCreate(
            asset_no=f"A{uid}",
            item_id=item.id,
            office_id=office_id,
            section_id=section_id,
        ),
    )


# ===========================================================================
# ASSET REGISTRATION (tests 1–10)
# ===========================================================================

def test_1_register_valid_asset(db, asset_setup):
    """Test 1: Register a valid asset — succeeds."""
    s = asset_setup
    asset = create_asset(
        db,
        AssetCreate(
            asset_no=f"CPU001{s['uid']}",
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
            serial_no=f"SN{s['uid']}001",  # unique per test run
            detail=AssetDetailCreate(
                make="HP",
                model="ProDesk 400",
                purchase_date=date(2022, 5, 10),
                purchase_value=45000.00,
            ),
        ),
    )
    assert asset.id is not None
    assert asset.asset_no == f"CPU001{s['uid']}".upper()
    assert asset.status == AssetStatus.IN_STORE


def test_2_asset_detail_created(db, asset_setup):
    """Test 2: AssetDetail is created with the asset."""
    s = asset_setup
    asset = create_asset(
        db,
        AssetCreate(
            asset_no=f"CPU002{s['uid']}",
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
            detail=AssetDetailCreate(
                make="Dell",
                model="Optiplex 3090",
                purchase_date=date(2021, 3, 15),
                purchase_value=55000.00,
                technical_specifications="Intel i5, 8GB RAM, 256GB SSD",
            ),
        ),
    )
    db.refresh(asset)
    assert asset.asset_detail is not None
    assert asset.asset_detail.make == "Dell"
    assert asset.asset_detail.purchase_date == date(2021, 3, 15)


def test_3_initial_asset_movement_created(db, asset_setup):
    """Test 3: Initial AssetMovement (RECEIPT) is created automatically."""
    s = asset_setup
    asset = create_asset(
        db,
        AssetCreate(
            asset_no=f"CPU003{s['uid']}",
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
        ),
    )
    db.refresh(asset)
    assert len(asset.movements) == 1
    mv = asset.movements[0]
    assert mv.movement_type == AssetMovementType.RECEIPT
    assert mv.to_office_id == s["gcp_office"].id
    assert "Registration" in (mv.remarks or "")


def test_4_asset_creation_is_atomic(db, asset_setup):
    """Test 4: Asset creation with invalid section causes full rollback — no partial record."""
    s = asset_setup
    asset_no = f"AT04{s['uid']}"
    with pytest.raises(ValueError):
        create_asset(
            db,
            AssetCreate(
                asset_no=asset_no,
                item_id=s["asset_item"].id,
                office_id=s["gcp_office"].id,
                section_id=s["other_section"].id,  # belongs to branch_b, not gcp
            ),
        )
    result = db.query(Asset).filter(
        Asset.asset_no == asset_no.upper()
    ).first()
    assert result is None


def test_5_duplicate_asset_no_rejected(db, asset_setup):
    """Test 5: Duplicate asset_no is rejected."""
    s = asset_setup
    asset_no = f"DUP{s['uid']}"
    create_asset(
        db,
        AssetCreate(
            asset_no=asset_no,
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
        ),
    )
    with pytest.raises(ValueError, match="already exists"):
        create_asset(
            db,
            AssetCreate(
                asset_no=asset_no,
                item_id=s["asset_item"].id,
                office_id=s["branch_a"].id,
            ),
        )


def test_6_inactive_item_rejected(db, asset_setup):
    """Test 6: Inactive item is rejected for asset registration."""
    s = asset_setup
    with pytest.raises(ValueError, match="not found"):
        create_asset(
            db,
            AssetCreate(
                asset_no=f"INA{s['uid']}",
                item_id=s["inactive_item"].id,
                office_id=s["gcp_office"].id,
            ),
        )


def test_7_material_item_rejected_for_asset(db, asset_setup):
    """Test 7: Material item is rejected for asset registration."""
    s = asset_setup
    with pytest.raises(ValueError, match="Asset category"):
        create_asset(
            db,
            AssetCreate(
                asset_no=f"MAT{s['uid']}",
                item_id=s["material_item"].id,
                office_id=s["gcp_office"].id,
            ),
        )


def test_8_section_from_another_office_rejected(db, asset_setup):
    """Test 8: Section belonging to another office is rejected."""
    s = asset_setup
    with pytest.raises(ValueError, match="section does not belong"):
        create_asset(
            db,
            AssetCreate(
                asset_no=f"SEC{s['uid']}",
                item_id=s["asset_item"].id,
                office_id=s["gcp_office"].id,
                section_id=s["other_section"].id,  # belongs to branch_b
            ),
        )


def test_9_nonexistent_office_rejected(db, asset_setup):
    """Test 9: A non-existent office is rejected."""
    s = asset_setup
    with pytest.raises(ValueError, match="Office not found"):
        create_asset(
            db,
            AssetCreate(
                asset_no=f"UNO{s['uid']}",
                item_id=s["asset_item"].id,
                office_id=999999,
            ),
        )


def test_10_old_purchase_date_accepted(db, asset_setup):
    """Test 10: Old purchase date (before CSMS go-live) is accepted."""
    s = asset_setup
    asset = create_asset(
        db,
        AssetCreate(
            asset_no=f"OLD{s['uid']}",
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
            detail=AssetDetailCreate(purchase_date=date(2015, 6, 1)),
        ),
    )
    db.refresh(asset)
    assert asset.asset_detail.purchase_date == date(2015, 6, 1)


# ===========================================================================
# OPENING STOCK — MATERIAL-ONLY VALIDATION (tests 11–13)
# ===========================================================================

def test_11_material_item_accepted_for_opening_stock(db, asset_setup):
    """Test 11: Material item is accepted for opening stock."""
    s = asset_setup
    stock = create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=s["fy"].id,
            office_id=s["branch_a"].id,
            item_id=s["material_item"].id,
            quantity=Decimal("100"),
            unit_rate=Decimal("10.00"),
        ),
    )
    assert stock.id is not None
    assert stock.item_id == s["material_item"].id


def test_12_asset_item_rejected_for_opening_stock(db, asset_setup):
    """Test 12: Asset item is rejected for opening stock — backend validation."""
    s = asset_setup
    with pytest.raises(ValueError, match="Material items"):
        create_opening_stock(
            db,
            OpeningStockCreate(
                financial_year_id=s["fy"].id,
                office_id=s["branch_a"].id,
                item_id=s["asset_item"].id,
                quantity=Decimal("5"),
                unit_rate=Decimal("45000.00"),
            ),
        )


def test_13_asset_item_rejected_on_opening_stock_update(db, asset_setup):
    """Test 13: Changing opening stock item to an asset item is also rejected."""
    s = asset_setup
    stock = create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=s["fy"].id,
            office_id=s["branch_b"].id,
            item_id=s["material_item"].id,
            quantity=Decimal("50"),
            unit_rate=Decimal("5.00"),
        ),
    )
    with pytest.raises(ValueError, match="Material items"):
        update_opening_stock(
            db,
            stock.id,
            OpeningStockUpdate(item_id=s["asset_item"].id),
        )


# ===========================================================================
# ASSET SCOPE (tests 14–20)
# ===========================================================================

def test_14_branch_user_can_view_own_office(db, asset_setup):
    """Test 14: Branch user can view their own office."""
    s = asset_setup
    assert can_view_office(db, s["branch_sk"], s["branch_a"].id)


def test_15_branch_user_cannot_view_another_branch(db, asset_setup):
    """Test 15: Branch user cannot view another branch."""
    s = asset_setup
    assert not can_view_office(db, s["branch_sk"], s["branch_b"].id)


def test_16_branch_user_limited_transact_scope(db, asset_setup):
    """Test 16: Branch user's authorized stock IDs are limited to their branch."""
    s = asset_setup
    auth_ids = get_authorized_stock_office_ids(db, s["branch_sk"])
    assert s["branch_a"].id in auth_ids
    assert s["branch_b"].id not in auth_ids
    assert s["gcp_office"].id not in auth_ids


def test_17_central_storekeeper_can_transact_central_store(db, asset_setup):
    """Test 17: Central Storekeeper can transact on their GCP / Central Store office."""
    s = asset_setup
    assert can_transact_office(db, s["central_sk"], s["gcp_office"].id)


def test_18_central_storekeeper_cannot_transact_branch(db, asset_setup):
    """Test 18: Central Storekeeper cannot transact on branch offices."""
    s = asset_setup
    assert not can_transact_office(db, s["central_sk"], s["branch_a"].id)


def test_19_director_can_view_all_offices(db, asset_setup):
    """Test 19: Director has department-wide view access to all offices."""
    s = asset_setup
    assert is_department_wide_viewer(db, s["director_user"])
    assert can_view_office(db, s["director_user"], s["branch_a"].id)
    assert can_view_office(db, s["director_user"], s["branch_b"].id)
    assert can_view_office(db, s["director_user"], s["gcp_office"].id)


def test_20_director_has_no_stock_transaction_authority(db, asset_setup):
    """Test 20: Director has view-only — no stock transaction authority."""
    s = asset_setup
    auth_ids = get_authorized_stock_office_ids(db, s["director_user"])
    assert len(auth_ids) == 0


# ===========================================================================
# ASSET HISTORY (tests 21–24)
# ===========================================================================

def test_21_asset_location_change_creates_movement(db, asset_setup):
    """Test 21: Asset movement creates an AssetMovement and updates asset location."""
    s = asset_setup
    asset = make_asset(db, s["asset_item"], s["gcp_office"].id)

    create_asset_movement(
        db,
        AssetMovementCreate(
            movement_type=AssetMovementType.ISSUE,
            to_office_id=s["branch_a"].id,
            to_section_id=s["branch_a_section"].id,
            remarks="Issued to Branch A",
        ),
        asset_id=asset.id,
    )
    db.refresh(asset)
    assert len(asset.movements) == 2  # initial RECEIPT + this ISSUE
    assert asset.office_id == s["branch_a"].id
    assert asset.section_id == s["branch_a_section"].id
    assert asset.status == AssetStatus.ISSUED


def test_22_asset_lifecycle_change_creates_movement(db, asset_setup):
    """Test 22: Asset status lifecycle change is recorded as AssetMovement."""
    s = asset_setup
    asset = make_asset(db, s["asset_item"], s["gcp_office"].id)

    create_asset_movement(
        db,
        AssetMovementCreate(
            movement_type=AssetMovementType.CONDEMNATION,
            new_status=AssetStatus.CONDEMNED,
            remarks="Condemned after inspection",
        ),
        asset_id=asset.id,
    )
    db.refresh(asset)
    assert asset.status == AssetStatus.CONDEMNED
    condemnations = [
        m for m in asset.movements
        if m.movement_type == AssetMovementType.CONDEMNATION
    ]
    assert len(condemnations) == 1


def test_23_asset_remains_same_record_across_financial_years(db, asset_setup):
    """Test 23: Asset record is permanent — not tied to any financial year."""
    s = asset_setup
    asset = make_asset(db, s["asset_item"], s["gcp_office"].id)
    original_id = asset.id

    # Creating a new FY must not affect the asset record
    create_financial_year(
        db,
        FinancialYearCreate(
            start_date=date(2025, 4, 1),
            end_date=date(2026, 3, 31),
        ),
    )

    fetched = get_asset_by_id(db, original_id)
    assert fetched is not None
    assert fetched.id == original_id
    # The Asset model must have no financial_year_id attribute
    assert not hasattr(Asset, "financial_year_id")


def test_24_asset_register_has_no_fy_filter(db, asset_setup):
    """Test 24: Asset register query returns results without any FY filter."""
    s = asset_setup
    asset = make_asset(db, s["asset_item"], s["gcp_office"].id)

    result = get_all_assets(db=db, office_id=s["gcp_office"].id)
    asset_ids = [a.id for a in result["items"]]
    assert asset.id in asset_ids


# ===========================================================================
# CENTRAL STORE SPECIFIC TESTS (A, B, C)
# ===========================================================================

def test_A_register_asset_for_central_store(db, asset_setup):
    """Test A: Asset registered for Central Store has correct office_id and initial movement."""
    s = asset_setup
    asset = create_asset(
        db,
        AssetCreate(
            asset_no=f"CSA{s['uid']}",
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
            section_id=s["gcp_section"].id,
        ),
    )
    assert asset.office_id == s["gcp_office"].id
    db.refresh(asset)
    assert len(asset.movements) >= 1
    initial_mv = asset.movements[0]
    assert initial_mv.movement_type == AssetMovementType.RECEIPT
    assert initial_mv.to_office_id == s["gcp_office"].id


def test_B_gcp_asset_office_id_not_overwritten_by_stock_mapping(db, asset_setup):
    """
    Test B: An asset at GCP has office_id = GCP.
    The material stock mapping (GCP → canonical Central Store) must NOT
    overwrite Asset.office_id — stock ownership ≠ asset location identity.
    """
    s = asset_setup
    asset = create_asset(
        db,
        AssetCreate(
            asset_no=f"GCB{s['uid']}",
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
        ),
    )

    # Stock mapping may resolve GCP to canonical Central Store
    # but that must NOT affect the asset's location
    _ = get_stock_office_id(db, s["gcp_office"].id)

    # Asset must retain its set office_id
    db.refresh(asset)
    assert asset.office_id == s["gcp_office"].id


def test_C_asset_transfer_updates_location_not_stock_ownership(db, asset_setup):
    """
    Test C: Asset issued from Central Store to GCP / Pre-press creates AssetMovement
    and updates Asset.office_id and section_id to reflect the actual new location.
    """
    s = asset_setup
    asset = create_asset(
        db,
        AssetCreate(
            asset_no=f"XFC{s['uid']}",
            item_id=s["asset_item"].id,
            office_id=s["gcp_office"].id,
        ),
    )

    create_asset_movement(
        db,
        AssetMovementCreate(
            movement_type=AssetMovementType.ISSUE,
            from_office_id=s["gcp_office"].id,
            to_office_id=s["gcp_office"].id,
            to_section_id=s["gcp_section"].id,
            remarks="Issued to Pre-press section",
        ),
        asset_id=asset.id,
    )

    db.refresh(asset)
    assert asset.office_id == s["gcp_office"].id
    assert asset.section_id == s["gcp_section"].id

    issue_movs = [
        m for m in asset.movements
        if m.movement_type == AssetMovementType.ISSUE
    ]
    assert len(issue_movs) == 1
    assert issue_movs[0].to_office_id == s["gcp_office"].id
    assert issue_movs[0].to_section_id == s["gcp_section"].id
