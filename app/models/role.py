from typing import TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.role_permission import RolePermission
    from app.models.user_role import UserRole


class Role(BaseModel):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # user_roles: Mapped[list["UserRole"]] = relationship(
    #     back_populates="role",
    #     cascade="all, delete-orphan",
    # )

    # role_permissions: Mapped[list["RolePermission"]] = relationship(
    #     back_populates="role",
    #     cascade="all, delete-orphan",
    # )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
            back_populates="role",
    )

    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="role",
    )