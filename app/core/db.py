from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import DATABASE_URL
from app.models.base import Base


engine = create_engine(
    DATABASE_URL,
    echo=True)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False,
    bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()