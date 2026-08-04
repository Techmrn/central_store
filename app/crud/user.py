from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.office import Office
from app.models.section import Section

from app.schemas.user import (
    UserCreate,
    UserUpdate,
)

from app.core.pagination import get_pagination_result


# ---------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------

def normalize_user_code(code: str) -> str:
    """
    Returns normalized PEN number.
    """
    return code.strip()


def normalize_username(username: str) -> str:
    """
    Returns lowercase username.
    """
    return username.strip().lower()


def normalize_full_name(name: str) -> str:
    """
    Returns formatted display name.
    """
    return name.strip().title()


# ---------------------------------------------------------------
# Create
# ---------------------------------------------------------------

def create_user(
    db: Session,
    user: UserCreate,
):

    code = normalize_user_code(user.code)
    username = normalize_username(user.username)
    full_name = normalize_full_name(user.full_name)

    designation = (
        user.designation.strip()
        if user.designation
        else None
    )

    email = (
        user.email.strip().lower()
        if user.email
        else None
    )

    mobile = (
        user.mobile.strip()
        if user.mobile
        else None
    )

    remarks = (
        user.remarks.strip()
        if user.remarks
        else None
    )

    # -----------------------------------------------------------
    # Validate PEN Number
    # -----------------------------------------------------------

    if not code.isdigit():
        raise ValueError(
            "PEN Number must contain only digits."
        )

    if len(code) not in (6, 7):
        raise ValueError(
            "PEN Number must be 6 or 7 digits."
        )

    # -----------------------------------------------------------
    # Duplicate PEN
    # -----------------------------------------------------------

    duplicate_code = (
        db.query(User)
        .filter(
            func.trim(User.code) == code,
        )
        .first()
    )

    if duplicate_code:
        raise ValueError(
            "PEN Number already exists."
        )

    # -----------------------------------------------------------
    # Duplicate Username
    # -----------------------------------------------------------

    duplicate_username = (
        db.query(User)
        .filter(
            func.lower(func.trim(User.username))
            == username,
            User.is_active == True,
        )
        .first()
    )

    if duplicate_username:
        raise ValueError(
            "Username already exists."
        )

    # -----------------------------------------------------------
    # Validate Office
    # -----------------------------------------------------------

    office = (
        db.query(Office)
        .filter(
            Office.id == user.office_id,
            Office.is_active == True,
        )
        .first()
    )

    if office is None:
        raise ValueError(
            "Invalid office selected."
        )

    # -----------------------------------------------------------
    # Validate Section
    # -----------------------------------------------------------

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

        if section is None:
            raise ValueError(
                "Selected section does not belong to the selected office."
            )

    db_user = User(
        code=code,
        username=username,
        password_hash=user.password,      # Temporary
        full_name=full_name,
        designation=designation,
        office_id=user.office_id,
        section_id=user.section_id,
        email=email,
        mobile=mobile,
        remarks=remarks,
    )

    try:

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user

    except IntegrityError:

        db.rollback()

        raise ValueError(
            "PEN Number already exists."
        )

    except Exception:

        db.rollback()
        raise


    # ---------------------------------------------------------------
# Read All
# ---------------------------------------------------------------

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

    query = query.order_by(User.full_name)

    return get_pagination_result(
        query=query,
        page=page,
    )


# ---------------------------------------------------------------
# Read One
# ---------------------------------------------------------------

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


# ---------------------------------------------------------------
# Read by Username
# ---------------------------------------------------------------

def get_user_by_username(
    db: Session,
    username: str,
):

    username = normalize_username(username)

    return (
        db.query(User)
        .filter(
            func.lower(func.trim(User.username)) == username,
            User.is_active == True,
        )
        .first()
    )

# ---------------------------------------------------------------
# Update
# ---------------------------------------------------------------

def update_user(
    db: Session,
    user_id: int,
    user: UserUpdate,
):

    db_user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,
        )
        .first()
    )

    if db_user is None:
        return None

    update_data = user.model_dump(exclude_unset=True)

    # -----------------------------------------------------------
    # PEN Number
    # -----------------------------------------------------------

    if "code" in update_data:

        code = normalize_user_code(update_data["code"])

        if not code.isdigit():
            raise ValueError(
                "PEN Number must contain only digits."
            )

        if len(code) not in (6, 7):
            raise ValueError(
                "PEN Number must be 6 or 7 digits."
            )

        duplicate = (
            db.query(User)
            .filter(
                func.trim(User.code) == code,
                User.id != user_id,
            )
            .first()
        )

        if duplicate:
            raise ValueError(
                "PEN Number already exists."
            )

        db_user.code = code

    # -----------------------------------------------------------
    # Username
    # -----------------------------------------------------------

    if "username" in update_data:

        username = normalize_username(
            update_data["username"]
        )

        duplicate = (
            db.query(User)
            .filter(
                func.lower(func.trim(User.username))
                == username,
                User.id != user_id,
                User.is_active == True,
            )
            .first()
        )

        if duplicate:
            raise ValueError(
                "Username already exists."
            )

        db_user.username = username

    # -----------------------------------------------------------
    # Password
    # -----------------------------------------------------------

    if "password" in update_data:

        # Replace with password hashing later
        db_user.password_hash = update_data["password"]

    # -----------------------------------------------------------
    # Full Name
    # -----------------------------------------------------------

    if "full_name" in update_data:

        db_user.full_name = normalize_full_name(
            update_data["full_name"]
        )

    # -----------------------------------------------------------
    # Designation
    # -----------------------------------------------------------

    if "designation" in update_data:

        designation = update_data["designation"]

        db_user.designation = (
            designation.strip()
            if designation
            else None
        )

    # -----------------------------------------------------------
    # Office
    # -----------------------------------------------------------

    if "office_id" in update_data:

        office = (
            db.query(Office)
            .filter(
                Office.id == update_data["office_id"],
                Office.is_active == True,
            )
            .first()
        )

        if office is None:
            raise ValueError(
                "Invalid office selected."
            )

        db_user.office_id = update_data["office_id"]

    # -----------------------------------------------------------
    # Section
    # -----------------------------------------------------------

    if "section_id" in update_data:

        office_id = (
            update_data["office_id"]
            if "office_id" in update_data
            else db_user.office_id
        )

        if update_data["section_id"] is None:

            db_user.section_id = None

        else:

            section = (
                db.query(Section)
                .filter(
                    Section.id == update_data["section_id"],
                    Section.office_id == office_id,
                    Section.is_active == True,
                )
                .first()
            )

            if section is None:
                raise ValueError(
                    "Selected section does not belong to the selected office."
                )

            db_user.section_id = update_data["section_id"]

    # -----------------------------------------------------------
    # Email
    # -----------------------------------------------------------

    if "email" in update_data:

        email = update_data["email"]

        db_user.email = (
            email.strip().lower()
            if email
            else None
        )

    # -----------------------------------------------------------
    # Mobile
    # -----------------------------------------------------------

    if "mobile" in update_data:

        mobile = update_data["mobile"]

        db_user.mobile = (
            mobile.strip()
            if mobile
            else None
        )

    # -----------------------------------------------------------
    # Remarks
    # -----------------------------------------------------------

    if "remarks" in update_data:

        remarks = update_data["remarks"]

        db_user.remarks = (
            remarks.strip()
            if remarks
            else None
        )

    try:

        db.commit()
        db.refresh(db_user)

        return db_user

    except IntegrityError:

        db.rollback()

        raise ValueError(
            "PEN Number already exists."
        )

    except Exception:

        db.rollback()
        raise

    # ---------------------------------------------------------------
# Soft Delete
# ---------------------------------------------------------------

def delete_user(
    db: Session,
    user_id: int,
):

    db_user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,
        )
        .first()
    )

    if db_user is None:
        return None

    db_user.is_active = False

    try:

        db.commit()
        db.refresh(db_user)

        return db_user

    except Exception:

        db.rollback()
        raise


# ---------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------

def get_user_lookup(
    db: Session,
):

    return (
        db.query(User)
        .filter(
            User.is_active == True,
        )
        .order_by(User.full_name)
        .all()
    )