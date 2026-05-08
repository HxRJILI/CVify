from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import Config

# Create the SQLAlchemy engine using the configured database URL
engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False} if Config.DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

# Create a customized Session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative class definitions
Base = declarative_base()

def get_db():
    """
    Generator that creates a new database session and closes it after use.
    Can be used as a context manager or dependency.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database by creating all defined tables.
    Must import models before calling create_all to ensure they are registered with Base.
    """
    import core.models
    Base.metadata.create_all(bind=engine)

    if Config.DATABASE_URL.startswith("sqlite"):
        inspector = inspect(engine)
        existing_columns = {column["name"] for column in inspector.get_columns("cv_profiles")}
        if "photo_path" not in existing_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE cv_profiles ADD COLUMN photo_path VARCHAR(500)"))

        if inspector.has_table("generated_cvs"):
            existing_cv_columns = {column["name"] for column in inspector.get_columns("generated_cvs")}
            with engine.begin() as connection:
                if "job_title" not in existing_cv_columns:
                    connection.execute(text("ALTER TABLE generated_cvs ADD COLUMN job_title VARCHAR(200)"))
                if "match_score" not in existing_cv_columns:
                    connection.execute(text("ALTER TABLE generated_cvs ADD COLUMN match_score INTEGER"))
                if "match_summary" not in existing_cv_columns:
                    connection.execute(text("ALTER TABLE generated_cvs ADD COLUMN match_summary TEXT"))
