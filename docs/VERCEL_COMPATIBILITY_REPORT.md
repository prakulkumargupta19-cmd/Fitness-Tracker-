# Vercel Compatibility Report

**Report status:** This is the pre-implementation baseline audit. Sections A–R and the blocker table describe findings at audit time, not the current worktree.

**Audit scope:** tracked/untracked application source under the repository root, excluding `.git/` and `.venv/`. The repository currently has extensive uncommitted and untracked changes; this report reflects the working tree as inspected and does not treat those changes as authored by this task.

## A. Current Architecture

- Flask API application is defined as module-level `app` in `backend/app.py`.
- Flask routes cover signup, OTP verification, login, password reset, sessions, student profile/sports, admin management, attendance, and performance.
- `backend/db.py` already opens a new psycopg 3 connection per call using `SUPABASE_DB_URL` and `dict_row`.
- Database schema/setup, tests, and README still describe a MySQL deployment.
- `frontend1/` is the active static HTML/CSS/JavaScript frontend. `dev_server.py` serves it and proxies local API requests to Flask.
- No `vercel.json`, `api/index.py`, health route, or admin diagnostics endpoint was present at audit time.

## B. Frontend Architecture

- Plain static HTML pages and four shared JavaScript files under `frontend1/js/`; no package manifest/build step.
- `frontend1/js/config.js` sets a hardcoded `http://localhost:5000` API base for localhost/127.0.0.1 and a relative API base elsewhere.
- Pages share that config and use cookie credentials for API calls.
- External Bootstrap, Bootstrap Icons, Google Fonts, and Chart.js are loaded from CDNs.
- `frontend1/css/admin/admin-dashboard.css` and other static files are used by page-relative references; static serving and rewrite behavior need an explicit Vercel config and URL smoke test.

## C. Flask Architecture

- `backend/app.py` creates Flask at import time and does not call `app.run()` in the viewed module; local startup is delegated to `backend/setup_and_run.py` / `run_all.py`.
- The app does not use a factory. It imports route modules and registers their routes during import.
- The app includes session cookies, a CORS `after_request` handler, HTTP exception handling, and a generic exception handler.
- Existing HTTP/API handlers do not add request IDs. API internal errors return a generic message but the server logging is not structured; HTTP exception descriptions are passed through.
- CORS is manually implemented from `CORS_ALLOWED_ORIGINS`; no Flask-CORS dependency is configured.

## D. Database Architecture

- `backend/db.py` expects `SUPABASE_DB_URL`, uses psycopg 3, and creates per-call connections. It has no pooling or connection health helper.
- `.env.example`, `README.md`, `backend/setup_and_run.py`, and MySQL integration test fixtures still use `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`.
- `backend/schema.sql` is explicitly MySQL 8 schema, includes `CREATE DATABASE`/`USE`, MySQL `ENUM`, `AUTO_INCREMENT`, `ON UPDATE`, `UNSIGNED`, `INDEX` clauses, and duplicated table sections.
- There is no clean PostgreSQL-only schema/migration path established yet.

## E. Current Deployment Blockers

| File | Function/section | Problem | Why it breaks on Vercel/Supabase | Exact fix required |
|---|---|---|---|---|
| `backend/app.py` | module imports and startup | Flask app is importable, but backend modules expect differing import roots and there is no dedicated deployment entry point. | Vercel needs a predictable serverless Python handler without starting a persistent server. | Add a minimal `api/index.py` that imports/re-exports the existing Flask app, and configure explicit Vercel routes. Validate import from repository root. |
| `backend/db.py` | `get_db` | psycopg/Supabase URL is used, but the environment name in docs/config is inconsistent and failed connection handling is left to callers. | Deployment variables cannot be configured reliably; endpoints lack a health/readiness test. | Standardize `SUPABASE_DB_URL`, keep per-request connections, and add a safe database health helper. |
| `backend/app.py` | SQL in signup, profile, sports, admin, and coach routes | Remaining MySQL syntax includes `ON DUPLICATE KEY UPDATE`, `IF`, `GROUP_CONCAT`, `NOW()`, and `cursor.lastrowid`. | psycopg/PostgreSQL rejects several of these constructs or returns no `lastrowid`. | Rewrite statements for PostgreSQL using verified conflict targets, `RETURNING`, `STRING_AGG`, `CASE`, and PostgreSQL-compatible date/time expressions. |
| `backend/attendance.py` | attendance summaries and writes | `SUM(status = ...)`, `INSERT IGNORE`, and `ON DUPLICATE KEY UPDATE ... VALUES(...)` remain. | These are MySQL-specific in current form. | Use filtered/conditional aggregates, `ON CONFLICT` with actual keys, and PostgreSQL `EXCLUDED` references. |
| `backend/performance.py` | create resource | Reads `cursor.lastrowid`. | psycopg does not implement MySQL cursor ID behavior. | Add `RETURNING id` and fetch the returned row. |
| `backend/schema.sql` | whole file | MySQL DDL, database selection, duplicated table definitions, MySQL view expression. | Cannot be applied to Supabase PostgreSQL. | Produce a PostgreSQL schema with identity keys, checked text domains/enums, constraints/indexes, view expressions, and idempotent catalog inserts; retain existing schema data through documented migration steps. |
| `backend/migrations/*.sql` | all existing migrations | All four migration files are MySQL DDL and have no PostgreSQL equivalent. | Existing installs cannot migrate cleanly on Supabase. | Replace or add ordered PostgreSQL migrations and document one-time application to an empty/existing Supabase schema. |
| `backend/setup_and_run.py` | initialization and admin setup | Uses PyMySQL, MySQL database creation/introspection, and MySQL DDL; also assigns demo coach sports. | Not usable with Supabase PostgreSQL or Vercel and has inappropriate sample assignment behavior for production. | Replace with a PostgreSQL-aware local initializer/migration runner or remove it from production instructions; preserve local development without creating seeded identities. |
| `tests/conftest.py` | opt-in database fixture | Creates/drops a disposable MySQL database using PyMySQL and MySQL schema assumptions. | It cannot validate PostgreSQL behavior and requires a local MySQL server. | Use a PostgreSQL test database/isolated schema and opt-in URL, never destructive operations against a shared/production DB. |
| `tests/test_mysql_workflow.py` | integration workflow | MySQL-specific name, environment, and `lastrowid` assumptions. | The test suite does not certify the requested backend. | Migrate the integration test to PostgreSQL and use `RETURNING`; keep DB-free tests secret-free. |
| `frontend1/js/config.js` | API base configuration | Hardcodes local API URL based on hostname. | Local URL logic is inappropriate for deployed frontend and does not support configurable separate deployments. | Prefer same-origin relative URLs; allow an explicit public API base injected before scripts when frontend/API are separate. |
| repository root | Vercel configuration | No Vercel config or serverless API entry exists. | Static pages and Flask routes will not be routed to the right runtime. | Add minimal `vercel.json` and Python entry point; verify all pages, assets, and `/api/*` routes. |
| `backend/app.py` | diagnostics | No `/api/health` or protected admin diagnostics endpoint exists. | Requested status visibility and deployment checks are unavailable. | Add non-sensitive health checks and role-protected diagnostics; never serialize secret values. |
| `backend/app.py` | request/error handling | Missing request IDs, correlation response headers, structured request logs, and safe environment-aware API error envelope. | Failures in serverless logs are harder to correlate; malformed/internal errors have inconsistent bodies. | Add request ID lifecycle, safe JSON error handlers, and structured stdout logging without credentials/OTP/session values. |
| `backend/auth/emails.py` | OTP delivery and test-mode helpers | `OTP_LOG_TO_TERMINAL = True` and OTP values are printed unconditionally in a debug print; test mode also prints identities. | OTPs and personal data may be visible in Vercel logs. | Remove OTP logging and identity prints; retain only safe delivery/configuration state logs. |
| `backend/app.py` | CORS/session settings | CORS is manually allowed based on `CORS_ALLOWED_ORIGINS`; production frontend variable `FRONTEND_URL` is not used. Session defaults permit non-secure cookies unless explicitly configured. | Misconfiguration can break credentialed requests or weaken production cookies. | Resolve exact production origin from configuration, add preflight coverage, require secure cookies under production, and test allowed/denied origins. |
| `README.md`, `.env.example` | configuration/deployment | Documents MySQL setup and local execution; `.env.example` lists MySQL variables and not the requested Supabase config. | Instructions conflict with existing psycopg helper and requested deployment. | Update local and Vercel steps, Supabase URL, actually-used mail/session values, and exact Vercel environment setup. |
| repository root | diagnostics/checklist | No `scripts/verify_vercel.py` or `DEPLOYMENT_CHECKLIST.md`. | There is no repeatable post-migration static audit or deployment checklist. | Create both and make checks exclude `.git`, virtual environments, and non-source artifacts. |

## F. Files That Must Change

`backend/app.py`, `backend/attendance.py`, `backend/performance.py`, `backend/db.py`, `backend/auth/emails.py`, `backend/schema.sql`, `backend/migrations/*.sql`, `backend/setup_and_run.py`, `frontend1/js/config.js`, `tests/conftest.py`, `tests/test_mysql_workflow.py`, `requirements.txt`, `.env.example`, `.gitignore`, and `README.md`. Add `api/index.py`, `vercel.json`, `backend/logging_config.py`, `scripts/verify_vercel.py`, `DEPLOYMENT_CHECKLIST.md`, and PostgreSQL migration documentation as needed.

## G. Files That Can Likely Remain Unchanged

- HTML/CSS assets and business-facing page structure unless URL checks reveal broken paths.
- Auth/session page JavaScript that uses the shared API base, after confirming it does not bypass configuration.
- `backend/auth/decorators.py` and most of `backend/auth/helpers.py` where SQL has already been written in PostgreSQL form; verify all statements and conversions before leaving unchanged.
- `backend/seed_data.py` currently disables demo identity seeding and should remain disabled.

## H–I. MySQL and PostgreSQL Findings

The static SQL scan found MySQL-specific constructs in:

- `backend/app.py`: `ON DUPLICATE KEY UPDATE`, `IF`, `GROUP_CONCAT`, `cursor.lastrowid`, `NOW()`.
- `backend/attendance.py`: boolean `SUM` expressions, `INSERT IGNORE`, MySQL upsert syntax.
- `backend/performance.py`: `cursor.lastrowid`.
- `backend/schema.sql`: `AUTO_INCREMENT`, `ENUM`, `DATETIME`, `UNSIGNED`, `ON UPDATE`, `INDEX`, database selection, `TIMESTAMPDIFF`, duplicated schema blocks.
- `backend/migrations/001_performance_records.sql` and `002_admin_otp_verifications.sql`: MySQL DDL/enums.
- `backend/migrations/003_signup_otp_abuse_controls.sql` and `004_auth_otp_attempt_limits.sql`: MySQL `TINYINT UNSIGNED` alterations.
- `backend/setup_and_run.py`, `tests/conftest.py`, and `tests/test_mysql_workflow.py`: PyMySQL/MySQL provisioning assumptions.

`backend/auth/helpers.py` already uses psycopg-compatible parameter placeholders, `CASE`, and PostgreSQL interval syntax in the inspected portions, but requires a full query review before certification.

## J–K. Vercel and Environment Findings

- No Vercel config/API adapter was present.
- `backend/app.py` does not appear to start a server at import, but module imports and cold-start side effects need import testing.
- `run_all.py` intentionally starts multiple local servers/threads; it is local-only and must not be a Vercel entry point.
- `backend/setup_and_run.py` is likewise a local setup tool and cannot run during Vercel import.
- Existing configuration variables include `SECRET_KEY`, `APP_ENV`, `FLASK_DEBUG`, session cookie options, `CORS_ALLOWED_ORIGINS`, `SUPABASE_DB_URL` (database helper), and `MAIL_*`; `FRONTEND_URL`, app version, and Vercel environment are not standardized.
- Environment files and deployment files must be scanned without printing values; no credentials are copied into this report.

## L. Frontend API URL Findings

- `frontend1/js/config.js` has the only intentional localhost API origin found in the shared frontend source.
- Most API calls use the shared configuration, but individual HTML pages have inline fetches; verify they use `API_BASE`/`API_URL` and same-origin relative calls.
- CDN dependencies need network availability; this is not an API URL blocker but is an external runtime dependency.

## M–N. Authentication, Sessions, and CORS Findings

- OTP state is stored in database tables (including separate admin OTP table); inspected helpers do not rely on Python process memory.
- Flask signed-cookie sessions carry pending login/signup/reset state; this is compatible with stateless functions only if secret, cookie domain/security, and request origins are configured consistently.
- OTP email logging is a confirmed sensitive-data leak.
- CORS is conditional and not wildcarded in the inspected handler, but preflight, configured-origin, and secure-cookie behavior need tests after standardization.
- Admin-only routes use `role_required("admin")`; diagnostics must use that mechanism or equivalent database-confirmed role lookup.

## O. Filesystem and P. Background Work Findings

- No application data upload or persistent write path was found in the inspected backend routes. Static assets are read from the repository.
- `backend/setup_and_run.py` reads schema files; `dev_server.py` serves static assets.
- `run_all.py` starts local Flask/static servers and a browser process; it is a local development launcher, not a serverless runtime.
- No durable background worker/task queue was found. SMTP delivery is synchronous and subject to serverless function time limits.

## Q. Email/OTP Findings

- Email is sent synchronously using `smtplib` and `MAIL_*`.
- `backend/auth/emails.py` has a hardcoded OTP logging flag and unconditional OTP debug print; must be removed.
- OTP expiry/attempt/send limits are database-backed in the inspected route/helper paths, but rate limiting concurrency, transaction correctness, and Vercel SMTP delivery limits need targeted tests.
- Vercel/Supabase credentials must be environment variables; `.env.example` currently has placeholders only but uses outdated DB names.

## R. Other Risks and Audit Limitations

- `backend/schema.sql` contains repeated legacy table definitions and a MySQL-specific view; a mechanical SQL replacement would be unsafe.
- Existing uncommitted changes include deleted legacy `frontend/` paths, modified root documentation, schema/app/requirements, and numerous untracked replacement files. No unrelated working-tree changes should be reverted.
- User-supplied `.env` values and credentials were not read or printed. Only variable names and placeholder documentation were inspected.
- This is a compatibility audit, not a production deployment verification. Supabase/Vercel/mail integrations require credentials and hosted environments and must be explicitly marked untested absent those services.

## Post-audit implementation and verification status

- PostgreSQL schema, application SQL, Vercel entry/routing, structured request logging, health and protected diagnostics endpoints, environment configuration, and deployment documentation have since been implemented.
- The admin portal now includes a diagnostics page backed by `/api/admin/diagnostics`; the endpoint remains admin-protected and returns status/configuration information without secret values.
- `python -m pytest -q`: 32 passed, 2 skipped.
- `python scripts/verify_vercel.py`: static checks pass.
- Frontend relative `href`/`src` checks and the admin dashboard inline JavaScript syntax check pass.
- Existing MySQL data has not been migrated. Live PostgreSQL schema execution, hosted Supabase connectivity, SMTP delivery, and an actual Vercel deployment remain unverified and are release checklist items, not claimed as completed.
