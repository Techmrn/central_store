from app.core.db import SessionLocal

from app.services.permission_seed import (
    seed_permissions,
    seed_admin_permissions,
)


db = SessionLocal()

try:
    permission_count = seed_permissions(db)
    print(f"Permissions created: {permission_count}")

    admin_mapping_count = seed_admin_permissions(db)
    print(
        f"ADMIN permissions assigned: "
        f"{admin_mapping_count}"
    )

finally:
    db.close()