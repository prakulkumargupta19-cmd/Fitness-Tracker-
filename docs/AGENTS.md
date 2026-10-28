# AI Coding-Agent Instructions

These instructions apply to coding agents working in the repository root (`C:\Users\HP\fitness-tracker`). Do not confuse this repository with a separate `FIT-TRACK` project. Follow more specific user instructions when they do not conflict with security or data-safety guidance.

## Read first

- `README.md` for the root project and current setup claims.
- `docs/DEVELOPER_SETUP.md` for local commands and code map.
- `docs/PROJECT_DOCUMENTATION.md` for architecture and security boundaries.
- `docs/PROJECT_READINESS.md` for known failing checks and deployment gaps.
- Relevant implementation, tests, schema, and migrations before editing them.

## Architecture map

- `backend/app.py`: Flask app configuration, CSRF/request tracking, authentication/admin routes, and route registration.
- `backend/auth/`: OTP, email, identity, session, and authorization helpers.
- `backend/attendance.py`, `backend/performance.py`: attendance and performance routes.
- `backend/reference_features.py`, `backend/reference_extensions.py`: additional domain feature routes, including Fit Track functionality.
- `backend/db.py`: database backend selection/connection helpers.
- `backend/schema.sql`: PostgreSQL schema; `backend/local_schema.sql`: SQLite schema; `backend/migrations/`: ordered PostgreSQL migrations.
- `api/index.py`, `vercel.json`: intended Vercel handler and deployment config.
- `frontend1/`: static HTML/CSS/JavaScript browser application.
- `tests/`: pytest suite, including opt-in PostgreSQL workflow coverage.
- `scripts/`: deployment compatibility and Supabase connectivity checks.

## Required local verification

Use the active project virtual environment when available. From the repository root:

```powershell
python -m pytest -q
python scripts/verify_vercel.py
```

For a schema/database task, inspect the relevant tests and run PostgreSQL workflow tests only with an explicitly dedicated, disposable non-production `SUPABASE_TEST_DB_URL` and `RUN_POSTGRES_TESTS=true`. Never run initialization, migrations, destructive operations, or integration tests against production. `python scripts/test_supabase_connection.py` requires a configured connection and should only target an approved non-production environment.

The last observed results were **22 failed, 14 passed, 2 skipped** for pytest and **NOT READY FOR VERCEL** for the static audit. Re-run checks after changes, report results honestly, and distinguish pre-existing failures from regressions. Do not claim Vercel, Supabase, SMTP, browser E2E, or production verification unless actually performed.

## Safety rules for sensitive areas

- Do not casually modify or delete `backend/schema.sql`, `backend/local_schema.sql`, migration files, database selection/connection code, or initialization safeguards. Read their callers and tests first; get explicit user direction before destructive schema/data changes.
- Do not casually change authentication/OTP/password-reset code, session signing/cookie settings, CSRF enforcement, role decorators, or tenant/user data scoping. Preserve security checks and add tests for both allowed and denied paths.
- Never print, copy into docs, or commit contents from `.env`, credentials, database URLs, real OTPs, session cookies, production logs, or real user data. `.env` is sensitive even if not tracked.
- Never initialize, reset, migrate, or test against production. Prefer mocked tests or isolated disposable databases.
- Avoid exposing privileged storage or database credentials to frontend code.

## General implementation rules

- Match the existing Flask, pytest, and vanilla JavaScript stack; do not add dependencies or introduce a framework without a clear need.
- Keep changes focused, preserve unrelated worktree changes, and inspect `git status` before editing or reverting anything.
- Update the appropriate tests and documentation when behavior, setup, database schema, or deployment assumptions change.
- No formatter/linter/build script is currently configured as a required check. Do not invent one; report if additional validation cannot run.
- Before finishing, inspect the diff, verify edited files, run applicable checks, and summarize changes, risks, and actual check outcomes.