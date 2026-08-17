import uuid
import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.category import Category
from app.models.enums import Category_Type, MovementType, TransactionStatus
from app.models.office import Office, OfficeType
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.office import Office
from app.models.receipt import Receipt, ReceiptLine
from app.models.role import Role
from app.models.section import Section
from app.models.stock_movement import StockMovement
from app.models.unit import Unit
from app.models.user import User
from app.models.user_role import UserRole

from app.crud.receipt import (
    create_receipt,
    delete_receipt,
    get_all_receipts,
    get_receipt_by_id,
    update_receipt,
)
from app.crud.item import create_temporary_item, promote_temporary_item, get_all_items
from app.schemas.receipt import ReceiptCreate, ReceiptLineCreate, ReceiptUpdate
from app.services.posting_service import post_receipt
from app.services.stock_service import get_item_stock
from app.dependencies.ui_auth import get_current_user_ui
from app.dependencies.auth import get_current_user
from app.services.permission_seed import seed_permissions, seed_admin_permissions


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_setup(db_session: Session):
    seed_permissions(db_session)
    seed_admin_permissions(db_session)

    uid = uuid.uuid4().hex[:6]

    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    if not fy:
        fy = FinancialYear(year_name="2026-2027", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), is_active=True)
        db_session.add(fy)
        db_session.commit()
        db_session.refresh(fy)

    office = db_session.query(Office).filter(Office.is_active == True).first()
    if not office:
        office = Office(name=f"Central Store {uid}", code=f"CS-{uid}", office_type=OfficeType.GCP, is_active=True)
        db_session.add(office)
        db_session.commit()
        db_session.refresh(office)

    section = Section(name=f"Electrical Section {uid}", code=f"SEC-{uid}", office_id=office.id, is_active=True)
    db_session.add(section)
    db_session.commit()
    db_session.refresh(section)

    user = db_session.query(User).filter(User.is_active == True).first()
    if not user:
        user = User(
            code=f"U-{uid}",
            username=f"storekeeper_{uid}",
            password_hash=hash_password("admin123"),
            full_name="Receipt Storekeeper",
            office_id=office.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    role = db_session.query(Role).filter(Role.is_active == True).first()
    if role:
        existing_ur = db_session.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
        if not existing_ur:
            db_session.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
            db_session.commit()

    unit = db_session.query(Unit).filter(Unit.is_active == True).first()
    if not unit:
        unit = Unit(name="Numbers", code="NOS", is_active=True)
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)

    cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    if not cat:
        cat = Category(name=f"Hardware {uid}", type=Category_Type.MATERIAL, is_active=True)
        db_session.add(cat)
        db_session.commit()
        db_session.refresh(cat)

    item1 = Item(name=f"Bearing 6204 {uid}", code=f"BRG-{uid}", category_id=cat.id, unit_id=unit.id, is_active=True)
    item2 = Item(name=f"Lubricant Grease {uid}", code=f"GRS-{uid}", category_id=cat.id, unit_id=unit.id, is_active=True)
    db_session.add_all([item1, item2])
    db_session.commit()
    db_session.refresh(item1)
    db_session.refresh(item2)

    return {
        "uid": uid,
        "fy": fy,
        "office": office,
        "section": section,
        "user": user,
        "unit": unit,
        "item1": item1,
        "item2": item2,
    }


@pytest.fixture
def auth_client(test_setup):
    user = test_setup["user"]
    app.dependency_overrides[get_current_user_ui] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


# =========================================================================
# UNIT TESTS: CRUD & SERVICES
# =========================================================================

def test_create_and_post_goods_receipt(db_session: Session, test_setup):
    s = test_setup

    initial_stock_1 = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office"].id)
    assert initial_stock_1 == 0.0

    # 1. Create DRAFT Receipt
    receipt_in = ReceiptCreate(
        financial_year_id=s["fy"].id,
        office_id=s["office"].id,
        section_id=s["section"].id,
        receipt_date=date.today(),
        supplier_name="M/s Industrial Spares Ltd",
        reference_no="INV-99881",
        remarks="Test consignment",
        lines=[
            ReceiptLineCreate(item_id=s["item1"].id, quantity=50.0, unit_price=250.0, remarks="Batch 1"),
            ReceiptLineCreate(item_id=s["item2"].id, quantity=10.0, unit_price=600.0, remarks="Batch A"),
        ],
    )
    receipt = create_receipt(db=db_session, receipt_in=receipt_in, user_id=s["user"].id)

    assert receipt.id is not None
    assert receipt.receipt_no.startswith("REC-")
    assert receipt.status == TransactionStatus.DRAFT
    assert len(receipt.lines) == 2
    assert receipt.supplier_name == "M/s Industrial Spares Ltd"

    # Verify DRAFT does NOT affect stock
    stock_during_draft = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office"].id)
    assert stock_during_draft == 0.0

    # 2. Post Receipt
    posted_receipt = post_receipt(db=db_session, receipt_id=receipt.id, user_id=s["user"].id)
    assert posted_receipt.status == TransactionStatus.POSTED
    assert posted_receipt.posted_by_id == s["user"].id
    assert posted_receipt.posted_at is not None

    # Verify stock has increased
    stock_after_post_1 = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office"].id)
    stock_after_post_2 = get_item_stock(db=db_session, item_id=s["item2"].id, office_id=s["office"].id)
    assert stock_after_post_1 == 50.0
    assert stock_after_post_2 == 10.0

    # Verify StockMovements created
    movements = db_session.query(StockMovement).filter(
        StockMovement.reference_type == "RECEIPT",
        StockMovement.reference_id == receipt.id,
    ).all()
    assert len(movements) == 2
    for m in movements:
        assert m.movement_type == MovementType.RECEIPT
        assert m.office_id == s["office"].id
        assert m.quantity_in > 0
        assert m.quantity_out == 0.0


def test_edit_draft_receipt(db_session: Session, test_setup):
    s = test_setup

    receipt_in = ReceiptCreate(
        financial_year_id=s["fy"].id,
        office_id=s["office"].id,
        lines=[
            ReceiptLineCreate(item_id=s["item1"].id, quantity=10.0, unit_price=100.0),
        ],
    )
    receipt = create_receipt(db=db_session, receipt_in=receipt_in, user_id=s["user"].id)
    original_no = receipt.receipt_no

    # Update draft
    update_in = ReceiptUpdate(
        supplier_name="Updated Vendor Corp",
        reference_no="CH-777",
        remarks="Updated note",
        lines=[
            ReceiptLineCreate(item_id=s["item1"].id, quantity=30.0, unit_price=120.0),
            ReceiptLineCreate(item_id=s["item2"].id, quantity=5.0, unit_price=500.0),
        ],
    )
    updated = update_receipt(db=db_session, receipt_id=receipt.id, receipt_in=update_in)
    assert updated.receipt_no == original_no
    assert updated.supplier_name == "Updated Vendor Corp"
    assert updated.reference_no == "CH-777"
    assert len(updated.lines) == 2
    assert float(updated.lines[0].quantity) == 30.0


def test_delete_draft_receipt(db_session: Session, test_setup):
    s = test_setup

    receipt_in = ReceiptCreate(
        financial_year_id=s["fy"].id,
        office_id=s["office"].id,
        lines=[ReceiptLineCreate(item_id=s["item1"].id, quantity=15.0)],
    )
    receipt = create_receipt(db=db_session, receipt_in=receipt_in, user_id=s["user"].id)
    receipt_id = receipt.id

    deleted = delete_receipt(db=db_session, receipt_id=receipt_id)
    assert deleted.is_active is False

    # Should not be returned by get_receipt_by_id
    assert get_receipt_by_id(db=db_session, receipt_id=receipt_id) is None


def test_posted_receipt_immutability(db_session: Session, test_setup):
    s = test_setup

    receipt_in = ReceiptCreate(
        financial_year_id=s["fy"].id,
        office_id=s["office"].id,
        lines=[ReceiptLineCreate(item_id=s["item1"].id, quantity=25.0)],
    )
    receipt = create_receipt(db=db_session, receipt_in=receipt_in, user_id=s["user"].id)
    post_receipt(db=db_session, receipt_id=receipt.id, user_id=s["user"].id)

    # 1. Cannot re-post
    with pytest.raises(ValueError, match="already posted"):
        post_receipt(db=db_session, receipt_id=receipt.id, user_id=s["user"].id)

    # 2. Cannot edit
    with pytest.raises(ValueError, match="Cannot update a posted Receipt"):
        update_receipt(db=db_session, receipt_id=receipt.id, receipt_in=ReceiptUpdate(supplier_name="New"))

    # 3. Cannot delete
    with pytest.raises(ValueError, match="Cannot delete a posted Receipt"):
        delete_receipt(db=db_session, receipt_id=receipt.id)


def test_invalid_section_rejected(db_session: Session, test_setup):
    s = test_setup

    # Create another office
    other_office = Office(name=f"Other Office {s['uid']}", code=f"OTH-{s['uid']}", office_type=OfficeType.GCP, is_active=True)
    db_session.add(other_office)
    db_session.commit()

    other_section = Section(name=f"Other Section {s['uid']}", code=f"OTH-S-{s['uid']}", office_id=other_office.id, is_active=True)
    db_session.add(other_section)
    db_session.commit()

    # Attempt receipt with mismatched section
    receipt_in = ReceiptCreate(
        financial_year_id=s["fy"].id,
        office_id=s["office"].id,
        section_id=other_section.id,
        lines=[ReceiptLineCreate(item_id=s["item1"].id, quantity=10.0)],
    )
    with pytest.raises(ValueError, match="does not belong to the specified office"):
        create_receipt(db=db_session, receipt_in=receipt_in, user_id=s["user"].id)


# =========================================================================
# END-TO-END UI WORKFLOW TESTS
# =========================================================================

def test_goods_receipt_ui_workflow(auth_client: TestClient, db_session: Session, test_setup):
    client = auth_client
    s = test_setup

    # 1. Test GET /receipts (List Page)
    res_list = client.get("/receipts")
    assert res_list.status_code == 200
    assert "Goods Receipts Register" in res_list.text
    assert "New Goods Receipt" in res_list.text

    # 2. Test GET /receipts/new (Create Page)
    res_new = client.get("/receipts/new")
    assert res_new.status_code == 200
    assert "New Goods Receipt" in res_new.text
    assert "Save as Draft" in res_new.text
    assert "Post to Stock" in res_new.text

    # 3. Test POST /receipts/new with action_type=save_draft
    res_save_draft = client.post(
        "/receipts/new",
        data={
            "action_type": "save_draft",
            "receipt_date": date.today().isoformat(),
            "office_id": str(s["office"].id),
            "section_id": str(s["section"].id),
            "financial_year_id": str(s["fy"].id),
            "supplier_name": "Acme Tools Ltd",
            "reference_no": "INV-1002",
            "remarks": "Draft receipt from UI",
            "item_id[]": [str(s["item1"].id), str(s["item2"].id)],
            "quantity[]": ["40.0", "15.0"],
            "unit_price[]": ["300.0", "450.0"],
            "line_remarks[]": ["Line 1", "Line 2"],
        },
        follow_redirects=False,
    )
    assert res_save_draft.status_code == 303
    location = res_save_draft.headers["location"]
    assert "/receipts/view/" in location

    receipt_id = int(location.split("/view/")[1].split("?")[0])

    # Verify View page for Draft
    res_view_draft = client.get(f"/receipts/view/{receipt_id}")
    assert res_view_draft.status_code == 200
    assert "Acme Tools Ltd" in res_view_draft.text
    assert "INV-1002" in res_view_draft.text
    assert "DRAFT" in res_view_draft.text
    assert "Edit Draft" in res_view_draft.text

    # Stock should still be 0
    assert get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office"].id) == 0.0

    # 4. Test GET /receipts/edit/{receipt_id} (Edit Page)
    res_edit_page = client.get(f"/receipts/edit/{receipt_id}")
    assert res_edit_page.status_code == 200
    assert "Edit Goods Receipt Draft" in res_edit_page.text

    # 5. Test POST /receipts/edit/{receipt_id} to update
    res_update_draft = client.post(
        f"/receipts/edit/{receipt_id}",
        data={
            "action_type": "save_draft",
            "receipt_date": date.today().isoformat(),
            "section_id": str(s["section"].id),
            "supplier_name": "Acme Tools International",
            "reference_no": "INV-1002-REV",
            "remarks": "Updated draft remarks",
            "item_id[]": [str(s["item1"].id)],
            "quantity[]": ["60.0"],
            "unit_price[]": ["320.0"],
            "line_remarks[]": ["Updated single line"],
        },
        follow_redirects=False,
    )
    assert res_update_draft.status_code == 303

    # 6. Test POST /receipts/post/{receipt_id} (Post to Stock)
    res_post = client.post(f"/receipts/post/{receipt_id}", follow_redirects=False)
    assert res_post.status_code == 303
    assert f"/receipts/view/{receipt_id}?success=" in res_post.headers["location"]

    # Verify View page for POSTED receipt
    res_view_posted = client.get(f"/receipts/view/{receipt_id}")
    assert res_view_posted.status_code == 200
    assert "POSTED" in res_view_posted.text
    assert "Print GRN" in res_view_posted.text
    # Edit button should no longer appear on posted receipt
    assert "Edit Draft" not in res_view_posted.text

    # Verify Stock increased in ledger
    stock_after_post = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office"].id)
    assert stock_after_post == 60.0

    # 7. Test Printable GRN page
    res_print = client.get(f"/receipts/print/{receipt_id}")
    assert res_print.status_code == 200
    assert "GOODS RECEIPT NOTE (GRN)" in res_print.text
    assert "Acme Tools International" in res_print.text
    assert "INV-1002-REV" in res_print.text


def test_local_purchase_temporary_item_lifecycle(db_session: Session, test_setup):
    s = test_setup

    # 1. Create a Local Purchase / Temporary Item
    lp_item = create_temporary_item(
        db=db_session,
        name=f"Special Seal Kit {s['uid']}",
        category_id=s["item1"].category_id,
        unit_id=s["unit"].id,
        specification="Custom local fabrication",
        remarks="One-off purchase",
    )
    assert lp_item.id is not None
    assert lp_item.is_temporary is True
    assert lp_item.code.startswith("LP-")

    # 2. Verify it is hidden from default permanent Item Master listing
    catalogue_items = get_all_items(db=db_session, search=s["uid"], include_temporary=False)
    assert not any(i.id == lp_item.id for i in catalogue_items["items"])

    # But included when include_temporary=True
    all_items = get_all_items(db=db_session, search=s["uid"], include_temporary=True)
    assert any(i.id == lp_item.id for i in all_items["items"])

    # 3. Receive Local Purchase item via Goods Receipt
    receipt_in = ReceiptCreate(
        financial_year_id=s["fy"].id,
        office_id=s["office"].id,
        supplier_name="City Hardware Market",
        reference_no="CASH-MEMO-55",
        lines=[
            ReceiptLineCreate(item_id=lp_item.id, quantity=12.0, unit_price=450.0, remarks="Local urgent buy")
        ],
    )
    receipt = create_receipt(db=db_session, receipt_in=receipt_in, user_id=s["user"].id)
    post_receipt(db=db_session, receipt_id=receipt.id, user_id=s["user"].id)

    # 4. Verify Stock increased in authoritative StockMovement ledger
    stock = get_item_stock(db=db_session, item_id=lp_item.id, office_id=s["office"].id)
    assert stock == 12.0

    # 5. Promote Local Purchase item to Permanent Catalogue Item
    promoted = promote_temporary_item(
        db=db_session,
        item_id=lp_item.id,
        code=f"CAT-SEAL-{s['uid'].upper()}",
        name=f"Hydraulic Seal Kit Standard {s['uid']}",
    )
    assert promoted.id == lp_item.id  # item_id preserved!
    assert promoted.is_temporary is False
    assert promoted.code == f"CAT-SEAL-{s['uid'].upper()}"

    # Stock movements and historical stock ledger preserved
    assert get_item_stock(db=db_session, item_id=lp_item.id, office_id=s["office"].id) == 12.0

    # Now appears in normal catalogue listing
    updated_catalogue = get_all_items(db=db_session, search=s["uid"], include_temporary=False)
    assert any(i.id == lp_item.id for i in updated_catalogue["items"])


def test_quick_create_item_endpoint_and_receipt_integration(auth_client: TestClient, db_session: Session, test_setup):
    client = auth_client
    s = test_setup

    # 1. Test POST /receipts/quick-create-item
    res = client.post(
        "/receipts/quick-create-item",
        json={
            "name": f"Instant Local Tool {s['uid']}",
            "category_id": s["item1"].category_id,
            "unit_id": s["unit"].id,
            "specification": "Hardware store buy",
            "remarks": "On the fly item",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    created_item = data["item"]
    assert created_item["is_temporary"] is True
    assert created_item["code"].startswith("LP-")

    # 2. Use newly created item in Goods Receipt submission
    res_receipt = client.post(
        "/receipts/new",
        data={
            "action_type": "post",
            "receipt_date": date.today().isoformat(),
            "office_id": str(s["office"].id),
            "financial_year_id": str(s["fy"].id),
            "supplier_name": "Metro Hardware",
            "reference_no": "CASH-888",
            "item_id[]": [str(created_item["id"])],
            "quantity[]": ["20.0"],
            "unit_price[]": ["150.0"],
            "line_remarks[]": ["Local Purchase Receipt"],
        },
        follow_redirects=False,
    )
    assert res_receipt.status_code == 303

    # Stock should be 20.0
    assert get_item_stock(db=db_session, item_id=created_item["id"], office_id=s["office"].id) == 20.0

