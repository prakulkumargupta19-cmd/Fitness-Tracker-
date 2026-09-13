# Fitness Tracker Project – Remaining Work and Action Plan

## 1. Project overview
This project is a role-based athlete tracking system for students, coaches, and administrators. The backend is built with Flask and MySQL, while the frontend is a static HTML/JavaScript interface.

Current high-level purpose:
- Students track personal performance and progress.
- Coaches review assigned athletes, add assessments, sessions, goals, and feedback.
- Admins manage accounts and view system-wide data.

---

## 2. Current status
### Backend
- Core Flask backend is implemented and the API structure is in place.
- Authentication, sessions, role checks, and database access are mostly working.
- Demo-user authentication has been restored for local use.
- Backend smoke tests are now in place for regression checks.

### Frontend
- Student and coach login pages exist, but they still need validation and flow checks against the backend.
- Coach dashboard and admin dashboard are mostly UI prototypes and require real data wiring.
- Admin login OTP flow must be completed consistently across the UI and backend.

### Database
- MySQL schema exists and supports the required domain model.
- Seed data and initialization logic need to be kept idempotent for repeated local runs.

---

## 3. What still needs to be done

### Priority 1 – Critical blockers
#### 3.1 Complete frontend login flow verification
- Confirm all student, coach, and admin login pages submit to the correct API routes.
- Check that role values are sent correctly (`student`/`coach`/`admin`).
- Ensure all login responses display clear success or error messages in the UI.
- Redirect authenticated users to the correct dashboard after login.

#### 3.2 Finish admin OTP workflow
- Confirm the admin login page triggers `/api/admin-login` correctly.
- Verify the OTP verification page sends the correct email and OTP payload.
- Ensure the resend OTP flow works without stale session issues.
- Test full admin login end-to-end.

#### 3.3 Harden local setup and environment configuration
- Document all required environment variables clearly.
- Ensure `.env` or startup scripts provide `SECRET_KEY` and mail settings for local use.
- Define a standard local startup command for developers.

### Priority 2 – Functional completion
#### 3.4 Integrate dashboards with real backend APIs
- Student dashboard: load assessments, sessions, goals, and feedback from the API.
- Coach dashboard: load assigned athletes and allow create/update workflows.
- Admin dashboard: replace mock data with real users and counts from backend endpoints.

#### 3.5 Finish coach-side CRUD workflows
- Assessments creation
- Training session creation
- Goal creation
- Feedback creation
- Athlete assignment validation

#### 3.6 Complete admin operations
- User directory should be fully visible and correctly filtered for admins.
- Admin should be able to view all athlete records and dashboard metrics.
- Add read-only and protected write checks for admin access.

### Priority 3 – Quality and production readiness
#### 3.7 Add validation and sanitization checks
- Verify all API inputs before database writes.
- Add stricter form validation on frontend pages.
- Ensure numeric values and dates remain within allowed ranges.

#### 3.8 Improve deployment setup
- Add production environment configuration.
- Document MySQL setup instructions and expected schema setup steps.
- Decide whether to use development seeds in production or disable them.
- Add a proper deployment checklist.

#### 3.9 Add monitoring and maintenance tools
- Health check route for backend status.
- Logging for failed login, OTP issues, and database errors.
- Basic rate-limiting and audit logging for sensitive auth operations.

---

## 4. Recommended implementation order
1. Fix and verify all login flows.
2. Complete admin OTP and session handling.
3. Connect dashboards to the real backend.
4. Finish coach create/update actions.
5. Add validation and production hardening.
6. Add deployment and observability documentation.

---

## 5. Suggested developers’ checklist
### Backend
- [ ] Start backend using the standard command.
- [ ] Ensure `SECRET_KEY` is configured.
- [ ] Confirm MySQL server is running.
- [ ] Run the backend smoke test suite.
- [ ] Check login and OTP endpoints with real data.

### Frontend
- [ ] Verify all forms call the correct API endpoints.
- [ ] Confirm session cookies are sent correctly.
- [ ] Check successful redirects after login.
- [ ] Replace static mock data with API-driven data.

### Release readiness
- [ ] Validate all major role flows: student, coach, admin.
- [ ] Test OTP reset and verification flows.
- [ ] Confirm no broken routes or missing assets.
- [ ] Review production security settings before deployment.

---

## 6. Immediate next step
The next major milestone should be:
"Complete the full student, coach, and admin login and dashboard wiring so the application works end-to-end with the backend API and no mock-only UI flows remain."

This is the project’s highest-value target before production deployment.
