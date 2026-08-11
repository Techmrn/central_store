import uuid
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.asset import Asset
from app.models.category import Category
from app.models.enums import AssetStatus, Category_Type, DestinationType, IndentStatus, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.indent_line import IndentLine
from app.models.item import Item
from app.models.unit import Unit
from app.models.office import Office
from app.models.opening_stock import OpeningStock
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
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
def auth_client(db_session: Session):
    seed_permissions(db_session)
    seed_admin_permissions(db_session)

    user = db_session.query(User).filter(User.is_active == True).first()
    if not user:
        office = db_session.query(Office).filter(Office.is_active == True).first()
        user = User(
            code="U-TEST1",
            username="test_storekeeper",
            password_hash=hash_password("admin123"),
            full_name="Test Storekeeper",
            office_id=office.id if office else 1,
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

    app.dependency_overrides[get_current_user_ui] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_physical_indent_recording_and_single_step_submit_workflow(auth_client, db_session: Session):
    client = auth_client
    uid = uuid.uuid4().hex[:6]
    printed_indent_no = f"PRINT-{uid}"

    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    store_office = db_session.query(Office).filter(Office.is_active == True).first()
    mat_cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    asset_cat = db_session.query(Category).filter(Category.type == Category_Type.ASSET, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    # 1. Create items & stock
    mat_item = Item(name=f"Phys Test Material {uid}", code=f"PHY-MAT-{uid}", category_id=mat_cat.id, unit_id=unit.id)
    ast_item = Item(name=f"Phys Test Asset {uid}", code=f"PHY-AST-{uid}", category_id=asset_cat.id, unit_id=unit.id)
    db_session.add_all([mat_item, ast_item])
    db_session.commit()

    op1 = OpeningStock(financial_year_id=fy.id, office_id=store_office.id, item_id=mat_item.id, quantity=100.0, unit_rate=100.0, total_value=10000.0)
    op2 = OpeningStock(financial_year_id=fy.id, office_id=store_office.id, item_id=ast_item.id, quantity=2.0, unit_rate=30000.0, total_value=60000.0)
    db_session.add_all([op1, op2])
    db_session.commit()

    ast_record = Asset(asset_no=f"PHY-AST-NO-{uid}", item_id=ast_item.id, office_id=store_office.id, status=AssetStatus.IN_STORE)
    db_session.add(ast_record)
    db_session.commit()

    # 2. Test Dashboard UI & Record Physical Indent link
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert "Record Physical Indent" in res_dash.text

    # 3. Test Physical Indent Entry Form Page
    res_entry_page = client.get("/indents/entry")
    assert res_entry_page.status_code == 200
    assert "Record Physical Indent" in res_entry_page.text

    # 4. Test Temporary Save Action (action_type=save)
    res_save = client.post(
        "/indents/entry",
        data={
            "indent_no": printed_indent_no,
            "indent_date": date.today().isoformat(),
            "office_id": str(store_office.id),
            "reference_no": f"REF-{uid}",
            "remarks": "Temporary save test",
            "action_type": "save",
            "item_id[]": [str(mat_item.id), str(ast_item.id)],
            "requested_qty[]": ["20.0", "1.0"],
            "issued_qty[]": ["15.0", "1.0"],
            "line_remarks[]": ["Material supply", "Asset supply"],
        },
        follow_redirects=False,
    )
    assert res_save.status_code == 303
    assert "/indents?success=" in res_save.headers["location"]

    # Verify saved indent in DB (status DRAFT / Saved)
    saved_indent = (
        db_session.query(Indent)
        .filter(
            Indent.office_id == store_office.id,
            Indent.indent_no == printed_indent_no,
            Indent.is_active == True,
        )
        .first()
    )
    assert saved_indent is not None
    assert saved_indent.status == IndentStatus.DRAFT
    assert len(saved_indent.lines) == 2

    # 5. Test Duplicate Printed Indent Prevention
    res_dup = client.post(
        "/indents/entry",
        data={
            "indent_no": printed_indent_no,
            "indent_date": date.today().isoformat(),
            "office_id": str(store_office.id),
            "action_type": "save",
            "item_id[]": [str(mat_item.id)],
            "requested_qty[]": ["5.0"],
            "issued_qty[]": ["5.0"],
        },
        follow_redirects=False,
    )
    assert res_dup.status_code == 303
    assert "already+exists" in res_dup.headers["location"]

    # 6. Test Single-Step SUBMIT Action for Saved Entry
    res_submit = client.post(
        f"/indents/{saved_indent.id}/process",
        data={
            "action_type": "submit",
            f"issued_qty_{saved_indent.lines[0].id}": "15.0",
            f"remarks_{saved_indent.lines[0].id}": "Issued paper",
            f"issued_qty_{saved_indent.lines[1].id}": "1.0",
            f"remarks_{saved_indent.lines[1].id}": "Issued laptop",
        },
        follow_redirects=False,
    )
    assert res_submit.status_code == 303
    assert f"/indents/receipt/{saved_indent.id}" in res_submit.headers["location"]

    # 7. Verify atomic transaction completion
    db_session.refresh(saved_indent)
    db_session.refresh(ast_record)
    assert saved_indent.status == IndentStatus.CLOSED
    assert ast_record.status == AssetStatus.ISSUED

    # 8. Test Receipt Page
    res_receipt = client.get(f"/indents/receipt/{saved_indent.id}")
    assert res_receipt.status_code == 200
    assert printed_indent_no in res_receipt.text
    assert "Completed &amp; Posted Successfully" in res_receipt.text or "Completed & Posted Successfully" in res_receipt.text
