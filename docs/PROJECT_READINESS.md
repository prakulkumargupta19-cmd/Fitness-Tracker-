# Project Readiness Assessment

**Assessment:** **Local static checks pass; deployment is not yet verified for production.**  
**Scope:** repository root only; not a separate `FIT-TRACK` project.  
**Evidence:** source and configuration inspection, targeted attendance/database tests, and `scripts/verify_vercel.py` run in this workspace on 2026-10-31.

## Decision

The local attendance status flow is implemented across coach, admin, and student views, and the Vercel static diagnostic passes. A release should remain blocked until the complete non-database test suite, hosted database/schema, mail, and Vercel Preview are verified in a non-production deployment.

## Critical blockers observed

### 1. Broader test suite needs verification

An earlier broad run resulted in **22 failed, 14 passed, 2 skipped**. A subsequent broad targeted run also had unrelated failures in auth/CSRF and diagnostics coverage. The focused attendance and hosted-database checks now pass (**6 passed, 1 skipped**); the skipped check requires an explicitly enabled separate PostgreSQL test database. Do not point tests at the configured application database or remove CSRF protection just to make tests green.

### 2. Hosted deployment still needs runtime verification

The current `python scripts/verify_vercel.py` passes all static checks, including:

- Vercel configuration and API entry point.
- Hosted PostgreSQL enforcement and source checks.
- Dependency imports, frontend API base, secret scans, and health/diagnostics markers.

The diagnostic explicitly reports that hosted Supabase, SMTP, and Vercel runtime checks remain necessary; its pass result is static validation only.

### 3. Hosted services and schema are unverified

No live Supabase/PostgreSQL, SMTP, or Vercel deployment was configured/validated as part of this assessment. A passing local test cannot prove schema compatibility, connection capacity, migrations, OTP delivery, browser cookie behavior, or serverless timeout behavior. A prior schema audit says its live comparison was blocked because `SUPABASE_DB_URL` was unavailable at that time; re-run a safe connection/schema audit against the intended non-production project.

### 4. Conflicting project setup guidance

Root `README.md` presents PostgreSQL/Supabase as the database and says the PostgreSQL schema/migration are applied by initialization. Current source also contains a local SQLite schema/backend, and `pyproject.toml` declares Python `>=3.12` while README says Python 3.10+. `VERCEL_UPLOAD.md` describes storage/service-role variables and capabilities not represented consistently in `.env.example` and README. Treat these as configuration drift: establish authoritative runtime behavior and make all guides/configuration agree before handoff or deployment.

## Positive evidence

- Flask API, static frontend, environment-based configuration, health endpoint, role-protected admin diagnostics, and a Vercel entry-point file exist.
- PostgreSQL schema and ordered migration files exist; separate local SQLite support is present.
- Tests cover multiple authentication, role/access, attendance, deployment and PostgreSQL workflow cases, although the current suite does not pass.
- Deployment audit checks for obvious committed secret files and hardcoded credentials; those checks passed in the run.
- README documents environment setup, local services, tests, and deployment at a high level.

These are implementation assets, not evidence of a successful production deployment.

## High-priority improvements

1. Fix the 22 failing tests, preserving CSRF and authorization protections; add tests proving legitimate token-bearing writes succeed and missing/invalid tokens are rejected.
2. Make the Vercel configuration, Python runtime declaration, entry point, and static audit agree; validate with a Preview deployment and route/static-asset smoke tests.
3. Explicitly restrict SQLite to local development if that is the intention; test that production cannot fall back to ephemeral local storage.
4. Reconcile README, `.env.example`, `pyproject.toml`, `VERCEL_UPLOAD.md`, and setup scripts so new developers receive one accurate database/storage setup path.
5. Test PostgreSQL schema plus all required migrations against a disposable clean database, then compare the live non-production schema and constraints with the application contract.
6. Verify real SMTP OTP delivery, expiry/attempt limits, password-reset workflow, and cookie/CSRF behavior in a Preview using test accounts.
7. Validate uploads/media, private storage permissions, size limits, access controls and Vercel function limits if these workflows are intended for this release.
8. Define backup/restore, migration rollback/forward procedures, monitoring/alerting, incident ownership, and a production smoke-test/rollback plan.
9. Clarify product scope and remove or finish demo pages that still contain TODO API handlers if they are reachable or presented as supported UI.

## Minimum release gate

- [ ] `python -m pytest -q` passes in a clean environment; database-backed cases are run separately with a dedicated disposable PostgreSQL test DB.
- [ ] `python scripts/verify_vercel.py` passes and its policy matches actual supported production configuration.
- [ ] A Vercel Preview serves all required frontend assets and API routes correctly.
- [ ] Health check reports a healthy database on the intended non-production Supabase project; schema, migrations, indexes, and constraints are verified.
- [ ] Signup/login/OTP/reset, role authorization, CSRF, logout, attendance, performance, and any in-scope Fit Track flows pass browser-level smoke tests.
- [ ] SMTP and any storage provider are tested with non-production credentials and representative files.
- [ ] Production secrets, cookie flags, CORS origin, database pooling/limits, backups, and rollback plan are reviewed.
- [ ] No unresolved test/audit failures or known critical security/data-loss issues remain.

## Reproduction commands

```powershell
python -m pytest -q
python scripts/verify_vercel.py
python scripts/test_supabase_connection.py
```

The live connection check requires a deliberately configured database URL. Do not point tests, schema setup, or migration experiments at production. This assessment should be refreshed after the blockers are fixed and a Preview deployment has been exercised.
