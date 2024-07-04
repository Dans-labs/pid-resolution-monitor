from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from settings import settings

engine = create_engine(settings.POSTGRES_CONNECTION_STRING, echo=True, future=True, pool_recycle=3600, pool_size=5,
                       max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    This function creates a database session,
    yield it to the get_db function, rollback the transaction
    if there's an exception and then finally closes the session.

    Yields:
        db: scoped database session
    """

    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        raise e
    finally:
        db.close()
