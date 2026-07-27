from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


# ---------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------

def normalize_category_name(name: str) -> tuple[str, str]:
    """
    Returns:
        normalized_name -> Used for duplicate checking
        display_name    -> Stored in database
    """
    cleaned = name.strip()
    return cleaned.lower(), cleaned


def normalize_category_code(code: str) -> str:
    """
    Returns uppercase trimmed category code.

    """
    return code.strip().upper()


# ---------------------------------------------------------------
# Create
# ---------------------------------------------------------------

def create_category(db: Session, category: CategoryCreate):

    normalized_name, display_name = normalize_category_name(category.name)
    category_code = normalize_category_code(category.code)

    # Check duplicate code
    duplicate_code = (
        db.query(Category)
        .filter(
            func.upper(func.trim(Category.code)) == category_code,
        )
        .first()
    )

    if duplicate_code:
        raise ValueError("Category code already exists.")

    # Check duplicate name
    duplicate_name = (
        db.query(Category)
        .filter(
            func.lower(func.trim(Category.name)) == normalized_name,
            Category.is_active == True,
        )
        .first()
    )

    if duplicate_name:
        raise ValueError("Category name already exists.")

    db_category = Category(
        code=category_code,
        name=display_name,
        type=category.type,
    )

    try:
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category

    except IntegrityError:
        db.rollback()
        raise ValueError("Category code already exists.")

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------
# Read All
# ---------------------------------------------------------------

def get_all_categories(db: Session, search:str = "",):

    query = db.query(Category).filter(Category.is_active == True)

    if search:
        search = search.strip()

        query = query.filter(
            or_(
                Category.code.ilike(f"%{search}%"),
                Category.name.ilike(f"%{search}%"),
            )
        )

    categories = query.order_by(Category.name).all()

    return categories



# ---------------------------------------------------------------
# Read One
# ---------------------------------------------------------------

def get_category_by_id(db: Session, category_id: int):

    return (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.is_active == True,
        )
        .first()
    )


# ---------------------------------------------------------------
# Update
# ---------------------------------------------------------------

def update_category(
    db: Session,
    category_id: int,
    category: CategoryUpdate,
):

    db_category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.is_active == True,
        )
        .first()
    )

    if db_category is None:
        return None

    update_data = category.model_dump(exclude_unset=True)

    # ------------------------
    # Code
    # ------------------------

    if "code" in update_data:

        category_code = normalize_category_code(update_data["code"])

        duplicate = (
            db.query(Category)
            .filter(
                func.upper(func.trim(Category.code)) == category_code,
                Category.id != category_id,
            )
            .first()
        )

        if duplicate:
            raise ValueError("Category code already exists.")

        db_category.code = category_code

    # ------------------------
    # Name
    # ------------------------

    if "name" in update_data:

        normalized_name, display_name = normalize_category_name(
            update_data["name"]
        )

        duplicate = (
            db.query(Category)
            .filter(
                func.lower(func.trim(Category.name)) == normalized_name,
                Category.id != category_id,
                Category.is_active == True,
            )
            .first()
        )

        if duplicate:
            raise ValueError("Category name already exists.")

        db_category.name = display_name

    # ------------------------
    # Type
    # ------------------------

    if "type" in update_data:
        db_category.type = update_data["type"]

    try:
        db.commit()
        db.refresh(db_category)
        return db_category

    except IntegrityError:
        db.rollback()
        raise ValueError("Category code already exists.")

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------
# Soft Delete
# ---------------------------------------------------------------

def delete_category(
    db: Session,
    category_id: int,
):

    db_category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.is_active == True,
        )
        .first()
    )

    if db_category is None:
        return None

    db_category.is_active = False

    try:
        db.commit()
        db.refresh(db_category)
        return db_category

    except Exception:
        db.rollback()
        raise