# Smart College Attendance Management System

A production-ready full-stack web application for college attendance management — featuring **three distinct role portals (Administrator, Teacher, Student)**, manual attendance marking, **PyMuPDF digital roster extraction**, scanned register processing, attendance correction audit trails, and live database analytics.

---

## 🌟 Master Features

1. **Mandatory 3-Role Login Landing Page**:
   - Three clickable cards: **Administrator**, **Teacher**, and **Student**.
   - Server-side role enforcement: backend rejects any role mismatch/spoofing.
   - Session preservation on page refresh and automatic routing to role-specific workspaces.
2. **PDF Student Roster Import**:
   - Dedicated Administrator page (`/admin/roster-import`).
   - Direct text extraction via **PyMuPDF** (`pymupdf==1.28.2`).
   - Duplicate USN detection, interactive preview table, and atomic database commits.
3. **Teacher Quick-Add Capabilities**:
   - Teachers can instantly add new students to an assigned class (`full_name` + `USN`).
   - Teachers can add new subjects (`subject_name` + `subject_code`) without waiting for admin approval.
4. **Attendance Correction & Audit Trail**:
   - Teachers can edit past finalized attendance records with mandatory audit justification (`AttendanceCorrection` log).
   - Students can file formal correction requests directly from their portal.
5. **Real-time Database Metrics (Zero Fake Stats)**:
   - Dedicated analytics endpoints (`/api/dashboards/admin`, `/api/dashboards/teacher`, `/api/dashboards/student`).
   - Recharts visual analytics: attendance trends, doughnut distribution, and shortage warnings (<75%).
6. **Institutional Design System**:
   - Custom palette: `#F4F5F1` Canvas, `#243630` Forest Green, `#465F56` Secondary, `#FF685F` Coral, `#55D5ED` Cyan.

---

## 🛠️ Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, React Router 6, TanStack Query, Recharts, React Hook Form + Zod |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2 (Async), Pydantic v2, Alembic, SlowAPI |
| Database | PostgreSQL 16 (production & Docker) / SQLite async fallback (local dev) |
| Document Processing | PyMuPDF (`fitz`), Tesseract OCR 5 (`pytesseract`), OpenCV |
| Auth & Security | Stateless JWT (HS256), Argon2 password hashing, Role-based guard middleware |
| Testing | Pytest (`pytest-asyncio`), Vitest, React Testing Library |
| Deployment | Docker, Docker Compose |

---

## Prerequisites

- Docker Desktop (Windows/Mac/Linux) — recommended
- **OR** for local development:
  - Python 3.12+
  - Node.js 20+
  - PostgreSQL 16
  - Tesseract OCR (see below)

---

## Quick Start with Docker

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd attendance_project
cp .env.example .env
```

Edit `.env` and set **strong** values for:
- `POSTGRES_PASSWORD`
- `SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `BOOTSTRAP_ADMIN_PASSWORD`

### 2. Start all services

```bash
docker compose up --build -d
```

Wait ~30 seconds for all services to become healthy.

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Create the administrator account

```bash
docker compose exec backend python scripts/create_admin.py
```

### 5. (Optional) Load development seed data

```bash
docker compose exec backend python scripts/seed_dev.py
```

> ⚠️ **Never run seed_dev.py in production.** It creates test accounts with known passwords.

### 6. Access the application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt

# Create .env from template
copy ..\.env.example .env   # Windows
# edit .env to point to your local PostgreSQL

# Run migrations
alembic upgrade head

# Create admin
python scripts/create_admin.py

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local

npm run dev
# Open http://localhost:5173
```

---

## Tesseract OCR — Installation

### Windows (local development)
1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install Tesseract 5.x with English language data
3. Add Tesseract to PATH, or set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` in `.env`

### Linux / Docker
Tesseract is installed automatically by the backend Dockerfile:
```dockerfile
RUN apt-get install -y tesseract-ocr tesseract-ocr-eng
```

### Verify installation
```bash
tesseract --version
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL URL | Required |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Required |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `60` |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `http://localhost:5173` |
| `UPLOAD_DIR` | Path for uploaded files | `uploads` |
| `MAX_UPLOAD_SIZE_MB` | Max image upload size | `10` |
| `TESSERACT_CMD` | Tesseract executable path | `tesseract` |
| `OCR_MIN_CONFIDENCE` | Min OCR confidence score | `50` |
| `MIN_ATTENDANCE_PERCENTAGE` | Default attendance threshold | `75` |
| `BOOTSTRAP_ADMIN_USERNAME` | Admin username for setup | `admin` |
| `BOOTSTRAP_ADMIN_EMAIL` | Admin email for setup | Required |
| `BOOTSTRAP_ADMIN_PASSWORD` | Admin password for setup | Required (strong) |
| `APP_ENV` | `development` or `production` | `development` |
| `VITE_API_BASE_URL` | Frontend API base URL | `http://localhost:8000` |

---

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Roll back one step
alembic downgrade -1

# View current state
alembic current
```

---

## Running Tests

### Backend
```bash
cd backend

# Install test dependencies (already in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest app/tests/test_auth.py -v
```

### Frontend
```bash
cd frontend
npm run test
```

---

## Development Seed Accounts

After running `scripts/create_admin.py` and `scripts/seed_dev.py`:

| Role Portal | Username / Identifier | Password | Access Details |
|-------------|-----------------------|----------|----------------|
| **Administrator** | `admin` | `Admin@SecurePass123` | Full access to departments, classes, subjects, students, teachers, PDF roster import, audit logs |
| **Teacher** | `dr.sharma` | `Lecturer@123` | CS301 (Data Structures) & CS302 (DBMS), Take attendance, Quick-add student/subject, Process registers |
| **Teacher** | `prof.patel` | `Lecturer@123` | CS303 (Computer Networks), Take attendance, Session reviews |
| **Student** | `1cs21cs001` | `Student@123` | USN 1CS21CS001: Personal attendance metrics, subject breakdown, shortage alerts, correction requests |
| **Student** | `1cs21cs002` | `Student@123` | USN 1CS21CS002: Personal attendance records |
| **Student** | `1cs21cs003` | `Student@123` | USN 1CS21CS003: Personal attendance records |

> 🔒 **Security Notice**: On the login page, select the matching **Role Card** before entering credentials. The backend verifies the actual role in the database and rejects any cross-role spoofing.

---

## Stopping the Application

```bash
docker compose down          # Stop containers
docker compose down -v       # Stop and remove volumes (data lost)
```

---

## Troubleshooting

### Database connection fails
- Check `DATABASE_URL` in `.env`
- Ensure PostgreSQL container is healthy: `docker compose ps`
- Wait 10–15 seconds after `docker compose up` before running migrations

### Migrations fail
- Ensure the database is running and credentials are correct
- Check `alembic.ini` has the correct `sqlalchemy.url` (overridden by env in `alembic/env.py`)

### OCR returns no results
- Image quality too low — try a clearer, well-lit photo
- Tesseract not installed — check `TESSERACT_CMD` path in `.env`
- Run `docker compose exec backend tesseract --version` to verify

### Frontend shows 401 errors
- Token may have expired — log out and log back in
- Check `VITE_API_BASE_URL` points to the correct backend

### CORS errors
- Add the frontend origin to `ALLOWED_ORIGINS` in `.env`
- Restart the backend after changing CORS settings

---

## Project Structure

```
attendance_project/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # FastAPI route handlers
│   │   ├── core/            # Config, DB, auth, dependencies
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── attendance/  # Attendance business logic
│   │   │   ├── ocr/         # OCR pipeline
│   │   │   └── reports/     # Report generation
│   │   └── tests/           # Pytest test suite
│   ├── alembic/             # Database migrations
│   ├── scripts/             # Admin bootstrap & seed
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/             # Axios API clients
│       ├── components/ui/   # Reusable UI components
│       ├── features/auth/   # Auth context & guards
│       ├── layouts/         # App shell & sidebar
│       ├── pages/
│       │   ├── admin/       # Administrator pages
│       │   ├── lecturer/    # Lecturer pages
│       │   └── student/     # Student pages
│       └── types/           # TypeScript interfaces
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Implemented Features

### Authentication & Security
- JWT-based auth with Argon2 password hashing
- Role-based access control (Admin, Lecturer, Student)
- Backend authorization on every protected endpoint
- Audit logging for all significant actions
- Secure file upload with type/size validation
- CORS, rate limiting, safe error responses

### Administrator
- Dashboard with stats and charts
- Full CRUD: departments, classes, subjects
- Student and lecturer management with optional login accounts
- Teaching assignment management
- Attendance session overview
- Class attendance reports with CSV export
- Audit log viewer
- Application settings (configurable attendance threshold)

### Lecturer
- Dashboard with assignment and session summaries
- Create attendance sessions (manual or OCR)
- Manual attendance — mark each student present/absent, bulk actions
- Draft save and explicit finalization
- OCR upload with image preview, preprocessing, and Tesseract extraction
- OCR review — correct matched/unmatched/uncertain rows, assign students, set status
- Authorized correction of finalized records with reason and audit trail
- Session detail view, attendance history, reports with CSV export

### Student
- Dashboard with overall and per-subject attendance
- Attendance shortage warnings
- Subject-wise attendance with progress bars
- Full attendance report with chart, print support

### OCR Pipeline
- OpenCV preprocessing: grayscale, denoise, adaptive threshold, deskew
- Tesseract OCR with confidence scores
- USN extraction and normalization
- Roster matching: exact, fuzzy (bigram similarity), uncertain, unmatched, duplicate, missing
- Structured draft returned to lecturer for review
- Attendance status never auto-finalized

### Reports & Calculations
- Attendance % = attended / finalized sessions × 100
- Only finalized sessions in calculations (draft sessions excluded)
- Division-by-zero safe
- CSV export for class reports
- Print-friendly student report

---

## Known Limitations

1. **OCR accuracy** depends heavily on image quality. Handwritten registers may have low confidence scores requiring significant manual correction.
2. **PaddleOCR** is designed as an alternative but not yet wired in — the matcher/preprocessor pipeline is modular and ready for it.
3. The **upload directory** is local filesystem — for production, replace with S3 or equivalent object storage.
4. The **refresh token** is not stored server-side — logout does not invalidate tokens (stateless JWT). Add a token denylist for stricter logout.
5. **Mobile layout** is functional but not fully optimized for small screens.
