import uuid
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.office import Office, OfficeType
from app.models.section import Section
from app.models.financial_year import FinancialYear
from app.models.category import Category
from app.models.unit import Unit
from app.models.item import Item
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.enums import (
    Category_Type,
    DestinationType,
    IndentStatus,
    MovementType,
    RequestSource,
    TransactionStatus,
    UnserviceableStatus,
)
from app.models.indent import Indent
from app.models.indent_line import IndentLine
from app.models.issue import Issue, IssueLine
from app.models.stock_transfer import StockTransfer, StockTransferLine
from app.models.opening_stock import OpeningStock
from app.models.stock_movement import StockMovement
from app.models.unserviceable_material import UnserviceableMaterial

from app.crud.office import create_office
from app.crud.section import create_section
from app.crud.financial_year import create_financial_year
from app.crud.category import create_category
from app.crud.unit import create_unit
from app.crud.item import create_item
from app.crud.opening_stock import create_opening_stock
from app.crud.indent import create_indent
from app.crud.issue import create_issue
from app.crud.stock_transfer import create_transfer
from app.crud.unserviceable import (
    create_unserviceable_material,
    update_unserviceable_material_status,
)

from app.schemas.office import OfficeCreate
from app.schemas.sections import SectionCreate
from app.schemas.financial_year import FinancialYearCreate
from app.schemas.category import CategoryCreate
from app.schemas.unit import UnitCreate
from app.schemas.item import ItemCreate
from app.schemas.opening_stock import OpeningStockCreate
from app.schemas.indent import IndentCreate, IndentLineCreate
from app.schemas.issue import IssueCreate, IssueLineCreate
from app.schemas.stock_transfer import StockTransferCreate, StockTransferLineCreate
from app.schemas.unserviceable import (
    UnserviceableMaterialCreate,
    UnserviceableMaterialStatusUpdate,
)

from app.services.stock_service import (
    get_item_stock,
    get_item_usable_stock,
    get_item_unserviceable_stock,
    validate_stock_availability,
)
from app.services.posting_service import post_issue, post_transfer
from app.services.scope_service import (
    get_canonical_central_store_id,
    get_stock_office_id,
    get_authorized_view_office_ids,
    get_authorized_stock_office_ids,
    can_view_office,
    can_transact_office,
    is_department_wide_viewer,
    is_central_store_user,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_setup(db: Session):
    uid = uuid.uuid4().hex[:6]

    # 1. Offices: Directorate, GCP (Central Store), Branch A (Kollam), Branch B (Kozhikode)
    dir_office = create_office(
        db,
        OfficeCreate(name=f"Directorate {uid}", code=f"DIR_{uid}", office_type=OfficeType.DIRECTORATE),
    )
    gcp_office = create_office(
        db,
        OfficeCreate(name=f"Govt Central Press {uid}", code=f"GCP_{uid}", office_type=OfficeType.GCP),
    )
    branch_a = create_office(
        db,
        OfficeCreate(name=f"Branch Kollam {uid}", code=f"KLM_{uid}", office_type=OfficeType.BRANCH),
    )
    branch_b = create_office(
        db,
        OfficeCreate(name=f"Branch Kozhikode {uid}", code=f"KKD_{uid}", office_type=OfficeType.BRANCH),
    )

    # 2. Sections per office
    dir_section = create_section(
        db,
        SectionCreate(name=f"Directorate Admin {uid}", code=f"DA_{uid}", office_id=dir_office.id),
    )
    gcp_section = create_section(
        db,
        SectionCreate(name=f"GCP Binding Section {uid}", code=f"GB_{uid}", office_id=gcp_office.id),
    )
    branch_a_section = create_section(
        db,
        SectionCreate(name=f"Kollam Press Section {uid}", code=f"KS_{uid}", office_id=branch_a.id),
    )

    # 3. Financial Years: FY 2026-27 & FY 2027-28
    fy1 = db.query(FinancialYear).filter(FinancialYear.year_name == "2026-27").first()
    if not fy1:
        fy1 = create_financial_year(
            db,
            FinancialYearCreate(
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
                is_active=True,
            ),
        )
    if not fy1:
        fy1 = db.query(FinancialYear).first()

    fy2 = db.query(FinancialYear).filter(FinancialYear.year_name == "2027-28").first()
    if not fy2:
        fy2 = create_financial_year(
            db,
            FinancialYearCreate(
                start_date=date(2027, 4, 1),
                end_date=date(2028, 3, 31),
                is_active=True,
            ),
        )
    if not fy2 or fy2.id == fy1.id:
        fy2 = db.query(FinancialYear).filter(FinancialYear.id != fy1.id).first()
    if not fy2:
        fy2 = FinancialYear(year_name=f"FY-{uid}", start_date=date(2028, 4, 1), end_date=date(2029, 3, 31), is_active=True)
        db.add(fy2)
        db.commit()
        db.refresh(fy2)

    # 4. Master Data: Unit, Category, Items
    unit = create_unit(db, UnitCreate(name=f"Ream {uid}", symbol=f"RM_{uid}"))
    cat_mat = create_category(db, CategoryCreate(name=f"Paper {uid}", code=f"PAP_{uid}", type=Category_Type.MATERIAL))
    item1 = create_item(db, ItemCreate(name=f"A4 Paper 80GSM {uid}", code=f"A4_{uid}", category_id=cat_mat.id, unit_id=unit.id))
    item2 = create_item(db, ItemCreate(name=f"Bond Paper {uid}", code=f"BND_{uid}", category_id=cat_mat.id, unit_id=unit.id))

    # 5. Roles
    r_admin = db.query(Role).filter(Role.code == "ADMIN").first()
    if not r_admin:
        r_admin = Role(name="System Admin", code="ADMIN", is_active=True)
        db.add(r_admin)
        db.commit()

    r_csk = db.query(Role).filter(Role.code == "CENTRAL_STORE_KEEPER").first()
    if not r_csk:
        r_csk = Role(name="Central Storekeeper", code="CENTRAL_STORE_KEEPER", is_active=True)
        db.add(r_csk)
        db.commit()

    r_bsk = db.query(Role).filter(Role.code == "STOREKEEPER").first()
    if not r_bsk:
        r_bsk = Role(name="Storekeeper", code="STOREKEEPER", is_active=True)
        db.add(r_bsk)
        db.commit()

    r_director = db.query(Role).filter(Role.code == "DIRECTOR").first()
    if not r_director:
        r_director = Role(name="Director", code="DIRECTOR", is_active=True)
        db.add(r_director)
        db.commit()

    # 6. Users
    u_csk = User(code=f"C{uid[:6]}", username=f"csk_{uid}", password_hash="hash123", full_name="Central Store Keeper", office_id=gcp_office.id, is_active=True)
    u_bsk_a = User(code=f"B{uid[:6]}", username=f"bsk_a_{uid}", password_hash="hash123", full_name="Branch A Storekeeper", office_id=branch_a.id, is_active=True)
    u_dir = User(code=f"D{uid[:6]}", username=f"dir_{uid}", password_hash="hash123", full_name="Department Director", office_id=dir_office.id, is_active=True)
    db.add_all([u_csk, u_bsk_a, u_dir])
    db.commit()

    db.add(UserRole(user_id=u_csk.id, role_id=r_csk.id))
    db.add(UserRole(user_id=u_bsk_a.id, role_id=r_bsk.id))
    db.add(UserRole(user_id=u_dir.id, role_id=r_director.id))
    db.commit()

    return {
        "uid": uid,
        "dir_office": dir_office,
        "gcp_office": gcp_office,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "dir_section": dir_section,
        "gcp_section": gcp_section,
        "branch_a_section": branch_a_section,
        "fy1": fy1,
        "fy2": fy2,
        "item1": item1,
        "item2": item2,
        "u_csk": u_csk,
        "u_bsk_a": u_bsk_a,
        "u_dir": u_dir,
    }


# ==============================================================================
# 1. DIRECTORATE / GCP SHARED CENTRAL STORE STOCK BALANCE
# ==============================================================================
def test_directorate_and_gcp_share_single_central_store_stock(db: Session, test_setup):
    data = test_setup
    item = data["item1"]
    fy = data["fy1"]
    gcp = data["gcp_office"]
    directorate = data["dir_office"]

    # Canonical store resolution should point Directorate and GCP to Central Store
    cs_id = get_stock_office_id(db, directorate.id)
    assert cs_id == get_stock_office_id(db, gcp.id)

    # 1. Add Opening Stock to Central Store (200 units)
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=cs_id,
            quantity=Decimal("200.0"),
            unit_rate=Decimal("50.0"),
        ),
    )

    # Stock queried via Directorate office_id or GCP office_id must yield the exact same 200 units
    stock_via_dir = get_item_stock(db, item.id, office_id=directorate.id, financial_year_id=fy.id)
    stock_via_gcp = get_item_stock(db, item.id, office_id=gcp.id, financial_year_id=fy.id)
    assert stock_via_dir == 200.0
    assert stock_via_gcp == 200.0


def test_issue_to_directorate_section_deducts_shared_central_store_stock(db: Session, test_setup):
    data = test_setup
    item = data["item1"]
    fy = data["fy1"]
    directorate = data["dir_office"]
    dir_section = data["dir_section"]
    gcp = data["gcp_office"]
    user = data["u_csk"]

    cs_id = get_stock_office_id(db, directorate.id)

    # Ensure Central Store has 200 opening stock
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=cs_id,
            quantity=Decimal("200.0"),
            unit_rate=Decimal("50.0"),
        ),
    )

    initial_stock = get_item_stock(db, item.id, office_id=directorate.id, financial_year_id=fy.id)
    assert initial_stock >= 200.0

    # Create Physical Indent for Directorate Admin Section (requested 30, issued 30)
    indent = create_indent(
        db=db,
        indent_in=IndentCreate(
            indent_no=f"IND-DIR-{data['uid']}",
            indent_date=date.today(),
            received_date=date.today(),
            financial_year_id=fy.id,
            office_id=directorate.id,
            section_id=dir_section.id,
            request_source=RequestSource.PHYSICAL,
            lines=[
                IndentLineCreate(
                    item_id=item.id,
                    requested_quantity=30.0,
                    issued_quantity=30.0,
                )
            ],
        ),
        user_id=user.id,
    )

    # Organizational identity preserved
    assert indent.office_id == directorate.id
    assert indent.section_id == dir_section.id

    # Create Issue
    issue = create_issue(
        db=db,
        issue_in=IssueCreate(
            financial_year_id=fy.id,
            indent_id=indent.id,
            office_id=directorate.id,
            section_id=dir_section.id,
            destination_type=DestinationType.INTERNAL,
            issue_date=date.today(),
            lines=[IssueLineCreate(item_id=item.id, quantity=30.0)],
        ),
        user_id=user.id,
    )

    # Post Issue
    post_issue(db=db, issue_id=issue.id, user_id=user.id)

    # Stock in Central Store deducted by 30
    stock_after_dir = get_item_stock(db, item.id, office_id=directorate.id, financial_year_id=fy.id)
    stock_after_gcp = get_item_stock(db, item.id, office_id=gcp.id, financial_year_id=fy.id)
    assert stock_after_dir == initial_stock - 30.0
    assert stock_after_gcp == initial_stock - 30.0


# ==============================================================================
# 2. CENTRAL STORE TRANSACTION SCOPE & AUTHORITIES
# ==============================================================================
def test_central_storekeeper_has_exactly_one_stock_scope(db: Session, test_setup):
    data = test_setup
    u_csk = data["u_csk"]
    u_bsk_a = data["u_bsk_a"]
    u_dir = data["u_dir"]
    gcp = data["gcp_office"]
    branch_a = data["branch_a"]

    # Central Storekeeper stock authority has exactly 1 stock scope (the canonical Central Store)
    cs_stock_ids = get_authorized_stock_office_ids(db, u_csk)
    assert len(cs_stock_ids) == 1
    assert cs_stock_ids[0] == get_stock_office_id(db, gcp.id)

    # Branch Storekeeper stock authority has exactly 1 branch stock scope
    branch_stock_ids = get_authorized_stock_office_ids(db, u_bsk_a)
    assert branch_stock_ids == [branch_a.id]

    # Director has view authority but 0 stock transaction authority
    assert get_authorized_view_office_ids(db, u_dir) is None  # None = Department-wide view
    assert get_authorized_stock_office_ids(db, u_dir) == []   # No direct transaction ownership


def test_central_storekeeper_cannot_transact_directly_in_branch_store(db: Session, test_setup):
    data = test_setup
    u_csk = data["u_csk"]
    branch_a = data["branch_a"]
    gcp = data["gcp_office"]
    dir_office = data["dir_office"]

    # Central Storekeeper can transact for Central Store (GCP/Directorate)
    assert can_transact_office(db, u_csk, gcp.id) is True
    assert can_transact_office(db, u_csk, dir_office.id) is True

    # Central Storekeeper CANNOT directly transact within branch store
    assert can_transact_office(db, u_csk, branch_a.id) is False


# ==============================================================================
# 3. ORGANIZATIONAL SECTIONS INTEGRITY
# ==============================================================================
def test_sections_maintain_strict_office_relationship(db: Session, test_setup):
    data = test_setup
    dir_office = data["dir_office"]
    gcp = data["gcp_office"]
    dir_section = data["dir_section"]
    gcp_section = data["gcp_section"]

    # Sections have distinct administrative office links
    assert dir_section.office_id == dir_office.id
    assert gcp_section.office_id == gcp.id
    assert dir_section.office_id != gcp_section.office_id


# ==============================================================================
# 4. CENTRAL STORE -> BRANCH TRANSFER WORKFLOW
# ==============================================================================
def test_central_store_to_branch_transfer(db: Session, test_setup):
    data = test_setup
    item = data["item1"]
    fy = data["fy1"]
    gcp = data["gcp_office"]
    branch_a = data["branch_a"]
    user = data["u_csk"]

    cs_id = get_stock_office_id(db, gcp.id)

    # Ensure Central Store has opening stock
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=cs_id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("50.0"),
        ),
    )

    initial_cs_stock = get_item_stock(db, item.id, office_id=cs_id, financial_year_id=fy.id)
    initial_branch_stock = get_item_stock(db, item.id, office_id=branch_a.id, financial_year_id=fy.id)

    # 1. Create Transfer: CS -> Branch A (50 units)
    transfer = create_transfer(
        db=db,
        transfer_in=StockTransferCreate(
            transfer_date=date.today(),
            financial_year_id=fy.id,
            from_office_id=cs_id,
            to_office_id=branch_a.id,
            remarks="Dispatch paper stock to Kollam Branch",
            lines=[StockTransferLineCreate(item_id=item.id, quantity=50.0)],
        ),
        user_id=user.id,
    )

    assert transfer.from_office_id == cs_id
    assert transfer.to_office_id == branch_a.id

    # 2. Post Transfer
    posted = post_transfer(db=db, transfer_id=transfer.id, user_id=user.id)
    assert posted.status == TransactionStatus.POSTED

    # 3. Verify Stock Ledger Deductions and Additions
    new_cs_stock = get_item_stock(db, item.id, office_id=cs_id, financial_year_id=fy.id)
    new_branch_stock = get_item_stock(db, item.id, office_id=branch_a.id, financial_year_id=fy.id)

    assert new_cs_stock == initial_cs_stock - 50.0
    assert new_branch_stock == initial_branch_stock + 50.0


def test_transfer_within_same_stock_store_is_rejected(db: Session, test_setup):
    data = test_setup
    item = data["item1"]
    fy = data["fy1"]
    gcp = data["gcp_office"]
    directorate = data["dir_office"]
    user = data["u_csk"]

    # Directorate and GCP map to the same Central Store stock scope
    with pytest.raises(ValueError, match="Source and destination"):
        create_transfer(
            db=db,
            transfer_in=StockTransferCreate(
                transfer_date=date.today(),
                financial_year_id=fy.id,
                from_office_id=gcp.id,
                to_office_id=directorate.id,
                lines=[StockTransferLineCreate(item_id=item.id, quantity=10.0)],
            ),
            user_id=user.id,
        )


# ==============================================================================
# 5. FINANCIAL YEAR ISOLATION
# ==============================================================================
def test_stock_financial_year_isolation(db: Session, test_setup):
    data = test_setup
    item = data["item2"]
    fy1 = data["fy1"]
    fy2 = data["fy2"]
    branch_a = data["branch_a"]

    # Set Opening Stock: 100 in FY1, 40 in FY2
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy1.id,
            item_id=item.id,
            office_id=branch_a.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("10.0"),
        ),
    )
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy2.id,
            item_id=item.id,
            office_id=branch_a.id,
            quantity=Decimal("40.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    assert get_item_stock(db, item.id, branch_a.id, fy1.id) == 100.0
    assert get_item_stock(db, item.id, branch_a.id, fy2.id) == 40.0

    # Stock validation in FY2 fails for 50 requested
    assert validate_stock_availability(db, item.id, branch_a.id, 40.0, fy2.id) is True
    with pytest.raises(ValueError, match="Insufficient stock"):
        validate_stock_availability(db, item.id, branch_a.id, 50.0, fy2.id)


# ==============================================================================
# 6. UNSERVICEABLE MATERIAL ACCOUNTING
# ==============================================================================
def test_unserviceable_material_accounting_and_repair_lifecycle(db: Session, test_setup):
    data = test_setup
    item = data["item1"]
    fy = data["fy1"]
    branch_b = data["branch_b"]

    # 1. Opening Stock 100 in Branch B
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=branch_b.id,
            quantity=Decimal("100.0"),
            unit_rate=Decimal("20.0"),
        ),
    )
    assert get_item_stock(db, item.id, branch_b.id, fy.id) == 100.0
    assert get_item_usable_stock(db, item.id, branch_b.id, fy.id) == 100.0

    # 2. Mark 20 as UNSERVICEABLE -> creates ADJUSTMENT_OUT
    un_mat = create_unserviceable_material(
        db=db,
        data=UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=branch_b.id,
            quantity=20.0,
            reason="Water damage",
        ),
    )
    assert un_mat.status == UnserviceableStatus.UNSERVICEABLE
    assert get_item_stock(db, item.id, branch_b.id, fy.id) == 80.0
    assert get_item_usable_stock(db, item.id, branch_b.id, fy.id) == 80.0
    assert get_item_unserviceable_stock(db, item.id, branch_b.id, fy.id) == 20.0

    # 3. Repair 5 units -> creates ADJUSTMENT_IN
    update_unserviceable_material_status(
        db=db,
        unserviceable_id=un_mat.id,
        update_data=UnserviceableMaterialStatusUpdate(
            status=UnserviceableStatus.REPAIRED,
            quantity=5.0,
            remarks="Dried and sorted",
        ),
    )
    # Stock restored: 80 + 5 = 85. Active unserviceable: 20 - 5 = 15.
    assert get_item_stock(db, item.id, branch_b.id, fy.id) == 85.0
    assert get_item_usable_stock(db, item.id, branch_b.id, fy.id) == 85.0
    assert get_item_unserviceable_stock(db, item.id, branch_b.id, fy.id) == 15.0

    # 4. Condemn remaining 15 -> No stock movement
    # Find remaining active record
    remaining = db.query(UnserviceableMaterial).filter(
        UnserviceableMaterial.item_id == item.id,
        UnserviceableMaterial.office_id == branch_b.id,
        UnserviceableMaterial.status == UnserviceableStatus.UNSERVICEABLE,
        UnserviceableMaterial.is_active == True,
    ).first()

    update_unserviceable_material_status(
        db=db,
        unserviceable_id=remaining.id,
        update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.CONDEMNED),
    )
    assert get_item_stock(db, item.id, branch_b.id, fy.id) == 85.0
    assert get_item_usable_stock(db, item.id, branch_b.id, fy.id) == 85.0

    # 5. Dispose condemned record -> No second stock deduction
    update_unserviceable_material_status(
        db=db,
        unserviceable_id=remaining.id,
        update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.DISPOSED),
    )
    assert get_item_stock(db, item.id, branch_b.id, fy.id) == 85.0
    assert get_item_usable_stock(db, item.id, branch_b.id, fy.id) == 85.0


def test_unserviceable_repair_cannot_happen_twice(db: Session, test_setup):
    data = test_setup
    item = data["item2"]
    fy = data["fy1"]
    branch_a = data["branch_a"]

    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=branch_a.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    un_mat = create_unserviceable_material(
        db=db,
        data=UnserviceableMaterialCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=branch_a.id,
            quantity=10.0,
            reason="Torn reams",
        ),
    )

    # Full repair
    update_unserviceable_material_status(
        db=db,
        unserviceable_id=un_mat.id,
        update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.REPAIRED),
    )

    # Attempting to repair again or transition a terminal state must raise ValueError
    with pytest.raises(ValueError, match="Invalid status transition"):
        update_unserviceable_material_status(
            db=db,
            unserviceable_id=un_mat.id,
            update_data=UnserviceableMaterialStatusUpdate(status=UnserviceableStatus.REPAIRED),
        )


def test_cross_office_unserviceable_declaration_is_rejected(db: Session, test_setup):
    data = test_setup
    item = data["item1"]
    fy = data["fy1"]
    branch_a = data["branch_a"]
    branch_b = data["branch_b"]

    with pytest.raises(ValueError, match="Office mismatch"):
        create_unserviceable_material(
            db=db,
            data=UnserviceableMaterialCreate(
                financial_year_id=fy.id,
                item_id=item.id,
                office_id=branch_b.id,
                quantity=5.0,
                reason="Unauthorized attempt",
            ),
            office_id=branch_a.id,  # Authorized office is Branch A, payload is Branch B
        )


def test_branch_to_branch_transfer(db: Session, test_setup):
    data = test_setup
    item = data["item2"]
    fy = data["fy1"]
    branch_a = data["branch_a"]
    branch_b = data["branch_b"]
    user = data["u_csk"]

    # 1. Branch A has 60 opening stock
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=branch_a.id,
            quantity=Decimal("60.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    initial_a = get_item_stock(db, item.id, branch_a.id, fy.id)
    initial_b = get_item_stock(db, item.id, branch_b.id, fy.id)

    # 2. Transfer: Branch A -> Branch B (25 units)
    transfer = create_transfer(
        db=db,
        transfer_in=StockTransferCreate(
            transfer_date=date.today(),
            financial_year_id=fy.id,
            from_office_id=branch_a.id,
            to_office_id=branch_b.id,
            remarks="Inter-branch emergency paper transfer",
            lines=[StockTransferLineCreate(item_id=item.id, quantity=25.0)],
        ),
        user_id=user.id,
    )

    posted = post_transfer(db=db, transfer_id=transfer.id, user_id=user.id)
    assert posted.status == TransactionStatus.POSTED

    new_a = get_item_stock(db, item.id, branch_a.id, fy.id)
    new_b = get_item_stock(db, item.id, branch_b.id, fy.id)

    assert new_a == initial_a - 25.0
    assert new_b == initial_b + 25.0


def test_same_item_and_fy_different_offices_returns_separate_stock(db: Session, test_setup):
    data = test_setup
    item = data["item2"]
    fy = data["fy2"]
    branch_a = data["branch_a"]
    branch_b = data["branch_b"]

    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=branch_a.id,
            quantity=Decimal("75.0"),
            unit_rate=Decimal("10.0"),
        ),
    )
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy.id,
            item_id=item.id,
            office_id=branch_b.id,
            quantity=Decimal("30.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    assert get_item_stock(db, item.id, branch_a.id, fy.id) == 75.0
    assert get_item_stock(db, item.id, branch_b.id, fy.id) == 30.0


def test_opening_movement_in_fy1_does_not_suppress_opening_stock_in_fy2(db: Session, test_setup):
    data = test_setup
    item = data["item2"]
    fy1 = data["fy1"]
    fy2 = data["fy2"]
    branch_b = data["branch_b"]

    # In FY1, create an explicit OPENING StockMovement
    sm = StockMovement(
        financial_year_id=fy1.id,
        item_id=item.id,
        office_id=branch_b.id,
        movement_type=MovementType.OPENING,
        quantity_in=50.0,
        quantity_out=0.0,
        reference_type="OPENING_BALANCE",
        reference_id=1,
    )
    db.add(sm)
    db.commit()

    # In FY2, create an OpeningStock record
    create_opening_stock(
        db,
        OpeningStockCreate(
            financial_year_id=fy2.id,
            item_id=item.id,
            office_id=branch_b.id,
            quantity=Decimal("80.0"),
            unit_rate=Decimal("10.0"),
        ),
    )

    # FY1 has 50 from movement
    assert get_item_stock(db, item.id, branch_b.id, fy1.id) == 50.0
    # FY2 must read its 80 from OpeningStock without being suppressed by FY1 movement
    assert get_item_stock(db, item.id, branch_b.id, fy2.id) == 80.0


def test_branch_user_cannot_view_another_branch_stock(db: Session, test_setup):
    data = test_setup
    u_bsk_a = data["u_bsk_a"]
    branch_a = data["branch_a"]
    branch_b = data["branch_b"]
    gcp = data["gcp_office"]

    # Branch A user can view Branch A only
    assert can_view_office(db, u_bsk_a, branch_a.id) is True
    assert can_view_office(db, u_bsk_a, branch_b.id) is False
    assert can_view_office(db, u_bsk_a, gcp.id) is False

    # Authorized view list contains only Branch A
    assert get_authorized_view_office_ids(db, u_bsk_a) == [branch_a.id]

