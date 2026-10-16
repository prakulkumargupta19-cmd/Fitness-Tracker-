# Fitness Performance Tracker

A full-stack fitness and sports performance management application built for students, coaches, and administrators. The platform combines a static HTML/CSS/JavaScript frontend with a Flask REST API and a Supabase PostgreSQL database. It is designed for deployment on Vercel while keeping the database and server-side session logic in a secure backend.

## Overview

The application supports three main users:

- Students: sign up with an institutional email, verify OTP, complete profile data, choose sports, and view attendance/performance records.
- Coaches: sign up, wait for admin approval, manage assigned athletes, mark attendance, and create training/performance records.
- Admins: sign in with OTP, review coach applications, assign sports, and monitor student/coach records.

The current codebase is organized around a Python Flask service in `backend/` and a static portal in `frontend1/`.

## Current architecture

- `frontend1/` hosts the web UI pages and shared frontend assets.
- `backend/app.py` contains the main Flask app, session handling, route registration, authentication flows, admin logic, and health checks.
- `backend/attendance.py` manages student and coach attendance APIs and role-based access logic.
- `backend/performance.py` manages assessments, training sessions, goals, and coach feedback records.
- `backend/reference_features.py` exposes the Fit-Track reference feature layer without changing root authentication.
- `backend/auth/` contains OTP generation, email delivery, helpers, and authorization decorators.
- `backend/db.py` uses a local SQLite database by default and supports PostgreSQL through an explicit production configuration.
- `backend/schema.sql` defines the production PostgreSQL schema.
- `backend/migrations/006_fit_track_reference_features.sql` adds the PostgreSQL data model recreated from the separate `Fit-Track/` reference project.
- `api/index.py` exposes the Flask app to Vercel serverless hosting.
- `dev_server.py` serves `frontend1/` locally and proxies `/api/` requests to the backend Flask process.

## Key features

### Student features
- Email-based signup and OTP verification
- Profile setup and personal information capture
- Sport selection and assignment tracking
- Attendance overview with weekly summaries
- Performance record visibility
- Fit-Track passports, programmes, schedules, events, live scores, media, announcements, chat, certificates, and reports
- Session-based authentication with Flask cookies

### Coach features
- Coach signup and approval workflow
- Admin-assigned sport permissions
- Athlete roster based on assigned sports
- Attendance entries for verified students
- Training, assessment, and feedback creation/editing
- Role-aware data restrictions

### Admin features
- OTP-based admin login
- Review pending coach applications
- Approve or reject coach registrations
- Assign sports to coaches
- Inspect students and athlete-related records
- Admin diagnostics endpoint for environment health checks

## Technology stack

- Python 3.10+
- Flask 3.x
- PostgreSQL / Supabase
- psycopg 3
- HTML, CSS, JavaScript
- Vercel deployment target
- SMTP email delivery for OTPs and notifications

## Repository structure

```text
fitness-tracker/
├── .env.example                  # Sample environment variables
├── .gitignore                    # Git ignore rules
├── README.md                     # Project overview and setup guide
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # Dev/test dependencies
├── pytest.ini                    # Pytest configuration
├── dev_server.py                 # Local frontend + proxy server
├── run_all.py                    # Runs backend + frontend together
├── vercel.json                   # Vercel routing configuration
├── api/
│   └── index.py                  # Vercel serverless entry point
├── backend/
│   ├── app.py                    # Main Flask app
│   ├── attendance.py             # Attendance APIs
│   ├── performance.py            # Performance CRUD APIs
│   ├── db.py                     # DB connection helper
│   ├── schema.sql                # PostgreSQL schema
│   ├── setup_and_run.py          # DB init and app start helper
│   ├── auth/
│   │   ├── decorators.py         # Auth decorators
│   │   ├── emails.py             # Email sending logic
│   │   ├── helpers.py           # OTP + user/session helper functions
│   │   └── __init__.py
│   ├── migrations/
│   │   └── ...                   # PostgreSQL migration files
│   ├── logging_config.py        # JSON logging config
│   ├── seed_data.py             # Legacy seed file
│   ├── utils.py                 # Shared response helpers
│   └── start.ps1                # Local PowerShell helper
├── frontend1/
│   ├── index.html               # Public landing page
│   ├── admin/                   # Admin pages
│   ├── coach/                   # Coach pages
│   ├── student/                 # Student pages
│   ├── shared/                  # Shared recovery pages
│   ├── js/
│   │   ├── api-client.js        # API wrappers
│   │   ├── auth-flow.js         # Auth flow logic
│   │   ├── auth-guard.js        # Protected page checks
│   │   └── config.js            # API base configuration
│   └── css/                     # Stylesheets
├── docs/
│   ├── DATABASE_REQUIREMENTS.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   └── PROJECT_DOCUMENTATION.md
├── scripts/
│   └── verify_vercel.py         # Vercel compatibility checks
├── tests/                       # Automated tests
├── demo/                        # Demo pages and samples
├── reference/                    # Reference materials
└── .env                         # Local environment (not committed)
```

## Local development setup

### 1) Create environment

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

On Linux/macOS Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Run the install command and the app with the same Python environment. On Windows,
after activating `.venv`, use `python` (not an unrelated system interpreter).
If you do not activate it, use `.venv\Scripts\python.exe` for both commands:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe run_all.py
```

### 2) Configure environment variables

Copy `.env.example` to `.env`. Local development uses the SQLite database automatically, so no Supabase account or database URL is required. At minimum, set:

```env
DATABASE_BACKEND=sqlite
LOCAL_DB_PATH=backend/fitness_tracker.sqlite3
SECRET_KEY=your-long-random-secret
APP_ENV=development
APP_VERSION=1.0.0
FRONTEND_URL=http://localhost:8080
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_SECURITY=starttls
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password
MAIL_FROM=your_sender_email
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
```

For real OTP delivery, fill in the SMTP values. Gmail requires an App Password when two-factor authentication is enabled. Verify the credentials without sending an email with:

```powershell
.\.venv\Scripts\python.exe scripts\test_smtp.py
```

Use `DATABASE_BACKEND=postgres` only when you intentionally want to use Supabase/PostgreSQL.

### 3) Initialize the database

For local SQLite, initialization is automatic. You can also run the non-destructive initializer explicitly:

```powershell
python backend/setup_and_run.py --init-only
```

This initializer is designed to be non-destructive and applies the local schema without deleting current data. For PostgreSQL, it applies `backend/schema.sql` followed by the migrations under `backend/migrations/`.

### 4) Run the app locally

The easiest option is to start both services together in one terminal. First
activate the virtual environment and install the dependencies as described
above. On Windows, use PowerShell:

```powershell
python run_all.py
```

On Linux/macOS:

```bash
python run_all.py
```

This launches the Flask API and the static frontend server together on ports 5000 and 8080, and opens the app in the browser.

If you want to start them manually instead, use two terminals:

Windows PowerShell:

```powershell
python backend/setup_and_run.py
python dev_server.py
```

Linux/macOS Bash:

```bash
python backend/setup_and_run.py
python dev_server.py
```

Then open:

```text
http://localhost:8080
```

The static frontend serves pages from `frontend1/`, while `/api/*` requests are proxied to the Flask backend on port 5000. The local database is stored in `backend/fitness_tracker.sqlite3` and is ignored by Git.

## Authentication and session model

This app uses Flask session cookies for user authentication. Sessions are tied to the authenticated `user_id` and `role`, and protected routes are checked with decorators in `backend/auth/decorators.py`.

OTP-based sign-in is used for:
- student and coach signup verification
- login verification
- password resets
- admin login and password reset flows

The app uses hashed OTP values stored in the database and rejects expired or overused verification codes.

## Database model

The database schema is defined in `backend/schema.sql` and includes tables for:

- `users` — core user accounts for students and coaches
- `admins` — administrative users
- `student_profiles` — student profile details
- `pending_registrations` — pending coach/student onboarding records
- `otp_verifications` and `admin_otp_verifications` — one-time code storage
- `sports` — supported sports catalog
- `coach_sports` and `student_sports` — many-to-many role mapping
- `physical_assessments`, `training_sessions`, `goals`, and `coach_feedback` — performance tracking
- `attendance_sessions` and `attendance_records` — attendance tracking
- Fit-Track reference tables — sports facilities, programmes, enrollments, daily assessments, tournaments, registrations, matches, media, achievements, certificates, announcements, messages, and coaching sessions

The schema is PostgreSQL-specific and is not a MySQL migration.

## API design

Most API routes are under `/api/` and return JSON payloads with a consistent `success` response shape. Error handling is centralized in `backend/app.py` so invalid requests and unexpected exceptions are logged and returned as JSON responses.

Important route families include:

- Auth: `/api/signup`, `/api/login`, `/api/logout`, `/api/forgot-password`, `/api/reset-password`
- Admin: `/api/admin/*`
- Student: `/api/student/*`
- Coach: `/api/coach/*`
- Performance: assessments, goals, training, and feedback-related endpoints
- Attendance: student and coach attendance endpoints and summaries

## Testing

Run the database-free test suite:

```powershell
python -m pytest -q
```

For database-backed integration tests, use a dedicated non-production database and opt in explicitly:

```powershell
$env:SUPABASE_TEST_DB_URL = "postgresql://..."
$env:RUN_POSTGRES_TESTS = "true"
python -m pytest -q
```

The deployment verification script can also be run:

```powershell
python scripts/verify_vercel.py
```

## Deployment

The application is targeted at Vercel for hosting the static frontend and Python API. `api/index.py` imports the Flask app, and `vercel.json` routes API traffic to the backend and serves the static app from `frontend1/`.

Production setup should include:
- `SUPABASE_DB_URL`
- `SECRET_KEY`
- SMTP configuration
- `FRONTEND_URL`
- `APP_ENV` or `VERCEL_ENV`
- optionally `APP_VERSION`

Never expose production secrets in frontend JavaScript.

## Notes and cautions

- Keep `.env` local and do not commit it.
- Use a dedicated Supabase project or a safe non-production database for testing.
- Apply schema changes carefully; the app expects PostgreSQL behavior and data types.
- Admin creation for first-run setup should be done intentionally and removed from environment config afterward.

## Documentation references

Additional project docs are already present in:

- `docs/PROJECT_DOCUMENTATION.md`
- `docs/DATABASE_REQUIREMENTS.md`
- `docs/DEPLOYMENT_CHECKLIST.md`
- `VERCEL_COMPATIBILITY_REPORT.md`

These supplements are useful for architecture context, database constraints, and deployment checks.
