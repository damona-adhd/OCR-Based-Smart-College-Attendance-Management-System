"""Reset all dev account passwords to known values."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User
import app.models  # noqa

PASSWORDS = {
    "admin":      "Admin@SecurePass123",
    "dr.sharma":  "Lecturer@123",
    "prof.patel": "Lecturer@123",
    "1cs21cs001": "Student@123",
    "1cs21cs002": "Student@123",
    "1cs21cs003": "Student@123",
}

async def main():
    kw = {"connect_args": {"check_same_thread": False}} if "sqlite" in settings.DATABASE_URL else {}
    engine = create_async_engine(settings.DATABASE_URL, echo=False, **kw)
    S = async_sessionmaker(engine, expire_on_commit=False)
    async with S() as db:
        r = await db.execute(select(User))
        users = r.scalars().all()
        for u in users:
            pw = PASSWORDS.get(u.username)
            if pw:
                u.password_hash = hash_password(pw)
                print(f"  Reset {u.username} [{u.role.value}]  ->  {pw}")
        await db.commit()
        print("\nAll passwords reset. Verifying...")
        r2 = await db.execute(select(User))
        for u in r2.scalars().all():
            pw = PASSWORDS.get(u.username)
            if pw:
                ok = verify_password(pw, u.password_hash)
                print(f"  {'OK' if ok else 'FAIL'} {u.username}")
    await engine.dispose()

asyncio.run(main())
