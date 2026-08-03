"""
Starter for app/crud/user.py

Implement:
- create_user() (as discussed)
- get_all_users()
- get_user_by_id()
- get_user_by_username()
- update_user()
- delete_user()

Validation:
- PEN (code): numeric, 6/7 digits
- Username unique (lowercase)
- Office exists
- Section belongs to selected office
- Soft delete
- Temporary password_hash=user.password
"""

import math

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.constants import PAGE_SIZE

from app.models.user import User
from app.models.office import Office
from app.models.section import Section

from app.schemas.user import (
    UserCreate,
    UserUpdate,
)


def create_user(db: Session, user: UserCreate):

    code = user.code.strip()
    username = user.username.strip().lower()
    full_name = user.full_name.strip().title()
    designation = user.designation.strip() if user.designation else None
    email = user.email.strip().lower() if user.email else None
    mobile = user.mobile.strip() if user.mobile else None
    remarks = user.remarks.strip() if user.remarks else None

    # ----------------------------------------------------
    # Validate PEN Number
    # ----------------------------------------------------

    if not code.isdigit():
        raise ValueError("PEN Number must contain only digits.")

    if len(code) not in (6, 7):
        raise ValueError("PEN Number must be 6 or 7 digits.")

    # ----------------------------------------------------
    # Duplicate Code
    # ----------------------------------------------------

    existing_code = (
        db.query(User)
        .filter(
            User.code == code,
            User.is_active == True,
        )
        .first()
    )

    if existing_code:
        raise ValueError("PEN Number already exists.")

    # ----------------------------------------------------
    # Duplicate Username
    # ----------------------------------------------------

    existing_username = (
        db.query(User)
        .filter(
            func.lower(User.username) == username,
            User.is_active == True,
        )
        .first()
    )

    if existing_username:
        raise ValueError("Username already exists.")

    # ----------------------------------------------------
    # Validate Office
    # ----------------------------------------------------

    office = (
        db.query(Office)
        .filter(
            Office.id == user.office_id,
            Office.is_active == True,
        )
        .first()
    )

    if not office:
        raise ValueError("Invalid office selected.")

    # ----------------------------------------------------
    # Validate Section
    # ----------------------------------------------------

    if user.section_id is not None:

        section = (
            db.query(Section)
            .filter(
                Section.id == user.section_id,
                Section.office_id == user.office_id,
                Section.is_active == True,
            )
            .first()
        )

        if not section:
            raise ValueError(
                "Selected section does not belong to the selected office."
            )

    # ----------------------------------------------------
    # Create User
    # ----------------------------------------------------

    db_user = User(
        code=code,
        username=username,
        password_hash=user.password,      # Will be hashed later
        full_name=full_name,
        designation=designation,
        office_id=user.office_id,
        section_id=user.section_id,
        email=email,
        mobile=mobile,
        remarks=remarks,
    )

    db.add(db_user)

    try:
        db.commit()
        db.refresh(db_user)
        return db_user

    except Exception:
        db.rollback()
        raise

# ----------------------------------------------------
# Get all User
# ----------------------------------------------------


def get_all_users(
    db: Session,
    search: str = "",
    page: int = 1,
):

    query = (
        db.query(User)
        .join(
            Office,
            User.office_id == Office.id,
        )
        .outerjoin(
            Section,
            User.section_id == Section.id,
        )
        .filter(
            User.is_active == True,
            Office.is_active == True,
        )
    )

    if search:

        search = search.strip()

        query = query.filter(
            or_(
                User.code.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
                Office.name.ilike(f"%{search}%"),
                Section.name.ilike(f"%{search}%"),
            )
        )

    total_records = query.count()

    users = (
        query
        .order_by(User.full_name)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return {
        "items": users,
        "current_page": page,
        "page_size": PAGE_SIZE,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / PAGE_SIZE)
        if total_records
        else 1,
    }


#------------------------------------------------------------
#       Get by USER NAME & ID
#------------------------------------------------------------

def get_user_by_id(
    db: Session,
    user_id: int,
):

    return (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,
        )
        .first()
    )



def get_user_by_username(
    db: Session,
    username: str,
):

    username = username.strip().lower()

    return (
        db.query(User)
        .filter(
            func.lower(User.username) == username,
            User.is_active == True,
        )
        .first()
    )

#************* UPDATE USER ********************************
#-----------------------------------------------------------

def update_user(
    db: Session,
    user_id: int,
    user: UserUpdate,
):

    db_user = get_user_by_id(db, user_id)

    if not db_user:
        raise ValueError("User not found.")

    # ----------------------------------------------------
    # PEN Number
    # ----------------------------------------------------

    if user.code is not None:

        code = user.code.strip()

        if not code.isdigit():
            raise ValueError("PEN Number must contain only digits.")

        if len(code) not in (6, 7):
            raise ValueError("PEN Number must be 6 or 7 digits.")

        existing_code = (
            db.query(User)
            .filter(
                User.code == code,
                User.id != user_id,
                User.is_active == True,
            )
            .first()
        )

        if existing_code:
            raise ValueError("PEN Number already exists.")

        db_user.code = code

    # ----------------------------------------------------
    # Username
    # ----------------------------------------------------

    if user.username is not None:

        username = user.username.strip().lower()

        existing_username = (
            db.query(User)
            .filter(
                func.lower(User.username) == username,
                User.id != user_id,
                User.is_active == True,
            )
            .first()
        )

        if existing_username:
            raise ValueError("Username already exists.")

        db_user.username = username

    # ----------------------------------------------------
    # Password
    # ----------------------------------------------------

    if user.password:

        # Later replace with password hashing
        db_user.password_hash = user.password

    # ----------------------------------------------------
    # Full Name
    # ----------------------------------------------------

    if user.full_name is not None:
        db_user.full_name = user.full_name.strip().title()

    # ----------------------------------------------------
    # Designation
    # ----------------------------------------------------

    if user.designation is not None:
        db_user.designation = (
            user.designation.strip()
            if user.designation
            else None
        )

    # ----------------------------------------------------
    # Office
    # ----------------------------------------------------

    if user.office_id is not None:

        office = (
            db.query(Office)
            .filter(
                Office.id == user.office_id,
                Office.is_active == True,
            )
            .first()
        )

        if not office:
            raise ValueError("Invalid office selected.")

        db_user.office_id = user.office_id

    # ----------------------------------------------------
    # Section
    # ----------------------------------------------------

    if user.section_id is not None:

        office_id = (
            user.office_id
            if user.office_id is not None
            else db_user.office_id
        )

        section = (
            db.query(Section)
            .filter(
                Section.id == user.section_id,
                Section.office_id == office_id,
                Section.is_active == True,
            )
            .first()
        )

        if not section:
            raise ValueError(
                "Selected section does not belong to the selected office."
            )

        db_user.section_id = user.section_id

    # ----------------------------------------------------
    # Email
    # ----------------------------------------------------

    if user.email is not None:
        db_user.email = (
            user.email.strip().lower()
            if user.email
            else None
        )

    # ----------------------------------------------------
    # Mobile
    # ----------------------------------------------------

    if user.mobile is not None:
        db_user.mobile = (
            user.mobile.strip()
            if user.mobile
            else None
        )

    # ----------------------------------------------------
    # Remarks
    # ----------------------------------------------------

    if user.remarks is not None:
        db_user.remarks = (
            user.remarks.strip()
            if user.remarks
            else None
        )

    try:

        db.commit()
        db.refresh(db_user)

        return db_user

    except Exception:

        db.rollback()
        raise


#---------------------------------------------------------------
# Delete User
#---------------------------------------------------------------

def delete_user(
    db: Session,
    user_id: int,
):

    db_user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if not db_user:
        raise ValueError("User not found.")

    db_user.is_active = False

    try:

        db.commit()

        return db_user

    except Exception:

        db.rollback()
        raise

    