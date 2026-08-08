from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.user_role import UserRole
from app.models.user import User
from app.models.role import Role
from app.schemas.user_role import UserRoleCreate
from app.core.pagination import get_pagination_result


def create_user_role(
    db: Session,
    user_role: UserRoleCreate,
):
    # Verify user exists
    user = db.query(User).filter(User.id == user_role.user_id, User.is_active == True).first()
    if not user:
        raise ValueError("User not found.")

    # Verify role exists
    role = db.query(Role).filter(Role.id == user_role.role_id, Role.is_active == True).first()
    if not role:
        raise ValueError("Role not found.")

    # Check for duplicate
    existing = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user_role.user_id,
            UserRole.role_id == user_role.role_id,
            UserRole.is_active == True,
        )
        .first()
    )
    if existing:
        raise ValueError("User role mapping already exists.")

    db_obj = UserRole(
        user_id=user_role.user_id,
        role_id=user_role.role_id,
    )

    db.add(db_obj)
    try:
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise


def get_all_user_roles(
    db: Session,
    search: str = "",
    user_id: int | None = None,
    role_id: int | None = None,
    page: int = 1,
):
    query = (
        db.query(UserRole)
        .join(User, UserRole.user_id == User.id)
        .join(Role, UserRole.role_id == Role.id)
        .filter(
            UserRole.is_active == True,
            User.is_active == True,
            Role.is_active == True,
        )
        .options(
            joinedload(UserRole.user),
            joinedload(UserRole.role),
        )
    )

    if user_id:
        query = query.filter(UserRole.user_id == user_id)

    if role_id:
        query = query.filter(UserRole.role_id == role_id)

    if search:
        search = search.strip()
        query = query.filter(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.code.ilike(f"%{search}%"),
                Role.name.ilike(f"%{search}%"),
                Role.code.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(User.full_name, Role.name)

    return get_pagination_result(query=query, page=page)


def get_user_role_by_id(db: Session, user_role_id: int):
    return (
        db.query(UserRole)
        .options(
            joinedload(UserRole.user),
            joinedload(UserRole.role),
        )
        .filter(
            UserRole.id == user_role_id,
            UserRole.is_active == True,
        )
        .first()
    )


def delete_user_role(db: Session, user_role_id: int):
    db_obj = get_user_role_by_id(db, user_role_id)
    if not db_obj:
        raise ValueError("User role mapping not found.")

    db_obj.is_active = False

    try:
        db.commit()
        return db_obj
    except Exception:
        db.rollback()
        raise


def bulk_assign_user_roles(
    db: Session,
    user_id: int,
    role_ids: list[int],
):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise ValueError("User not found.")

    # Soft delete existing mappings for this user
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.is_active == True).all()
    for item in existing:
        item.is_active = False

    # Add new mappings
    new_objs = []
    for r_id in role_ids:
        role = db.query(Role).filter(Role.id == r_id, Role.is_active == True).first()
        if role:
            new_objs.append(UserRole(user_id=user_id, role_id=r_id))

    if new_objs:
        db.add_all(new_objs)

    try:
        db.commit()
        return get_all_user_roles(db, user_id=user_id)
    except Exception:
        db.rollback()
        raise


def get_roles_by_user(db: Session, user_id: int):
    return (
        db.query(Role)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            Role.is_active == True,
        )
        .all()
    )
