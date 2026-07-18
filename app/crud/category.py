from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.category import Category

from app.schemas.category import (CategoryCreate,CategoryRead, CategoryUpdate)

def create_category(db: Session, category: CategoryCreate):

# Normalize the input

    normalized_name = category.name.strip().lower()
    display_name = category.name.strip().title()

 # Check for duplicate active category

    existing = (
        db.query(Category)
        .filter(func.lower(func.trim(Category.name)) == normalized_name,
                Category.is_active == True)
                .first()
    )

    if existing:
        return False
    
    db_category = Category(
        name=display_name,
        type=category.type,
    )

    db.add(db_category)

    db.commit()

    db.refresh(db_category)

    return db_category

def get_all_categories(db: Session):
    return(
        db.query(Category).
        filter(Category.is_active == True).
        order_by(Category.name).
        all())

def get_category_by_id(db: Session, category_id: int):
    return(db.query(Category).filter(Category.id == category_id).first())

# def update_category (db: Session, category_id: int, category: CategoryUpdate):
#     db_category = db.query(Category).filter(Category.id == category_id).first()

#     if not db_category:
#         return None
    
#     duplicate = (
#         db.query(Category)
#         .filter(Category.name == category.name, Category.id != category_id) # category_id from url
#         .first()
#     )

#     if duplicate:
#         return False
    
#     db_category.name = category.name
#     db_category.type = category.type

#     db.commit()
#     db.refresh(db_category)
#     return db_category

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

    # Normalize user input
    normalized_name = category.name.strip().lower()
    display_name = category.name.strip().title()

    # Check duplicates among active categories
    duplicate = (
        db.query(Category)
        .filter(
            func.lower(func.trim(Category.name)) == normalized_name,
            Category.id != category_id,
            Category.is_active == True,
        )
        .first()
    )

    if duplicate is not None:
        return False

    # Update object
    db_category.name = display_name
    db_category.type = category.type

    # Save
    db.commit()

    # Reload updated values
    db.refresh(db_category)

    return db_category

def delete_category(db: Session, category_id: int):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    
    if not db_category:
        return None
    
    db_category.is_active = False
    db.commit()
    db.refresh(db_category)
   
    return db_category






