import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app import models  # noqa: F401  # Import all models so tables are registered

# 1. Fetch the absolute system URL path injected from your docker-compose environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine_kwargs = {}
if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool

    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }

# 2. Build the unified database communications engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# 3. Create a unique session factory instance 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database(target_engine=None):
    """Create all SQLAlchemy tables if they do not exist."""
    engine_to_use = target_engine or engine
    Base.metadata.create_all(bind=engine_to_use)


# 4. Define the contextual dependency injector
def get_db():
    """
    Yields a transactional database session context manager.
    Automatically closes connection hooks when the API execution loop finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
