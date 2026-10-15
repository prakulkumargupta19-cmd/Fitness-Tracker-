# Inspiria Digital Sports Passport V7 — System Blueprint

## Core identity model
Every student record has two identifiers: the college Student ID/Registration Number and an automatically generated permanent Sports Passport ID (`IKC-SP-YYYY-#####`). The Sports Passport ID is the platform identity shown across profiles and event operations.

## Roles
- **Admin:** master read/write access across the system.
- **Coach:** read access to assigned coachees; write access only to attendance, development metrics/remarks; reports and coach-student chat.
- **Student:** self-service personal profile view, event registration, performance/certificate downloads, chat, fixtures/live score/media/announcement access.

## Tournament data model
1. **Registrations** — student self-registration/application information.
2. **Official Participants** — Admin-owned final participant list imported from XLSX/XLS; only Name, Department, Category and Year are displayed.
3. **Fixtures** — Boys/Girls category, stage, teams/departments, scores, status and per-side player rosters.
4. **Draw Documents** — League/Knockout PDF projections for Boys/Girls.
5. **Results** — manually confirmed Winner and Runner-up for each category.
6. **Media** — Admin-uploaded event photos/videos; up to 30 latest photos populate the rolling 3D event carousel.
7. **Certificates** — uploaded Participation/Achievement templates and generated recipient PDFs.

## Certificate logic
- Participation: one certificate per official participant.
- Achievement: participant category must match a result category, and participant Name or Department must match the Winner or Runner-up entry.
- Generated certificates receive a unique certificate number and can be downloaded by Admin and the linked student.

## Facilities
Each active sport/activity has a named facility/venue, optional cover photo and multi-image facility gallery. Admin can edit/upload/delete; Coach and Student roles are view-only.

## Responsive behaviour
- Desktop: fixed sidebar.
- Tablet/mobile: off-canvas hamburger navigation.
- Multi-column panels collapse to one/two columns based on width.
- Tables use horizontal touch scrolling.
- Fixture cards, forms, dialogs, galleries and carousels reflow for smaller screens.
- Event and facility images use responsive object-fit layouts.

## Production next steps
College SSO/OTP, audit logs, CSRF, object storage/CDN, role-permission test suite, certificate-template coordinate editor, bulk certificate ZIP export, push/email notifications, database migration tooling and production PostgreSQL.


## V6 final operational layer
- **Profile media:** `students.photo_path` and `coaches.photo_path` are Admin-managed master photographs.
- **Bulk assignment:** Admin can attach any active sport/activity to multiple Sports Passports or enroll multiple students in a coaching programme at once.
- **Fixture squads:** player lists remain optional; each side is limited to 15 names. Master student selections are checked against the represented department (with legacy department aliases supported).
- **Announcement media:** announcements may carry an optional image displayed with the text notice.
- **Cumulative projections:** weekly (last 7 days), monthly (current calendar month) and yearly (current calendar year) aggregate attendance, overall performance and every sport-specific metric across coached sports. These aggregate projection CSVs are available to all signed-in roles and contain no student-level private information.


## V7 coaching schedule
- `coaching_sessions` stores dated sessions against the existing `programmes` table.
- Published fields: programme/sport, coach, session date, start/end time, venue, status and notes.
- Admin has master write access to all sessions.
- A Coach has write access only when `programmes.coach_id` matches that coach account.
- Students have read-only access and receive no create/edit/delete controls.
- Status values supported by the interface: Scheduled, Rescheduled, Cancelled and Completed.
- Session management is non-destructive to existing V6 student, coaching, event, analytics and certificate data.
