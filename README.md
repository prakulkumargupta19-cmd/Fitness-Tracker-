# Fitness Performance Tracker

Fitness Tracker is a static HTML/CSS/JavaScript frontend backed by a Flask API and PostgreSQL database. The production target is Vercel for the frontend/API and Supabase PostgreSQL for persistent data.

## Requirements

- Python 3.10 or newer
- A Supabase PostgreSQL project for real database-backed use
- SMTP credentials to deliver real signup, login, and password-reset OTP messages

## Local setup

From the repository root, create and activate a virtual environment, install requirements, and copy the environment template:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set `SUPABASE_DB_URL` to a PostgreSQL connection string from Supabase and set a unique `SECRET_KEY`. Use the Supabase direct or pooler URI appropriate for your network. Do not commit `.env`.

Apply the PostgreSQL schema and incremental coach workflow migration to the selected Supabase project locally:

```powershell
python backend/setup_and_run.py --init-only
```

The initializer applies `backend/schema.sql` and `backend/migrations/005_coach_assignment_attendance_workflow.sql`; it is idempotent and does not delete data. For a fresh project you can also apply both files in that order in the Supabase SQL Editor. To create the initial administrator, temporarily configure `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` in the local environment before running the initializer. This is an explicit one-time action; never add these credentials to frontend configuration or commit them.

Start the local Flask API and the static frontend/API proxy in separate terminals:

```powershell
python backend/setup_and_run.py
python dev_server.py
```

Open `http://localhost:8080`. The development server proxies same-origin `/api/` requests to Flask, matching the production same-origin Vercel layout.

## Environment variables

| Variable | Purpose |
|---|---|
| `SUPABASE_DB_URL` | PostgreSQL connection string; server-side only |
| `DB_CONNECT_TIMEOUT` | Connection timeout in seconds |
| `SECRET_KEY` | Flask signed-session secret; required in production |
| `APP_ENV` / `VERCEL_ENV` | Deployment mode |
| `APP_VERSION` | Public non-secret version shown in diagnostics |
| `FRONTEND_URL` | Exact production frontend origin allowed for credentialed CORS |
| `CORS_ALLOWED_ORIGINS` | Optional comma-separated local-development origins |
| `SESSION_COOKIE_SECURE` | Secure-cookie override; secure is enforced in production |
| `SESSION_COOKIE_SAMESITE` | Session cookie same-site policy |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY` | SMTP transport settings |
| `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` | SMTP credentials and sender |
| `FLASK_HOST`, `PORT`, `FLASK_DEBUG` | Local Flask launcher settings |
| `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` | Optional one-time local initial-admin creation |
| `FITNESS_TEST_MODE` | Test-only suppression of real email delivery; OTPs are never logged |

Configure production secrets in Vercel Project Settings → Environment Variables, not in frontend code. Configure the production `FRONTEND_URL` to the exact deployed site origin. Vercel provides `VERCEL_ENV` automatically.

## Database migration notes

`backend/schema.sql` is the PostgreSQL schema for a new Supabase database. The previous MySQL schema and MySQL-specific setup have been replaced, but applying a new PostgreSQL schema does not convert or copy an existing MySQL database. Back up and migrate existing records separately, preserving IDs and foreign-key relationships, before switching the application to that database. Validate the migration against a separate test project first.

`backend/migrations/` contains PostgreSQL-compatible incremental DDL. Applying `backend/schema.sql` followed by migration `005_coach_assignment_attendance_workflow.sql` creates coach approval fields and auditable attendance fields. Admin-assigned coach sports and student-selected sports determine each coach's athlete roster; no individual athlete assignment table is used. The application uses Supabase/PostgreSQL through `SUPABASE_DB_URL`; it does not connect to MySQL. Do not point integration tests or migration experiments at production.

## Tests and compatibility check

Run the database-free test suite:

```powershell
python -m pytest -q
```

The end-to-end PostgreSQL workflow is opt-in and requires a dedicated non-production test database:

```powershell
$env:SUPABASE_TEST_DB_URL = "postgresql://..."
$env:RUN_POSTGRES_TESTS = "true"
python -m pytest -q
```

The test fixture refuses to use the same URL for `SUPABASE_TEST_DB_URL` and `SUPABASE_DB_URL`. The database-free suite and static compatibility checks do not require production credentials.

Run the repository deployment audit:

```powershell
python scripts/verify_vercel.py
```

## Deploy to Vercel

1. Push the repository to the intended Git provider and import it into Vercel. Keep the repository root as the project root.
2. Use the `Other` framework preset. `vercel.json` configures the Python API entry point and serves static pages/assets from `frontend1/`; no frontend build command is required.
3. In Vercel Project Settings → Environment Variables, configure `SUPABASE_DB_URL`, `SECRET_KEY`, SMTP `MAIL_*` values, `FRONTEND_URL`, and optionally `APP_VERSION` for Production and Preview as appropriate. Never configure production credentials in client-side variables.
4. Apply `backend/schema.sql` to the intended Supabase project before sending traffic. Create the first admin through the one-time setup workflow against the intended database, then remove the `INITIAL_ADMIN_*` values from the environment.
5. Deploy with the Vercel dashboard or CLI:

   ```sh
   npm install --global vercel
   vercel
   vercel --prod
   ```

6. Verify `https://<deployment-domain>/api/health`, login/OTP delivery, cookie-backed sessions, and `/api/admin/diagnostics` with an authenticated admin account.

See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for the release checklist. A successful static audit is not a substitute for testing with the actual Supabase, SMTP, and Vercel environments.
