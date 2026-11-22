"""Engine, session handling and schema creation."""
import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL
from modules.data_management.models import Base

logger = logging.getLogger(__name__)


def create_db_engine(url: str = DATABASE_URL) -> Engine:
    engine = create_engine(url, future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        # SQLite does NOT enforce foreign keys unless asked, per connection.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker = SessionLocal) -> Iterator[Session]:
    """One transaction: commit if the block succeeds, roll back if it raises."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database transaction rolled back")
        raise
    finally:
        session.close()


def init_db(target_engine: Engine = engine) -> None:
    """Create any missing tables. Safe to call repeatedly."""
    Base.metadata.create_all(target_engine)
    logger.info("Database initialised")
