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
    Assign all available permissions to the ADMIN role.

    ADMIN role ID is currently 1.
    Returns the number of new role-permission mappings created.
    """

    admin_role_id = 1

    created_count = 0

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
                    role_id=admin_role_id,
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