from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.permission import Permission

from app.schemas.permission import (
    PermissionCreate,
    PermissionUpdate,
)

from app.core.pagination import get_pagination_result


# ---------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------

def normalize_module(module: str) -> str:
    return module.strip().title()


def normalize_action(action: str) -> str:
    return action.strip().title()


def generate_permission_code(
    module: str,
    action: str,
) -> str:

    return (
        f"{module}_{action}"
        .replace(" ", "_")
        .upper()
    )


def generate_permission_name(
    module: str,
    action: str,
) -> str:

    return f"{action} {module}"


# ---------------------------------------------------------------
# Create
# ---------------------------------------------------------------

def create_permission(
    db: Session,
    permission: PermissionCreate,
):

    module = normalize_module(permission.module)
    action = normalize_action(permission.action)

    code = generate_permission_code(
        module,
        action,
    )

    name = generate_permission_name(
        module,
        action,
    )

    description = (
        permission.description.strip()
        if permission.description
        else None
    )

    # -----------------------------------------------------------
    # Duplicate Permission
    # -----------------------------------------------------------

    duplicate = (
        db.query(Permission)
        .filter(
            func.upper(func.trim(Permission.code)) == code,
        )
        .first()
    )

    if duplicate:
        raise ValueError(
            "Permission already exists."
        )

    db_permission = Permission(
        code=code,
        module=module,
        action=action,
        name=name,
        description=description,
    )

    try:

        db.add(db_permission)
        db.commit()
        db.refresh(db_permission)

        return db_permission

    except IntegrityError:

        db.rollback()

        raise ValueError(
            "Permission already exists."
        )

    except Exception:

        db.rollback()
        raise

# ---------------------------------------------------------------
# Read All
# ---------------------------------------------------------------

def get_all_permissions(
    db: Session,
    search: str = "",
    page: int = 1,
):

    query = (
        db.query(Permission)
        .filter(
            Permission.is_active == True,
        )
    )

    if search:

        search = search.strip()

        query = query.filter(
            or_(
                Permission.code.ilike(f"%{search}%"),
                Permission.module.ilike(f"%{search}%"),
                Permission.action.ilike(f"%{search}%"),
                Permission.name.ilike(f"%{search}%"),
                Permission.description.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(
        Permission.module,
        Permission.action,
    )

    return get_pagination_result(
        query=query,
        page=page,
    )


# ---------------------------------------------------------------
# Read One
# ---------------------------------------------------------------

def get_permission_by_id(
    db: Session,
    permission_id: int,
):

    return (
        db.query(Permission)
        .filter(
            Permission.id == permission_id,
            Permission.is_active == True,
        )
        .first()
    )


# ---------------------------------------------------------------
# Read by Code
# ---------------------------------------------------------------

def get_permission_by_code(
    db: Session,
    code: str,
):

    code = code.strip().upper()

    return (
        db.query(Permission)
        .filter(
            func.upper(
                func.trim(Permission.code)
            ) == code,
            Permission.is_active == True,
        )
        .first()
    )


# ---------------------------------------------------------------
# Update
# ---------------------------------------------------------------

def update_permission(
    db: Session,
    permission_id: int,
    permission: PermissionUpdate,
):

    db_permission = (
        db.query(Permission)
        .filter(
            Permission.id == permission_id,
            Permission.is_active == True,
        )
        .first()
    )

    if db_permission is None:
        return None

    update_data = permission.model_dump(
        exclude_unset=True,
    )

    module = (
        normalize_module(
            update_data["module"]
        )
        if "module" in update_data
        else db_permission.module
    )

    action = (
        normalize_action(
            update_data["action"]
        )
        if "action" in update_data
        else db_permission.action
    )

    code = generate_permission_code(
        module,
        action,
    )

    name = generate_permission_name(
        module,
        action,
    )

    duplicate = (
        db.query(Permission)
        .filter(
            func.upper(
                func.trim(Permission.code)
            ) == code,
            Permission.id != permission_id,
        )
        .first()
    )

    if duplicate:
        raise ValueError(
            "Permission already exists."
        )

    db_permission.module = module
    db_permission.action = action
    db_permission.code = code
    db_permission.name = name

    if "description" in update_data:

        db_permission.description = (
            update_data["description"].strip()
            if update_data["description"]
            else None
        )

    try:

        db.commit()
        db.refresh(db_permission)

        return db_permission

    except IntegrityError:

        db.rollback()

        raise ValueError(
            "Permission already exists."
        )

    except Exception:

        db.rollback()
        raise

# ---------------------------------------------------------------
# Soft Delete
# ---------------------------------------------------------------

def delete_permission(
    db: Session,
    permission_id: int,
):

    db_permission = (
        db.query(Permission)
        .filter(
            Permission.id == permission_id,
            Permission.is_active == True,
        )
        .first()
    )

    if db_permission is None:
        return None

    db_permission.is_active = False

    try:

        db.commit()
        db.refresh(db_permission)

        return db_permission

    except Exception:

        db.rollback()
        raise


# ---------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------

def get_permission_lookup(
    db: Session,
):

    return (
        db.query(Permission)
        .filter(
            Permission.is_active == True,
        )
        .order_by(
            Permission.module,
            Permission.action,
        )
        .all()
    )