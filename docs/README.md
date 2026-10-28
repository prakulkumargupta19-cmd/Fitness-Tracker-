# Fitness Performance Tracker

A fitness and sports performance portal for students, coaches, and administrators. It brings registration and verification, athlete profiles, sport-based coaching workflows, attendance, and performance tracking together in one web application.

> This README describes the repository root, not a separate `FIT-TRACK` project. The codebase also contains additional Fit Track feature modules; see [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for scope and architecture notes.

## Key features

- Student and coach signup, email OTP verification, login, and password-reset flows.
- Student profiles and sport selection; administrator review and approval of coaches.
- Coach access scoped to assigned sports and eligible students.
- Attendance and performance records, including assessments, training sessions, goals, and coach feedback.
- Role-protected administrative workflows and diagnostics.
- Static browser frontend with a Flask JSON API, PostgreSQL/Supabase persistence, and local SQLite support in the backend.

These capabilities are present in source; not every flow has been verified in a live deployment. Current release gaps are tracked in [PROJECT_READINESS.md](PROJECT_READINESS.md).

## Tech stack

- **Frontend:** HTML, CSS, vanilla JavaScript (`frontend1/`)
- **Backend:** Python 3.12+, Flask 3.x
- **Database:** PostgreSQL via psycopg 3 (Supabase target); SQLite local option
- **Email:** SMTP for OTP and account messages
- **Tests:** pytest
- **Deployment target:** Vercel static frontend and Python API

## Requirements

- Python 3.12 (declared in `pyproject.toml` and `.python-version`; this supersedes the older Python 3.10+ statement in prior README content).
- A non-production PostgreSQL/Supabase database for the PostgreSQL workflow, or the explicitly selected local SQLite mode.
- SMTP credentials only when testing real email delivery.

## Quick start (Windows PowerShell)

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Configure `.env` for the chosen database and set a unique `SECRET_KEY`. Never commit `.env` or use production credentials for local development. For PostgreSQL, confirm `SUPABASE_DB_URL` targets a development database, then initialize:

```powershell
python backend/setup_and_run.py --init-only
```

Start the API and frontend proxy in separate terminals:

```powershell
python backend/setup_and_run.py
python dev_server.py
```

Open <http://localhost:8080>. The frontend is static and does not require `npm install` or a frontend build. Local database selection and the setup guide are documented in [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md); check the selected backend before initialization because setup guidance/configuration is being reconciled.

## Tests and static checks

```powershell
python -m pytest -q
python scripts/verify_vercel.py
```

The PostgreSQL integration workflow is opt-in and must use a dedicated non-production test database:

```powershell
$env:SUPABASE_TEST_DB_URL = "postgresql://<test-connection>"
$env:RUN_POSTGRES_TESTS = "true"
python -m pytest -q
```

The last recorded run in this workspace had **22 failed, 14 passed, and 2 skipped**; the Vercel audit also failed. See [PROJECT_READINESS.md](PROJECT_READINESS.md) for details. Do not treat deployment as ready until those issues are resolved and a Preview environment is verified.

## Documentation

- [Developer setup](DEVELOPER_SETUP.md)
- [Project documentation](PROJECT_DOCUMENTATION.md)
- [Project readiness and release gate](PROJECT_READINESS.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [AI coding-agent instructions](AGENTS.md)
- [Supabase schema audit](SUPABASE_SCHEMA_AUDIT.md)
- [Vercel compatibility report](VERCEL_COMPATIBILITY_REPORT.md)
- [Vercel deployment notes](VERCEL_UPLOAD.md)

## License

No license has been identified in the repository. Until the project owner adds a `LICENSE` file and selects terms, reuse, redistribution, and contributions are subject to the rights holder's applicable rights; do not assume this project is MIT-licensed or otherwise open source.