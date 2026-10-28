# Developer Setup

This guide covers the repository root (`C:\Users\HP\fitness-tracker`), not any separate `FIT-TRACK` project or directory. The application is a Flask API, a static HTML/CSS/JavaScript client in `frontend1/`, and a database layer with PostgreSQL/Supabase support and a local SQLite option. Vercel configuration and checks currently need repair; see [PROJECT_READINESS.md](PROJECT_READINESS.md) before planning a deployment.

## Requirements

- Python 3.12 is the version declared in `pyproject.toml` and pinned by `.python-version` (the README says Python 3.10+, so use 3.12 to match project metadata).
- Git and a terminal. Commands below use PowerShell on Windows.
- For the shared PostgreSQL workflow: a non-production Supabase/PostgreSQL database and its connection URL. The backend also has local SQLite support; inspect `backend/db.py` and `backend/setup_and_run.py` for backend selection before initializing a local database.
- SMTP credentials are needed to exercise actual email OTP flows; tests should mock mail or use isolated test configuration.

## Install

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set local values in `.env`. Never commit `.env` or use production credentials during development. At minimum, set `SECRET_KEY` to a unique random value and configure the database connection/backend required by the selected local workflow. Consult `backend/db.py`, `backend/setup_and_run.py`, and `.env.example` for the actual supported names; root guides currently disagree about SQLite and database environment options. Do not assume `SUPABASE_DB_URL` is needed when intentionally using SQLite.

For the PostgreSQL/Supabase schema workflow, the README documents:

```powershell
python backend/setup_and_run.py --init-only
```

This applies schema and migrations to the configured database. Verify the selected backend and target URL first; never initialize against production casually. The initializer also supports local SQLite, so read its output and confirm which database it selected. Existing MySQL data is not automatically migrated.

## Run locally

Open two terminals at the repository root. Start the API:

```powershell
python backend/setup_and_run.py
```

Start the static frontend and same-origin API proxy:

```powershell
python dev_server.py
```

Visit `http://localhost:8080`. `python run_all.py` is an alternate combined local launcher. The frontend is static; there is no npm build step.

## Tests and checks

```powershell
python -m pytest -q
python scripts/verify_vercel.py
```

PostgreSQL workflow tests are opt-in and must use a dedicated non-production database, never the development or production database:

```powershell
$env:SUPABASE_TEST_DB_URL = "postgresql://<test-connection>"
$env:RUN_POSTGRES_TESTS = "true"
python -m pytest -q
```

The test fixture checks that the test URL differs from `SUPABASE_DB_URL`; still independently confirm the target project before running. Live Supabase connectivity can be checked with `python scripts/test_supabase_connection.py` after configuring its database URL.

## Code map

| Path | Purpose |
|---|---|
| `backend/app.py` | Flask app, sessions/CSRF, auth, health and diagnostics, application routes and route registration |
| `backend/auth/` | Authentication helpers, OTP/email handling, authorization decorators |
| `backend/attendance.py`, `backend/performance.py` | Attendance and performance routes/business logic |
| `backend/reference_features.py`, `backend/reference_extensions.py` | Additional Fit Track domain routes/features |
| `backend/db.py` | Database selection and connection helpers |
| `backend/schema.sql`, `backend/local_schema.sql`, `backend/migrations/` | PostgreSQL and local SQLite schema/migration sources |
| `api/index.py`, `vercel.json` | Intended Vercel Flask entry point and routing (currently inconsistent with the audit script) |
| `frontend1/` | Static user interface and browser JavaScript |
| `dev_server.py`, `run_all.py` | Local development serving/launching |
| `tests/` | Unit, route, integration, and opt-in PostgreSQL workflow tests |
| `scripts/` | Deployment audit and database connectivity checks |

## Contribution conventions

- Follow existing Flask, psycopg/SQLite adaptation, and plain-JavaScript patterns; do not add a framework without confirming its use in the codebase.
- Make schema changes in the matching schema and add an ordered migration when required. Do not make destructive initialization changes.
- Add or update tests for behavior, authorization, data scoping, and schema changes. Run the test suite and deployment audit; currently both have known failures (see readiness report).
- Keep secrets server-side, never log OTPs or credentials, and use role checks for protected routes.
- Keep this guide, `README.md`, and `PROJECT_READINESS.md` consistent when setup or runtime behavior changes.