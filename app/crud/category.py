from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.category import Category

from app.schemas.category import (CategoryCreate,CategoryRead, CategoryUpdate)

def create_category(db: Session, category: CategoryCreate):
    existing = (
        db.query(Category)
        .filter(Category.name == category.name).first()
    )

    if existing:
        return None
    
    db_category = Category(
        name=category.name,
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

def update_category(db: Session, category_id: int, category: CategoryUpdate):
    db_category = db.query(Category).filter(Category.id == category_id).first()

    if not db_category:
        return None

    new_name = category.name.strip()

    duplicate = (
        db.query(Category)
        .filter(
            func.lower(Category.name) == new_name.lower(),
            Category.id != category_id,
        )
        .first()
    )

    if duplicate:
        return False

    db_category.name = new_name
    db_category.type = category.type

    db.commit()
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






