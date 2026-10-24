# Frontend Integration Guide

Use the routes and request fields below as the integration reference for the current Flask backend. Route details can evolve; check `backend/app.py` and the relevant backend modules when extending this guide.

## API requests and security

- Use the shared request utilities in `frontend1/js/api-client.js` where possible.
- Authentication is session-cookie based; browser requests need to retain credentials.
- The backend enforces CSRF protection for state-changing requests. Obtain a token from `GET /api/csrf-token` and send it as `X-CSRFToken` (the shared API client handles this flow).
- Check the HTTP status and JSON `success`/`message` fields. Present useful feedback and loading states rather than treating all responses as successful.

## Student profile and onboarding

The current profile routes are:

| Purpose | Method | Route |
|---|---|---|
| Read signed-in user's profile | `GET` | `/api/profile` |
| Save/update a student profile | `PUT` or `PATCH` | `/api/profile` |
| Complete verified student onboarding | `POST` | `/api/profile/setup` |
| List sports catalog | `GET` | `/api/sports` |
| Read signed-in student's sport selections | `GET` | `/api/student/sports` |

Profile setup requires `date_of_birth` (or legacy `dob`) and `emergency_contact` (or legacy `emergency-phone`). Optional profile fields include `height_cm`, `weight_kg`, `goal`, `department`, `semester`, `gender`, `student_id` (or `student_number`), `blood_group`, `medical_history`, `address`, `parent_name`, `parent_phone`, and `parent_address`. Sports are sent as a `sports` array of catalog names; legacy clients may send comma-separated `sport_activity` or `activity`.

Example request body:

```json
{
  "date_of_birth": "2005-03-12",
  "emergency_contact": "9876543210",
  "department": "Computer Science",
  "semester": "4",
  "gender": "female",
  "student_id": "STU-31",
  "blood_group": "O+",
  "medical_history": "",
  "address": "1 Example Road",
  "parent_name": "Example Parent",
  "parent_phone": "9876543211",
  "parent_address": "2 Example Road",
  "sports": ["Football", "Basketball"]
}
```

On save, the API upserts the profile row by `user_id` and synchronizes selected sports. After saving, use the returned `profile` or fetch `GET /api/profile` to refresh the UI. Optional blank text is represented as null by the backend.

## Other common feature areas

The backend has routes for student dashboard data, coach rosters/attendance/assessments, admin coach and student management, announcements, chat, and tournaments/events. Do not rely on old route names in earlier drafts of this guide; inspect route declarations in `backend/app.py`, `backend/attendance.py`, and related modules before wiring a new page.

## Persistence note

The API's database schema must be applied to the same database used by the running app. A successful frontend response and mocked unit tests alone do not establish that a production database is configured, migrated, or backed up.