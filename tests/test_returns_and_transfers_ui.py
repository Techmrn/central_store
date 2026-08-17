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
from app.models.section import Section
from app.models.stock_return import StockReturn
from app.models.stock_transfer import StockTransfer
from app.models.unit import Unit
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.services.stock_service import get_item_stock
from app.dependencies.ui_auth import get_current_user_ui
from app.services.permission_seed import seed_permissions, seed_admin_permissions
from app.crud.stock_return import create_return, delete_return, update_return, get_return_by_id
from app.crud.stock_transfer import create_transfer, delete_transfer, update_transfer, get_transfer_by_id
from app.services.posting_service import post_return, post_transfer
from app.models.stock_movement import StockMovement


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_setup(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    seed_permissions(db_session)
    seed_admin_permissions(db_session)

    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    if not fy:
        fy = FinancialYear(year_name="2026-2027", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), is_active=True)
        db_session.add(fy)
        db_session.commit()
        db_session.refresh(fy)

    office1 = db_session.query(Office).filter(Office.is_active == True).first()
    if not office1:
        office1 = Office(name=f"Main Store {uid}", code=f"MS-{uid}", office_type=OfficeType.GCP, is_active=True)
        db_session.add(office1)
        db_session.commit()
        db_session.refresh(office1)

    office2 = Office(name=f"Branch Store {uid}", code=f"BS-{uid}", office_type=OfficeType.BRANCH, is_active=True)
    db_session.add(office2)
    db_session.commit()
    db_session.refresh(office2)

    section = Section(name=f"Production Section {uid}", code=f"PRD-{uid}", office_id=office1.id, is_active=True)
    db_session.add(section)
    db_session.commit()
    db_session.refresh(section)

    user = db_session.query(User).filter(User.is_active == True).first()
    if not user:
        user = User(
            username=f"storekeeper_{uid}",
            password_hash=hash_password("password123"),
            full_name="Store Keeper",
            is_active=True,
            office_id=office1.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    admin_role = db_session.query(Role).filter(Role.is_active == True).first()
    if admin_role:
        existing_ur = db_session.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == admin_role.id).first()
        if not existing_ur:
            db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
            db_session.commit()

    unit = db_session.query(Unit).filter(Unit.is_active == True).first()
    if not unit:
        unit = Unit(name="Number", symbol="Nos", code="NOS", is_active=True)
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)

    cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    if not cat:
        cat = Category(name=f"Material Cat {uid}", code=f"MAT-{uid}", type=Category_Type.MATERIAL, is_active=True)
        db_session.add(cat)
        db_session.commit()
        db_session.refresh(cat)

    item1 = Item(name=f"Steel Plate {uid}", code=f"STP-{uid}", category_id=cat.id, unit_id=unit.id, is_active=True)
    item2 = Item(name=f"Welding Rod {uid}", code=f"ROD-{uid}", category_id=cat.id, unit_id=unit.id, is_active=True)
    db_session.add_all([item1, item2])
    db_session.commit()
    db_session.refresh(item1)
    db_session.refresh(item2)

    return {
        "uid": uid,
        "fy": fy,
        "office1": office1,
        "office2": office2,
        "section": section,
        "user": user,
        "unit": unit,
        "cat": cat,
        "item1": item1,
        "item2": item2,
    }


@pytest.fixture
def auth_client(test_setup):
    user = test_setup["user"]
    app.dependency_overrides[get_current_user_ui] = lambda: user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_stock_return_ui_workflow(auth_client: TestClient, db_session: Session, test_setup):
    client = auth_client
    s = test_setup

    # 1. Test GET /stock-returns (Register list)
    res_list = client.get("/stock-returns")
    assert res_list.status_code == 200
    assert "Stock Returns Register" in res_list.text

    # 2. Test GET /stock-returns/new (Create form)
    res_new = client.get("/stock-returns/new")
    assert res_new.status_code == 200
    assert "Record Stock Return" in res_new.text
    assert "Save as Draft" in res_new.text

    # 3. Test POST /stock-returns/new (Save as Draft)
    res_save = client.post(
        "/stock-returns/new",
        data={
            "action_type": "save_draft",
            "return_date": date.today().isoformat(),
            "office_id": str(s["office1"].id),
            "section_id": str(s["section"].id),
            "financial_year_id": str(s["fy"].id),
            "remarks": "Excess project material returned",
            "item_id[]": [str(s["item1"].id)],
            "quantity[]": ["15.0"],
            "line_remarks[]": ["Unused sheets"],
        },
        follow_redirects=False,
    )
    assert res_save.status_code == 303
    location = res_save.headers["location"]
    assert "/stock-returns/view/" in location
    return_id = int(location.split("/view/")[1].split("?")[0])

    # 4. View Draft Return
    res_view = client.get(f"/stock-returns/view/{return_id}")
    assert res_view.status_code == 200
    assert "DRAFT" in res_view.text
    assert "Excess project material returned" in res_view.text

    # Stock should not change in draft
    assert get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office1"].id) == 0.0

    # 5. Edit Draft Return
    res_edit_page = client.get(f"/stock-returns/edit/{return_id}")
    assert res_edit_page.status_code == 200
    assert "Edit Stock Return Draft" in res_edit_page.text

    res_update = client.post(
        f"/stock-returns/edit/{return_id}",
        data={
            "action_type": "save_draft",
            "return_date": date.today().isoformat(),
            "section_id": str(s["section"].id),
            "remarks": "Updated excess return remarks",
            "item_id[]": [str(s["item1"].id)],
            "quantity[]": ["20.0"],
            "line_remarks[]": ["Updated 20 sheets"],
        },
        follow_redirects=False,
    )
    assert res_update.status_code == 303

    # 6. Post Return to Stock
    res_post = client.post(f"/stock-returns/post/{return_id}", follow_redirects=False)
    assert res_post.status_code == 303

    # Verify Stock increased in store
    assert get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office1"].id) == 20.0

    # 7. Printable Slip
    res_print = client.get(f"/stock-returns/print/{return_id}")
    assert res_print.status_code == 200
    assert "STOCK RETURN SLIP" in res_print.text


def test_stock_transfer_ui_workflow(auth_client: TestClient, db_session: Session, test_setup):
    client = auth_client
    s = test_setup

    # Give source store some initial stock (100.0)
    initial_movement = StockMovement(
        financial_year_id=s["fy"].id,
        item_id=s["item1"].id,
        office_id=s["office1"].id,
        movement_type=MovementType.RECEIPT,
        quantity_in=100.0,
        quantity_out=0.0,
        movement_date=date.today(),
        reference_type="SETUP",
        reference_id=1,
        reference_no="INIT-01",
    )
    db_session.add(initial_movement)
    db_session.commit()

    source_stock_before = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office1"].id)
    target_stock_before = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office2"].id)
    assert source_stock_before >= 100.0
    assert target_stock_before == 0.0

    # 1. Test GET /transfers (Register list)
    res_list = client.get("/transfers")
    assert res_list.status_code == 200
    assert "Stock Transfers Register" in res_list.text

    # 2. Test GET /transfers/new (Create form)
    res_new = client.get("/transfers/new")
    assert res_new.status_code == 200
    assert "New Stock Transfer" in res_new.text

    # 3. Test POST /transfers/new (Save as Draft)
    res_save = client.post(
        "/transfers/new",
        data={
            "action_type": "save_draft",
            "transfer_date": date.today().isoformat(),
            "from_office_id": str(s["office1"].id),
            "to_office_id": str(s["office2"].id),
            "financial_year_id": str(s["fy"].id),
            "remarks": "Inter-store transfer from main to branch",
            "item_id[]": [str(s["item1"].id)],
            "quantity[]": ["35.0"],
            "line_remarks[]": ["Transfer bundle A"],
        },
        follow_redirects=False,
    )
    assert res_save.status_code == 303
    location = res_save.headers["location"]
    assert "/transfers/view/" in location
    transfer_id = int(location.split("/view/")[1].split("?")[0])

    # 4. View Draft Transfer
    res_view = client.get(f"/transfers/view/{transfer_id}")
    assert res_view.status_code == 200
    assert "DRAFT" in res_view.text

    # Stock should remain unchanged during draft
    assert get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office2"].id) == 0.0

    # 5. Post Transfer to Stock
    res_post = client.post(f"/transfers/post/{transfer_id}", follow_redirects=False)
    assert res_post.status_code == 303

    # Stock should decrease at source and increase at target
    source_stock_after = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office1"].id)
    target_stock_after = get_item_stock(db=db_session, item_id=s["item1"].id, office_id=s["office2"].id)
    assert target_stock_after == 35.0
    assert source_stock_after == source_stock_before - 35.0

    # 6. Printable Voucher / Gate Pass
    res_print = client.get(f"/transfers/print/{transfer_id}")
    assert res_print.status_code == 200
    assert "INTER-STORE TRANSFER VOUCHER" in res_print.text


def test_transfer_same_location_rejected(auth_client: TestClient, db_session: Session, test_setup):
    client = auth_client
    s = test_setup

    res = client.post(
        "/transfers/new",
        data={
            "action_type": "save_draft",
            "transfer_date": date.today().isoformat(),
            "from_office_id": str(s["office1"].id),
            "to_office_id": str(s["office1"].id),  # Identical
            "financial_year_id": str(s["fy"].id),
            "item_id[]": [str(s["item1"].id)],
            "quantity[]": ["10.0"],
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "cannot+be+identical" in res.headers["location"]
