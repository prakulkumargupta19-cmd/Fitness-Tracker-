# Fitness Performance Tracker

A Flask API and static HTML/CSS/JavaScript frontend for student registration, coach approval and sport assignment, attendance, and performance records. MySQL is the source of truth.

## Requirements

- Python 3.10 or newer
- MySQL 8.0.16 or newer
- SMTP credentials for real signup/login/password-reset OTP delivery

## Configure

1. Copy `.env.example` to `.env`.
2. Set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` for the MySQL account/database. The account needs access to the configured database and schema DDL privileges during initial setup.
3. Set a unique `SECRET_KEY`. Production startup exits if it is missing.
4. Set `MAIL_USERNAME`, `MAIL_PASSWORD`, and, when needed, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY`, and `MAIL_FROM`. OTP logging should remain disabled in production.
5. Set `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` once to create the first administrator. The password must be at least 12 characters. These values are used only for an idempotent insert; there is no public admin signup.

Do not commit `.env`. `.env.example` contains placeholders only.

## Database Setup

From the repository root, run the non-destructive schema initializer:

```powershell
python backend/setup_and_run.py --init-only
```

The initializer creates the configured database if absent and applies missing tables using `CREATE TABLE IF NOT EXISTS`; it preserves existing rows and seeds only the reference sport catalog. Existing application tables are not dropped or recreated. The current schema includes `student_sports`, `coach_sports`, performance tables, attendance tables, and `admin_otp_verifications`, which stores admin login and password-reset OTPs separately from user OTPs. OTP sends are limited to five per hour and each code allows five guesses. `backend/migrations/001_performance_records.sql`, `backend/migrations/002_admin_otp_verifications.sql`, `backend/migrations/003_signup_otp_abuse_controls.sql`, and `backend/migrations/004_auth_otp_attempt_limits.sql` are available for existing installations. The normal initializer applies missing tables and OTP control columns non-destructively.

`reset_db.py` and the launcher's `--reset` option are intentionally disabled. Do not use a destructive reset for deployment or development data.

## Run Locally

Start Flask from the repository root:

```powershell
python backend/setup_and_run.py
```

The API listens on `0.0.0.0:5000` by default. Configure `DB_*`, `MAIL_*`, `SECRET_KEY`, `FLASK_HOST`, `PORT`, and `FLASK_DEBUG` through `.env` or process environment variables.

The frontend is plain static HTML; it has no npm build step. In a second terminal, run the local server with its `/api` proxy:

```powershell
python dev_server.py
```

To develop with separate frontend/API origins, set `window.FITNESS_API_BASE` in `frontend1/js/config.js` to the Flask API origin (for local development, `http://localhost:5000`) and set the matching frontend origin in `CORS_ALLOWED_ORIGINS`. The frontend sends session cookies with `credentials: include`.

## Deployment

Prefer serving `frontend1/` and proxying `/api/` to Flask under the same public origin. This keeps the frontend API base relative and avoids cross-site cookie restrictions. For separate hosting, configure `window.FITNESS_API_BASE` to the public API URL before the frontend scripts run, set `CORS_ALLOWED_ORIGINS` to the exact frontend origin(s), and use HTTPS with `SESSION_COOKIE_SECURE=true` and an appropriate `SESSION_COOKIE_SAMESITE` value. Never deploy a `127.0.0.1` API address.

Initialize the schema once with `python backend/setup_and_run.py --init-only`, then run the API through the included WSGI server:

```sh
gunicorn --chdir backend --bind 0.0.0.0:${PORT:-5000} app:app
```

Keep `FLASK_DEBUG=false`. Provision MySQL and SMTP credentials through the host's secret/environment manager. Do not expose database credentials, SMTP credentials, `SECRET_KEY`, or OTP values in frontend files or logs.

## Tests

Install test dependencies and run unit/mocked API tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

MySQL integration tests use a fresh, unique test database and are opt-in:

```powershell
$env:RUN_MYSQL_TESTS = "true"
python -m pytest -q
```

Provide valid test MySQL credentials through `DB_*`. The fixture creates and drops only its newly named test database; it never resets the application database.
