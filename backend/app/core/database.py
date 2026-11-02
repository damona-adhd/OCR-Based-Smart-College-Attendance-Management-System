from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# SQLite needs check_same_thread=False and no pool_size/max_overflow
_is_sqlite = "sqlite" in settings.DATABASE_URL

_engine_kwargs: dict = dict(echo=settings.APP_ENV == "development")
if not _is_sqlite:
    _engine_kwargs.update(pool_pre_ping=True, pool_size=10, max_overflow=20)
else:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
