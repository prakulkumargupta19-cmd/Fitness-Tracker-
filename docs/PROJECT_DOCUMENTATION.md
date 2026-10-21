# Fitness Performance Tracker: Codebase Documentation

**Updated:** 2026-10-02  
**Application type:** Flask REST API, Supabase PostgreSQL database, static HTML/CSS/JavaScript frontend, Vercel serverless deployment

This guide describes the current repository structure and behavior. For deployment and setup instructions maintained by the project, also see [README.md](../README.md). Do not put secrets or real OTPs in this document.

## 1. System Overview

The application supports three roles:

- **Student:** register with an institutional email, verify signup OTP, complete a profile, choose sports, and view attendance and performance information.
- **Coach:** register and verify an email, wait for administrator approval, receive sport assignments, and manage assigned athletes' attendance and performance records.
- **Admin:** sign in with OTP, review coach applications, assign sports, and inspect users, students, attendance, and performance information.

The Flask API owns identity, authorization, database operations, OTP validation, coach approvals, and record scoping. The browser frontend is static and calls the API with JSON requests. Authentication state is held in Flask's signed session cookie; browser requests generally send credentials so the cookie is included.

```text
Browser pages (frontend1/)
        | JSON + session cookie
        v
Vercel Python function (api/index.py)
        |
        v
Flask API (backend/app.py)
        |                   |
        v                   v
Supabase PostgreSQL         SMTP (backend/auth/emails.py)
```

## 2. Repository Map

### Root

| Path | Responsibility |
| --- | --- |
| [README.md](../README.md) | Setup, local run, deployment, and test instructions. |
| [run_all.py](../run_all.py) | Starts the static frontend server and Flask setup/server processes together. |
| [dev_server.py](../dev_server.py) | Serves `frontend1/` on port 8080 and proxies `/api/`, `/session`, and `/logout` to `127.0.0.1:5000`. |
| [requirements.txt](../requirements.txt) | Runtime Python dependencies. |
| [requirements-dev.txt](../requirements-dev.txt) | Development/test dependencies. |
| [pytest.ini](../pytest.ini) | Pytest root import path and test discovery settings. |
| [.env.example](../.env.example) | Safe environment-variable template; contains placeholders only. |
| [reset_db.py](../reset_db.py) | Intentionally exits without dropping data; directs users to non-destructive setup. |

### Backend

| Path | Responsibility |
| --- | --- |
| [backend/app.py](../backend/app.py) | Flask app configuration, JSON error handling, authentication, account verification, profiles, sports, coach approval, admin endpoints, and route registration. |
| [backend/db.py](../backend/db.py) | Loads the optional root `.env`, uses `SUPABASE_DB_URL`, and returns short-lived psycopg connections. |
| [backend/schema.sql](../backend/schema.sql) | PostgreSQL tables, keys, indexes, reference sport rows, triggers, and the `student_details` view. |
| [backend/setup_and_run.py](../backend/setup_and_run.py) | Non-destructive PostgreSQL schema initialization, optional initial admin creation, and local API startup. |
| [backend/attendance.py](../backend/attendance.py) | Attendance APIs and role/sport/student eligibility checks. |
| [backend/performance.py](../backend/performance.py) | CRUD API registration for assessments, training sessions, goals, and coach feedback. |
| [backend/reference_features.py](../backend/reference_features.py) | Core Fit-Track sports, coaching, tournament, chat, announcement, and report APIs. |
| [backend/reference_extensions.py](../backend/reference_extensions.py) | Bulk assignments, XLS/XLSX participant import, projection exports, media/photos, draw uploads, and certificate generation/download APIs. |
| [backend/auth/helpers.py](../backend/auth/helpers.py) | OTP generation/storage/verification, user lookup, password hashing helpers, and session setup. |
| [backend/auth/decorators.py](../backend/auth/decorators.py) | Login and role authorization decorators. |
| [backend/auth/emails.py](../backend/auth/emails.py) | SMTP transport and account/OTP email helpers. |
| [backend/utils.py](../backend/utils.py) | Shared JSON response construction helpers. |
| [backend/seed_data.py](../backend/seed_data.py) | Legacy seed entry point; intentionally disabled. |
| [backend/start.ps1](../backend/start.ps1) | PowerShell wrapper for initialization and API startup flags. |

Database migrations are in `backend/migrations/`: the authentication/performance migrations plus `005_coach_assignment_attendance_workflow.sql`, `006_fit_track_reference_features.sql`, and `007_fit_track_integrity.sql`. Migration 007 is additive and does not modify authentication or OTP tables.

### Deployment

| Path | Responsibility |
| --- | --- |
| [api/index.py](../api/index.py) | Imports and exposes the existing Flask application to Vercel. |
| [vercel.json](../vercel.json) | Routes API requests to the Python function and static files to `frontend1/`. |
| [backend/logging_config.py](../backend/logging_config.py) | JSON stdout logging with a constrained set of safe fields. |
| [scripts/verify_vercel.py](../scripts/verify_vercel.py) | Static deployment/dependency/source checks. |
| [DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md) | Release and platform setup checklist. |
| [VERCEL_COMPATIBILITY_REPORT.md](../VERCEL_COMPATIBILITY_REPORT.md) | Initial compatibility findings before migration changes. |

### Frontend

| Path | Responsibility |
| --- | --- |
| [frontend1/index.html](../frontend1/index.html) | Public portal/landing page and entry point for student, coach, and admin flows. There is no `landing-page.html` in the current tree. |
| [frontend1/js/config.js](../frontend1/js/config.js) | API base URL and role-to-login/dashboard maps. |
| [frontend1/js/api-client.js](../frontend1/js/api-client.js) | Shared JSON request wrapper and higher-level auth/profile/performance API methods. |
| [frontend1/js/auth-flow.js](../frontend1/js/auth-flow.js) | Login/signup/recovery event wiring, session checks, and role routing for pages that include it. |
| [frontend1/js/auth-guard.js](../frontend1/js/auth-guard.js) | Optional session guard for protected pages that include it. |
| [frontend1/css/common/app-theme.css](../frontend1/css/common/app-theme.css) | Shared visual tokens and common styles for authentication and onboarding pages. |
| [frontend1/landing-page.css](../frontend1/landing-page.css) | Public landing page styling. |
| [frontend1/css/common/global.css](../frontend1/css/common/global.css) | Shared baseline utilities. |
| [frontend1/css/common/verification-portal.css](../frontend1/css/common/verification-portal.css) | Common OTP/verification presentation. |

Role-specific styles are under `frontend1/css/admin/`, `frontend1/css/coach/`, and `frontend1/css/student/`. Dashboard HTML lives under `frontend1/admin/`, `frontend1/coach/`, and `frontend1/student/`; recovery pages are under `frontend1/shared/`; redirect/demo pages are under `frontend1/demo/`.

### Frontend Pages

| Area | Pages |
| --- | --- |
| Public | `frontend1/index.html` |
| Student | `student-login.html`, `student-loginotp.html`, `student-signup.html`, `student-signup-verify.html`, `student-basicinfo.html`, `student-personalinfo.html`, `student-dashboard.html`, `verify.html` |
| Coach | `coach-login.html`, `coach-loginotp.html`, `coach-signup.html`, `coach-signup-verify.html`, `coach-waiting.html`, `coach-dashboard.html`, `verify.html` |
| Admin | `admin-login.html`, `admin-loginotp.html`, `admin-signup.html`, `admin-signup-verify.html`, `admin-dashboard.html`, `verify.html` |
| Shared password recovery | `forgot-password.html`, `verify-otp.html`, `set-password.html` |
| Demo/redirect | `demo/assessment-form.html`, `demo/session-form.html`; a separate legacy `demo/session_form.html` is also present at repository root. |

Admin signup pages are redirects to the admin login page; public admin registration is not part of the supported onboarding flow. Some role-specific verification pages remain alongside the shared password-recovery screens.

## 3. Backend Request and Authorization Model

- JSON APIs generally return an object with a `success` flag and, when relevant, `message`, `user`, or `data` fields.
- HTTP errors under `/api/` are returned as JSON. Unexpected API exceptions are logged server-side and returned as a generic 500 response.
- `login_required` checks for `session['user_id']`.
- `role_required(...)` reloads the user from the database, refreshes the role in the session, blocks missing users, and prevents unapproved coaches from accessing coach-only routes.
- SQL values use psycopg placeholders. Table names in the performance CRUD layer are selected from a fixed internal resource map.
- `config.js` uses a same-origin API base by default. For a separate frontend/API origin, inject the public API origin before it loads, set the exact `FRONTEND_URL`, and configure secure session-cookie settings appropriately.

## 4. Authentication and User Flows

### Student Registration

1. `POST /api/signup` stages the registration in `pending_registrations`; student/coach addresses are restricted to `@inspiria.edu.in` and passwords must be at least eight characters.
2. `POST /api/account-verification/verify` validates the OTP. A student account is then created in `users` and the browser may continue with `POST /api/profile/setup`.
3. Student profile data and selected sports are written to `student_profiles` and `student_sports`.
4. Student login uses `/api/login`; successful password validation issues a login OTP. `/api/login/verify-otp` completes the session.

### Coach Registration and Approval

1. Registration is staged and email-verified using the same signup endpoints.
2. After verification, the application remains pending admin approval; the user is not yet an active coach account.
3. Admin reviews `/api/admin/coaches/pending`, then approves with selected sports using `/api/admin/coaches/approve` or rejects using `/api/admin/coaches/reject`.
4. Approval creates an active coach user and sport assignments. Coach access is limited to verified students sharing assigned sports.
5. `GET /api/coach/status?email=...` supports the waiting page's approval polling.

### Admin Access

Admin identities live in `admins`, separate from student/coach `users`. The initial admin is provisioned by optional `INITIAL_ADMIN_*` environment values. Admin login uses the shared login handler and a separate `admin_otp_verifications` table.

### Password Recovery

1. `POST /api/forgot-password` creates and emails a password-reset OTP.
2. `POST /api/forgot-password/verify-otp` consumes the OTP and marks the reset as verified in the Flask session.
3. `POST /api/reset-password` requires the matching session email and verified state, updates the password hash, clears the reset session keys, and sends a confirmation email.

The shared UI pages are `frontend1/shared/forgot-password.html`, `verify-otp.html`, and `set-password.html`.

## 5. API Reference

### Authentication, Verification, and Session

| Method | Path | Access / purpose |
| --- | --- | --- |
| POST | `/api/signup`, `/api/register` | Public; stage a student or coach registration and send signup OTP. |
| POST | `/api/login`, `/api/auth/login`, `/api/admin-login`, `/api/admin/login` | Public; validate credentials and issue a login OTP. |
| POST | `/api/login/verify-otp`, `/api/admin-login/verify-otp`, `/api/admin/login/verify-otp` | Public endpoint with pending-login session state; verify OTP and complete login. |
| POST | `/api/login/resend-otp`, `/api/admin-login/resend-otp`, `/api/admin/login/resend-otp` | Pending login; issue another login OTP. |
| GET/POST | `/api/logout`, `/api/auth/logout`, `/api/admin/logout` | Public; clear the current session. |
| GET | `/session`, `/api/session`, `/api/auth/me` | Authenticated; return session user. |
| GET | `/api/admin/session` | Admin; return administrator session. |
| POST | `/api/account-verification/send` | Public; resend signup verification OTP. |
| POST | `/api/account-verification/verify` | Public with pending registration data; verify signup OTP. |
| GET | `/api/coach/status?email=...` | Public status lookup for the coach waiting screen. |
| POST | `/api/forgot-password` | Public; start password reset. |
| POST | `/api/forgot-password/resend-otp` | Public; resend reset OTP. |
| POST | `/api/forgot-password/verify-otp` | Public; verify reset OTP and set reset session state. |
| POST | `/api/reset-password` | Reset session required; update password. |

### Profiles, Sports, and Role Administration

| Method | Path | Access / purpose |
| --- | --- | --- |
| GET | `/api/profile` | Authenticated; current user/profile. |
| PUT/PATCH | `/api/profile` | Student; update profile, selected sports, or password (with current password for password changes). |
| POST | `/api/profile/setup` | Pending verified student signup session; save initial profile. |
| GET | `/api/sports` | Public sport catalog. |
| GET/POST/PUT | `/api/student/sports` | Student; read/update selected sports. |
| DELETE | `/api/student/sports/<sport_id>` | Student; remove one selected sport. |
| GET | `/api/student/dashboard` | Student; dashboard profile and attendance payload. |
| GET | `/api/admin/users`, `/api/users` | Admin; list users and admins. |
| GET | `/api/admin/coaches/pending` | Admin; pending coach applications. |
| GET | `/api/admin/students` | Admin; student directory and profile summary. |
| GET/POST/PUT | `/api/admin/coach-sports` | Admin; inspect, add, or replace approved coach sport assignments. |
| DELETE | `/api/admin/coach-sports/<coach_id>/<sport_id>` | Admin; remove an assignment. |
| POST | `/api/admin/coaches/approve`, `/api/admin/coaches/reject` | Admin; approve/reject staged applications or legacy coach users. |
| POST | `/api/coaches/<user_id>/approval` | Admin; legacy approve/reject action. |
| GET | `/api/coach/athletes` | Approved coach; list verified assigned students. |

### Attendance

Attendance routes are registered by [backend/attendance.py](../backend/attendance.py):

- Student: `GET /api/student/attendance` returns personal history/summary.
- Coach: `GET /api/coach/attendance/sessions`, `GET /api/coach/sports`, `GET /api/coach/attendance/students?sport_id=...`, `GET /api/coach/attendance/records?sport_id=...&session_date=...`, and `POST /api/coach/attendance/records` to save or update present/absent rows.
- Admin: `GET /api/admin/students/<student_id>/attendance` and `GET /api/admin/attendance` with optional `session_date` and `sport_id` filters.

A coach must be approved and assigned to the sport. Student eligibility is checked against `student_sports`; attendance statuses are restricted to `present` and `absent`.

### Performance Records

[backend/performance.py](../backend/performance.py) registers the same CRUD pattern for these resource paths:

- `/api/assessments` → `physical_assessments`
- `/api/training-sessions` → `training_sessions`
- `/api/goals` → `goals`
- `/api/feedback` → `coach_feedback`

Each has `GET` list, `POST` create, `GET /<record_id>`, `PUT /<record_id>`, and `DELETE /<record_id>`. Students can read their own records, coaches can manage records for assigned eligible students, and admins can read across users. Record creation/update/deletion is coach-restricted by the current implementation.

## 6. Database Model

The primary schema is Supabase PostgreSQL. Main entities in [backend/schema.sql](../backend/schema.sql):

| Table/view | Purpose |
| --- | --- |
| `users` | Student and coach identities; role, password hash, verification and coach approval status. |
| `admins` | Separate administrator identity space. |
| `pending_registrations` | Signup drafts before final account creation/approval. |
| `student_profiles` | Student personal, emergency-contact, fitness, and department details. |
| `otp_verifications` | Hashed OTPs for non-admin accounts. |
| `admin_otp_verifications` | Hashed OTPs for admin login and password reset. |
| `sports` | Canonical sport catalog. |
| `student_sports` | Student-to-sport many-to-many choices. |
| `coach_sports` | Admin-assigned coach-to-sport many-to-many assignments. |
| `physical_assessments` | Coach-entered student fitness assessments. |
| `training_sessions` | Coach-entered training details. |
| `goals` | Student goals tracked by a coach. |
| `coach_feedback` | Feedback/rating records. |
| `attendance_sessions` | One coach/sport/date session. |
| `attendance_records` | Per-student `present`/`absent` status for a session. |
| `student_details` view | Student profile with age calculated from date of birth. |

Foreign keys use cascading deletes for dependent profile, OTP, sports, and record data where defined. `student_profiles` is one-to-one with `users`; the sports joins are many-to-many.

## 7. Configuration and Secrets

Configuration is loaded from the environment; local development may use the root `.env`. `.env.example` documents these variable names:

| Group | Variables |
| --- | --- |
| Runtime | `APP_ENV`, `SECRET_KEY`, `FLASK_HOST`, `PORT`, `FLASK_DEBUG` |
| Database | `SUPABASE_DB_URL`, `DB_CONNECT_TIMEOUT` |
| Browser/session | `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE` |
| Version | `APP_VERSION` |
| SMTP | `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` |
| Initial admin | `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` |
| Tests/debug | `FITNESS_TEST_MODE` |

Use a unique strong `SECRET_KEY` in production. Keep `.env` out of version control and configure secrets through the deployment environment. For public deployments use HTTPS, `SESSION_COOKIE_SECURE=true`, exact CORS origins, and `FLASK_DEBUG=false`.

## 8. Setup, Run, and Test

### Install and Initialize

```powershell
python -m pip install -r requirements-dev.txt
python backend/setup_and_run.py --init-only
```

The initializer applies the idempotent PostgreSQL schema and optionally inserts an initial admin. It does not drop application data. It does not convert or copy records from a previous MySQL database; existing records require a separately validated migration.

### Run Locally

Start only the API:

```powershell
python backend/setup_and_run.py
```

Start the static frontend with API proxy:

```powershell
python dev_server.py
```

Open `http://localhost:8080`. Alternatively, `python run_all.py` starts both services. The frontend is plain HTML/CSS/JavaScript and has no npm build step.

### Run Tests

```powershell
python -m pytest -q
```

PostgreSQL integration tests are opt-in and require a dedicated non-production database URL:

```powershell
$env:SUPABASE_TEST_DB_URL = "postgresql://..."
$env:RUN_POSTGRES_TESTS = "true"
python -m pytest -q
```

Test modules cover authentication, admin OTPs, core role/profile flows, attendance, deployment endpoints, and the PostgreSQL workflow. See `tests/conftest.py` for test database protections. Never point the integration fixture at a production database.

## 9. Security and Current Maintenance Notes

Review these current implementation details before deploying or treating this guide as a claim that every page path is healthy:

1. **SMTP remains environment-dependent:** OTP delivery is synchronous and requires working SMTP configuration. Test delivery in a non-production deployment before relying on signup, login, or reset flows.
2. **Hosted services require deployment testing:** Unit/mocked tests do not prove Vercel routing, Supabase connectivity, browser cookie behavior, or SMTP delivery. Verify these against a Preview deployment and non-production services.
3. **Existing data needs a migration plan:** The PostgreSQL schema is idempotent for object creation, not a MySQL data converter. Back up and migrate existing records separately, validating keys and relationships before production cutover.
4. **Legacy reset module:** Root `reset_db.py` is intentionally disabled. Do not use destructive scripts or manual database drops for routine setup.
5. **Local launcher only:** `run_all.py` and `dev_server.py` are local development tools; Vercel imports the Flask application through `api/index.py`.

## 10. Change Workflow

- Keep API request/response shapes and role checks in sync with `frontend1/js/api-client.js` and the page-level handlers.
- Add schema changes as ordered migration files and make startup compatibility work non-destructive.
- Add focused tests in the nearest existing `tests/test_*.py` module.
- Update this guide and `README.md` when routes, schema, setup, or deployment behavior changes.
