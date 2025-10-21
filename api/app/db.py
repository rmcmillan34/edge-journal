from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
try:
    # SQLAlchemy 2.x
    from sqlalchemy.orm import DeclarativeBase  # type: ignore

    class Base(DeclarativeBase):
        pass
except Exception:
    # Fallback for SQLAlchemy < 2.0
    from sqlalchemy.orm import declarative_base  # type: ignore

    Base = declarative_base()
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
