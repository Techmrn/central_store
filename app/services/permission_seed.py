#auto creates module+action code in permission code in permission table
from sqlalchemy.orm import Session

from app.crud.permission import create_permission, get_permission_by_code
from app.schemas.permission import PermissionCreate
from app.crud.role_permission import create_role_permission
from app.schemas.role_permission import RolePermissionCreate


PERMISSIONS = [
    # Category
    ("Category", "View", "View category records"),
    ("Category", "Create", "Create category records"),
    ("Category", "Update", "Update category records"),
    ("Category", "Delete", "Delete category records"),

    # Unit
    ("Unit", "View", "View unit records"),
    ("Unit", "Create", "Create unit records"),
    ("Unit", "Update", "Update unit records"),
    ("Unit", "Delete", "Delete unit records"),

    # Office
    ("Office", "View", "View office records"),
    ("Office", "Create", "Create office records"),
    ("Office", "Update", "Update office records"),
    ("Office", "Delete", "Delete office records"),

    # Section
    ("Section", "View", "View section records"),
    ("Section", "Create", "Create section records"),
    ("Section", "Update", "Update section records"),
    ("Section", "Delete", "Delete section records"),

    # Financial Year
    ("Financial Year", "View", "View financial year records"),
    ("Financial Year", "Create", "Create financial year records"),
    ("Financial Year", "Update", "Update financial year records"),
    ("Financial Year", "Delete", "Delete financial year records"),

    # Item
    ("Item", "View", "View item records"),
    ("Item", "Create", "Create item records"),
    ("Item", "Update", "Update item records"),
    ("Item", "Delete", "Delete item records"),

    # Opening Stock
    ("Opening Stock", "View", "View opening stock records"),
    ("Opening Stock", "Create", "Create opening stock records"),
    ("Opening Stock", "Update", "Update opening stock records"),
    ("Opening Stock", "Delete", "Delete opening stock records"),

    # User
    ("User", "View", "View user records"),
    ("User", "Create", "Create user records"),
    ("User", "Update", "Update user records"),
    ("User", "Delete", "Delete user records"),

    # Role
    ("Role", "View", "View role records"),
    ("Role", "Create", "Create role records"),
    ("Role", "Update", "Update role records"),
    ("Role", "Delete", "Delete role records"),

    # Permission
    ("Permission", "View", "View permission records"),
    ("Permission", "Create", "Create permission records"),
    ("Permission", "Update", "Update permission records"),
    ("Permission", "Delete", "Delete permission records"),

    # User Role
    ("User Role", "Assign", "Assign roles to users"),
    ("User Role", "Remove", "Remove roles from users"),

    # Role Permission
    ("Role Permission", "Assign", "Assign permissions to roles"),
    ("Role Permission", "Remove", "Remove permissions from roles"),

    # Login History
    ("Login History", "View", "View login history"),

    ("User Role", "View", "View user-role assignments"),
    ("Role Permission", "View", "View role-permission assignments"),

    # Asset
    ("Asset", "View", "View asset records"),
    ("Asset", "Create", "Create asset records"),
    ("Asset", "Update", "Update asset records"),
    ("Asset", "Delete", "Delete asset records"),

    # Asset Movement
    ("Asset Movement", "View", "View asset movement records"),
    ("Asset Movement", "Create", "Create asset movement records"),

    # Indent
    ("Indent", "View", "View indent records"),
    ("Indent", "Create", "Create indent records"),
    ("Indent", "Update", "Update indent records"),
    ("Indent", "Delete", "Delete indent records"),
    ("Indent", "Close", "Close indent records"),

    # Issue
    ("Issue", "View", "View issue records"),
    ("Issue", "Create", "Create issue records"),
    ("Issue", "Update", "Update issue records"),
    ("Issue", "Delete", "Delete issue records"),
    ("Issue", "Post", "Post issue records"),

    # Receipt
    ("Receipt", "View", "View receipt records"),
    ("Receipt", "Create", "Create receipt records"),
    ("Receipt", "Update", "Update receipt records"),
    ("Receipt", "Delete", "Delete receipt records"),
    ("Receipt", "Post", "Post receipt records"),

    # Return
    ("Return", "View", "View return records"),
    ("Return", "Create", "Create return records"),
    ("Return", "Post", "Post return records"),

    # Transfer
    ("Transfer", "View", "View transfer records"),
    ("Transfer", "Create", "Create transfer records"),
    ("Transfer", "Post", "Post transfer records"),

    # Stock
    ("Stock", "View", "View stock records and registers"),
    ("Stock", "Adjust", "Adjust stock records"),

    # Outward Pass
    ("Outward Pass", "View", "View outward pass records"),
    ("Outward Pass", "Create", "Create outward pass records"),
]




def seed_permissions(db: Session) -> int:
    """
    Create missing permissions.

    Returns the number of permissions created.
    """

    created_count = 0

    for module, action, description in PERMISSIONS:

        code = (
            f"{module}_{action}"
            .upper()
            .replace(" ", "_")
        )

        existing = get_permission_by_code(
            db=db,
            code=code,
        )

        if existing:
            continue

        create_permission(
            db=db,
            permission=PermissionCreate(
                module=module,
                action=action,
                description=description,
            ),
        )

        created_count += 1

    return created_count




def seed_admin_permissions(db: Session) -> int:
    """
    Assign all available permissions to ADMIN and STOREKEEPER roles.

    Dynamically looks up roles by code instead of assuming fixed IDs.
    Returns the number of new role-permission mappings created.
    """
    from sqlalchemy import func
    from app.models.role import Role

    target_roles = (
        db.query(Role)
        .filter(
            Role.is_active == True,
            func.upper(Role.code).in_(
                ["ADMIN", "STOREKEEPER", "CENTRAL_STORE_KEEPER", "STORE_KEEPER"]
            ),
        )
        .all()
    )

    if not target_roles:
        first_role = (
            db.query(Role)
            .filter(Role.is_active == True)
            .order_by(Role.id)
            .first()
        )
        if first_role:
            target_roles = [first_role]

    created_count = 0

    for role in target_roles:
        for module, action, _description in PERMISSIONS:
            code = (
                f"{module}_{action}"
                .upper()
                .replace(" ", "_")
            )

            permission = get_permission_by_code(
                db=db,
                code=code,
            )

            if permission is None:
                continue

            try:
                create_role_permission(
                    db=db,
                    role_permission=RolePermissionCreate(
                        role_id=role.id,
                        permission_id=permission.id,
                    ),
                )
                created_count += 1

            except ValueError as exc:
                if str(exc) == "Role permission mapping already exists.":
                    continue
                raise

    return created_count


""" create a temperory seeder in root and run this manually"""