from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


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