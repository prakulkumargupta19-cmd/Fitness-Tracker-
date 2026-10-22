# Fitness Performance Tracker — Setup & Run Guide

> **Platform:** Windows (PowerShell) · Python 3.10+ · No npm/Node required

---

## Table of Contents

1. [What You Are Setting Up](#1-what-you-are-setting-up)
2. [Prerequisites](#2-prerequisites)
3. [Clone & Environment Setup](#3-clone--environment-setup)
4. [Configure Environment Variables](#4-configure-environment-variables)
5. [Database Setup](#5-database-setup)
6. [Running the Project Locally](#6-running-the-project-locally)
7. [Running Tests](#7-running-tests)
8. [Deploying to Vercel + Supabase](#8-deploying-to-vercel--supabase)
9. [Common Errors & Fixes](#9-common-errors--fixes)
10. [Folder Structure Reference](#10-folder-structure-reference)

---

## 1. What You Are Setting Up

This project is a **sports performance management platform** for a college (Inspiria Knowledge Campus).  
It has **two layers**:

| Layer | Description |
|---|---|
| **Backend** | Python Flask REST API with PostgreSQL (Supabase) or SQLite (local dev) |
| **Frontend** | Static HTML / CSS / JavaScript — zero build step required |

Three user roles exist: **Student**, **Coach**, and **Admin**. Each has its own login portal and data scope.

---

## 2. Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.10+ | Use `python --version` to verify |
| pip | Latest | Bundled with Python |
| Git | Any | For cloning |
| A text editor | — | VS Code recommended |
| SMTP credentials | — | Gmail, SendGrid, or any SMTP provider for OTP emails |
| Supabase account | — | **Only for production.** Local dev uses SQLite. |

---

## 3. Clone & Environment Setup

```powershell
# 1. Clone the repository
git clone <your-repo-url>
cd fitness-tracker

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
.venv\Scripts\activate

# 4. Install runtime dependencies
pip install -r requirements.txt

# 5. Install development/test dependencies
pip install -r requirements-dev.txt
```

---

## 4. Configure Environment Variables

Copy the example file and fill in your values:

```powershell
copy .env.example .env
```

Then open `.env` and edit it. Here is what each variable does:

### Database (choose one mode)

```dotenv
# LOCAL DEVELOPMENT (default — no Supabase needed)
DATABASE_BACKEND=sqlite
LOCAL_DB_PATH=backend/fitness_tracker.sqlite3

# PRODUCTION (set this instead)
DATABASE_BACKEND=postgres
SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres?sslmode=require
DB_CONNECT_TIMEOUT=5
```

### Flask / Session

```dotenv
APP_ENV=development          # Set to "production" on Vercel
SECRET_KEY=replace-with-a-long-random-secret
FLASK_HOST=127.0.0.1
PORT=5000
FLASK_DEBUG=false
SESSION_COOKIE_SECURE=false  # Set to true in production (HTTPS only)
SESSION_COOKIE_SAMESITE=Lax
```

### CORS / Frontend Origin

```dotenv
FRONTEND_URL=                # Leave blank locally; set to your Vercel domain in production
CORS_ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

### SMTP — Required for OTP emails

```dotenv
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_SECURITY=starttls
MAIL_TIMEOUT=20
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=your-email@gmail.com
```

> **Gmail tip:** Use an [App Password](https://support.google.com/accounts/answer/185833) — not your real Gmail password.

### Initial Admin (one-time setup)

```dotenv
INITIAL_ADMIN_NAME=Admin Name
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=StrongPassword@123
```

> After the first admin is created, clear these values from `.env`. There is no public admin signup route.

### Test / Debug mode

```dotenv
FITNESS_TEST_MODE=false     # Set to true ONLY in isolated test environments
```

---

## 5. Database Setup

### For local development (SQLite — no Supabase needed)

```powershell
# Initialise the schema and optionally create the first admin
python backend/setup_and_run.py --init-only
```

This creates the SQLite file at `backend/fitness_tracker.sqlite3` and applies all schema + migrations automatically. It is **non-destructive** — running it again is safe.

### For production (Supabase PostgreSQL)

```powershell
# Set your Supabase URL in .env, then run:
$env:DATABASE_BACKEND = "postgres"
python backend/setup_and_run.py --init-only
```

This applies `backend/schema.sql` and migrations 005–007 to your Supabase database. Run it **once** before the first deployment, after setting the Supabase URL. Vercel deployments do not apply database migrations.

### Migration files applied (in order)

| File | What it adds |
|---|---|
| `001_performance_records.sql` | Physical assessments, training sessions, goals, coach feedback |
| `002_admin_otp_verifications.sql` | Separate OTP table for admin logins |
| `003_signup_otp_abuse_controls.sql` | Rate limiting for signup OTP requests |
| `004_auth_otp_attempt_limits.sql` | Attempt counters for all OTP flows |
| `005_coach_assignment_attendance_workflow.sql` | Attendance sessions, records, coach-student sport linking |
| `006_fit_track_reference_features.sql` | Fit-Track layer: sports facilities, programmes, tournaments, certificates, chat, media |
| `007_fit_track_integrity.sql` | Squad limits, relationship constraints, timestamp triggers, indexes |

---

## 6. Running the Project Locally

### Option A — Run everything with one command (recommended)

```powershell
python run_all.py
```

This starts:
- **Flask API** on `http://127.0.0.1:5000` (auto-selects a free port if 5000 is busy)
- **Frontend proxy server** on `http://localhost:8080`
- Opens your browser automatically at `http://localhost:8080`

### Option B — Run services separately

**Terminal 1 — Start the Flask API:**
```powershell
python backend/setup_and_run.py
```

**Terminal 2 — Start the frontend proxy:**
```powershell
python dev_server.py
```

Then open `http://localhost:8080` in your browser.

### How the local proxy works

`dev_server.py` serves all `frontend1/` static files on port `8080`. Any request to `/api/*`, `/session`, or `/logout` is **proxied** to the Flask API on port `5000`. This means:
- No CORS issues during local development
- No hardcoded `localhost:5000` in your browser
- JS files are served with `no-cache` headers so config changes reload immediately

### Port configuration

| Service | Default Port | Override Variable |
|---|---|---|
| Frontend proxy | `8080` | `FITNESS_FRONTEND_PORT` |
| Flask API | `5000` | `FITNESS_BACKEND_PORT` or `PORT` |

---

## 7. Running Tests

### Quick test run (no database needed)

```powershell
python -m pytest -q
```

Expected result: all tests pass, 2 skipped (the skipped tests require a real Supabase connection).

### PostgreSQL integration tests (optional)

```powershell
$env:SUPABASE_TEST_DB_URL = "postgresql://..."  # Use a DEDICATED TEST database, never production
$env:RUN_POSTGRES_TESTS = "true"
python -m pytest -q
```

### Verify Vercel compatibility

```powershell
python scripts/verify_vercel.py
```

### Test SMTP email

```powershell
python scripts/test_smtp.py
```

### Test Supabase connection

```powershell
python scripts/test_supabase_connection.py
```

### Test modules overview

| File | What it tests |
|---|---|
| `tests/test_auth.py` | Signup, login, OTP, password reset flows |
| `tests/test_admin_otp.py` | Admin OTP login and verification |
| `tests/test_attendance.py` | Attendance marking and summaries |
| `tests/test_core_flows.py` | Student/coach/admin role flows |
| `tests/test_deployment.py` | Health endpoint, Vercel routing |
| `tests/test_integration.py` | Cross-module integration scenarios |
| `tests/test_fit_track_database.py` | Fit-Track feature database operations |
| `tests/test_fit_track_extensions.py` | Bulk operations, file uploads, certificates |
| `tests/test_postgres_workflow.py` | Full PostgreSQL schema workflow (opt-in) |

---

## 8. Deploying to Vercel + Supabase

### Step 1 — Create a Supabase project

1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose a region close to your Vercel function region
3. Copy the **PostgreSQL connection string** from Project Settings → Database → Connection String → URI mode
4. Store it securely — this is your `SUPABASE_DB_URL`

### Step 2 — Push to GitHub

```powershell
git add .
git commit -m "ready for deployment"
git push origin main
```

### Step 3 — Import to Vercel

1. Go to [vercel.com](https://vercel.com) → New Project → Import your repo
2. Set **Framework Preset** to `Other`
3. Leave build command and output directory blank — `vercel.json` handles routing

### Step 4 — Set environment variables in Vercel

In Project Settings → Environment Variables, set:

| Variable | Value |
|---|---|
| `DATABASE_BACKEND` | `postgres` |
| `SUPABASE_DB_URL` | Your Supabase PostgreSQL URI |
| `SECRET_KEY` | A long random string (use `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `APP_ENV` | `production` |
| `FITNESS_TEST_MODE` | `false` |
| `FRONTEND_URL` | Your Vercel domain e.g. `https://your-app.vercel.app` |
| `SESSION_COOKIE_SECURE` | `true` |
| `MAIL_SERVER` | Your SMTP server |
| `MAIL_PORT` | `587` |
| `MAIL_SECURITY` | `starttls` |
| `MAIL_USERNAME` | Your email |
| `MAIL_PASSWORD` | Your email app password |
| `MAIL_FROM` | Your sender email |

### Step 5 — Deploy Preview first

- Deploy to **Preview** environment first
- Test every auth flow (signup, OTP, login, password reset)
- Check `/api/health` returns `{"status": "ok"}`
- Then promote to **Production**

### How Vercel routing works

`vercel.json` routes:
- `/api/*` → `api/index.py` (Python serverless function wrapping Flask)
- Everything else → `frontend1/` static files

---

## 9. Common Errors & Fixes

| Error | Likely Cause | Fix |
|---|---|---|
| `SECRET_KEY must be configured in production` | `APP_ENV=production` but no SECRET_KEY | Set `SECRET_KEY` in environment or `.env` |
| `ModuleNotFoundError: No module named 'psycopg'` | Missing dependency | Run `pip install -r requirements.txt` |
| `The API server is unavailable` on frontend | Flask is not running | Start Flask with `python backend/setup_and_run.py` |
| Port 5000 is already in use | Another service using port 5000 | `run_all.py` auto-selects a free port; or set `PORT=5001` in `.env` |
| SMTP connection refused | Wrong SMTP config | Check `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY`, and app password |
| OTP email not received | Spam folder / SMTP not configured | Check spam; verify SMTP settings with `python scripts/test_smtp.py` |
| Database table not found | Schema not initialised | Run `python backend/setup_and_run.py --init-only` |
| 401 Unauthorized on all routes | Session cookie missing | Check `SESSION_COOKIE_SAMESITE` and `CORS_ALLOWED_ORIGINS` match frontend origin |

---

## 10. Folder Structure Reference

```
fitness-tracker/
│
├── backend/                        Flask API (Python)
│   ├── app.py                      Main app: auth, login, signup, admin, CORS, session
│   ├── attendance.py               Attendance marking and summary APIs
│   ├── performance.py              Assessments, training sessions, goals, feedback
│   ├── reference_features.py       Fit-Track core: sports, coaching, tournaments, chat, reports
│   ├── reference_extensions.py     Fit-Track extras: bulk import, media, certificates, draw PDFs
│   ├── db.py                       Database connection (PostgreSQL via psycopg / SQLite fallback)
│   ├── schema.sql                  Full PostgreSQL table definitions
│   ├── local_schema.sql            SQLite schema for local development
│   ├── setup_and_run.py            Schema initialiser + local Flask launcher
│   ├── logging_config.py           Structured logging configuration
│   ├── utils.py                    Shared utility helpers
│   ├── seed_data.py                Optional demo data seeder
│   ├── auth/
│   │   ├── helpers.py              OTP generation, session setup, user lookup
│   │   ├── emails.py               SMTP email delivery (OTPs, approvals, welcome)
│   │   └── decorators.py           @login_required and @role_required decorators
│   └── migrations/                 Ordered SQL upgrade scripts (001–007)
│
├── frontend1/                      Static HTML/CSS/JavaScript frontend
│   ├── index.html                  Landing page
│   ├── student/                    Student login, signup, dashboard pages
│   ├── coach/                      Coach login, signup, dashboard, waiting-room pages
│   ├── admin/                      Admin login and dashboard pages
│   ├── shared/                     Shared Fit-Track feature pages (chat, events, sports, etc.)
│   ├── css/                        All CSS files organised by role
│   └── js/
│       ├── config.js               API base URL configuration
│       ├── api-client.js           All API call functions (single source of truth)
│       ├── auth-flow.js            Login, signup, OTP, and password reset handlers
│       ├── auth-guard.js           Route protection — redirects unauthenticated users
│       └── reference-pages.js      Fit-Track feature page JS handlers
│
├── api/
│   └── index.py                    Vercel serverless entry point (imports Flask app)
│
├── tests/                          Pytest test suite
├── scripts/                        Utility scripts (SMTP test, Supabase check, Vercel verify)
├── docs/                           Project documentation
├── Fit-Track/                      Original reference project (Flask + SQLite prototype)
│
├── run_all.py                      Starts both Flask API and frontend proxy together
├── dev_server.py                   Frontend proxy server (port 8080 → Flask port 5000)
├── requirements.txt                Runtime Python dependencies
├── requirements-dev.txt            Development/test dependencies
├── .env.example                    Environment variable template
├── vercel.json                     Vercel routing and build configuration
└── pytest.ini                      Pytest configuration
```
