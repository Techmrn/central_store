from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.category import Category

from app.schemas.category import (CategoryCreate,CategoryRead, CategoryUpdate)

#---------------------------------------------------------------
###### Helper functions for CRUD operations on Category model
#---------------------------------------------------------------

def normalize_category_name(name: str) -> tuple[str, str]:
    """
    Returns :  normalized_name -> Used for duplicate checking
        display_name    -> Stored in database
    """
    cleaned = name.strip()
    return cleaned.lower(), cleaned.title()

#----------------------------------------------------------------
#    Create
#---------------------------------------------------------------


def create_category(db: Session, category: CategoryCreate):


    normalized_name, display_name = normalize_category_name(category.name)

 # Check for duplicate active category

    duplicate = (
        db.query(Category)
        .filter(func.lower(func.trim(Category.name)) == normalized_name,
                Category.is_active == True)
                .first()
    )

    if duplicate:
        raise ValueError(f"Category with name '{category.name}' already exists.")
    
    db_category = Category(
        name=display_name,
        type=category.type,
    )

    try:
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category
    
    except Exception:
        db.rollback()
        raise

#----------------------------------------------------------------
#    Read All
#---------------------------------------------------------------
   

def get_all_categories(db: Session):
    return(
        db.query(Category).
        filter(Category.is_active == True).
        order_by(Category.name).
        all())

# --------------------------------------------------
# Read One
# --------------------------------------------------


def get_category_by_id(db: Session, category_id: int):
    return(db.query(Category)
           .filter(Category.id == category_id, 
                   Category.is_active == True,)
           .first())

# --------------------------------------------------
# Update
# --------------------------------------------------

def update_category(
    db: Session,
    category_id: int,
    category: CategoryUpdate,
):
    # Find active category
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
            raise ValueError("Category already exists.")

        db_category.name = display_name

    if "type" in update_data:
        db_category.type = update_data["type"]

    if "is_active" in update_data:
        db_category.is_active = update_data["is_active"]

    try:
        db.commit()
        db.refresh(db_category)
        return db_category

    except Exception:
        db.rollback()
        raise

# --------------------------------------------------
# Soft Delete
# --------------------------------------------------

def delete_category(db: Session, category_id: int):
    db_category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.is_active == True)
        .first()
    )
    
    if not db_category:
        return None
    
    db_category.is_active = False

    try:
        db.commit()
        db.refresh(db_category)
        return db_category

    except Exception:
        db.rollback()
        raise







