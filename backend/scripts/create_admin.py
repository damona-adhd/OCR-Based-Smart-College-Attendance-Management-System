"""
First-run admin creation script.
Usage: python scripts/create_admin.py
Reads credentials from environment variables.
"""
import asyncio
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.models.user import User, UserRole
import app.models  # noqa — ensures all tables are registered with Base


async def create_admin():
    _is_sqlite = "sqlite" in settings.DATABASE_URL
    _kwargs = {"echo": False}
    if _is_sqlite:
        _kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(settings.DATABASE_URL, **_kwargs)

    # Create all tables (safe no-op if they already exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        username = settings.BOOTSTRAP_ADMIN_USERNAME
        email    = settings.BOOTSTRAP_ADMIN_EMAIL
        password = settings.BOOTSTRAP_ADMIN_PASSWORD

        if password in ("change_me_admin_password", ""):
            print("ERROR: Set BOOTSTRAP_ADMIN_PASSWORD in your .env — do not use the default.")
            return

        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            print(f"Admin user '{username}' already exists.")
            return

        admin = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        await db.commit()
        print(f"[OK] Admin user '{username}' created.")
        print(f"  Email:    {email}")
        print(f"  Password: {password}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
