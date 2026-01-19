import os
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://assumptions:assumptions@db:5432/assumptions"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_with_tenant(tenant_id: UUID):
    def _get_db():
        db = SessionLocal()
        try:
            db.execute(text(f"SET app.current_tenant = '{tenant_id}'"))
            yield db
        finally:
            db.close()

    return _get_db
