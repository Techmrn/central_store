from sqlalchemy import func, or_
from sqlalchemy.orm import Session
import math

from app.models.office import Office
from app.schemas.office import OfficeCreate, OfficeUpdate
from app.core.constants import PAGE_SIZE


def create_office(db: Session, office: OfficeCreate):

    code = office.code.strip().upper()
    name = office.name.strip().title()
    office_type = office.office_type
    display_order = office.display_order
    remarks = office.remarks.strip() if office.remarks else None
    existing_code = db.query(Office).filter(
        func.upper(Office.code) == code,
        Office.is_active == True,
    ).first()

    if existing_code:
        raise ValueError("Office code already exists.")

    existing_name = db.query(Office).filter(
        func.lower(Office.name) == name.lower(),
        Office.is_active == True,
    ).first()

    if existing_name:
        raise ValueError("Office name already exists.")
    
    db_office = Office(
        code=code,
        name=name,
        office_type=office_type,
        display_order=display_order,
        remarks=remarks
    )
    
    db.add(db_office)

    try:
        db.commit()
        db.refresh(db_office)
        return db_office
    except Exception:
        db.rollback()
        raise



def get_all_offices(
        db: Session,
        search: str = "",
        page: int = 1,
        ):

    query = db.query(Office).filter(Office.is_active == True)
    
    if search:
            search = search.strip()
    
            query = query.filter(
                or_(
                    Office.code.ilike(f"%{search}%"),
                    Office.name.ilike(f"%{search}%"),
                )
            )
    
    total_records = query.count()
    
    offices = (
            query
            .order_by(Office.name)
            .offset((page-1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
            .all()
        )
    
    return {
            "items": offices,
            "current_page": page,
            "page_size": PAGE_SIZE,
            "total_records": total_records,
            "total_pages": math.ceil(total_records / PAGE_SIZE) if total_records else 1,
        }

    

def get_office_by_id(db: Session, office_id: int):
    return (
        db.query(Office).
        filter(Office.id == office_id, Office.is_active == True)
        .first()
    )



def update_office(db: Session, office_id: int, office: OfficeUpdate):
    db_office = get_office_by_id(db, office_id)

    if not db_office:
        raise ValueError("Office not found.")

    if office.code:
        code = office.code.strip().upper()
        existing_code = db.query(Office).filter(
            func.upper(Office.code) == code,
            Office.id != office_id,
            Office.is_active == True,
        ).first()

        if existing_code:
            raise ValueError("Office code already exists.")

        db_office.code = code

    if office.name:
        name = office.name.strip().title()
        existing_name = db.query(Office).filter(
            func.lower(Office.name) == name.lower(),
            Office.id != office_id,
            Office.is_active == True,
        ).first()

        if existing_name:
            raise ValueError("Office name already exists.")

        db_office.name = name

    if office.office_type is not None:
        db_office.office_type = office.office_type

    if office.display_order is not None:
        db_office.display_order = office.display_order

    if office.remarks is not None:
        db_office.remarks = office.remarks

    try:
        db.commit()
        db.refresh(db_office)
        return db_office
    except Exception:
        db.rollback()
        raise

def delete_office(db: Session, office_id: int):
    db_office = get_office_by_id(db, office_id)

    if not db_office:
        raise ValueError("Office not found.")

    db_office.is_active = False

    try:
        db.commit()
        return db_office
    except Exception:
        db.rollback()
        raise


#FOR DROP DOWN IN INDENT MENU

def get_all_offices_dropdown(db: Session):
    return (
        db.query(Office)
        .filter(Office.is_active == True)
        .order_by(Office.display_order, Office.name)
        .all()
    )

