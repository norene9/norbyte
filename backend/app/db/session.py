import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Fetch the absolute system URL path injected from your docker-compose environment
DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

# 2. Build the unified database communications engine
engine = create_engine(DATABASE_URL)

# 3. Create a unique session factory instance 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
