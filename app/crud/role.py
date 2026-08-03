from sqlalchemy import func, or_
from sqlalchemy.orm import Session
import math

from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.core.constants import PAGE_SIZE


def create_role(db: Session, role: RoleCreate):

    code = role.code.strip().upper()
    name = role.name.strip().title()
    description = role.description.strip() if role.description else None

    existing_code = (
        db.query(Role)
        .filter(
            func.upper(Role.code) == code,
            Role.is_active == True,
        )
        .first()
    )

    if existing_code:
        raise ValueError("Role code already exists.")

    existing_name = (
        db.query(Role)
        .filter(
            func.lower(Role.name) == name.lower(),
            Role.is_active == True,
        )
        .first()
    )

    if existing_name:
        raise ValueError("Role name already exists.")

    db_role = Role(
        code=code,
        name=name,
        description=description,
    )

    db.add(db_role)

    try:
        db.commit()
        db.refresh(db_role)
        return db_role
    except Exception:
        db.rollback()
        raise


def get_all_roles(
    db: Session,
    search: str = "",
    page: int = 1,
):

    query = db.query(Role).filter(Role.is_active == True)

    if search:
        search = search.strip()

        query = query.filter(
            or_(
                Role.code.ilike(f"%{search}%"),
                Role.name.ilike(f"%{search}%"),
                Role.description.ilike(f"%{search}%"),
            )
        )

    total_records = query.count()

    roles = (
        query
        .order_by(Role.name)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return {
        "items": roles,
        "current_page": page,
        "page_size": PAGE_SIZE,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / PAGE_SIZE) if total_records else 1,
    }


def get_role_by_id(db: Session, role_id: int):

    return (
        db.query(Role)
        .filter(
            Role.id == role_id,
            Role.is_active == True,
        )
        .first()
    )


def update_role(
    db: Session,
    role_id: int,
    role: RoleUpdate,
):

    db_role = get_role_by_id(db, role_id)

    if not db_role:
        raise ValueError("Role not found.")

    if role.code:

        code = role.code.strip().upper()

        existing_code = (
            db.query(Role)
            .filter(
                func.upper(Role.code) == code,
                Role.id != role_id,
                Role.is_active == True,
            )
            .first()
        )

        if existing_code:
            raise ValueError("Role code already exists.")

        db_role.code = code

    if role.name:

        name = role.name.strip().title()

        existing_name = (
            db.query(Role)
            .filter(
                func.lower(Role.name) == name.lower(),
                Role.id != role_id,
                Role.is_active == True,
            )
            .first()
        )

        if existing_name:
            raise ValueError("Role name already exists.")

        db_role.name = name

    if role.description is not None:
        db_role.description = role.description.strip() if role.description else None

    try:
        db.commit()
        db.refresh(db_role)
        return db_role

    except Exception:
        db.rollback()
        raise


def delete_role(
    db: Session,
    role_id: int,
):

    db_role = get_role_by_id(db, role_id)

    if not db_role:
        raise ValueError("Role not found.")

    db_role.is_active = False

    try:
        db.commit()
        return db_role

    except Exception:
        db.rollback()
        raise