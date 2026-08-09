from sqlalchemy.orm import Session

from app.crud.user_role import get_roles_by_user
from app.crud.role_permission import get_permissions_by_role


def get_user_roles(
    db: Session,
    user_id: int,
):
    """
    Return all active roles assigned to a user.
    """
    return get_roles_by_user(
        db=db,
        user_id=user_id,
    )


def get_user_permissions(
    db: Session,
    user_id: int,
):
    """
    Return all active permissions available to a user
    through their active roles.
    """

    roles = get_user_roles(
        db=db,
        user_id=user_id,
    )

    permissions = {}

    for role in roles:
        role_permissions = get_permissions_by_role(
            db=db,
            role_id=role.id,
        )

        for permission in role_permissions:
            permissions[permission.code] = permission

    return list(permissions.values())


def has_permission(
    db: Session,
    user_id: int,
    permission_code: str,
) -> bool:
    """
    Check whether a user has a specific permission.
    """

    permission_code = permission_code.strip().upper()

    permissions = get_user_permissions(
        db=db,
        user_id=user_id,
    )

    return any(
        permission.code.upper() == permission_code
        for permission in permissions
    )