# Project Documentation (repository root)

This document describes the inspected codebase at the repository root. It does not document a separate `FIT-TRACK` project. The repository contains both a fitness performance tracker and additional Fit Track modules/routes in the same Flask backend; that scope should be clarified by maintainers.

## Product and architecture

The app is a static HTML/CSS/JavaScript frontend (`frontend1/`) communicating with a Flask JSON API (`backend/app.py`). Authentication/session handling and role-protected endpoints live in Flask. Database code supports PostgreSQL/Supabase and a local SQLite schema/path. Email OTP delivery uses SMTP. `api/index.py` is intended as the Vercel entry point; `dev_server.py` proxies local frontend API requests to the Flask server.

```text
Browser / frontend1
    | JSON, session cookie, CSRF token
    v
Flask API (backend/app.py; local launcher or api/index.py)
    |                       |
    v                       v
PostgreSQL / SQLite       SMTP email
```

## Main user capabilities visible in code

- Student/coach signup and email OTP verification, login, password-reset flows, and session handling.
- Student profiles and sport selection; coach approval and sport-based student access.
- Role-scoped attendance and performance features (assessments, training sessions, goals, feedback).
- Administrative coach review/assignment and diagnostics.
- Additional Fit Track feature/extension routes, including sports/programme/tournament/media-related workflows. These are within the codebase and should not be conflated with a separate project directory.
- Health and deployment diagnostics endpoints, request IDs/logging, session cookie settings, CSRF checks, and environment-based CORS behavior.

This list describes implementation visible in source, not proof that every UI flow or deployed integration works end-to-end.

## Repository map

| Path | Responsibility |
|---|---|
| `backend/app.py` | Flask configuration, common request/security behavior, auth and admin routes, route wiring |
| `backend/auth/` | OTP, identity, email, session and authorization helpers |
| `backend/attendance.py` | Attendance workflows and access rules |
| `backend/performance.py` | Performance-related endpoints |
| `backend/reference_features.py`, `backend/reference_extensions.py` | Additional domain features and file workflows |
| `backend/db.py` | Database backend and connection handling |
| `backend/schema.sql` | PostgreSQL schema |
| `backend/local_schema.sql` | SQLite schema for local mode |
| `backend/migrations/` | Incremental schema changes (001–007 currently present) |
| `api/index.py`, `vercel.json` | Intended serverless entry and deployment routing |
| `frontend1/` | Static pages, styles, and JavaScript API/client logic |
| `tests/` | Pytest suite including database-free and opt-in PostgreSQL coverage |
| `scripts/` | Deployment audit and safe database connectivity check |
| `DEVELOPER_SETUP.md` | Local setup and contributor workflow |
| `PROJECT_READINESS.md` | Current release readiness assessment and blockers |

## Data and security boundaries

The API is responsible for authentication, role authorization, input handling, and database access; do not rely on browser-side role checks for protection. Flask signed sessions require a stable secret in hosted environments. Non-idempotent API requests are subject to CSRF validation in `backend/app.py`; inspect the current frontend API client when changing request handling. Configure exact production origins and secure cookies. OTP/email functionality depends on SMTP configuration. Database schema and migrations must be coordinated with application SQL.

Do not expose database URLs, SMTP credentials, signing keys, OTPs, or privileged storage credentials to frontend configuration or logs. Use a dedicated non-production database for tests and migration validation. Local SQLite schema and PostgreSQL schema are distinct: test both backend selection and migration paths when changing database code.

## Maintenance priorities

1. Resolve the failing tests and reconcile the CSRF contract with test clients/requests so automated checks exercise the intended security behavior rather than fail before route logic.
2. Align Vercel configuration and `scripts/verify_vercel.py`; establish whether SQLite is intentionally supported in production or only locally, then make the audit match that policy.
3. Document one authoritative database/backend selection process: `README.md`, `.env.example`, `pyproject.toml`, `backend/db.py`, and setup scripts currently leave conflicting signals.
4. Add deployment-level verification for Vercel routing, hosted PostgreSQL schema/migrations, SMTP delivery, browser cookies/CSRF, and uploads/media where applicable.
5. Establish backup, restore, and verified migration procedures for existing databases; the PostgreSQL schema is not a conversion tool for legacy MySQL data.
6. Clarify whether the Fit Track feature modules are in scope for this product, remove stale demo or dead-end paths where confirmed, and add user-facing end-to-end coverage for each supported workflow.
7. Consider CI that runs tests and static deployment checks on every change, plus dependency/security review and documented operational ownership.

See [PROJECT_READINESS.md](PROJECT_READINESS.md) for observed verification results and release blockers. See [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md) for developer commands.