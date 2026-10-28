# Production Readiness and Data Safety

> **Status: Not confirmed production-ready.** Repository code and schema files have been updated for student profile persistence, but no live database inspection or deployment verification is represented by this document.

## Student profile persistence changes

- Profile setup and profile updates use an upsert keyed by `student_profiles.user_id`; repeat submissions update the existing row.
- The save flow includes academic, health, address, parent-contact, and existing profile fields, and updates normalized sports selections transactionally.
- PostgreSQL schema/migration and local SQLite schema support the fields returned by the profile API.
- The SQLite startup upgrade adds `gender` when missing and is additive. It does not drop the profile table or intentionally remove existing records.
- The PostgreSQL migration is additive, but must still be applied to the actual target database.

These code changes do **not** prove that a specific deployment's connection points to the intended database, that the schema migration has run, or that previous submissions are present. Confirm those points directly against the configured database before relying on production data.

## Release checklist

### Database and preservation

- [ ] Confirm `SUPABASE_DB_URL` (or the production database setting) points to the intended project and environment.
- [ ] Take and verify a database backup before applying schema changes.
- [ ] Apply the ordered PostgreSQL schema/migrations, including `006_fit_track_reference_features.sql`, to the target database.
- [ ] Verify `student_profiles` has the columns queried and written by the app: `department`, `semester`, `gender`, `student_number`, `bio`, health/address/parent fields, `passport_id`, and `photo_path`.
- [ ] Submit a test profile in a controlled test account; read it back through `GET /api/profile` and confirm values persisted after a new request/session.
- [ ] Verify existing student rows remain present and unchanged except for intended nullable/additive schema updates.
- [ ] Document restore/rollback steps and retention policy.

### Application, security, and deployment

- [ ] Configure production secrets, database URL, SMTP, frontend origin, and secure session-cookie settings.
- [ ] Verify CSRF token handling, authorization boundaries, and CORS in the deployed environment.
- [ ] Run unit tests and PostgreSQL integration tests against a non-production database.
- [ ] Verify deployment routing, uploads/storage durability, logs, monitoring, and backups.

## Validation caveats

Tests that use fake or mocked database connections validate application logic, not the live schema or durability of remote writes. Likewise, successful Python compilation does not validate SQL execution on PostgreSQL. Do not mark the database ready until a real database migration and read-after-write check have succeeded.