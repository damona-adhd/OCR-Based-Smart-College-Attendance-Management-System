from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.core.limiter import limiter
from app.api.routes import (
    auth, departments, classes, subjects,
    students, lecturers, teaching_assignments,
    attendance, upload, ocr, reports, settings as settings_router,
    roster, dashboards, corrections,
)

# Configure logging — shows OCR debug info in the uvicorn console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("app.services.ocr").setLevel(logging.INFO)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Auto-create tables for SQLite local dev (skipped when using Alembic + PostgreSQL)."""
    if "sqlite" in settings.DATABASE_URL:
        # Import all models so Base knows about them
        import app.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)



# ---- Global exception handler — never expose stack traces ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.APP_ENV == "development":
        import traceback
        detail = traceback.format_exc()
    else:
        detail = "An internal error occurred."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail},
    )


# ---- Health check ----
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


# ---- API Routers ----
PREFIX = "/api"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(departments.router, prefix=PREFIX)
app.include_router(classes.router, prefix=PREFIX)
app.include_router(subjects.router, prefix=PREFIX)
app.include_router(students.router, prefix=PREFIX)
app.include_router(lecturers.router, prefix=PREFIX)
app.include_router(teaching_assignments.router, prefix=PREFIX)
app.include_router(attendance.router, prefix=PREFIX)
app.include_router(upload.router, prefix=PREFIX)
app.include_router(ocr.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(settings_router.router, prefix=PREFIX)
app.include_router(roster.router, prefix=PREFIX)
app.include_router(dashboards.router, prefix=PREFIX)
app.include_router(corrections.router, prefix=PREFIX)
