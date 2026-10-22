# Fitness Performance Tracker

> A full-stack sports performance management platform for college students, coaches, and administrators.
> **Backend:** Python Flask REST API + PostgreSQL (Supabase) | **Frontend:** Static HTML/CSS/JavaScript | **Deployment:** Vercel

---

## What This Project Does

This platform is built for **Inspiria Knowledge Campus** to manage sports activities across three user roles:

| Role | What they do |
|---|---|
| **Student** | Sign up with college email and verify via OTP, sign in with email and password, build a sports profile, view attendance and performance, chat with coach, download certificates |
| **Coach** | Register and verify via OTP, wait for admin approval, sign in with email and password, manage assigned athletes, mark attendance, log performance assessments, give feedback |
| **Admin** | OTP-secured login, approve/reject coaches, assign sports, manage tournaments, events, certificates, announcements, full data access |

The full feature set is derived from the **Fit-Track** reference prototype (`Fit-Track/`) and significantly extended with a production-grade auth system, PostgreSQL database, Vercel deployment, and REST API architecture.

---

## Quick Start (Local Development)

```powershell
# 1. Clone and enter the project
git clone <repo-url>
cd fitness-tracker

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Configure environment
copy .env.example .env
# Edit .env — set SECRET_KEY and SMTP settings at minimum

# 5. Initialise the database (SQLite locally, no Supabase needed)
python backend/setup_and_run.py --init-only

# 6. Run everything
python run_all.py
# Opens http://localhost:8080 automatically
```

> Full setup instructions with all options: **[docs/SETUP.md](docs/SETUP.md)**

---

## Architecture

```
Browser  (frontend1/  static HTML/CSS/JS)
        |  JSON + session cookie
        v
Vercel Python Serverless  (api/index.py)
        |
        v
Flask REST API  (backend/app.py)
        |                      |
        v                      v
Supabase PostgreSQL       SMTP Email Server
(production)              (OTPs, approvals)
```

- **Local dev:** `dev_server.py` serves `frontend1/` on port `8080` and proxies `/api/*` to Flask on port `5000`
- **Production:** `vercel.json` routes `/api/*` to `api/index.py` (serverless), everything else to `frontend1/`

---

## Backend Modules

| File | Responsibility |
|---|---|
| `backend/app.py` | Flask app, CORS, session, auth routes, admin routes, health check, diagnostics |
| `backend/attendance.py` | Attendance sessions, records, weekly summary, role-scoped access |
| `backend/performance.py` | CRUD for assessments, training sessions, goals, coach feedback |
| `backend/reference_features.py` | Fit-Track feature APIs: sports, coaching, tournaments, chat, announcements, reports |
| `backend/reference_extensions.py` | Fit-Track extras: bulk assignment, XLSX import, file uploads, certificates, draw PDFs, media |
| `backend/db.py` | Database connection — SQLite (local) or PostgreSQL via `SUPABASE_DB_URL` |
| `backend/schema.sql` | PostgreSQL DDL — all tables, indexes, constraints, triggers |
| `backend/auth/helpers.py` | OTP generation, hashing, verification, session helpers |
| `backend/auth/emails.py` | SMTP email delivery for OTP and notification flows |
| `backend/auth/decorators.py` | `@login_required` and `@role_required` decorators |
| `backend/migrations/` | 7 ordered, idempotent SQL migration files (001-007) |
| `api/index.py` | Vercel serverless entry point |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Web framework | Flask 3.x |
| Database (production) | PostgreSQL via Supabase |
| Database (local dev) | SQLite |
| DB driver | psycopg 3 (binary) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| UI framework | Bootstrap 5.3 + Bootstrap Icons |
| Charts | Chart.js |
| PDF generation | reportlab + pypdf + Pillow |
| Excel import | openpyxl + xlrd |
| Email | smtplib (STARTTLS/SSL) |
| Deployment | Vercel (serverless) |
| Tests | pytest |

---

## Running Tests

```powershell
# Standard test run (no database needed)
python -m pytest -q

# With PostgreSQL integration tests (use a dedicated test DB only)
$env:SUPABASE_TEST_DB_URL = "postgresql://..."
$env:RUN_POSTGRES_TESTS = "true"
python -m pytest -q

# Verify Vercel static compatibility
python scripts/verify_vercel.py

# Test SMTP email delivery
python scripts/test_smtp.py

# Test Supabase connection
python scripts/test_supabase_connection.py
```

---

## API Overview

All routes are under `/api/`. Every response is JSON with a `success` field.

| Route group | Description |
|---|---|
| `POST /api/signup` | Register a student or coach |
| `POST /api/login` | Initiate login — sends OTP |
| `POST /api/login/verify` | Complete login with OTP |
| `POST /api/logout` | End session |
| `POST /api/forgot-password` | Start password reset |
| `POST /api/reset-password` | Complete reset with OTP |
| `GET /api/session` | Check current session and role |
| `GET /api/health` | Server and database health check |
| `/api/student/*` | Student profile and sports data |
| `/api/coach/*` | Coach athlete roster |
| `/api/admin/*` | Coach approvals, student list, diagnostics |
| `/api/assessments` | Physical assessment records |
| `/api/training-sessions` | Training session logs |
| `/api/goals` | Student goals |
| `/api/feedback` | Coach feedback for students |
| `/api/attendance/*` | Attendance sessions and records |
| `/api/fit-track/*` | Sports, programmes, tournaments, chat, certificates, reports, media |

---

## Project Status

> **Not yet production ready.** The backend is well-structured and the auth system is solid, but critical items remain open:
> - Supabase not provisioned; live database schema unverified
> - File uploads will not persist on Vercel (needs object storage solution)
> - CSRF protection is not implemented
> - Most Fit-Track frontend pages are UI shells not yet wired to the API
> - SMTP not tested in a live deployed environment

See **[docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md)** for the full checklist.

---

## Documentation

| Document | What it covers |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Complete local setup, env config, database init, running, testing, and Vercel deployment |
| [docs/BACKEND_FEATURE_COMPARISON.md](docs/BACKEND_FEATURE_COMPARISON.md) | Fit-Track vs Fitness Tracker feature comparison — what carried over, what is new, what is missing |
| [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) | Full checklist of what is done, what is missing, and what must be fixed before go-live |
| [docs/FRONTEND_DEVELOPER_GUIDE.md](docs/FRONTEND_DEVELOPER_GUIDE.md) | Frontend architecture, which pages work, which are broken, and exactly what changes to make |

---

## Security Notes

- Never commit `.env` — it is in `.gitignore`
- Never expose `SUPABASE_DB_URL`, `SECRET_KEY`, or SMTP credentials in frontend JavaScript
- Use a dedicated non-production Supabase project for all integration testing
- `FLASK_DEBUG` must be `false` in production
- `SESSION_COOKIE_SECURE` must be `true` in production
- The initial admin is created via `INITIAL_ADMIN_*` env vars only — clear them after first run