# Production Readiness Checklist

> **Verdict: ⚠️ NOT PRODUCTION READY**  
> The backend architecture and code quality are solid, but several critical gaps must be closed before real users or real data can be put on this system.  
> Use this checklist to track progress toward a production-safe release.

---

## How to Read This Checklist

| Symbol | Meaning |
|---|---|
| ✅ | Done and verified |
| ⚠️ | Partially done or needs verification |
| ❌ | Not done — blocks production or is a significant risk |

---

## 1. Infrastructure & Hosting

- ✅ `vercel.json` is configured to route `/api/*` to `api/index.py` and static files to `frontend1/`
- ✅ `api/index.py` exists and imports the Flask app as a Vercel-compatible serverless handler
- ✅ Framework preset is `Other` — no build command or output directory override needed
- ❌ **No live Vercel deployment has been tested** — Preview and Production environments have not been exercised with real traffic
- ❌ **Supabase project has not been provisioned** — `SUPABASE_DB_URL` is not configured; every live table status is UNKNOWN
- ❌ **Schema has not been applied to a live Supabase database** — `python backend/setup_and_run.py --init-only` has not been run against a real PostgreSQL instance
- ❌ **No Supabase region has been selected** in relation to the Vercel function region — cold-start latency is unknown

---

## 2. Environment Variables & Secrets

- ✅ `.env.example` covers all required variables with placeholders
- ✅ `.env` is in `.gitignore` — no secrets committed to source control
- ✅ `SECRET_KEY` is enforced at startup in production mode (`RuntimeError` if missing)
- ✅ Diagnostics endpoint (`/api/admin/diagnostics`) does not expose secret values
- ❌ **`SECRET_KEY` has not been set in Vercel** — production will refuse to start
- ❌ **`SUPABASE_DB_URL` has not been set in Vercel**
- ❌ **SMTP credentials have not been set** — OTP emails will fail silently or crash
- ❌ **`FRONTEND_URL` has not been set** — CORS will block all cross-origin requests in production
- ⚠️ `SESSION_COOKIE_SECURE` must be `true` in production — not yet verified in a deployed context
- ⚠️ `APP_ENV=production` must be explicitly set in Vercel Project Settings → Environment Variables

---

## 3. Database

- ✅ PostgreSQL schema (`backend/schema.sql`) is well-defined and idempotent
- ✅ All 7 migration files are ordered and non-destructive
- ✅ Case-insensitive email uniqueness enforced with `LOWER(email)` indexes
- ✅ `updated_at` triggers defined for all applicable tables
- ✅ Application SQL uses PostgreSQL-compatible syntax (`%s`, `ON CONFLICT`, `RETURNING`, `psycopg` adapters)
- ✅ No MySQL-specific syntax (`AUTO_INCREMENT`, `GROUP_CONCAT`, etc.) remains in production code
- ❌ **Live Supabase database has not been connected** — all 15+ required base tables are UNKNOWN status
- ❌ **`scripts/test_supabase_connection.py` has not passed** against the target Supabase project
- ❌ **No backup or rollback plan exists** for the live database
- ⚠️ SQLite is used locally — any SQLite-specific SQL that slips in will fail on PostgreSQL in production
- ⚠️ Student profile is missing `blood_group`, `medical_history`, `address`, `parent_name`, `parent_phone`, `parent_address` columns that Fit-Track had — if those are needed, schema changes are required

---

## 4. Email / OTP Delivery

- ✅ SMTP email delivery is implemented for: signup OTP, login OTP, password reset OTP, coach approval/rejection, password reset confirmation
- ✅ OTP values are hashed before storage — plain OTPs are never stored in the database
- ✅ OTP expiry and attempt limits are enforced
- ✅ Abuse controls block repeated OTP send requests (migrations 003, 004)
- ❌ **SMTP has not been tested against a real mail provider in a deployed environment**
- ❌ **`python scripts/test_smtp.py` has not been run with production credentials**
- ❌ **OTP email delivery is synchronous** — if SMTP times out, the API request hangs. On Vercel, function timeout is ~10 seconds. High SMTP latency will cause 504 errors.
- ⚠️ No email queue / retry mechanism — a failed OTP send means the user is stuck
- ⚠️ `FITNESS_TEST_MODE=false` must be verified in production — test mode skips OTP enforcement

---

## 5. Security

- ✅ Passwords are hashed with PBKDF2 via `werkzeug.security`
- ✅ Admin login requires both password and OTP — no single-factor admin access
- ✅ Role-based access decorators on every protected route (`@role_required`)
- ✅ Session cookies are HttpOnly, configurable SameSite, and Secure in production
- ✅ CORS is manually implemented from `CORS_ALLOWED_ORIGINS` — no wildcard in production
- ✅ No MySQL/legacy connector in production code path
- ✅ No secrets in frontend JS files
- ❌ **No CSRF protection** — Flask does not include CSRF tokens by default. State-changing POST requests are vulnerable to cross-site request forgery without it.
- ❌ **File upload validation is extension-only** — MIME type is not validated. A malicious user could rename a file and upload it. No malware scanning.
- ❌ **Upload size limit** (`FIT_TRACK_MAX_UPLOAD_MB`, default 16 MB) is set, but no per-file-type size limit
- ❌ **No audit log** — no record of who changed what, when
- ❌ **No rate limiting on login attempts** — only OTP attempts are counted, not the login endpoint itself
- ⚠️ HTTP exception descriptions are passed through to JSON responses — may expose internal detail in some edge cases
- ⚠️ Uploaded files are stored on the local filesystem — **this does not persist on Vercel** (serverless, read-only filesystem). A cloud object store (S3, Supabase Storage, Cloudinary) is required for production uploads.

---

## 6. File Uploads & Storage

- ✅ Upload extensions are allowlisted (images, videos, PDFs, certificates, spreadsheets)
- ✅ `secure_filename` is used to sanitise uploaded filenames
- ✅ UUID-based filenames prevent collisions and path traversal
- ❌ **Vercel has a read-only filesystem** — all uploads written to `backend/uploads/` or `static/uploads/` will be **lost between function invocations**. Files cannot be persisted this way.
- ❌ **No cloud storage integration** — S3, Supabase Storage, or equivalent must be added before any upload feature works in production
- ❌ This means: facility photos, event media, certificate templates, profile photos, draw PDFs, and generated certificates **will not work on Vercel** without object storage

---

## 7. Frontend Completeness

- ✅ All login/signup pages exist for student, coach, and admin
- ✅ Student dashboard and basic profile pages exist
- ✅ Coach dashboard with athlete list and attendance exists
- ✅ Admin dashboard with coach approval workflow exists
- ✅ Shared Fit-Track pages exist: announcements, chat, coaching, events, gallery, matches, profile, reports, schedule, sports
- ✅ Auth guard (`auth-guard.js`) protects all pages from unauthenticated access
- ✅ Single `api-client.js` for all API calls — no inline hardcoded URLs
- ❌ **Fit-Track shared pages are mostly static placeholders** — `frontend1/shared/fit-track-*.html` pages are not fully wired to the backend API. The `reference-pages.js` handles some, but most feature pages need real API integration work.
- ❌ **No student event registration page**
- ❌ **No certificate download page for students**
- ❌ **No live score viewer page**
- ❌ **No dedicated announcement image display**
- ❌ **No student profile photo upload interface**
- ⚠️ All CSS and JS dependencies (Bootstrap, Bootstrap Icons, Chart.js, Inter font) are loaded from CDN — the app breaks without internet access and is at CDN availability risk
- ⚠️ No loading states or error boundaries on most pages — API failures show blank sections

---

## 8. Testing

- ✅ 32 unit/integration tests passing, 2 skipped
- ✅ Tests cover: auth flows, admin OTP, attendance, core role flows, deployment endpoints, Fit-Track DB, Fit-Track extensions, integration scenarios
- ✅ `pytest.ini` configured for test discovery and import paths
- ✅ Conftest protects against accidentally connecting to a production database in tests
- ❌ **No end-to-end browser tests** — no Playwright or Selenium tests that verify the full user journey in a browser
- ❌ **PostgreSQL integration tests have never been run** — the opt-in `RUN_POSTGRES_TESTS` flag has not been exercised with a real Supabase test database
- ❌ **No SMTP integration test has passed in CI** — OTP email delivery is untested end-to-end
- ❌ **No load/stress tests** — unknown how the system behaves under concurrent users
- ⚠️ Tests use mocked DB — they do not guarantee the live Supabase schema matches what the app expects

---

## 9. Deployment Process

- ✅ `scripts/verify_vercel.py` passes all static compatibility checks
- ✅ `python -m pytest -q` passes locally
- ✅ `reset_db.py` is intentionally disabled — no destructive schema reset script is active
- ❌ **No CI/CD pipeline** — there is no GitHub Actions or equivalent workflow that runs tests on every push
- ❌ **No staging/preview deployment** has been tested with real Supabase + SMTP credentials
- ❌ **No documented rollback procedure** if a migration breaks a live database
- ⚠️ Vercel build command must apply migrations — this has not been verified to work end-to-end on the platform

---

## 10. Data & Privacy

- ✅ Coach-scoped data endpoints hide medical/parent/address fields from coaches
- ✅ Students can only see their own records
- ✅ OTP values are never logged
- ❌ **No data retention policy** — no automated deletion of old OTPs, expired sessions, or stale pending registrations
- ❌ **No privacy policy or terms of service** integrated into the frontend
- ❌ **Medical/family data** (blood group, medical history, parent info) from the Fit-Track prototype are missing from the fitness-tracker schema — if they are needed, schema + GDPR considerations apply
- ⚠️ No user account deletion (GDPR "right to be forgotten") is implemented

---

## Production Readiness Score

| Area | Status |
|---|---|
| Backend code quality | ✅ Good |
| Database schema | ✅ Well-designed |
| Authentication & authorization | ✅ Solid |
| API design | ✅ Consistent |
| Infrastructure (Vercel + Supabase) | ❌ Not set up |
| SMTP / OTP delivery | ❌ Not tested live |
| File upload persistence | ❌ Broken on Vercel |
| Frontend completeness | ⚠️ Partial |
| CSRF protection | ❌ Missing |
| Audit logging | ❌ Missing |
| CI/CD | ❌ Missing |
| End-to-end tests | ❌ Missing |
| **Overall** | **⚠️ Not production ready** |

---

## Critical Blockers (Must Fix Before Any Real Users)

1. **Apply the schema** to the live Supabase database — ensure all tables and triggers are active
2. **Configure remaining Vercel env vars** — specifically `FRONTEND_URL` to fix CORS
3. **Solve file upload persistence** — integrate Supabase Storage or S3 before any upload feature goes live
4. **Add CSRF protection** — use `Flask-WTF` or implement CSRF tokens in the API
5. **Test SMTP end-to-end** — verify that OTP emails are actually reaching inboxes
6. **Wire up the Fit-Track frontend pages** — most shared feature pages are UI shells without real API calls