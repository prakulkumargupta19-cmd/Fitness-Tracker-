# Backend Feature Comparison: Fit-Track vs Fitness Tracker

> This document compares the original **Fit-Track** reference project (`Fit-Track/`) against the upgraded **Fitness Tracker** backend (`backend/`).  
> It answers: *What does Fit-Track have? Does Fitness Tracker have it? What extra features does Fitness Tracker add?*

---

## Quick Overview

| | Fit-Track | Fitness Tracker |
|---|---|---|
| **Type** | Prototype / Hackathon build | Production-target application |
| **Database** | SQLite (file-based, no config needed) | PostgreSQL via Supabase (production) + SQLite (local dev) |
| **Auth** | Username + password (no email verification) | Email + OTP verification + hashed passwords |
| **Frontend** | Jinja2 server-side templates | Static HTML/CSS/JS calling a REST API |
| **Deployment** | Local only (`python app.py`) | Vercel (serverless) + Supabase |
| **API style** | HTML routes returning rendered pages | JSON REST API (`/api/*` routes) |
| **Role system** | Admin / Coach / Student (username-based) | Admin / Coach / Student (email + JWT session cookie) |

---

## Section 1 — Authentication & User Management

### What Fit-Track Has

| Feature | Fit-Track implementation |
|---|---|
| Login | Username + password with `werkzeug` hash check |
| Roles | `admin`, `coach`, `student` — stored in `users.role` |
| Student self-registration | Email-domain validation (`@inspiria.edu.in`) — no OTP |
| Admin accounts | Hardcoded in `ADMINS` list + seeded on first run |
| Coach accounts | Hardcoded in `COACHES` list + seeded on first run |
| Session | Flask `session` (server-side cookie) |
| Password change | Not implemented |
| Forgot password | Not implemented |

### What Fitness Tracker Has ✅

| Feature | Status | Details |
|---|---|---|
| Email + password login | ✅ | `POST /api/login` → Direct login for students/coaches; OTP for admins |
| OTP-based login verification | ✅ | `POST /api/login/verify-otp` — Required for administrator accounts |
| Student email signup | ✅ | `POST /api/signup` with institutional email domain check |
| Signup OTP verification | ✅ | `POST /api/verify-otp` — email must be verified before access |
| Coach signup + approval workflow | ✅ | Coach registers → admin approves/rejects → coach notified by email |
| Admin OTP login | ✅ | Extra security layer — admin password alone is not enough |
| Forgot password | ✅ | `POST /api/forgot-password` → OTP email → `POST /api/reset-password` |
| Password reset success email | ✅ | Confirmation email sent after reset |
| Hashed passwords | ✅ | `werkzeug.security.generate_password_hash` (PBKDF2) |
| OTP expiry + attempt limits | ✅ | OTPs expire after N minutes; abuse controls block repeated attempts |
| Session cookie — HttpOnly, Secure, SameSite | ✅ | Configurable; enforced in production |
| Role-based access decorators | ✅ | `@login_required`, `@role_required("admin")`, etc. |
| Logout | ✅ | `POST /api/logout` clears the session |
| Coach status tracking | ✅ | `pending` → `approved` / `rejected` / `declined` with timestamps |
| Initial admin seeding | ✅ | Via `INITIAL_ADMIN_*` env vars — one-time, no public route |

---

## Section 2 — Student Features

### What Fit-Track Has

| Feature | Fit-Track implementation |
|---|---|
| Student profile | `students` table: name, student_id, email, phone, department, semester, sports, bio, emergency_contact, blood_group, medical_history, address, parent info |
| Auto-generated Sports Passport ID | `IKC-SP-YYYY-#####` format |
| Profile photo | Admin-managed (`photo_path` field) |
| Sports assignment | Admin assigns sports to students |
| View own profile | Student can view their Sports Passport page |
| Download own data | CSV performance data download |
| Chat with coach | Direct student-coach messaging |
| Event registration | Students self-register for events |
| Certificate download | Students download generated certificates from their passport |
| View announcements | Read-only access |
| View fixtures/live scores | Read-only access |
| View facility media | Read-only access |

### What Fitness Tracker Has ✅

| Feature | Status | Details |
|---|---|---|
| Student profile (basic) | ✅ | `student_profiles` table: DOB, emergency_contact, height, weight, goal, sport_activity, department |
| Personal info setup | ✅ | `POST /api/student/profile` multi-step onboarding |
| Sport selection | ✅ | `student_sports` table — students choose their sports |
| View own attendance | ✅ | `GET /api/attendance/student` with weekly summaries |
| View own performance records | ✅ | `GET /api/assessments`, `GET /api/goals`, `GET /api/training-sessions` |
| View coach feedback | ✅ | `GET /api/feedback` scoped to logged-in student |
| Sports Passport ID | ✅ | Carried forward from Fit-Track data model via migration 006 |
| Chat with coach | ✅ | `GET/POST /api/fit-track/messages` — scoped to own coach relationships |
| View announcements | ✅ | `GET /api/fit-track/announcements` |
| View events / live scores | ✅ | `GET /api/fit-track/tournaments`, `/api/fit-track/matches` |
| View facility / gallery media | ✅ | `GET /api/fit-track/facilities`, `/api/fit-track/gallery` |
| Download own certificate | ✅ | `GET /api/fit-track/certificates` filtered to own records |
| View coaching schedule | ✅ | `GET /api/fit-track/coaching-sessions` — read-only |
| View sports & programmes | ✅ | `GET /api/fit-track/sports`, `/api/fit-track/programmes` |
| Blood group / medical history / parent info | ⚠️ | Fields exist in Fit-Track; **not yet in fitness-tracker student_profiles schema** |
| Profile photo upload | ⚠️ | Fit-Track has it; fitness-tracker upload endpoint exists but no student-facing photo page |
| Download CSV performance report | ✅ | `GET /api/fit-track/reports` — privacy-scoped projection CSVs |

---

## Section 3 — Coach Features

### What Fit-Track Has

| Feature | Fit-Track implementation |
|---|---|
| View assigned athlete list | Coaches see students in their programme |
| Attendance marking | Per-session attendance for enrolled students |
| Athlete development metrics | Sport-specific scoring per student |
| Coach remarks | Text notes added to student records |
| Download coaching report | CSV report for assigned athletes |
| Chat with students | Direct messaging with assigned students |
| Manage coaching schedule sessions | Create/edit/delete dated sessions for own programme |
| View-only: student profile (limited) | Coaches cannot see medical/parent/address fields |

### What Fitness Tracker Has ✅

| Feature | Status | Details |
|---|---|---|
| Coach signup + approval flow | ✅ | Full email-based signup with admin approval (Fit-Track had hardcoded coaches) |
| View assigned athlete list | ✅ | `GET /api/coach/athletes` — scoped to approved coach's sports |
| Mark attendance | ✅ | `POST /api/attendance/sessions` + `POST /api/attendance/records` |
| Edit attendance | ✅ | `PATCH /api/attendance/records/:id` |
| Physical assessments for athletes | ✅ | `POST /api/assessments` with coach-student sport eligibility check |
| Training session logs | ✅ | `POST /api/training-sessions` |
| Athlete goals | ✅ | `POST /api/goals` |
| Coach feedback (with rating) | ✅ | `POST /api/feedback` with optional 0–10 rating |
| Download coaching report CSV | ✅ | `GET /api/fit-track/reports` scoped to coach's athletes |
| Chat with assigned students | ✅ | `GET/POST /api/fit-track/messages` |
| Manage coaching schedule | ✅ | Create/edit/delete sessions for own programme |
| View student profile (limited fields) | ✅ | Medical, parent, address fields hidden from coaches |
| Coach qualification / specialization / experience | ✅ | Extra fields in `users` table (`qualification`, `specialization`, `experience_years`) |

---

## Section 4 — Admin Features

### What Fit-Track Has

| Feature | Fit-Track implementation |
|---|---|
| Full student CRUD | Create, read, update, delete any student record |
| Full coach management | Add/edit coaches, assign sports |
| Sports / facility management | Add sports, upload facility photos, gallery |
| Coaching programme management | Create programmes, assign coaches |
| Tournament management | Create events, manage fixtures, scores, results |
| Draw PDF upload | Boys/Girls league/knockout draw documents |
| Official participant import | `.xlsx`/`.xls` import — Name, Department, Category, Year |
| Certificate template upload | PDF/PNG/JPG templates per event |
| Auto-generate certificates | Participation + Achievement certificates as PDFs |
| Announcements | Post/delete announcements with optional image |
| Media management | Upload/delete event photos/videos; facility gallery |
| Bulk sport assignment | Assign multiple students to a sport at once |
| Bulk coaching enrolment | Enrol multiple students in a programme at once |
| Profile photos | Upload/replace student and coach photos |
| Reports & analytics | Weekly/monthly/yearly projection CSVs |
| Live score updates | Per-sport live score fields |
| Squad management | Per-fixture squads capped at 15 per side, department-validated |
| Winners/Runners-up entry | Manual result entry per event category |

### What Fitness Tracker Has ✅

| Feature | Status | Details |
|---|---|---|
| Admin OTP login | ✅ | `POST /api/admin/login` + `POST /api/admin/login/verify` |
| Review pending coach applications | ✅ | `GET /api/admin/coaches/pending` |
| Approve / reject coaches | ✅ | `POST /api/admin/coaches/:id/approve` / `/reject` |
| Assign sports to coaches | ✅ | `POST /api/admin/coach-sports` |
| Inspect student records | ✅ | `GET /api/admin/students`, `GET /api/admin/students/:id` |
| Diagnostics endpoint | ✅ | `GET /api/admin/diagnostics` — env health, DB status, config summary |
| Sports catalogue management | ✅ | `GET/POST/PATCH/DELETE /api/fit-track/sports` — admin-only write |
| Facility management | ✅ | Facility name, cover photo, gallery upload/delete |
| Coaching programme management | ✅ | Full CRUD on programmes and coach assignments |
| Coaching schedule sessions | ✅ | Admin has master write access across all programmes |
| Tournament / event management | ✅ | Full event CRUD with dates, venues, sports |
| Fixture management | ✅ | `POST/PATCH/DELETE /api/fit-track/matches` — Boys/Girls, teams, scores, status |
| Draw PDF upload | ✅ | Separate Boys/Girls draw document upload |
| Official participant import | ✅ | `.xlsx`/`.xls` import via `POST /api/fit-track/participants/import` |
| Certificate template upload | ✅ | Upload per-event PDF/PNG/JPG templates |
| Auto-generate certificates | ✅ | Participation + Achievement PDFs via reportlab + pypdf + Pillow |
| Announcement management | ✅ | Post/delete announcements with optional image |
| Event media management | ✅ | Upload/delete photos and videos for events |
| Bulk sport assignment | ✅ | `POST /api/fit-track/bulk-assign-sport` |
| Bulk coaching enrolment | ✅ | `POST /api/fit-track/bulk-enrol` |
| Profile photo management | ✅ | `POST /api/fit-track/students/:id/photo` and coach photo endpoints |
| Reports & analytics | ✅ | Weekly/monthly/yearly projection CSVs with role-scoped data |
| Live score updates | ✅ | `PATCH /api/fit-track/matches/:id/live-score` |
| Squad management | ✅ | Per-fixture squads, 15-player cap enforced by `007_fit_track_integrity.sql` |
| Winners/Runners-up | ✅ | `POST /api/fit-track/results` |
| Attendance overview | ✅ | Admin can view all attendance records across all coaches |

---

## Section 5 — Extra Features in Fitness Tracker (Not in Fit-Track)

These features are **entirely new** in the Fitness Tracker and do not exist in Fit-Track at all:

| Feature | Description | Where in code |
|---|---|---|
| **Password-only student and coach login** | Students and approved coaches sign in with email and password; admins retain OTP verification | `backend/app.py` |
| **Coach approval workflow** | Coaches must register and wait for admin approval before access. Fit-Track hardcoded coaches. | `backend/app.py` → `/api/admin/coaches/*` |
| **Forgot password / password reset** | End-to-end OTP-authenticated password reset flow | `backend/app.py` → `/api/forgot-password`, `/api/reset-password` |
| **Physical assessments** | Structured records: speed, strength, endurance, agility, flexibility, reaction time, overall score | `backend/performance.py` → `physical_assessments` table |
| **Training session logs** | Per-sport training records with type, duration, and notes | `backend/performance.py` → `training_sessions` table |
| **Student goals tracking** | Create and track goals with target values, dates, and status | `backend/performance.py` → `goals` table |
| **Coach feedback with ratings** | Coaches leave rated (0–10) feedback notes for individual students | `backend/performance.py` → `coach_feedback` table |
| **Attendance with status options** | Present / Absent / Late / Excused statuses (Fit-Track only had present/absent) | `backend/attendance.py` |
| **Weekly attendance summary** | `GET /api/attendance/student` returns a 7-day rolling breakdown | `backend/attendance.py` |
| **Admin diagnostics endpoint** | `/api/admin/diagnostics` reports environment health, DB connectivity, and config without exposing secrets | `backend/app.py` |
| **Vercel serverless deployment** | `api/index.py` + `vercel.json` enable zero-infrastructure deployment. Fit-Track runs only locally. | `api/index.py`, `vercel.json` |
| **PostgreSQL schema + migrations** | 7 ordered migration files; idempotent; supports schema evolution without data loss | `backend/migrations/` |
| **Email domain validation** | Signup rejects non-institutional email addresses | `backend/auth/helpers.py` → `is_valid_domain()` |
| **OTP abuse rate limiting** | Blocks repeated OTP send requests and failed verification attempts | migrations 003, 004 |
| **Coach signup email notification** | Coach receives approval/rejection email | `backend/auth/emails.py` → `send_coach_approval_email()` |
| **Password reset success email** | User receives confirmation when password is changed | `backend/auth/emails.py` → `send_password_reset_success_email()` |
| **Structured request logging** | Every API request is logged with duration and request ID | `backend/logging_config.py` |
| **CORS from environment config** | Allowed origins controlled via `CORS_ALLOWED_ORIGINS` env var | `backend/app.py` → `after_request` |
| **Auth guard on all frontend pages** | Browser-side JS redirects unauthenticated users before any page renders | `frontend1/js/auth-guard.js` |
| **Single REST API (`api-client.js`)** | All frontend API calls go through one shared file — no inline fetches | `frontend1/js/api-client.js` |
| **Health check endpoint** | `/api/health` returns server + database status for uptime monitoring | `backend/app.py` |
| **Local dev proxy server** | `dev_server.py` proxies API calls so CORS is never an issue locally | `dev_server.py` |
| **`run_all.py` launcher** | One-command startup for both frontend and backend with port conflict detection | `run_all.py` |

---

## Section 6 — Features Partially Implemented or Pending

These features exist conceptually or partially in the backend but are **incomplete or not wired up** in the current frontend:

| Feature | Current State | Gap |
|---|---|---|
| Student profile photo | Upload endpoint exists (`/api/fit-track/students/:id/photo`) | No student-facing page to upload their own photo; only admin can manage it |
| Blood group / medical / parent data | Fully integrated in `student_profiles` table | ✅ Implemented (added schema columns, frontend inputs, and backend save logic) |
| Student Sports Passport ID | Present in Fit-Track prototype; migration 006 imports the table design | No API endpoint to expose the student's own passport ID to the frontend |
| Student event self-registration | Fit-Track has `GET /register/<event_id>` route | API endpoint exists (`POST /api/fit-track/registrations`) but no frontend event-registration page |
| Live score page | Fit-Track renders live scores in a template | API exists; no dedicated live-score frontend page in `frontend1/shared/` |
| Announcement image display | Backend stores image path | Frontend `fit-track-announcements.html` may not render the announcement image |
| Achievement certificate download link | Backend generates and stores the PDF | No clear frontend page showing the student's generated certificates with a download button |
| Coach qualification display | N/A | Fields removed from signup flow |

---

## Section 7 — Technology Stack Comparison

| Aspect | Fit-Track | Fitness Tracker |
|---|---|---|
| Language | Python 3 | Python 3.10+ |
| Web framework | Flask | Flask 3.x |
| Database | SQLite (file: `data/sports.db`) | PostgreSQL / Supabase (prod) + SQLite (dev) |
| DB driver | `sqlite3` (stdlib) | `psycopg[binary]` >= 3.2 |
| ORM | Raw SQL | Raw SQL (psycopg `dict_row`) |
| Frontend | Jinja2 templates (server-rendered) | Static HTML + JS fetch API |
| Auth | Username + Werkzeug password hash | Email + OTP + Werkzeug hash + Flask signed session |
| File uploads | `werkzeug.utils.secure_filename` → local `static/uploads/` | Same, but configurable via `FIT_TRACK_UPLOAD_ROOT` env var |
| PDF generation | `reportlab`, `pypdf`, `Pillow` | Same |
| Excel import | `openpyxl`, `xlrd` | Same |
| Deployment | Local only | Vercel serverless + Supabase |
| Tests | None | `pytest` suite — 32 tests (2 opt-in PostgreSQL) |
| SMTP | Not implemented | `smtplib` with TLS/STARTTLS, configurable via env |

---

## Summary Table

| Category | Fit-Track Features | Fitness Tracker Has Them | Extra in Fitness Tracker |
|---|---|---|---|
| Authentication | 3 | 3 ✅ (significantly enhanced) | +12 new auth features |
| Student features | 11 | 9 ✅ / 2 ⚠️ partial | +5 new student features |
| Coach features | 8 | 8 ✅ (enhanced with real signup flow) | +5 new coach features |
| Admin features | 19 | 19 ✅ (all carried forward) | +4 new admin features |
| Infrastructure | Local only | Vercel + Supabase | Full production path |
| Testing | 0 | 32 test cases | — |
| API style | HTML page routes | JSON REST API | — |