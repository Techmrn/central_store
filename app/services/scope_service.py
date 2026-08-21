from typing import Optional, List
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.office import Office, OfficeType
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.services.permission_service import get_user_roles

DEPARTMENT_VIEW_ROLES = {
    "ADMIN",
    "ADMINISTRATOR",
    "DIRECTOR",
    "SUPERINTENDENT",
}

STOREKEEPER_ROLES = {
    "ADMIN",
    "ADMINISTRATOR",
    "GSK",
    "GENERAL_STORE_KEEPER",
    "STOREKEEPER",
    "CENTRAL_STORE_KEEPER",
    "STORE_KEEPER",
}


def get_canonical_central_store_id(db: Session) -> Optional[int]:
    """
    Find the canonical Central Store office ID.
    Priority:
    1. Office with office_type == OfficeType.GCP (where Central Store is physically located)
    2. Office with code in ("CENTRAL_STORE", "CS", "GCP") or name containing "Central Store"
    3. Office with office_type == OfficeType.DIRECTORATE if no GCP office exists
    """
    # 1. Look for GCP office
    gcp_off = (
        db.query(Office)
        .filter(
            Office.office_type == OfficeType.GCP,
            Office.is_active == True,
        )
        .order_by(Office.id)
        .first()
    )
    if gcp_off:
        return gcp_off.id

    # 2. Look for explicit Central Store code or name
    cs_off = (
        db.query(Office)
        .filter(
            Office.is_active == True,
            or_(
                func.upper(Office.code).in_(["CENTRAL_STORE", "CS", "GCP"]),
                Office.name.ilike("%Central Store%"),
                Office.name.ilike("%Government Central Press%"),
            ),
        )
        .order_by(Office.id)
        .first()
    )
    if cs_off:
        return cs_off.id

    # 3. Fallback to Directorate office
    dir_off = (
        db.query(Office)
        .filter(
            Office.office_type == OfficeType.DIRECTORATE,
            Office.is_active == True,
        )
        .order_by(Office.id)
        .first()
    )
    if dir_off:
        return dir_off.id

    return None


def get_stock_office_id(db: Session, administrative_office_id: int) -> int:
    """
    Map an administrative office ID to its stock-owning store office ID.
    - Directorate & GCP share ONE Central Store stock balance.
    - Branches own their own independent stock balance.
    """
    if not administrative_office_id:
        return administrative_office_id

    office = db.query(Office).filter(Office.id == administrative_office_id).first()
    if not office:
        return administrative_office_id

    # Directorate and GCP share the Central Store stock balance
    if office.office_type in (OfficeType.DIRECTORATE, OfficeType.GCP):
        cs_id = get_canonical_central_store_id(db)
        if cs_id is not None:
            return cs_id

    # Branch offices, District Form Stores, etc. own their own store stock
    return administrative_office_id


def is_department_wide_viewer(db: Session, user: User) -> bool:
    """
    Check if the user has a department-wide view role (Director, Superintendent, Admin).
    """
    if not user:
        return False

    roles = get_user_roles(db=db, user_id=user.id)
    role_codes = {r.code.upper().strip() for r in roles if r.code}
    return bool(role_codes.intersection(DEPARTMENT_VIEW_ROLES))


def is_central_store_user(db: Session, user: User) -> bool:
    """
    Check if the user belongs to Central Store / Directorate / GCP.
    """
    if not user or not user.office_id:
        return False

    office = db.query(Office).filter(Office.id == user.office_id).first()
    if not office:
        return False

    if office.office_type in (OfficeType.DIRECTORATE, OfficeType.GCP):
        return True

    cs_id = get_canonical_central_store_id(db)
    return user.office_id == cs_id


def can_view_office(db: Session, user: User, office_id: int) -> bool:
    """
    Check if a user is authorized to view records for a specific office.
    """
    if not user or not office_id:
        return False

    # Department-wide viewers can view any office
    if is_department_wide_viewer(db, user):
        return True

    # Central Store user can view Central Store, Directorate, and GCP
    if is_central_store_user(db, user):
        target_office = db.query(Office).filter(Office.id == office_id).first()
        if target_office and target_office.office_type in (OfficeType.DIRECTORATE, OfficeType.GCP):
            return True
        cs_id = get_canonical_central_store_id(db)
        if office_id == cs_id or office_id == user.office_id:
            return True
        return False

    # Branch user can view only their own assigned office
    return user.office_id == office_id


def get_authorized_stock_office_ids(db: Session, user: User) -> List[int]:
    """
    Return the list of stock-owning store office IDs the user is authorized to transact against / hold stock in.
    - Admin: All stock store IDs
    - Central Storekeeper: Exactly ONE stock store ID (canonical Central Store)
    - Branch Storekeeper: Exactly ONE stock store ID (their branch office)
    - Viewers (Director, Superintendent, Office Head, Section User): Empty list (no stock transaction authority)
    """
    if not user:
        return []

    roles = get_user_roles(db=db, user_id=user.id)
    role_codes = {r.code.upper().strip() for r in roles if r.code}

    if "ADMIN" in role_codes or "ADMINISTRATOR" in role_codes:
        offices = db.query(Office.id).filter(Office.is_active == True).all()
        # Return unique stock-owning store IDs
        stock_ids = set()
        for off_id in [r[0] for r in offices]:
            stock_ids.add(get_stock_office_id(db, off_id))
        return list(stock_ids)

    if not role_codes.intersection(STOREKEEPER_ROLES):
        return []

    if is_central_store_user(db, user):
        cs_id = get_canonical_central_store_id(db)
        if cs_id is not None:
            return [cs_id]
        return [user.office_id] if user.office_id else []

    # Branch Storekeeper
    return [user.office_id] if user.office_id else []


def can_transact_office(db: Session, user: User, office_id: int) -> bool:
    """
    Check if a user has storekeeper transaction authority for a specific office.
    Validates against the user's authorized stock store IDs.
    """
    if not user or not office_id:
        return False

    stock_office_id = get_stock_office_id(db, office_id)
    authorized_stock_ids = get_authorized_stock_office_ids(db, user)
    return stock_office_id in authorized_stock_ids


def get_authorized_view_office_ids(db: Session, user: User) -> Optional[List[int]]:
    """
    Return list of office IDs the user is authorized to view.
    Returns None if the user has department-wide visibility (all offices).
    """
    if not user:
        return []

    if is_department_wide_viewer(db, user):
        return None  # None indicates all offices permitted

    if is_central_store_user(db, user):
        # Directorate + GCP + Central Store
        offices = (
            db.query(Office.id)
            .filter(
                Office.is_active == True,
                Office.office_type.in_([OfficeType.DIRECTORATE, OfficeType.GCP]),
            )
            .all()
        )
        office_ids = [r[0] for r in offices]
        cs_id = get_canonical_central_store_id(db)
        if cs_id and cs_id not in office_ids:
            office_ids.append(cs_id)
        if user.office_id and user.office_id not in office_ids:
            office_ids.append(user.office_id)
        return office_ids

    # Ordinary branch user
    return [user.office_id] if user.office_id else []


def get_authorized_transact_office_ids(db: Session, user: User) -> List[int]:
    """
    Alias for get_authorized_stock_office_ids to preserve backwards compatibility.
    """
    return get_authorized_stock_office_ids(db, user)


def validate_office_access(
    db: Session,
    user: User,
    office_id: int,
    is_transaction: bool = True,
):
    """
    Raise ValueError if user does not have required access to the office.
    """
    if is_transaction:
        if not can_transact_office(db=db, user=user, office_id=office_id):
            raise ValueError(f"You do not have store transaction authority for office ID {office_id}.")
    else:
        if not can_view_office(db=db, user=user, office_id=office_id):
            raise ValueError(f"You do not have permission to view records for office ID {office_id}.")
