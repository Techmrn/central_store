from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
import math 

from app.models.office import Office
from app.models.section import Section
from app.schemas.sections import SectionCreate, SectionUpdate, SectionRead
from app.core.constants import PAGE_SIZE
def create_section(db: Session, section: SectionCreate):

    section_name = section.name.strip()
    section_code = section.code.strip()

    duplicate = (
        db.query(Section)
        .filter(
            Section.office_id == section.office_id,
            Section.is_active == True,
            (
                (func.lower(Section.name) == section_name.lower())
                |
                (func.lower(Section.code) == section_code.lower())
            ),
        )
        .first()
    )

    if duplicate:
        raise ValueError(
            "Section name or code already exists in this office."
        )
    db_section = Section(
        office_id=section.office_id,
        name=section_name,
        code=section_code,
        remarks=section.remarks.strip() if section.remarks else None,
    )

    db.add(db_section)

    try:
            db.commit()
            db.refresh(db_section)
            return db_section
    except Exception:
            db.rollback()
            raise

def get_all_sections(
    db: Session,
    search: str = "",
    page: int = 1,
):

    query = (
        db.query(Section)
        .options(joinedload(Section.office))
        .filter(Section.is_active == True)
    )

    if search:

        search = search.strip()

        query = (
            query.join(Office)
            .filter(
                or_(
                    Section.code.ilike(f"%{search}%"),
                    Section.name.ilike(f"%{search}%"),
                    Office.name.ilike(f"%{search}%"),
                )
            )
        )

    total_records = query.count()

    sections = (
        query
        .order_by(Section.name)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return {
        "items": sections,
        "current_page": page,
        "page_size": PAGE_SIZE,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / PAGE_SIZE) if total_records else 1,
    }

def get_section_by_id (db: Session, section_id: int):
      return(
            db.query(Section).
            filter(Section.id == section_id, Section.is_active == True).
            first()
      )

def update_section(db: Session, section_id: int, section: SectionUpdate):
    db_section = get_section_by_id(db, section_id)

    if not db_section:
        raise ValueError("Section not found.")

    office_id = (
        section.office_id
        if section.office_id is not None
        else db_section.office_id
    )

    if section.code:
        code = section.code.strip().upper()

        existing_code = (
            db.query(Section)
            .filter(
                Section.office_id == office_id,
                func.upper(Section.code) == code,
                Section.id != section_id,
                Section.is_active == True,
            )
            .first()
        )

        if existing_code:
            raise ValueError("Section code already exists in this office.")

        db_section.code = code

    if section.name:
        name = section.name.strip().title()

        existing_name = (
            db.query(Section)
            .filter(
                Section.office_id == office_id,
                func.lower(Section.name) == name.lower(),
                Section.id != section_id,
                Section.is_active == True,
            )
            .first()
        )

        if existing_name:
            raise ValueError("Section name already exists in this office.")

        db_section.name = name

    if section.office_id is not None:
        db_section.office_id = section.office_id

    if section.remarks is not None:
        db_section.remarks = section.remarks.strip() if section.remarks else None

    try:
        db.commit()
        db.refresh(db_section)
        return db_section
    except Exception:
        db.rollback()
        raise

def delete_section(db: Session, section_id: int):
    db_section = get_section_by_id(db, section_id)

    if db_section is None:
        return None

    db_section.is_active = False

    try:
        db.commit()
        return db_section
    except Exception:
        db.rollback()
        raise


# Getting Correct Dropdown for indent menu

def get_all_sections_dropdown(db: Session):
    return (
        db.query(Section)
        .options(joinedload(Section.office))
        .filter(Section.is_active == True)
        .order_by(Section.name)
        .all()
    )




      

      