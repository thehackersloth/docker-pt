"""
Database configuration and initialization
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# PostgreSQL
DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


async def init_db():
    """Initialize database"""
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")

        # Create default admin user if not exists
        db = SessionLocal()
        try:
            from app.models.user import User, UserRole
            from app.core.security import get_password_hash
            import secrets
            import os

            admin = db.query(User).filter(User.username == "admin").first()
            if not admin:
                # Generate random password or use ADMIN_PASSWORD env var
                admin_password = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(16)
                admin = User(
                    username="admin",
                    email="admin@localhost",
                    hashed_password=get_password_hash(admin_password),
                    full_name="Administrator",
                    role=UserRole.ADMIN,
                    is_active=True
                )
                db.add(admin)
                db.commit()
                logger.warning("=" * 60)
                logger.warning(f"DEFAULT ADMIN CREDENTIALS: admin / {admin_password}")
                logger.warning("CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN")
                logger.warning("=" * 60)

                # Write password to flag file for first-boot UI display
                try:
                    from pathlib import Path
                    flag_file = Path("/data/.first_boot_password")
                    flag_file.parent.mkdir(parents=True, exist_ok=True)
                    flag_file.write_text(admin_password)
                    os.chmod(str(flag_file), 0o600)
                except Exception as fe:
                    logger.warning(f"Could not write first-boot flag: {fe}")
            else:
                logger.info("Admin user already exists")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
