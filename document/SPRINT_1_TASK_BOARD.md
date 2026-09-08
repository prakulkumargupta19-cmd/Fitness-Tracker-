# Fitness Tracker — Team Task Allocation

**Sprint 1 Start Date:** 2026-08-29  
**Sprint Duration:** 1 week (Monday-Friday)  
**Go-Live Target:** End of Sprint 1

---

## 🔴 BLOCKING ISSUES (Must Complete Before Any Other Work)

### Backend

**Task BK-CRIT-1:** Debug & Fix Login Form Submission  
- **Status:** CRITICAL BLOCKER
- **Description:** Student and coach login forms are not submitting. Form renders correctly, but clicking "Log In" doesn't trigger API call.
- **Files:** Check event listener logic in `student-login.html` and `coach-login.html`
- **Expected Outcome:** POST request to `/api/login` succeeds and user redirects to dashboard
- **Time Estimate:** 2-3 hours
- **Owner:** Frontend Team (investigate), Backend Team (monitor API logs)
- **Acceptance Criteria:**
  - [ ] Form submission sends POST to `/api/login`
  - [ ] Valid credentials (arjun@college.edu / 1234) successfully log in
  - [ ] Invalid credentials show error message
  - [ ] Browser Network tab shows successful 200 response

---

### Frontend

**Task FE-CRIT-1:** Fix Student Login Form Submission  
- **Status:** CRITICAL BLOCKER
- **Description:** [frontend/student/student-login.html](frontend/student/student-login.html) form doesn't submit on button click
- **Investigation Steps:**
  1. Open browser DevTools → Console tab
  2. Check for any JavaScript errors
  3. Verify `loginForm` ID matches form element
  4. Confirm event listener is attached: `document.getElementById('loginForm').addEventListener('submit', ...)`
  5. Check if form validation is blocking submission
- **Root Cause Hypothesis:** Event listener not attached or `e.preventDefault()` missing
- **Fix:** Ensure proper async form handler:
  ```javascript
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const res = await API.login({ email, password, role: 'student' });
    if (res.ok) {
      // Show success message
      // Redirect to dashboard
    } else {
      API.showMessage('message', res.data.message, 'error');
    }
  });
  ```
- **Time Estimate:** 2-3 hours
- **Owner:** Frontend Team
- **Acceptance Criteria:**
  - [ ] Clicking "Log In" button sends API request
  - [ ] Valid credentials accepted (arjun@college.edu / 1234)
  - [ ] Invalid credentials show error in UI (not alert())
  - [ ] Successful login redirects to /student/student-dashboard.html

**Task FE-CRIT-2:** Fix Coach Login Form Submission  
- **Status:** CRITICAL BLOCKER
- **Description:** Same as FE-CRIT-1 but for [frontend/coach/coach-login.html](frontend/coach/coach-login.html)
- **Time Estimate:** 1 hour (copy same fix pattern)
- **Owner:** Frontend Team

---

## 🔴 HIGH-PRIORITY ISSUES (Sprint 1 - Week 1)

### Backend

**Task BK-HIGH-1:** Implement Input Validation  
- **Status:** HIGH
- **Description:** Coach write endpoints (`POST /api/assessments`, `/api/goals`, etc.) need to validate all input fields
- **Files:** [backend/app.py](backend/app.py) (lines 705-840)
- **Required Validations:**
  - `height_cm`, `weight_kg`, `bmi`: Must be numeric, ranges (height 50-300cm, weight 20-300kg)
  - `duration_minutes`: Must be numeric, 1-600 range
  - `intensity_level`: Must be one of `('Low', 'Medium', 'High')`
  - `overall_rating`, `progress_pct`: Must be integers 0-100 or 1-10
  - `assessment_date`, `session_date`: Must be valid ISO 8601 format
  - `athlete_id`: Must be positive integer (already validated via `_validate_coach_owns_athlete`)
- **Implementation:**
  ```python
  def validate_assessment_data(data):
      """Return list of validation errors, empty list if valid."""
      errors = []
      if 'height_cm' in data and data['height_cm'] is not None:
          try:
              h = float(data['height_cm'])
              if h < 50 or h > 300:
                  errors.append("height_cm must be between 50 and 300")
          except (ValueError, TypeError):
              errors.append("height_cm must be a number")
      # ... similar for other fields
      return errors
  ```
- **Time Estimate:** 4 hours
- **Owner:** Backend Team (Lead), Frontend Team (provide test cases)
- **Acceptance Criteria:**
  - [ ] Invalid `height_cm` (e.g., "abc") returns 400 error
  - [ ] Out-of-range values rejected with clear message
  - [ ] All numerical fields validated before database insert
  - [ ] Error messages clear and actionable

**Task BK-HIGH-2:** Separate Development & Production Seed Data  
- **Status:** HIGH
- **Description:** Current [backend/seed.py](backend/seed.py) uses insecure password "1234" visible to users
- **Files:** [backend/seed.py](backend/seed.py)
- **Changes:**
  1. Rename current file → `seed-dev.py`
  2. Replace "1234" with random strong passwords (use `secrets` module)
  3. Update documentation to use environment variables for test credentials
  4. Add to `.gitignore`: `*.seed-db` and `seed-prod.py`
  5. Update [README.md](README.md) with:
     ```
     ## Development Setup
     
     **Warning:** Do not run `seed-dev.py` in production.
     
     Test credentials are available in environment:
     ```bash
     # Load test credentials (never share these in production)
     source .env.test
     echo $TEST_USER_STUDENT  # Outputs: arjun@college.edu
     ```
  6. Create `.env.test.example` showing pattern (without actual credentials)
- **Time Estimate:** 2 hours
- **Owner:** Backend Team + DevOps (if applicable)
- **Acceptance Criteria:**
  - [ ] `seed-dev.py` generates random 16+ character passwords
  - [ ] Test credentials NOT visible in seed script output
  - [ ] `.env.test` file exists and is in `.gitignore`
  - [ ] README documents where to find test credentials

**Task BK-HIGH-3:** Remove Hardcoded OTP Checks  
- **Status:** HIGH
- **Description:** [frontend/admin/admin-signup-verify.html](frontend/admin/admin-signup-verify.html) has hardcoded "123456" demo check
- **Files:** 
  - [frontend/admin/admin-signup-verify.html#L822-L830](frontend/admin/admin-signup-verify.html#L822-L830)
- **Current Code:**
  ```javascript
  if (otp !== "123456") {
      return showError("Invalid OTP. Please enter 123456 for this demo.");
  }
  ```
- **Fix:** Call actual API:
  ```javascript
  const res = await API.verifySignupOtp({ email: email, otp: otp });
  if (!res.ok) {
      API.showMessage('message', res.data.message || "OTP verification failed.", "error");
      return;
  }
  API.showMessage('message', "Admin account created successfully!", "success");
  setTimeout(() => window.location.href = "admin-login.html", 1500);
  ```
- **Time Estimate:** 1 hour
- **Owner:** Frontend Team
- **Acceptance Criteria:**
  - [ ] No hardcoded "123456" in code
  - [ ] OTP verification uses `/api/account-verification/verify`
  - [ ] Success redirects to admin-login
  - [ ] Errors show in UI (not browser alert)

---

### Frontend

**Task FE-HIGH-1:** Standardize All Notifications  
- **Status:** HIGH
- **Description:** Mix of `alert()` calls and `API.showMessage()` creates inconsistent UX
- **Files to Update:**
  - [frontend/admin/admin-loginotp.html#L399](frontend/admin/admin-loginotp.html#L399)
  - [frontend/admin/forgot-password.html#L213](frontend/admin/forgot-password.html#L213)
  - [frontend/admin/reset-password.html#L250](frontend/admin/reset-password.html#L250)
  - [frontend/admin/reset-password.html#L255](frontend/admin/reset-password.html#L255)
- **Pattern to Use:**
  ```javascript
  // ❌ REMOVE: alert("Message here");
  
  // ✅ REPLACE WITH:
  API.showMessage("message", "Message here", "success"); // or "error"
  ```
- **Time Estimate:** 2 hours (includes testing all 4 pages)
- **Owner:** Frontend Team
- **Acceptance Criteria:**
  - [ ] No `alert()` calls in production code
  - [ ] All messages use `API.showMessage()` pattern
  - [ ] Messages color-coded (green for success, red for error)
  - [ ] Mobile view displays messages properly

**Task FE-HIGH-2:** Update Admin Dashboard Copy  
- **Status:** HIGH
- **Description:** Dashboard promises features not yet implemented
- **Files:** [frontend/admin/admin-dashboard.html](frontend/admin/admin-dashboard.html)
- **Current Claims:**
  - "Manage system accounts, system logs, and user access permissions"
- **Backend Reality:**
  - Only `/api/users` GET exists (read-only)
  - No system logs endpoint
  - No permissions management API
- **Options:**
  1. **Honest Update:** Change to "View all registered users and their roles"
  2. **Expand Features:** Backend team adds POST/PUT/DELETE for user management (HIGH priority for next sprint)
- **Recommend:** Option 1 for Sprint 1, then schedule full user management for Sprint 2
- **Time Estimate:** 1 hour
- **Owner:** Frontend Team (in coordination with Backend)
- **Acceptance Criteria:**
  - [ ] Dashboard copy matches actual API capabilities
  - [ ] No features advertised that don't exist
  - [ ] UX is honest about current state

---

## 🟡 MEDIUM-PRIORITY ISSUES (Sprint 2 - After Go-Live)

### Backend

**Task BK-MED-1:** Add CSRF Protection  
- **Files:** [backend/app.py](backend/app.py)
- **Implementation:** `flask-wtf` library
- **Time Estimate:** 3 hours
- **Sprint:** 2

**Task BK-MED-2:** Implement Rate Limiting  
- **Endpoints:** `/api/login`, `/api/forgot-password`, `/api/admin-login/resend-otp`
- **Limit:** 5 attempts per minute per IP
- **Implementation:** `flask-limiter` library
- **Time Estimate:** 2 hours
- **Sprint:** 2

**Task BK-MED-3:** Add Pagination  
- **Endpoints:** All GET data endpoints (`/api/assessments`, `/api/goals`, etc.)
- **Implementation:** `limit` and `offset` query parameters
- **Time Estimate:** 3 hours
- **Sprint:** 2

**Task BK-MED-4:** Create Audit Logging Table  
- **Files:** [backend/schema.sql](backend/schema.sql)
- **Log:** All CREATE, UPDATE operations on assessments, goals, etc.
- **Time Estimate:** 2 hours
- **Sprint:** 2

**Task BK-MED-5:** Add Admin User CRUD Endpoints  
- **New Endpoints:**
  - `POST /api/users` (create user)
  - `PUT /api/users/{id}` (update user)
  - `DELETE /api/users/{id}` (soft delete)
  - `GET /api/users/{id}` (get details)
- **Time Estimate:** 5 hours
- **Sprint:** 2

---

### Frontend

**Task FE-MED-1:** Implement Admin User Management UI  
- **Features:** Add/edit/delete user modals
- **Dependency:** Backend CRUD endpoints (BK-MED-5)
- **Time Estimate:** 6 hours
- **Sprint:** 2

**Task FE-MED-2:** Add Loading Skeletons  
- **Pages:** Student, coach dashboards while data loads
- **Time Estimate:** 3 hours
- **Sprint:** 2

**Task FE-MED-3:** Implement Search & Filters  
- **Admin page:** Filter users by role, status, created date
- **Time Estimate:** 4 hours
- **Sprint:** 2

---

## 📅 SPRINT 1 TIMELINE

| Day | Backend Team | Frontend Team | QA |
|-----|--------------|---------------|-----|
| **Mon 8/29** | Debug login (BK-CRIT-1) | Fix student login (FE-CRIT-1, FE-CRIT-2) | Smoke test after fixes |
| **Tue 8/30** | Input validation (BK-HIGH-1) | Standardize notifications (FE-HIGH-1) | Test all endpoints |
| **Wed 8/31** | Separate seed data (BK-HIGH-2) | Update admin copy (FE-HIGH-2) | End-to-end flow test |
| **Thu 9/1** | Remove hardcoded OTPs (BK-HIGH-3) | Polish & bug fixes | Final checklist |
| **Fri 9/2** | Deploy & smoke test | Deploy & smoke test | Final sign-off |

---

## 📊 SPRINT 1 EFFORT BREAKDOWN

| Team | Task | Hours | Owner |
|------|------|-------|-------|
| **Backend** | BK-CRIT-1 (debug login) | 3 | Req: FE-CRIT-1 completion |
| | BK-HIGH-1 (validation) | 4 | Backend Lead |
| | BK-HIGH-2 (seed data) | 2 | Backend Lead |
| | BK-HIGH-3 (hardcoded OTP) | 1 | Backend Lead |
| | **Subtotal** | **10** | |
| **Frontend** | FE-CRIT-1 (student login) | 3 | Frontend Lead |
| | FE-CRIT-2 (coach login) | 1 | Frontend Lead |
| | FE-HIGH-1 (notifications) | 2 | Frontend Team |
| | FE-HIGH-2 (admin copy) | 1 | Frontend Team |
| | **Subtotal** | **7** | |
| **QA/Testing** | Smoke tests, end-to-end | 8 | QA Team |
| | **TOTAL SPRINT 1** | **25 hours** | |

---

## ✅ GO-LIVE CHECKLIST

- [ ] All CRITICAL tasks completed (login forms working)
- [ ] All HIGH tasks completed (validation, no hardcoded credentials)
- [ ] No `alert()` calls in production code
- [ ] Seed data uses environment variables, not hardcoded passwords
- [ ] Admin dashboard copy is accurate
- [ ] End-to-end test: Login → View Data → Create Entry → Logout
- [ ] Database seeded with test data
- [ ] `SECRET_KEY` environment variable set in deployment
- [ ] CORS origins configured for production domain
- [ ] Logging enabled and monitored

---

## 🎯 SUCCESS CRITERIA (Sprint 1 Completion)

1. **Users can log in** — Primary user journey works end-to-end
2. **Data is validated** — No garbage data can reach the database
3. **Security improved** — No demo hardcoded secrets in code
4. **UI is consistent** — No browser alerts; all messages styled
5. **Documentation is honest** — UI matches actual features
6. **Tests pass** — Smoke tests, login flow, CRUD operations

---

## 📞 ESCALATION & COMMUNICATION

- **Daily Standup:** 9:30 AM (15 min) — Blockers, progress, help needed
- **Blockers:** Report immediately in #dev-urgent Slack channel
- **FE-Backend Sync:** 2:00 PM daily (for API integration questions)
- **QA Handoff:** Friday 2:00 PM for testing before go-live

---

**Document Version:** 1.0  
**Last Updated:** 2026-08-29  
**Next Review:** 2026-09-02 (End of Sprint 1)
