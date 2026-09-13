# Fitness Performance Tracker

Complete project documentation for the application files outside the `document/` directory.

## 1. Project Overview

Fitness Performance Tracker is a role-based athlete management system with three user roles:

- **Student/player:** logs in, views assessments, training sessions, goals, and coach feedback.
- **Coach:** logs in, views assigned athletes, and creates assessments, sessions, goals, and feedback.
- **Admin:** logs in with password plus OTP, manages users, and assigns coaches to athletes.

The project uses:

- Python and Flask for the backend.
- MySQL for persistent application data.
- PyMySQL for database access.
- Flask sessions for authentication.
- OTP verification for signup, password reset, and admin login.
- Static HTML, CSS, and JavaScript for the frontend.

The Flask application can also serve the `frontend/` directory directly, which allows relative API URLs and session cookies to work on one origin.

## 2. Repository Structure

```text
fitness-tracker/
|-- .gitignore
|-- .vscode/settings.json
|-- README.md
|-- requirements.txt
|-- COMPLETE_PROJECT_DOCUMENTATION.md
|-- backend/
|   |-- .env
|   |-- app.py
|   |-- athlete_tracker.db
|   |-- reset_db.py
|   |-- schema.sql
|   |-- seed.py
|   |-- start.ps1
|   |-- test_backend.py
|-- frontend/
|   |-- index.html
|   |-- admin/
|   |-- coach/
|   |-- js/
|   |-- student/
|-- document/
```

The existing `document/` directory is intentionally excluded from this reference. It contains project reports and planning documents, not runtime source code.

## 3. Installation and Setup

### 3.1 Prerequisites

Install or prepare:

- Python 3.10 or newer.
- MySQL Server.
- A MySQL account that can create the `athlete_tracker` database.
- PowerShell on Windows.
- A browser with JavaScript enabled.

### 3.2 Create the Python environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`requirements.txt` contains:

- `Flask`: web server and routing.
- `Flask-Cors`: configured cross-origin behavior for API requests.
- `PyMySQL`: MySQL driver.
- `python-dotenv`: loads `backend/.env`.
- `Werkzeug`: password hashing and Flask support utilities.

### 3.3 Configure `backend/.env`

The application reads these variable names:

```text
DB_HOST
DB_USER
DB_PASSWORD
DB_NAME
SECRET_KEY
FITNESS_ALLOW_DEV_SECRET
FLASK_SECURE_COOKIE
CORS_ORIGINS
FITNESS_TEST_MODE
MAIL_USERNAME
MAIL_PASSWORD
MAIL_FROM
MAIL_SERVER
MAIL_PORT
FLASK_DEBUG
PORT
```

Do not commit real values from `.env`.

Important settings:

- `SECRET_KEY` is required unless `FITNESS_ALLOW_DEV_SECRET=true` is explicitly enabled for local development.
- `DB_NAME` normally points to `athlete_tracker`.
- `MAIL_USERNAME` and `MAIL_PASSWORD` are required for real OTP email delivery.
- `FITNESS_TEST_MODE=true` prints OTPs locally instead of requiring email delivery.
- `CORS_ORIGINS` is a comma-separated list of trusted frontend origins when the frontend and backend run on different origins.
- `FLASK_SECURE_COOKIE=true` should be used with HTTPS.
- `FLASK_DEBUG` should be false outside development.

### 3.4 Start the backend

From the project root:

```powershell
.\.venv\Scripts\python.exe backend\app.py
```

Or from `backend/`:

```powershell
.\.venv\Scripts\python.exe app.py
```

The default port is `5000`. It can be changed with `PORT`.

PowerShell launcher:

```powershell
cd backend
.\start.ps1
```

The launcher sets test mode off and debug mode to false unless `FLASK_DEBUG` was already supplied. Flask loads the secret from `.env`.

### 3.5 Reset the database

`backend/reset_db.py` drops and recreates the configured database using its own connection settings. It is destructive.

```powershell
cd backend
.\.venv\Scripts\python.exe reset_db.py
.\.venv\Scripts\python.exe app.py
```

After a reset, `app.py` initializes the schema and creates demo accounts when the database contains no users.

## 4. Backend Files

### `backend/app.py`

The main Flask application and business-logic module.

Responsibilities:

- Loads `.env`.
- Creates the Flask app.
- Configures signed sessions and cookie behavior.
- Configures restricted CORS using `CORS_ORIGINS`.
- Connects to MySQL with PyMySQL.
- Initializes the database schema when required.
- Creates demo accounts and demo assignments.
- Hashes and verifies passwords.
- Generates, hashes, expires, and verifies OTPs.
- Sends email through SMTP when mail configuration is available.
- Enforces login and role authorization decorators.
- Enforces CSRF headers for authenticated mutating API requests.
- Serves frontend files from `frontend/`.

Important helper functions:

- `get_db()`: opens a database connection.
- `init_db()`: creates the database/schema when the users table is absent.
- `ensure_demo_seed()`: creates demo users and coach-athlete assignments if no users exist.
- `generate_otp()`: returns a six-digit OTP.
- `save_otp()`, `get_otp()`, `verify_otp()`: OTP lifecycle functions.
- `canonical_role()`: converts frontend `student` to database role `player`.
- `login_required()`: requires a session user.
- `role_required()`: limits routes to selected roles.
- `new_code()`: creates `ADM###`, `COA###`, or `ATH###` user codes.
- `send_email()`: sends SMTP mail.
- `establish_session()`: stores authenticated user information in the Flask session.

Session values include user ID, user code, name, email, and role. A CSRF token is also stored in the session and is obtained from `GET /api/csrf-token`.

### `backend/schema.sql`

The authoritative MySQL schema. It drops and recreates seven tables when run as a full SQL script.

Tables:

1. `users`
   - Account identity and profile data.
   - Roles are `admin`, `coach`, and `player`.
   - Stores password hashes, verification status, sport, contact number, gender, and date of birth.

2. `otp_requests`
   - Stores hashed OTPs.
   - `purpose` distinguishes signup, password reset, and admin login.
   - Tracks payload, expiry, attempts, verification, and use state.

3. `coach_athletes`
   - Links coaches to players.
   - Composite primary key: `coach_id`, `athlete_id`.
   - Foreign keys cascade when users are deleted.

4. `physical_assessments`
   - Height, weight, BMI, body measurements, flexibility, mobility, posture, injuries, restrictions, remarks, and next assessment date.

5. `training_sessions`
   - Sport, duration, intensity, RPE, exercises, loads, repetitions, running metrics, fatigue, soreness, attendance, completion, observations, and recommendations.

6. `goals`
   - Goal title/type, baseline/current/target values, progress, status, dates, injury/recovery data, ratings, challenges, results, and next goals.

7. `coach_feedback`
   - Technical, fitness, behavioral, communication, teamwork, ratings, summary, action items, practice tasks, and follow-up date.

All athlete records contain both `athlete_id` and `coach_id` and reference `users`.

### `backend/seed.py`

Standalone demo-data seeder.

It creates:

- One admin.
- Two coaches.
- Five players.
- Coach-player assignments.
- Physical assessments.
- Training sessions.
- Goals.
- Coach feedback.

The demo password is `1234` in the development seed data. It must not be used in production.

The script skips seeding when the users table already contains users.

### `backend/reset_db.py`

Destructive database reset utility.

- Drops `athlete_tracker`.
- Recreates the empty database.
- Does not create tables or seed users itself.
- Uses connection settings defined inside the script rather than loading `.env`.

### `backend/start.ps1`

Windows PowerShell launcher.

- Sets `FITNESS_TEST_MODE=false`.
- Preserves an existing `FLASK_DEBUG` value or defaults it to false.
- Runs `python app.py`.
- Relies on `app.py` to load `backend/.env`.

### `backend/test_backend.py`

Python `unittest` regression tests.

Current coverage:

- Demo users exist.
- Student login succeeds.
- Authenticated mutations require a CSRF token.
- Logout succeeds with a valid CSRF token.
- Admin login rejects an invalid password.
- Admin login accepts a valid password and requires a valid OTP.

Run with:

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_backend -v
```

### `backend/athlete_tracker.db`

A local SQLite database file tracked in the repository. The active Flask application uses MySQL through PyMySQL, not this SQLite file. It should be treated as a local/generated artifact and should not be used as the source of truth for production data.

## 5. Backend API Reference

### Authentication and account routes

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/register` | Start player/coach registration and send signup OTP. |
| POST | `/api/admin-signup` | Start admin registration and send signup OTP. |
| POST | `/api/account-verification/send` | Resend signup OTP. |
| POST | `/api/account-verification/verify` | Verify signup OTP and create the account. |
| POST | `/api/admin-signup/resend-otp` | Admin signup OTP resend alias. |
| POST | `/api/admin-signup/verify-otp` | Admin signup OTP verification alias. |
| POST | `/api/login` | Student/player or coach password login. |
| POST | `/api/admin-login` | Admin password step; sends admin login OTP. |
| POST | `/api/admin-login/verify-otp` | Completes admin login. |
| POST | `/api/admin-login/resend-otp` | Resends admin login OTP. |
| POST | `/api/forgot-password` | Starts password reset. |
| POST | `/api/forgot-password/resend-otp` | Resends reset OTP. |
| POST | `/api/forgot-password/verify-otp` | Verifies reset OTP. |
| POST | `/api/verify-otp` | Compatibility alias for reset OTP verification. |
| POST | `/api/reset-password` | Changes a password after reset OTP verification. |
| GET | `/api/session` | Returns the current authenticated user. |
| GET | `/api/admin/session` | Returns the current authenticated admin. |
| GET | `/api/csrf-token` | Creates or returns the session CSRF token. |
| POST | `/api/logout` | Clears the current session. |
| POST | `/api/admin/logout` | Admin logout alias. |

Public authentication endpoints are exempt from authenticated-session CSRF checks because they create or establish sessions. Authenticated mutations require `X-CSRF-Token`.

### Data routes

| Method | Route | Access |
|---|---|---|
| GET | `/api/users` | Admin only. |
| GET | `/api/assessments` | Student, coach, or admin; filtered by role. |
| GET | `/api/training-sessions` | Student, coach, or admin; filtered by role. |
| GET | `/api/goals` | Student, coach, or admin; filtered by role. |
| GET | `/api/feedback` | Student, coach, or admin; filtered by role. |
| GET | `/api/coach/athletes` | Coach only; returns assigned athletes. |
| POST | `/api/assessments` | Coach only; assigned athlete required. |
| POST | `/api/training-sessions` | Coach only; assigned athlete required. |
| POST | `/api/goals` | Coach only; assigned athlete required. |
| POST | `/api/feedback` | Coach only; assigned athlete required. |
| GET | `/api/coach-athletes` | Admin only; lists assignments. |
| POST | `/api/coach-athletes` | Admin only; creates assignment. |
| DELETE | `/api/coach-athletes` | Admin only; removes assignment. |

## 6. Shared Frontend JavaScript

### `frontend/js/config.js`

Defines `window.APP_CONFIG`:

- `API_BASE`: empty by default for same-origin relative requests.
- `ROLE_MAP`: maps UI `student` to backend `player`.
- `DISPLAY_ROLE`: display names for roles.
- `DASHBOARD_PAGES`: dashboard paths.
- `LOGIN_PAGES`: login paths.
- `DEBUG`: enabled on localhost.

### `frontend/js/api-client.js`

The standard frontend API wrapper.

Responsibilities:

- Sends JSON requests.
- Includes cookies with `credentials: include`.
- Requests a CSRF token before non-GET calls.
- Adds `X-CSRF-Token` to mutating requests.
- Normalizes network and non-JSON errors.
- Exposes login, signup, OTP, reset, session, data, coach-write, admin-user, and assignment methods.
- Provides redirect and UI message helpers.

Important methods include `login`, `adminLogin`, `adminVerifyOtp`, `adminResendOtp`, `register`, `verifySignupOtp`, `forgotPassword`, `resetPassword`, `getSession`, `getAdminSession`, `getUsers`, `getAssignments`, `assignCoach`, and `removeAssignment`.

### `frontend/js/auth-guard.js`

Session guard for protected pages.

- Allows known public pages.
- Calls `API.getSession()` for other pages.
- Redirects unauthenticated users based on the current URL path.
- Stores minimal authenticated user information in `window.__USER`.

Pages must load `config.js`, `api-client.js`, and `auth-guard.js` for this guard to operate.

## 7. Frontend Pages

### Root

#### `frontend/index.html`

Role-selection portal. Links to student, coach, and admin login pages. It does not authenticate users itself.

### Student pages

#### `student/student-login.html`

- Collects email and password.
- Calls `API.login` with role `student`.
- Displays inline validation errors.
- Redirects to `student-dashboard.html` after success.

#### `student/student-signup.html`

- Collects name, email, password, password confirmation, sport, phone, gender, and date of birth.
- Calls `/api/register`.
- Stores the email for verification and routes to the signup OTP page.

#### `student/student-signup-verify.html`

Signup OTP page included in the project. Verify that its script references match the active shared API flow before using it as the production verification page.

#### `student/verify-signup.html`

Alternative signup verification page using the shared API client and `/api/account-verification/verify`.

#### `student/student-dashboard.html`

Student dashboard. Intended to display:

- Current session/user information.
- Physical assessments.
- Training sessions.
- Goals.
- Coach feedback.

#### `student/forgot-password.html`

Starts password recovery with `/api/forgot-password`.

#### `student/verify-reset.html`

Collects and verifies a reset OTP and preserves the reset context for the password page.

#### `student/reset-password.html`

Collects the new password and completes password reset.

### Coach pages

#### `coach/coach-login.html`

Coach login page using the shared login API with role `coach`.

#### `coach/coach-signup.html`

Coach registration UI. Its integration should be kept aligned with `/api/register` and the shared signup verification flow.

#### `coach/coach-signup-verify.html`

Coach signup OTP page. It should use the same backend verification contract as student signup.

#### `coach/coach-dashboard.html`

Large coach workspace containing athlete, assessment, training, exercise, goal, feedback, and settings sections. Backend integration and authentication guard coverage should be verified whenever coach functionality changes.

#### `coach/forgot-password.html`, `coach/verify.html`, `coach/reset-password.html`

Coach password-recovery pages.

### Admin pages

#### `admin/admin-login.html`

- Collects admin email and password.
- Calls `API.adminLogin`.
- Rejects invalid credentials through the backend response.
- Stores the login email in session storage.
- Redirects to `admin-loginotp.html` only after the password step succeeds.

#### `admin/admin-loginotp.html`

- Reads the temporary admin email.
- Collects six OTP digits.
- Calls `API.adminVerifyOtp`.
- Supports OTP resend through `API.adminResendOtp`.
- Redirects to the admin dashboard only after successful OTP verification.

#### `admin/admin-dashboard.html`

Admin workspace. Uses the shared API client to:

- Load users.
- Populate coach and athlete selectors.
- List coach-athlete assignments.
- Create assignments.
- Remove assignments.
- Log out through the backend session endpoint.

#### `admin/admin-signup.html`

Admin account creation UI. It must remain restricted in production because admin creation is a privileged operation.

#### `admin/admin-signup-verify.html`

Admin signup OTP page.

#### `admin/forgot-password.html`, `admin/verify.html`, `admin/reset-password.html`

Admin password-recovery pages.

## 8. Authentication Flows

### Student login

1. User opens `student/student-login.html`.
2. The page calls `API.login` with `role: student`.
3. The API client maps `student` to backend role `player`.
4. Flask checks the email, role, and password hash.
5. Flask creates a signed session.
6. The browser redirects to `student-dashboard.html`.
7. Protected dashboard requests use the session cookie.

### Admin login

1. User opens `admin/admin-login.html`.
2. The page sends email and password to `/api/admin-login`.
3. Flask checks that the account role is `admin`.
4. Flask creates and emails an OTP.
5. The browser opens `admin-loginotp.html`.
6. The OTP page submits the code to `/api/admin-login/verify-otp`.
7. Flask verifies the hashed OTP and establishes the admin session.
8. The browser opens `admin-dashboard.html`.

### Signup

1. User submits registration data.
2. Backend stores a hashed signup payload in `otp_requests`.
3. Backend sends a signup OTP.
4. User verifies the OTP.
5. Backend creates the account and marks it verified.

### Password reset

1. User submits an account email.
2. Backend stores a password-reset OTP.
3. User verifies the OTP.
4. User submits a new password.
5. Backend replaces the stored password hash.

## 9. Authorization Rules

- Anonymous users cannot access session or data endpoints.
- Students/players can read only their own athlete records.
- Coaches can read records for assigned athletes.
- Coaches can write records only for assigned athletes.
- Admins can list users and manage coach-athlete assignments.
- Admins are required to complete password and OTP authentication.
- Mutating authenticated requests require the session CSRF token.

## 10. Demo Accounts

The development seed creates demo accounts with the password `1234`:

- `admin@college.edu` - admin.
- `verma@college.edu` - coach.
- `sharma@college.edu` - coach.
- `arjun@college.edu` - player.
- `sneha@college.edu` - player.
- `kabir@college.edu` - player.
- `meera@college.edu` - player.
- `rohan@college.edu` - player.

Change or remove these accounts before production use.

## 11. Testing

### Backend tests

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_backend -v
```

The current test suite verifies:

- Seeding.
- Student login.
- CSRF enforcement.
- CSRF-valid logout.
- Admin invalid-password rejection.
- Admin OTP rejection.
- Admin valid OTP completion.

### Static checks

```powershell
.\.venv\Scripts\python.exe -m py_compile backend/app.py backend/seed.py backend/test_backend.py
node --check frontend/js/api-client.js
node --check frontend/js/config.js
node --check frontend/js/auth-guard.js
```

Inline scripts in HTML should be extracted and syntax-checked separately because Node does not directly accept `.html` files as JavaScript inputs.

### Manual checks

- Open the root portal.
- Test student login with valid and invalid credentials.
- Test admin password rejection.
- Test admin OTP rejection and success.
- Confirm dashboard routes reject anonymous sessions.
- Confirm a student cannot create coach records.
- Confirm a coach cannot access admin user management.
- Confirm admin assignment creation and removal.
- Test signup and password reset with `FITNESS_TEST_MODE=true` if email is not configured.

## 12. Known Limitations and Follow-Up Work

- `app.py` initializes the database at import time, so tests require a reachable MySQL instance.
- The schema initializer is application-driven; production deployments should run migrations or an explicit schema deployment process instead of relying on startup initialization.
- `reset_db.py` uses hardcoded connection defaults and is destructive.
- The SQLite file is not used by the Flask application.
- Demo passwords are intentionally weak and are for local testing only.
- Some older coach/admin signup and recovery pages may not use the shared API client consistently; verify those flows before release.
- Some pages depend on external Unsplash images or Tailwind CDN resources.
- The project currently has backend smoke tests but no browser automation suite.
- `.gitignore` should be expanded to exclude `.env`, Python caches, local databases, and other generated files before a production push.
- Configure `CORS_ORIGINS` explicitly when using VS Code Live Server or another separate frontend server.

## 13. Deployment Checklist

Before deployment:

- Set a strong random `SECRET_KEY`.
- Set production database credentials.
- Set `DB_NAME` consistently with the created database.
- Configure SMTP credentials or use an external OTP service.
- Set `CORS_ORIGINS` to trusted HTTPS origins only.
- Enable `FLASK_SECURE_COOKIE=true` behind HTTPS.
- Keep `FLASK_DEBUG=false`.
- Replace demo accounts and passwords.
- Do not commit `.env` or local database files.
- Run the schema through a controlled migration process.
- Run all backend tests.
- Test student and admin login from the deployed frontend origin.
- Confirm logout, CSRF, role authorization, OTP expiry, and password reset behavior.
