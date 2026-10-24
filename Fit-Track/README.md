# Inspiria Digital Sports Passport V7

A responsive Flask + SQLite prototype for Inspiria Knowledge Campus Sports operations. V7 keeps the complete V6 platform and adds a role-aware Coaching Schedule for dated sessions, timings, venue/status and session notes.

## Demo logins

### Master Admin
- `neehar.reddy` / `Inspiria@2026`
- `sushovan.gupta` / `Inspiria@2026`

### Coaches
All seeded coach accounts use `Inspiria@2026`:
- `nagen.tamang` — Football
- `rajendra.rajat` — Basketball
- `ritik.jaiswal` — Gym
- `siva.gurung` — Kick Boxing

### Student
- `aarav@inspiria.edu.in` / `Student@2026`

Students can self-register with an `@inspiria.edu.in` email. The prototype validates the email domain; production should use college SSO or verified OTP.

## V7 Coaching Schedule

- A new **Coaching Schedule** tab is visible to Admin, Coaches and Students.
- Every session can contain Programme/Sport, Date, Start Time, End Time, Venue, Status and Notes.
- **Master Admin** can create, edit, reschedule, cancel or delete sessions across all coaching programmes.
- **Coaches** can create/edit/delete sessions only for the programme assigned to them.
- **Students** have view-only access to the complete published coaching schedule.
- The schedule is month-filterable and responsive across mobile, tablet and desktop.
- Existing programme recurring schedule text remains unchanged and is shown alongside dated sessions.

## Role permissions

### Admin
Master edit access to student and coach profiles, sports/facilities, coaching programmes, events, fixtures, scores, official participant lists, results, draw PDFs, live scores, media, announcements, account controls and certificate generation.

### Coaches
Can view assigned coachees; edit only coaching attendance, athlete-development metrics and coach remarks; download coaching reports; chat with assigned students. Sensitive parent/address/medical fields remain hidden.

### Students
Can view only their own Sports Passport/performance, self-register for events, download performance data and generated certificates, chat with coaches, view fixtures/live scores, announcements and event/facility media, and download event photos/videos.

## V6 final additions


- Master profile-photo desk for student and coach photos; Admin can upload, replace and delete photographs.
- Bulk sports assignment: add multiple students to any active sports/activity in one action.
- Bulk coaching assignment: enlist multiple students under a coached programme/coach in one action.
- Optional fixture squads capped at 15 students per side; selected master records are department-validated and shown on the public team list.
- Announcement posts can include an optional image alongside title/message.
- Reports & Analytics is available to all signed-in roles with privacy-safe cumulative Weekly, Monthly and Yearly projections.
- Projection downloads aggregate every coached sport's attendance, overall performance and sport-specific development criteria into CSV.
- Students retain only their own detailed report; Coaches retain their coachee scope; Admin retains complete detail.
- Responsive desktop/tablet/mobile layout with off-canvas mobile navigation.
- Permanent auto-generated Sports Passport ID for every student, e.g. `IKC-SP-2026-00001`.
- Fixture category dropdown: Boys / Girls.
- Admin fixture editing: teams, date, round, venue, score and status.
- Admin fixture deletion.
- Per-fixture Team A / Team B player rosters with add/delete student names.
- Official event participant list imported only by Admin from `.xlsx` or `.xls`.
- Required official participant columns: `Name`, `Department`, `Category`, `Year`.
- Only those four participant fields are displayed in the public event participant table.
- Winners and Runners-up section for Boys/Girls with manual Admin entry.
- League/Knockout fixture projection PDF upload separately for Boys/Girls.
- Up to 30 latest event photos displayed in a continuously moving 3D/floating carousel.
- Admin can upload/delete event photos; other roles view/download only.
- Global Announcements tab and announcement ticker. Only Admin can publish/delete announcements.
- Certificate-template upload per event for Participation and Achievement certificates.
- Supported certificate templates: PDF, JPG, JPEG, PNG.
- Auto-generated PDF participation certificates for official participants.
- Auto-generated achievement certificates for official participants matching the entered Winner/Runner-up result and category.
- Students linked to an official participant record can download generated certificates from their Sports Passport.
- Sports/facility pages: Admin can name the facility, upload/replace/delete a cover photo, and add/delete gallery photos; Coaches/Students view only.

## Certificate template note

The prototype places the recipient name and certificate information in a standard centred area. For best results, upload a certificate template with clear open space around the centre. A future production version can add a drag-and-drop text-position configurator for arbitrary templates.

## Event participant Excel format

First worksheet, first row must include these headers (common aliases such as `Student Name` and `Dept` are also accepted):

| Name | Department | Category | Year |
|---|---|---|---|
| Ayushman Ray | BBA SM | Boys | 2026 |
| Sneha Mitra | BBA | Girls | 2026 |

Category must be exactly Boys or Girls.

## Run on Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Or run `./run_linux.sh`.

Open `http://127.0.0.1:5000`.

## Run on Windows

Run `run_windows.bat`, or:

```bat
py -3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Dependencies added in V5

- `openpyxl` — `.xlsx` participant imports
- `xlrd` — `.xls` participant imports
- `reportlab` + `pypdf` + `Pillow` — certificate generation from uploaded PDF/image templates

## Production notes

This remains a prototype/hackathon build. Before deployment: use a strong Flask secret, replace all demo passwords, connect college SSO/email verification, enable HTTPS/production WSGI, add CSRF protection, upload-size/MIME validation, malware scanning, audit logs, backups and institutional privacy controls for medical/emergency/parent data.

## Fresh database

The final package is shipped without `data/sports.db`. First run creates a fresh V7 database and seeds demo accounts, 14 sports, four coaching programmes, students, events and sample fixtures.
