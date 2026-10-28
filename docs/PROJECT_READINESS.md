# Project Readiness Assessment

**Assessment:** **Not production-ready / not yet verified for production.**  
**Scope:** repository root only; not a separate `FIT-TRACK` project.  
**Evidence:** source and configuration inspection plus checks run in this workspace before documentation changes.

## Decision

There is meaningful application functionality and deployment-oriented code, but a release should be blocked until automated checks pass and the hosting/database/mail configuration is verified in a non-production deployment. This is not a claim that the application cannot run; it is a statement that current evidence is insufficient and concrete checks fail.

## Critical blockers observed

### 1. Test suite fails

`python -m pytest -q` resulted in **22 failed, 14 passed, 2 skipped**. The run includes failures where state-changing/API requests receive 403 from the request CSRF check before intended test behavior, as well as a diagnostics endpoint 500. These failures mean authentication, profile, coach, attendance, and diagnostics paths cannot currently be treated as regression-verified. Investigate the CSRF token setup for tests and browser requests, and fix remaining failures based on the individual tracebacks. Do not remove CSRF protection just to make tests green.

### 2. Vercel audit fails

`python scripts/verify_vercel.py` reported:

- **Vercel configuration and API entry point: FAIL.** The checker expects `builds`/`routes` fields, while the current `vercel.json` uses `outputDirectory`/`rewrites`/`functions`. The intended deployment behavior is therefore not validated by the checker; verify against current Vercel configuration semantics and update one side consistently.
- **No MySQL or SQLite production-source constructs: FAIL.** It flags SQLite references in `backend/app.py`, `backend/db.py`, `backend/local_schema.sql`, and `backend/setup_and_run.py`, plus a MySQL/PyMySQL-related match in `backend/db.py`. SQLite is evidently a deliberate local option in the setup implementation, but the audit treats any SQLite as a deployment blocker. Decide and document whether SQLite is strictly local; adjust production boundaries/checks only after confirming it cannot be selected in hosted runtime.

Although other static checks passed (dependencies, environment names, frontend API base, secret-file scan, health and protected diagnostics markers), the script's final result was **NOT READY FOR VERCEL**.

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