# Setup and Database Initialization

This guide covers local setup and the checks needed before trusting a production database. Initializing schema is not the same as verifying existing production data.

## Prerequisites

- Python 3.10 or newer
- Git
- SMTP credentials for OTP email flows
- PostgreSQL/Supabase only when running against a remote PostgreSQL database

## Local development

From the repository root, create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Configure environment values using the repository's `.env.example` as a guide. Keep secrets out of source control. Local development uses SQLite unless configured otherwise; its default file is `backend/fitness_tracker.sqlite3` and can be overridden with `LOCAL_DB_PATH`.

Initialize the local schema:

```powershell
python backend/setup_and_run.py --init-only
```

Local SQLite startup creates missing tables and applies additive compatibility upgrades, including adding nullable `gender` when required. It does not intentionally delete existing records. Back up the SQLite file before manual database/schema operations.

Run the application with the repository's development launcher:

```powershell
python run_all.py
```

## Database schema and profile fields

- PostgreSQL base schema: `backend/schema.sql`
- Ordered PostgreSQL migrations: `backend/migrations/`
- Local SQLite schema and startup upgrades: `backend/local_schema.sql` and `backend/db.py`

Student profile persistence includes date of birth, emergency contact, body measurements, goal, sport selections, department, semester, gender, student number, blood group, medical history, address, and parent contact fields. Profile writes use an upsert by user ID, so a later submission updates the existing profile record.

For an existing PostgreSQL database, apply the required migrations (including `006_fit_track_reference_features.sql`) using the documented deployment process and verify the target schema. Do not assume that editing migration files applies them to a remote database.

## Tests and checks

```powershell
python -m pytest -q
python -m py_compile backend/app.py backend/db.py
```

Tests using mocked databases are useful for application behavior but do not prove connectivity, schema compatibility, or live-data persistence. Verify PostgreSQL writes with a controlled test account and read them back through `GET /api/profile` against the intended test/staging database.

## Production setup checklist

1. Provision the intended PostgreSQL/Supabase project and configure its connection string in the deployment environment.
2. Take a backup and apply the ordered schema/migrations to that database.
3. Confirm expected profile columns exist and run a read-after-write check.
4. Configure the application secrets, SMTP, frontend origin, and secure cookies.
5. Deploy and verify authentication, CSRF, profile save/read, and backups in the deployed environment.

Never use a destructive reset command on a database containing data you need to retain.