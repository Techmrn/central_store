from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.role_permission import RolePermission
from app.models.role import Role
from app.models.permission import Permission
from app.schemas.role_permission import RolePermissionCreate
from app.core.pagination import get_pagination_result


def create_role_permission(
    db: Session,
    role_permission: RolePermissionCreate,
):
    # Verify role exists
    role = db.query(Role).filter(Role.id == role_permission.role_id, Role.is_active == True).first()
    if not role:
        raise ValueError("Role not found.")

    # Verify permission exists
    permission = db.query(Permission).filter(Permission.id == role_permission.permission_id, Permission.is_active == True).first()
    if not permission:
        raise ValueError("Permission not found.")

    # Check for duplicate
    existing = (
        db.query(RolePermission)
        .filter(
            RolePermission.role_id == role_permission.role_id,
            RolePermission.permission_id == role_permission.permission_id,
            RolePermission.is_active == True,
        )
        .first()
    )
    if existing:
        raise ValueError("Role permission mapping already exists.")

    db_obj = RolePermission(
        role_id=role_permission.role_id,
        permission_id=role_permission.permission_id,
    )

    db.add(db_obj)
    try:
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise


def get_all_role_permissions(
    db: Session,
    search: str = "",
    role_id: int | None = None,
    permission_id: int | None = None,
    page: int = 1,
):
    query = (
        db.query(RolePermission)
        .join(Role, RolePermission.role_id == Role.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .filter(
            RolePermission.is_active == True,
            Role.is_active == True,
            Permission.is_active == True,
        )
        .options(
            joinedload(RolePermission.role),
            joinedload(RolePermission.permission),
        )
    )

    if role_id:
        query = query.filter(RolePermission.role_id == role_id)

    if permission_id:
        query = query.filter(RolePermission.permission_id == permission_id)

    if search:
        search = search.strip()
        query = query.filter(
            or_(
                Role.name.ilike(f"%{search}%"),
                Role.code.ilike(f"%{search}%"),
                Permission.name.ilike(f"%{search}%"),
                Permission.code.ilike(f"%{search}%"),
                Permission.module.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(Role.name, Permission.module, Permission.name)

    return get_pagination_result(query=query, page=page)


def get_role_permission_by_id(db: Session, role_permission_id: int):
    return (
        db.query(RolePermission)
        .options(
            joinedload(RolePermission.role),
            joinedload(RolePermission.permission),
        )
        .filter(
            RolePermission.id == role_permission_id,
            RolePermission.is_active == True,
        )
        .first()
    )


def delete_role_permission(db: Session, role_permission_id: int):
    db_obj = get_role_permission_by_id(db, role_permission_id)
    if not db_obj:
        raise ValueError("Role permission mapping not found.")

    db_obj.is_active = False

    try:
        db.commit()
        return db_obj
    except Exception:
        db.rollback()
        raise


def bulk_assign_role_permissions(
    db: Session,
    role_id: int,
    permission_ids: list[int],
):
    role = db.query(Role).filter(Role.id == role_id, Role.is_active == True).first()
    if not role:
        raise ValueError("Role not found.")

    # Soft delete existing mappings for this role
    existing = db.query(RolePermission).filter(RolePermission.role_id == role_id, RolePermission.is_active == True).all()
    for item in existing:
        item.is_active = False

    # Add new mappings
    new_objs = []
    for perm_id in permission_ids:
        perm = db.query(Permission).filter(Permission.id == perm_id, Permission.is_active == True).first()
        if perm:
            new_objs.append(RolePermission(role_id=role_id, permission_id=perm_id))

    if new_objs:
        db.add_all(new_objs)

    try:
        db.commit()
        return get_all_role_permissions(db, role_id=role_id)
    except Exception:
        db.rollback()
        raise


def get_permissions_by_role(db: Session, role_id: int):
    return (
        db.query(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .filter(
            RolePermission.role_id == role_id,
            RolePermission.is_active == True,
            Permission.is_active == True,
        )
        .all()
    )
