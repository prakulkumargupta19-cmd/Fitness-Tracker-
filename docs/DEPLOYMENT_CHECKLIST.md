# Vercel / Supabase Deployment Checklist

## Supabase PostgreSQL

- [ ] Supabase project is provisioned in a region close to the Vercel function.
- [ ] The Vercel build command `DATABASE_BACKEND=postgres python backend/setup_and_run.py --init-only` completes successfully and applies `backend/schema.sql` plus migrations 005–007 to the intended project.
- [ ] Existing MySQL records have been backed up and separately migrated/validated, if applicable.
- [ ] The Vercel-only `SUPABASE_DB_URL` uses a Supabase PostgreSQL connection string and is stored as a secret.
- [ ] Production records and test records use separate Supabase projects/databases.
- [ ] Exactly the intended initial administrator exists; there is no public administrator signup route.

## Vercel configuration

- [ ] Repository root is the Vercel project root.
- [ ] Framework preset is `Other`; `vercel.json` routes `/api/*` to `api/index.py` and static pages/assets to `frontend1/`.
- [ ] `SUPABASE_DB_URL`, `SECRET_KEY`, SMTP `MAIL_*`, and `FRONTEND_URL` are configured for the intended Vercel environments.
- [ ] Run `python scripts/test_supabase_connection.py` with the intended Supabase URL configured; confirm connection, `SELECT 1`, and every required table pass.
- [ ] Review `SUPABASE_SCHEMA_AUDIT.md`; compare live columns, constraints, defaults, indexes, view, and triggers against `DATABASE_REQUIREMENTS.md` before production cutover.
- [ ] `FRONTEND_URL` is the exact production origin; `SESSION_COOKIE_SECURE` is enabled (also enforced by production mode).
- [ ] No secret is configured as a browser-exposed/public variable.
- [ ] `FLASK_DEBUG` is `false` and the Vercel deployment environment is set to Production for the production domain.
- [ ] `/api/health` returns `status: ok` and database status `ok`.
- [ ] Static page, CSS, JavaScript, image, and favicon URLs have been checked on the deployment domain.

## Authentication and application behavior

- [ ] Student signup, email verification, login, forgot password, and password reset work.
- [ ] Coach signup, email verification, pending approval, approval/rejection, and coach login work.
- [ ] Admin login/OTP, admin authorization, and logout work.
- [ ] Session cookies work on the exact production origin with HTTPS.
- [ ] SMTP delivery and OTP expiry/attempt limits have been tested with the production mail provider.
- [ ] Attendance, student/coach relationships, assessments, sessions, goals, and feedback have been smoke-tested.
- [ ] `/api/admin/diagnostics` rejects unauthenticated/non-admin users and exposes no secrets.
- [ ] CORS allows the configured frontend origin only in production.

## Release safety

- [ ] `python scripts/verify_vercel.py` has no static compatibility blockers.
- [ ] `python -m pytest -q` passes.
- [ ] PostgreSQL workflow tests, if run, use only `SUPABASE_TEST_DB_URL` on a dedicated non-production database.
- [ ] `SUPABASE_DB_URL`, SMTP credentials, `SECRET_KEY`, OTPs, session cookies, and tokens are not in source control or logs.
- [ ] No persistent filesystem or local database is required at runtime.
- [ ] No MySQL/SQLite/PyMySQL requirement remains in production code.
- [ ] Database backups and rollback/migration plans are available before switching an existing installation.

## Exact Vercel setup

1. Import this repository with the repository root as the project root.
2. Select the `Other` preset. No frontend build command or output-directory override is required; `vercel.json` contains the build and routing configuration.
3. Set `SUPABASE_DB_URL`, `SECRET_KEY`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, and `FRONTEND_URL` in Project Settings → Environment Variables. Add `APP_VERSION` if desired.
4. The Vercel build command applies the PostgreSQL schema and Fit-Track migrations automatically. For a first-time setup or manual recovery, run `DATABASE_BACKEND=postgres python backend/setup_and_run.py --init-only` with the same production database environment variables, then verify `/api/health` before opening traffic.
5. Deploy a Preview first, test the complete auth and data flows, then deploy Production.
