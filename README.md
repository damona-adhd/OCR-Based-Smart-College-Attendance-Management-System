# Smart College Attendance Management System

A production-ready full-stack web application for college attendance management — featuring **three distinct role portals (Administrator, Teacher, Student)**, manual attendance marking, **PyMuPDF digital roster extraction**, scanned register processing with Google Gemini & Tesseract OCR, attendance correction audit trails, and live database analytics.

---

## 🌟 Master Features

1. **Mandatory 3-Role Login Landing Page**:
   - Three clickable cards: **Administrator**, **Teacher**, and **Student**.
   - Server-side role enforcement: backend rejects any role mismatch or privilege escalation.
   - Session preservation on page refresh and automatic routing to role-specific workspaces.
2. **Multi-Provider Document & Register Extraction**:
   - **Google Gemini Vision** (`google-genai`): Handles scanned, wrinkled, and handwritten attendance ledgers.
   - **PyMuPDF Direct Extraction** (`fitz`): Blazing-fast sub-second extraction on digital PDF registers.
   - **OpenCV Table Grid Detection**: Auto-detects table cells, borders, and rows.
   - **Tesseract OCR Fallback**: Windows auto-detected fallback for offline OCR.
   - **Candidate Preservation**: Never discards candidate rows, even for unenrolled classes.
3. **PDF Student Roster Import**:
   - Dedicated Administrator page (`/admin/roster-import`).
   - Duplicate USN detection, interactive preview table, and atomic database commits.
4. **Teacher Quick-Add Capabilities**:
   - Teachers can instantly add new students to an assigned class (`full_name` + `USN`).
   - Teachers can add new subjects (`subject_name` + `subject_code`) without waiting for admin approval.
5. **Attendance Correction & Audit Trail**:
   - Teachers can edit finalized attendance records with mandatory audit justification (`AttendanceCorrection` log).
   - Students can file formal correction requests directly from their portal.
6. **Real-time Database Metrics (Zero Fake Stats)**:
   - Dedicated analytics endpoints (`/api/dashboards/admin`, `/api/dashboards/teacher`, `/api/dashboards/student`).
   - Visual analytics: attendance trends, doughnut distribution, and shortage warnings (<75%).
7. **Institutional Design System**:
   - Custom palette: `#F4F5F1` Canvas, `#243630` Forest Green, `#465F56` Secondary, `#FF685F` Coral, `#55D5ED` Cyan.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, React Router 6, TanStack Query, Recharts, React Hook Form + Zod |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy 2 (Async), Pydantic v2, Alembic, SlowAPI |
| **Database** | SQLite async (`aiosqlite`) for zero-config local dev; PostgreSQL 16 for production & Docker |
| **Document Processing** | PyMuPDF (`pymupdf`), Google Gemini Vision (`google-genai`), OpenCV (`opencv-python-headless`), Tesseract OCR (`pytesseract`) |
| **Auth & Security** | Stateless JWT (HS256), Argon2 password hashing, Role-based guard middleware |
| **Testing** | Pytest (`pytest-asyncio`), Vitest, React Testing Library |

---

## ⚡ Complete Setup in One CMD Block (Windows Command Prompt)

Open **Command Prompt (`cmd.exe`)**, navigate to the project directory, and run the following block of commands to set up the entire project end-to-end:

```cmd
:: ============================================================================
:: SMART COLLEGE ATTENDANCE SYSTEM — ONE-BLOCK SETUP (CMD)
:: Run from the project root folder (e.g., D:\attendance_project2)
:: ============================================================================

:: 1. Create environment configuration files
copy .env.example .env
copy .env.example backend\.env

:: 2. Set up Python virtual environment and install backend dependencies
cd backend
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 3. Initialize SQLite database & seed default demonstration accounts
python scripts\create_admin.py
python scripts\seed_dev.py

:: 4. Install frontend dependencies
cd ..\frontend
npm install

:: 5. Return to root
cd ..
echo ============================================================================
echo Setup Complete! Run the start commands below to launch the servers.
echo ============================================================================
```

---

## 🚀 Running the Application

### Option A: Two Separate Terminals (Recommended)

Open two terminal windows (Command Prompt or PowerShell) from the project root:

#### **Terminal 1 — Backend (FastAPI)**
```cmd
cd backend
.venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```
*(If running globally without a virtualenv: `python -m uvicorn app.main:app --reload --port 8000`)*

#### **Terminal 2 — Frontend (Vite / React)**
```cmd
cd frontend
npm run dev
```

---

### Option B: One-Click Launch (PowerShell)

From PowerShell in the project root, start both servers in separate windows automatically:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; if (Test-Path .venv\Scripts\activate.ps1) { .\.venv\Scripts\activate }; python -m uvicorn app.main:app --reload --port 8000"; Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
```

---

### 🌐 Access URLs

| Interface | URL | Purpose |
|---|---|---|
| **Web Application** | **[http://localhost:5173](http://localhost:5173)** | Main 3-role portal login & dashboards |
| **Backend API Docs** | **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** | Interactive Swagger UI API explorer |
| **API Health Check** | **[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)** | Server status check (`{"status": "ok"}`) |

---

## 🔑 Pre-Seeded Login Accounts

After running `scripts/create_admin.py` and `scripts/seed_dev.py`, log in using any of the following accounts:

| Role Portal | Username / USN | Password | Included Permissions & Features |
|---|---|---|---|
| 🛡️ **Administrator** | `admin` | `Admin@SecurePass123` | Full access to departments, classes, subjects, faculty, students, PDF roster import, audit logs |
| 🎓 **Teacher** | `dr.sharma` | `Lecturer@123` | CS301 (Data Structures) & CS302 (DBMS), Manual attendance, OCR register processing, Past corrections |
| 🎓 **Teacher** | `prof.patel` | `Lecturer@123` | CS303 (Computer Networks), Take attendance, Session reviews |
| 👤 **Student** | `1cs21cs001` | `Student@123` | Personal attendance stats, subject breakdown, shortage alerts (<75%), correction requests |
| 👤 **Student** | `1cs21cs002` | `Student@123` | Personal attendance ledger and statistics |
| 👤 **Student** | `1cs21cs003` | `Student@123` | Personal attendance ledger and statistics |

> 🔒 **Security Notice**: On the login page, select the matching **Role Card** before entering credentials. The backend verifies the actual role in the database and rejects any cross-role spoofing.

---

## 📋 Step-by-Step Installation & Configuration Guide

### 1. Prerequisites
Ensure you have the following installed on your system:
- **Python**: Version 3.10, 3.11, 3.12, or 3.13 ([python.org](https://www.python.org/downloads/))
- **Node.js**: Version 18 or 20+ LTS ([nodejs.org](https://nodejs.org/))
- **Git** (optional, for cloning)

---

### 2. Configure Environment (`.env`)

Copy `.env.example` to `.env` in both the project root and `backend/`:

**Windows (CMD):**
```cmd
copy .env.example .env
copy .env.example backend\.env
```

**Linux / macOS (Bash):**
```bash
cp .env.example .env
cp .env.example backend/.env
```

#### Key Environment Variables in `.env`:
```env
# Database (Default uses local SQLite — no PostgreSQL install needed for development)
DATABASE_URL=sqlite+aiosqlite:///./attendance.db

# JWT Security
SECRET_KEY=dev_secret_key_not_for_production_replace_with_64_char_random_string_abc123xyz
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Document Extraction Engine
ATTENDANCE_EXTRACTION_PROVIDER=auto    # Options: auto, gemini, pymupdf, tesseract
ENABLE_OPENCV_GRID_DETECTION=true

# Google Gemini Vision (Optional - for advanced handwritten registers)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Tesseract OCR path (Auto-detected on standard Windows installations)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

### 3. Backend Setup & Dependencies Installation

1. Navigate to `backend/`:
   ```cmd
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```cmd
   python -m venv .venv
   call .venv\Scripts\activate
   ```
   *(On Linux/macOS: `source .venv/bin/activate`)*
3. **Install all required Python packages from `requirements.txt`:**
   ```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Initialize the database and create the initial Administrator account:
   ```cmd
   python scripts\create_admin.py
   ```
5. Populate the sample classes, subjects, teachers, and enrolled students:
   ```cmd
   python scripts\seed_dev.py
   ```

---

### 4. Frontend Setup

1. Navigate to `frontend/`:
   ```cmd
   cd ..\frontend
   ```
2. Install npm packages:
   ```cmd
   npm install
   ```
3. (Optional) Run frontend build check:
   ```cmd
   npm run build
   ```

---

## 🤖 Document Extraction & OCR Configuration

The system uses a resilient multi-tier extraction pipeline:

1. **PyMuPDF (`fitz`) — Instant Digital Extraction (Included)**:
   - Installed via `requirements.txt`.
   - Extracts selectable text and tables from digital PDF attendance sheets in under 0.5s without any external binaries or API keys.
2. **Google Gemini Vision — Handwritten & Scanned Registers (Recommended)**:
   - To enable AI vision extraction for photographed/scanned handwritten sheets:
     1. Get a free API key from [Google AI Studio](https://aistudio.google.com/).
     2. Add your key in `.env`:
        ```env
        GEMINI_API_KEY=AIzaSy...your_actual_key_here...
        GEMINI_MODEL=gemini-2.5-flash
        ```
3. **Tesseract OCR — Offline OCR Fallback**:
   - Windows: Download the installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
   - If installed to `C:\Program Files\Tesseract-OCR\tesseract.exe`, the application auto-detects it automatically.
   - Linux: `sudo apt-get install -y tesseract-ocr tesseract-ocr-eng`.

---

## 🧪 Running Automated Tests

### Backend Test Suite (Pytest)
```cmd
cd backend
python -m pytest app/tests
```
*(Tests cover authentication, attendance sessions, document extraction providers, roster matching, audit logging, and reporting).*

### Frontend Test Suite (Vitest)
```cmd
cd frontend
npm test -- --run
```

---

## 🐳 Alternative: Run with Docker Compose

If you have Docker Desktop installed and prefer containerized PostgreSQL:

```bash
# 1. Start all containers (PostgreSQL, FastAPI Backend, React Frontend)
docker compose up --build -d

# 2. Apply database migrations
docker compose exec backend alembic upgrade head

# 3. Create administrator and seed data
docker compose exec backend python scripts/create_admin.py
docker compose exec backend python scripts/seed_dev.py
```

To stop Docker containers:
```bash
docker compose down
```

---

## 🛠️ Troubleshooting & FAQs

### 1. "ModuleNotFoundError: No module named 'app'"
Make sure you are executing python commands either from within the `backend/` folder or using the module flag:
```cmd
cd backend
python scripts\seed_dev.py
```

### 2. "Duplicate student ID detected"
Each student can only have **one** attendance record per session. If a student was matched to multiple rows in an OCR scan, use the **Trash icon (`Action` column)** on the review page to delete redundant rows before clicking **Confirm & Save**.

### 3. Port 8000 or 5173 is already in use
Check and terminate any existing processes:
```powershell
# PowerShell:
Get-Process -Name python, node -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 4. Viewing Data in SQLite
The database file is stored at `backend\attendance.db`. You can view and edit tables using **[DB Browser for SQLite](https://sqlitebrowser.org/)** or via command line:
```cmd
python -m sqlite3 backend\attendance.db "SELECT id, full_name, usn FROM students LIMIT 5;"
```

---

## 📁 Project Directory Structure

```
attendance_project/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI endpoints (auth, attendance, ocr, dashboards, etc.)
│   │   ├── core/                # Configuration, DB engine, security, JWT dependencies
│   │   ├── models/              # SQLAlchemy ORM models (users, students, sessions, records)
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── services/
│   │   │   ├── attendance/      # Session finalization, draft saves & correction logic
│   │   │   ├── extraction/      # Gemini, PyMuPDF, OpenCV Grid & Tesseract providers
│   │   │   ├── ocr/             # Register extraction pipeline & roster matching
│   │   │   └── reports/         # Attendance reports & analytics
│   │   └── tests/               # Pytest integration & unit test suite
│   ├── alembic/                 # Database migrations (for PostgreSQL)
│   ├── scripts/
│   │   ├── create_admin.py      # Admin bootstrap script
│   │   └── seed_dev.py          # Development roster & user seed script
│   ├── uploads/                 # Uploaded register PDFs and images
│   ├── attendance.db            # Local SQLite database file
│   └── requirements.txt         # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios API clients for FastAPI
│   │   ├── components/ui/       # Badges, modals, cards, spinners, page headers
│   │   ├── features/auth/       # Role-card login context & route protection
│   │   ├── layouts/             # Dashboard layouts & navigation sidebars
│   │   ├── pages/
│   │   │   ├── admin/           # Admin portals (classes, teachers, students, roster import)
│   │   │   ├── lecturer/        # Teacher portals (take attendance, OCR review, reports)
│   │   │   └── student/         # Student portal (attendance charts, correction requests)
│   │   └── types/               # TypeScript definitions
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml           # PostgreSQL + backend + frontend container stack
├── .env.example                 # Environment template
└── README.md                    # Project documentation & execution guide
```
