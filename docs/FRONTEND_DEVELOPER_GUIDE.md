# Frontend Developer Guide

> **Who this is for:** Frontend developers joining this project who need to understand the current state of the UI, what is working, what is broken, and exactly what code changes need to be made.

---

## Table of Contents

1. [How the Frontend Works](#1-how-the-frontend-works)
2. [Folder Structure](#2-folder-structure)
3. [Key JavaScript Files](#3-key-javascript-files)
4. [Pages That Work Right Now](#4-pages-that-work-right-now)
5. [Pages That Are Broken or Incomplete](#5-pages-that-are-broken-or-incomplete)
6. [How to Call the API](#6-how-to-call-the-api)
7. [Session & Auth Guard](#7-session--auth-guard)
8. [Role-Based Page Access](#8-role-based-page-access)
9. [Changes That Must Be Made](#9-changes-that-must-be-made)
10. [CSS & Styling Conventions](#10-css--styling-conventions)
11. [Local Development Setup](#11-local-development-setup)
12. [Common Mistakes to Avoid](#12-common-mistakes-to-avoid)

---

## 1. How the Frontend Works

This is a **completely static frontend** — no React, no Vue, no Angular, no npm, no build step at all.  
Every page is a plain `.html` file. All dynamic behaviour (logins, data fetching, forms) is done with **vanilla JavaScript `fetch()` calls** to the backend REST API.

```
Browser opens an HTML page
       │
       ▼
frontend1/js/config.js       ← sets the API base URL
frontend1/js/api-client.js   ← all API call functions live here
frontend1/js/auth-guard.js   ← checks session, redirects if not logged in
       │
       ▼
Fetch calls go to /api/...   ← handled by Flask backend (or proxied locally)
```

**There is no `package.json`. No `npm install`. No bundler. No TypeScript.**  
You just edit `.html` and `.js` files and refresh the browser.

---

## 2. Folder Structure

```
frontend1/
│
├── index.html                      Landing page (public, no auth required)
│
├── student/
│   ├── student-login.html          Student login page
│   ├── student-loginotp.html       OTP verification after login
│   ├── student-signup.html         New student registration
│   ├── student-signup-verify.html  OTP verification after signup
│   ├── student-basicinfo.html      Step 1 of profile setup
│   ├── student-personalinfo.html   Step 2 of profile setup
│   ├── student-dashboard.html      ⚠️ Main student page — partially wired
│   └── verify.html                 Generic OTP verify page
│
├── coach/
│   ├── coach-login.html            Coach login
│   ├── coach-loginotp.html         Coach OTP verification
│   ├── coach-signup.html           Coach registration
│   ├── coach-signup-verify.html    Coach signup OTP verify
│   ├── coach-waiting.html          Shown while coach approval is pending
│   ├── coach-dashboard.html        ⚠️ Main coach page — partially wired
│   └── verify.html
│
├── admin/
│   ├── admin-login.html            Admin login (password step)
│   ├── admin-loginotp.html         Admin OTP step
│   ├── admin-dashboard.html        ⚠️ Main admin page — partially wired
│   └── verify.html
│
├── shared/                         Fit-Track feature pages (all need work)
│   ├── fit-track-announcements.html
│   ├── fit-track-chat.html
│   ├── fit-track-coaching.html
│   ├── fit-track-events.html
│   ├── fit-track-features.html
│   ├── fit-track-gallery.html
│   ├── fit-track-matches.html
│   ├── fit-track-profile.html
│   ├── fit-track-reports.html
│   ├── fit-track-schedule.html
│   ├── fit-track-sports.html
│   ├── forgot-password.html
│   ├── login-otp.html
│   ├── set-password.html
│   └── verify-otp.html
│
├── js/
│   ├── config.js                   API URL config (DO NOT hardcode API URLs elsewhere)
│   ├── api-client.js               All API call functions — add new ones here
│   ├── auth-flow.js                Login, signup, OTP, and reset logic
│   ├── auth-guard.js               Session checking + role-based redirect
│   └── reference-pages.js          Fit-Track feature page JS (needs lots of work)
│
├── css/
│   ├── common/                     Shared styles
│   ├── student/                    Student-specific styles
│   ├── coach/                      Coach-specific styles
│   └── admin/                      Admin-specific styles
│
└── scripts/
    └── override_css.py             Dev utility — ignore this
```

---

## 3. Key JavaScript Files

### `js/config.js` — API Base URL

This file runs first. It detects whether you are on localhost and sets `window.APP_CONFIG.API_BASE`.

**Rules:**
- On `localhost:8080` → API base is `""` (same-origin, proxied by `dev_server.py`)
- On `localhost:5001` or similar → API base is `http://localhost:5000`
- On production (Vercel) → API base is `""` (same-origin, handled by `vercel.json`)

**⚠️ Never hardcode `http://localhost:5000` in any HTML or JS file.** Always use `window.APP_CONFIG.API_BASE` or call through `api-client.js`.

---

### `js/api-client.js` — All API Calls

This is the **single source of truth for all API calls**. Every HTTP request to the backend must go through this file.

It exposes a global `window.FitnessAPI` object with methods like:

```javascript
// Auth
FitnessAPI.login(email, password)
FitnessAPI.verifyLoginOtp(otp)
FitnessAPI.signup(data)
FitnessAPI.verifySignupOtp(otp)
FitnessAPI.logout()
FitnessAPI.forgotPassword(email)
FitnessAPI.resetPassword(otp, newPassword)

// Student
FitnessAPI.getStudentProfile()
FitnessAPI.updateStudentProfile(data)
FitnessAPI.getStudentSports()
FitnessAPI.selectSport(sportId)

// Coach
FitnessAPI.getAthletes()
FitnessAPI.createAssessment(data)
FitnessAPI.createTrainingSession(data)
FitnessAPI.createGoal(data)
FitnessAPI.createFeedback(data)

// Admin
FitnessAPI.getUsers()
```

**If you need to call a new API endpoint, add a method here** — do not write `fetch()` calls inline in HTML pages.

---

### `js/auth-guard.js` — Session Check

This script runs on every protected page. It calls `GET /api/session` and:
- If not logged in → redirects to the appropriate login page
- If logged in with wrong role → redirects to that role's dashboard
- If logged in with correct role → lets the page load

**Every dashboard and feature page must include this script.**

---

### `js/auth-flow.js` — Login & Signup Forms

Handles form submissions for:
- Student email/password login
- Student signup + OTP step
- Coach email/password login
- Coach signup + OTP step
- Admin login + OTP step
- Forgot password flow
- Password reset flow

---

### `js/reference-pages.js` — Fit-Track Feature Pages

This handles the shared pages in `frontend1/shared/fit-track-*.html`. **This file is currently incomplete.** Most of the Fit-Track feature pages are HTML shells that are not properly connected to the API. See [Section 5](#5-pages-that-are-broken-or-incomplete) for details.

---

## 4. Pages That Work Right Now

These pages have been verified to have working HTML + JS wired to real API endpoints:

| Page | File | Notes |
|---|---|---|
| Landing page | `index.html` | Static, no API calls |
| Student login | `student/student-login.html` | ✅ Password login opens the student dashboard directly |
| Student signup | `student/student-signup.html` | ✅ Calls `POST /api/signup` |
| Student signup OTP | `student/student-signup-verify.html` | ✅ Calls `POST /api/verify-otp` |
| Student basic info | `student/student-basicinfo.html` | ✅ Calls `POST /api/student/profile` |
| Student personal info | `student/student-personalinfo.html` | ✅ Calls `PATCH /api/student/profile` |
| Coach login | `coach/coach-login.html` | ✅ Password login opens the coach dashboard directly |
| Coach signup | `coach/coach-signup.html` | ✅ Calls `POST /api/signup` |
| Coach signup OTP | `coach/coach-signup-verify.html` | ✅ Works |
| Coach waiting room | `coach/coach-waiting.html` | ✅ Shows pending approval state |
| Admin login | `admin/admin-login.html` | ✅ Works |
| Admin login OTP | `admin/admin-loginotp.html` | ✅ Works |
| Forgot password | `shared/forgot-password.html` | ✅ Works |
| Set new password | `shared/set-password.html` | ✅ Works |
| Shared OTP verify | `shared/verify-otp.html` | ✅ Works |

---

## 5. Pages That Are Broken or Incomplete

These pages exist in the repo but are **not fully functional**. They need real API integration work.

### Student Dashboard (`student/student-dashboard.html`) — ⚠️ Partial

**What works:** Page loads, sidebar renders, auth guard runs.  
**What is missing:**
- Attendance summary section calls the API but may not render the weekly breakdown correctly
- Performance chart (Chart.js) may show empty data if `/api/assessments` returns nothing
- The Fit-Track feature tabs (Sports, Events, Chat, etc.) redirect to `shared/` pages that are broken

**What to fix:**
1. Ensure `GET /api/student/dashboard` or individual endpoints are called on `DOMContentLoaded`
2. Render the weekly attendance data from `GET /api/attendance/student`
3. Render performance records from `GET /api/assessments?limit=5`
4. Add loading spinners and empty-state messages for each section

---

### Coach Dashboard (`coach/coach-dashboard.html`) — ⚠️ Partial

**What works:** Page and sidebar render.  
**What is missing:**
- Athlete list may not dynamically load from `GET /api/coach/athletes`
- Attendance marking form may not submit correctly
- Assessment creation form may not be wired to `POST /api/assessments`
- Feedback form wiring unclear

**What to fix:**
1. On page load: call `GET /api/coach/athletes` and render the athlete roster
2. Wire the attendance form to `POST /api/attendance/sessions` then `POST /api/attendance/records`
3. Wire assessment, training session, and feedback forms to their respective `POST /api/*` endpoints
4. Add success/error toast messages after each form submission

---

### Admin Dashboard (`admin/admin-dashboard.html`) — ⚠️ Partial

**What works:** Page renders; coach approval section works.  
**What is missing:**
- Student list view may not load from `GET /api/admin/students`
- Sports assignment UI may not be wired
- Diagnostics section may not display data from `GET /api/admin/diagnostics`

**What to fix:**
1. Fetch and render `GET /api/admin/students` in the students tab
2. Wire sports assignment (`POST /api/admin/coach-sports`) to the UI
3. Render diagnostics data from `GET /api/admin/diagnostics` in the health panel

---

### Shared Fit-Track Pages (`shared/fit-track-*.html`) — ❌ Most are shells

These pages were designed to match the Fit-Track prototype's features. Most of them contain static HTML layout but **are not connected to the backend API**. `reference-pages.js` handles some, but not all.

| Page File | Feature | Current State | What Needs to Happen |
|---|---|---|---|
| `fit-track-announcements.html` | Announcements | ❌ Static HTML only | Call `GET /api/fit-track/announcements`; render list; admin: show create/delete buttons |
| `fit-track-chat.html` | Coach-student messaging | ❌ Not wired | Call `GET /api/fit-track/messages`; `POST /api/fit-track/messages`; poll or refresh for new messages |
| `fit-track-coaching.html` | Coaching programmes | ❌ Not wired | Call `GET /api/fit-track/programmes`; show enrolment status for students |
| `fit-track-events.html` | Tournaments & events | ❌ Not wired | Call `GET /api/fit-track/tournaments`; show event list with dates and sport |
| `fit-track-gallery.html` | Event photo gallery | ❌ Not wired | Call `GET /api/fit-track/gallery`; render photo carousel |
| `fit-track-matches.html` | Fixtures & live scores | ❌ Not wired | Call `GET /api/fit-track/matches`; render fixture cards with scores |
| `fit-track-profile.html` | Sports passport profile | ❌ Not wired | Call `GET /api/fit-track/students/:id`; render athlete passport |
| `fit-track-reports.html` | Analytics & CSV download | ⚠️ Partial | Call `GET /api/fit-track/reports`; show projection tables; wire CSV download button |
| `fit-track-schedule.html` | Coaching schedule | ❌ Not wired | Call `GET /api/fit-track/coaching-sessions`; render calendar/list view |
| `fit-track-sports.html` | Sports & facilities | ❌ Not wired | Call `GET /api/fit-track/sports`; render sports cards with facility info |
| `fit-track-features.html` | Feature overview hub | ❌ Static | Either remove this page or make it a nav hub linking to the above pages |

---

### Missing Pages (Need to Be Created From Scratch)

These pages don't exist at all yet but are needed for a complete product:

| Page | Role | API to Call | What It Does |
|---|---|---|---|
| Student certificate downloads | Student | `GET /api/fit-track/certificates` | Shows list of generated certificates with download links |
| Student event registration | Student | `POST /api/fit-track/registrations` | Student can register interest for a tournament |
| Live score viewer | All | `GET /api/fit-track/matches/:id` | Shows real-time score; auto-refreshes every 30 seconds |
| Student profile photo upload | Student | `POST /api/fit-track/students/:id/photo` | Student uploads their own profile photo |
| Admin: certificate manager | Admin | `GET/POST /api/fit-track/certificate-templates` | Upload templates, generate and view certificates |
| Admin: draw PDF manager | Admin | `POST /api/fit-track/draws` | Upload Boys/Girls draw documents per tournament |
| Admin: participant import | Admin | `POST /api/fit-track/participants/import` | Upload XLSX file of official event participants |

---

## 6. How to Call the API

### Always use `FitnessAPI` from `api-client.js`

```html
<!-- Include these scripts in order on every page that needs API access -->
<script src="../js/config.js"></script>
<script src="../js/api-client.js"></script>
<script src="../js/auth-guard.js"></script>  <!-- only on protected pages -->
```

### Example — Fetching and rendering data

```javascript
document.addEventListener("DOMContentLoaded", async function () {

    // Get student's attendance summary
    const result = await FitnessAPI.request("GET", "/api/attendance/student");

    if (result.ok && result.data.success) {
        const records = result.data.records;
        // render records into your DOM
        records.forEach(function (record) {
            console.log(record.session_date, record.status);
        });
    } else {
        // Show an error message to the user
        document.getElementById("error-msg").textContent =
            result.data.message || "Failed to load attendance.";
    }

});
```

### Example — Submitting a form

```javascript
document.getElementById("my-form").addEventListener("submit", async function (e) {
    e.preventDefault();

    const payload = {
        session_date: document.getElementById("date").value,
        training_type: document.getElementById("type").value,
        duration_minutes: parseInt(document.getElementById("duration").value),
        sport_id: parseInt(document.getElementById("sport").value),
    };

    const result = await FitnessAPI.createTrainingSession(payload);

    if (result.ok && result.data.success) {
        alert("Session logged!");
    } else {
        alert(result.data.message || "Something went wrong.");
    }
});
```

### Adding a new API method to `api-client.js`

If you need to call an endpoint that does not have a method yet, add it to `api-client.js`:

```javascript
// Inside the window.FitnessAPI object in api-client.js:

getAnnouncements() {
    return apiRequest("GET", "/api/fit-track/announcements");
},

createAnnouncement(data) {
    return apiRequest("POST", "/api/fit-track/announcements", data);
},

deleteAnnouncement(id) {
    return apiRequest("DELETE", `/api/fit-track/announcements/${id}`);
},
```

### API response shape

Every API response follows this format:

```json
// Success
{ "success": true, "data": { ... } }
{ "success": true, "records": [ ... ] }
{ "success": true, "message": "Done." }

// Failure
{ "success": false, "message": "What went wrong" }
```

Always check `result.ok && result.data.success` before using the data.

---

## 7. Session & Auth Guard

### How the session works

- After successful student/coach password login or administrator OTP verification, the backend sets a **signed session cookie** (`HttpOnly`, `SameSite=Lax`)
- The cookie is automatically sent with every `fetch()` call because `credentials: "include"` is set in `api-client.js`
- The session stores `user_id` and `role`
- `GET /api/session` returns the current user info or `401` if not logged in

### Auth guard flow

Every protected page must include `auth-guard.js`. It runs immediately and:

1. Calls `GET /api/session`
2. If `401` → redirects to the correct login page for the expected role
3. If `200` but wrong role → redirects to that user's own dashboard
4. If `200` and correct role → the page continues loading

### How to protect a new page

```html
<head>
    <!-- config and api-client must come before auth-guard -->
    <script src="../js/config.js"></script>
    <script src="../js/api-client.js"></script>
</head>
<body>
    <!-- Your page HTML -->

    <!-- At the bottom, load auth guard with the expected role -->
    <script src="../js/auth-guard.js" data-role="student"></script>
</body>
```

Valid values for `data-role`: `student`, `coach`, `admin`

---

## 8. Role-Based Page Access

| Role | Login page | Dashboard | Can access shared pages |
|---|---|---|---|
| `student` | `student/student-login.html` | `student/student-dashboard.html` | Yes — view only |
| `coach` | `coach/coach-login.html` | `coach/coach-dashboard.html` | Yes — limited write |
| `admin` | `admin/admin-login.html` | `admin/admin-dashboard.html` | Yes — full write |

When building Fit-Track feature pages in `shared/`, some content/buttons should show only for certain roles:

```javascript
// Check role from the session response
const session = await FitnessAPI.request("GET", "/api/session");
const role = session.data.role; // "student", "coach", or "admin"

// Show admin controls only to admins
if (role === "admin") {
    document.getElementById("admin-controls").style.display = "block";
}
```

---

## 9. Changes That Must Be Made

This is a prioritised list of code changes needed. Each item states the file, what to change, and why.

---

### Priority 1 — Critical (core user journeys broken without these)

#### 9.1 Wire student dashboard to real API data

**File:** `frontend1/student/student-dashboard.html`  
**Change:** On `DOMContentLoaded`, call these endpoints and render results into the DOM:
- `GET /api/attendance/student` → render attendance percentage and weekly table
- `GET /api/assessments` → render latest 3–5 assessments
- `GET /api/goals` → render active goals
- `GET /api/student/sports` → render selected sports

**Why:** The student dashboard is the first thing a student sees after login. If it shows blank sections, the app feels broken.

---

#### 9.2 Wire coach dashboard to real API data

**File:** `frontend1/coach/coach-dashboard.html`  
**Change:**
- On load: call `GET /api/coach/athletes` → populate athlete selector/list
- Attendance form: submit to `POST /api/attendance/sessions` then `POST /api/attendance/records`
- Assessment form: submit to `POST /api/assessments`
- Feedback form: submit to `POST /api/feedback`
- Training log form: submit to `POST /api/training-sessions`

**Why:** Coaches cannot do their job without these forms working.

---

#### 9.3 Wire admin dashboard student list

**File:** `frontend1/admin/admin-dashboard.html`  
**Change:** Add a student list tab that calls `GET /api/admin/students` and renders a table with search/filter.  
**Why:** Admins need to be able to see all students — this is a core admin function.

---

#### 9.4 Add Fit-Track API methods to `api-client.js`

**File:** `frontend1/js/api-client.js`  
**Change:** Add methods for every `/api/fit-track/*` endpoint that does not already have one. Minimum required:

```javascript
// Announcements
getAnnouncements()
createAnnouncement(data)
deleteAnnouncement(id)

// Chat
getMessages(otherUserId)
sendMessage(data)

// Sports & facilities
getSports()
getFacilities()

// Programmes & coaching
getProgrammes()
getCoachingSessions()
createCoachingSession(data)

// Tournaments
getTournaments()
getMatches(tournamentId)

// Reports
getReports(period)     // period = "weekly" | "monthly" | "yearly"
downloadReportCsv(period)

// Certificates
getCertificates()
downloadCertificate(id)
```

**Why:** Without these methods, every `shared/` page developer will write their own `fetch()` calls — inconsistent, error-prone, hard to maintain.

---

### Priority 2 — Important (feature completeness)

#### 9.5 Build the announcements page

**File:** `frontend1/shared/fit-track-announcements.html`  
**Change:**
1. On load, call `GET /api/fit-track/announcements` and render each announcement (title, message, image if present, date)
2. If role is `admin`: show a "Post Announcement" form and "Delete" buttons
3. If announcement has an image, display `<img src="/api/fit-track/announcements/:id/image">`

---

#### 9.6 Build the chat page

**File:** `frontend1/shared/fit-track-chat.html`  
**Change:**
1. Load the list of conversations/contacts from the session role
   - Student: show only their assigned coach
   - Coach: show list of assigned athletes (`GET /api/coach/athletes`)
   - Admin: show all users
2. When a contact is selected, load messages: `GET /api/fit-track/messages?with=<user_id>`
3. Message send form: `POST /api/fit-track/messages` with `{ recipient_id, content }`
4. Auto-refresh messages every 10–15 seconds using `setInterval`

---

#### 9.7 Build the events/tournaments page

**File:** `frontend1/shared/fit-track-events.html`  
**Change:**
1. On load: `GET /api/fit-track/tournaments` → render event cards (name, sport, date, venue)
2. Each event card links to a detail view (can be a modal or a query-param route)
3. In the detail view:
   - Render fixtures: `GET /api/fit-track/matches?tournament_id=X`
   - Show live scores on each fixture card
   - Student role: show "Register" button → `POST /api/fit-track/registrations`
4. Admin role: show "Create Event", "Edit", "Delete" buttons

---

#### 9.8 Build the coaching schedule page

**File:** `frontend1/shared/fit-track-schedule.html`  
**Change:**
1. On load: `GET /api/fit-track/coaching-sessions` → render as a list or month-grid
2. Each session card shows: programme, date, time, venue, status, notes
3. Admin and coach roles: show "Add Session", "Edit", "Delete" buttons
4. Student role: read-only view

---

#### 9.9 Build the reports page

**File:** `frontend1/shared/fit-track-reports.html`  
**Change:**
1. Show 3 tabs: Weekly / Monthly / Yearly
2. Each tab calls `GET /api/fit-track/reports?period=weekly` etc.
3. Render the projection tables (attendance %, performance scores per sport)
4. "Download CSV" button calls `GET /api/fit-track/reports/download?period=weekly` and triggers a file download
5. Data is **already scoped by role on the backend** — students see only their own, coaches see their athletes, admin sees everyone

---

### Priority 3 — New pages to create

#### 9.10 Create student certificate page

**File to create:** `frontend1/student/student-certificates.html`

```html
<!-- Basic structure needed -->
<h2>My Certificates</h2>
<div id="cert-list">
    <!-- Render one card per certificate -->
    <!-- Each card: event name, type (Participation/Achievement), date, Download button -->
</div>
```

**API to call:** `GET /api/fit-track/certificates` — already scoped to the logged-in student  
**Download:** `GET /api/fit-track/certificates/:id/download`

---

#### 9.11 Create live score page

**File to create:** `frontend1/shared/fit-track-live.html`

**API to call:** `GET /api/fit-track/matches?status=live`  
**Refresh every 30 seconds:** use `setInterval(() => { loadLiveScores(); }, 30000)`

---

### Priority 4 — Quality & Polish

#### 9.12 Add loading states everywhere

Every section that loads data from the API should:
1. Show a spinner or skeleton while loading
2. Show a friendly "No data yet" message if the API returns an empty array
3. Show a readable error message if the API call fails

Currently most sections just show blank white space on failure.

---

#### 9.13 Replace CDN dependencies with local copies (optional but safer)

**Files:** All HTML files in `frontend1/`  
**Change:** Download Bootstrap, Bootstrap Icons, Chart.js, and Inter font and serve them from `frontend1/` instead of CDN links.  
**Why:** CDN outages or blocks will completely break the UI. Hosting locally makes the app work offline and in restricted networks.  
**How:**
```
frontend1/
└── vendor/
    ├── bootstrap.min.css
    ├── bootstrap-icons.min.css
    ├── chart.min.js
    └── inter-font.css
```
Then update `<link>` and `<script>` tags in all HTML files.

---

#### 9.14 Add toast/notification system

Currently forms show `alert()` dialogs (browser-native, ugly) or update a small text `<div>`. Add a proper toast notification component:

```javascript
// Add to api-client.js or a new notifications.js
function showToast(message, type) {  // type = "success" | "error" | "info"
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}
```

---

## 10. CSS & Styling Conventions

- **Design system:** Bootstrap 5.3 as the base; custom CSS layered on top
- **Icons:** Bootstrap Icons (`bi bi-*`)
- **Font:** Inter (Google Fonts CDN)
- **Color variables:** Each dashboard defines CSS custom properties at `:root` level:

```css
:root {
    --primary: #2563eb;
    --sidebar: #111827;
    --background: #f5f7fb;
    --card: #ffffff;
    --text: #172033;
    --muted: #718096;
    --border: #e7ebf2;
    --shadow: 0 10px 30px rgba(15, 23, 42, 0.07);
}
```

- **Sidebar pattern:** Fixed sidebar on desktop; off-canvas hamburger menu on mobile
- **CSS location:** Role-specific CSS goes in `css/student/`, `css/coach/`, `css/admin/`. Shared styles go in `css/common/`
- **Do not** write `style=""` inline attributes. Use class names or add to the role CSS file.

---

## 11. Local Development Setup

```powershell
# 1. Activate Python virtual environment
.venv\Scripts\activate

# 2. Start everything with one command
python run_all.py

# 3. Open your browser
# http://localhost:8080
```

**Frontend-only changes** (HTML/CSS/JS edits): just refresh the browser — no restart needed.  
**Backend changes** (Python edits): restart `run_all.py`.

### Browsing directly to a page

All pages are under `http://localhost:8080/` followed by their path relative to `frontend1/`:

```
http://localhost:8080/student/student-login.html
http://localhost:8080/coach/coach-dashboard.html
http://localhost:8080/shared/fit-track-announcements.html
```

### API calls during development

You can test API endpoints directly in your browser (GET requests) or using a tool like Postman / Thunder Client:

```
GET  http://localhost:8080/api/session
POST http://localhost:8080/api/login      { "email": "...", "password": "..." }
GET  http://localhost:8080/api/health
```

---

## 12. Common Mistakes to Avoid

| Mistake | Correct Approach |
|---|---|
| Writing `fetch("http://localhost:5000/api/...")` directly in HTML | Always use `FitnessAPI.*` methods from `api-client.js` |
| Not including `config.js` before `api-client.js` | Script order matters — `config.js` must come first |
| Forgetting `credentials: "include"` in fetch | `api-client.js` already handles this — use it |
| Not checking `result.ok && result.data.success` | Always check both — `ok` is HTTP status, `success` is app-level |
| Adding a new page without `auth-guard.js` | Unprotected pages let any visitor access dashboard content |
| Putting business logic in HTML `<script>` inline tags | Move it to `api-client.js`, `auth-flow.js`, or `reference-pages.js` |
| Using `alert()` for user feedback | Use a proper toast or in-page message element |
| Linking to backend endpoints directly in `href` | Use JS to trigger downloads or navigations, not bare `<a href="/api/...">` |
| Editing `vendor/` or CDN files | Never edit third-party files; update them as a package |
| Testing on port 5001 without checking API base | Open on port 8080 (proxied) or verify `window.FITNESS_API_BASE` is correct |