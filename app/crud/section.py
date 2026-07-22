from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.section import Section
from app.schemas.sections import SectionCreate, SectionUpdate, SectionRead

def create_section(db: Session, section: SectionCreate):

    section_name = section.name.strip()
    section_code = section.code.strip()

    duplicate = (
        db.query(Section)
        .filter(
            Section.office_id == section.office_id,
            Section.is_active == True,
            (
                (func.lower(Section.name) == section.office_id)
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
            db.refresh(db_office)
            return db_office
    except Exception:
            db.rollback()
            raise
    