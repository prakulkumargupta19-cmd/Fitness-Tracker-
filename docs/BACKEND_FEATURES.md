# Backend Features and Data Model

This document describes the backend behavior reflected in the repository. It is a code-level guide, not confirmation that a production database has been provisioned or migrated.

## Architecture

- Flask JSON API with role/session-based authorization and CSRF protection.
- Database access is implemented in `backend/db.py`; development can use SQLite and production configuration can use PostgreSQL.
- PostgreSQL base schema is `backend/schema.sql`. Additive PostgreSQL upgrades are in `backend/migrations/`.
- Local SQLite schema is `backend/local_schema.sql`; startup applies non-destructive compatibility upgrades in `initialize_local_database()`.

## Student profile persistence

`POST /api/profile/setup` completes verified-student onboarding. `PUT` or `PATCH /api/profile` updates an authenticated student's profile. Both use `_save_student_profile()` in `backend/app.py`.

The profile upsert stores the student's user ID, date of birth, emergency contact, height, weight, goal, selected sports as a comma-separated legacy field, department, semester, gender, student number, blood group, medical history, address, and parent name/phone/address. Blank optional text is saved as `NULL`. An existing row is updated using `ON CONFLICT (user_id) DO UPDATE`; it is not duplicated. Normalized sport selections are synchronized in `student_sports` in the same database transaction.

The student number accepts either `student_id` or `student_number` from the request and is stored in the database column `student_number`. The profile GET response also includes profile fields such as `bio`, `passport_id`, and `photo_path` where the schema supports them.

### Profile database columns

Both PostgreSQL and SQLite schemas include the profile fields used by the API. PostgreSQL migration `006_fit_track_reference_features.sql` adds the extended profile columns to existing installations. SQLite startup adds a nullable `gender` column to an existing `student_profiles` table if it is absent. These upgrades are additive; they do not intentionally delete or rewrite existing profile records.

## Other backend areas

The repository also contains authentication and OTP flows, coach approval and sport assignments, attendance, assessments, training sessions, goals, announcements, chat, and tournament/event features. See the route implementations under `backend/` for authoritative endpoint behavior.

## Operational caveat

Editing a schema or migration file does not apply it to a remote database automatically. Before relying on submitted data in production, configure the database connection, apply the migrations, and verify the target database schema and backups. Automated tests using mocked connections do not prove production persistence.