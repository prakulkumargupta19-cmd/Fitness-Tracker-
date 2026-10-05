# Database Requirements

## Scope and evidence

This inventory covers SQL in every `backend/**/*.py` file, including the optional
local initializer, and the canonical PostgreSQL definitions in
[`backend/schema.sql`](./backend/schema.sql). Types, defaults, nullability, and
declared constraints below are copied from that DDL; columns actually read or
written are confirmed by application SQL. Where application queries use `*`,
all columns of the selected table are required. No type or constraint is inferred
from Python values alone.

`REQUIRED` means `NOT NULL`; `NULL` means the DDL permits null. “No default”
means callers must supply the value when it is required. Application references
are listed per table; the route families identify actual SQL use.

## Required tables and columns

### `users`

**Used by:** `backend/app.py`, `backend/auth/helpers.py`,
`backend/auth/decorators.py`, `backend/attendance.py`, and
`backend/performance.py`.

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `role` | `TEXT` | required; none | `role IN ('student', 'coach')` |
| `full_name` | `VARCHAR(100)` | required; none | — |
| `email` | `VARCHAR(150)` | required; none | Unique |
| `password_hash` | `VARCHAR(255)` | required; none | — |
| `contact_number` | `VARCHAR(30)` | nullable; none | — |
| `is_verified` | `BOOLEAN` | required; `TRUE` | — |
| `coach_status` | `TEXT` | nullable; none | Coach: one of `pending`, `approved`, `rejected`; student: `NULL` |
| `last_login_at` | `TIMESTAMP WITHOUT TIME ZONE` | nullable; none | — |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |

**Foreign keys:** referenced by profile, OTP, coach/student sports, assessment,
training, goals, feedback, attendance-session, and attendance-record rows.
**Indexes:** unique `email` and unique `LOWER(email)` indexes, plus primary-key
index.

### `admins`

**Used by:** `backend/auth/helpers.py`, `backend/app.py`, and
`backend/setup_and_run.py`.

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity starts at `1000000` | Primary key |
| `full_name` | `VARCHAR(100)` | required; none | — |
| `email` | `VARCHAR(150)` | required; none | Unique |
| `password_hash` | `VARCHAR(255)` | required; none | — |
| `is_verified` | `BOOLEAN` | required; `TRUE` | — |
| `last_login_at` | `TIMESTAMP WITHOUT TIME ZONE` | nullable; none | — |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |

**Foreign keys:** referenced by `admin_otp_verifications.admin_id` and
`coach_sports.assigned_by`. **Indexes:** unique `email` and unique
`LOWER(email)` indexes, plus primary-key index.

### `student_profiles`

**Used by:** `backend/app.py` (profile read/upsert and student/admin views).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `user_id` | `BIGINT` | required; none | Primary key; FK to `users.id` (`ON DELETE CASCADE`) |
| `date_of_birth` | `DATE` | required; none | — |
| `emergency_contact` | `VARCHAR(30)` | required; none | — |
| `height_cm` | `DECIMAL(5,2)` | nullable; none | — |
| `weight_kg` | `DECIMAL(5,2)` | nullable; none | — |
| `goal` | `VARCHAR(255)` | nullable; none | — |
| `sport_activity` | `VARCHAR(255)` | nullable; none | — |
| `department` | `VARCHAR(100)` | nullable; none | — |

**Foreign keys:** `user_id` references `users.id`, cascading on delete.
**Indexes:** primary-key index on `user_id`.

### `otp_verifications`

**Used by:** `backend/auth/helpers.py` (`SELECT *` also requires every column).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `user_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `purpose` | `TEXT` | required; none | One of `signup`, `login`, `password_reset` |
| `otp_hash` | `VARCHAR(255)` | required; none | — |
| `expires_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; none | — |
| `attempt_count` | `SMALLINT` | required; `0` | Check `>= 0` |
| `is_used` | `BOOLEAN` | required; `FALSE` | — |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |

**Foreign keys:** `user_id` references `users.id`, cascading on delete.
**Indexes:** `(user_id, purpose)` and `(created_at)`; primary-key index.

### `pending_registrations`

**Used by:** `backend/app.py` (signup, verification, coach status and approval;
`SELECT *` requires every column).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `role` | `TEXT` | required; none | `role IN ('student', 'coach')` |
| `full_name` | `VARCHAR(100)` | required; none | — |
| `email` | `VARCHAR(150)` | required; none | Unique |
| `password_hash` | `VARCHAR(255)` | required; none | — |
| `contact_number` | `VARCHAR(30)` | nullable; none | — |
| `otp_hash` | `VARCHAR(255)` | required; none | — |
| `otp_expires_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; none | — |
| `otp_attempts` | `SMALLINT` | required; `0` | Check `>= 0` |
| `otp_sent_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |
| `otp_send_count` | `SMALLINT` | required; `1` | Check `>= 0` |
| `status` | `TEXT` | required; `'pending_verification'` | One of `pending_verification`, `pending_approval`, `rejected` |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |
| `verified_at` | `TIMESTAMP WITHOUT TIME ZONE` | nullable; none | — |

**Foreign keys:** none declared. **Indexes:** unique `email` and unique
`LOWER(email)` indexes, plus primary-key index.

### `sports`

**Used by:** `backend/app.py`, `backend/attendance.py`, and
`backend/performance.py`.

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `name` | `VARCHAR(50)` | required; none | Unique |

**Foreign keys:** referenced by `coach_sports`, `student_sports`,
`training_sessions`, and `attendance_sessions`. **Indexes:** unique name and
primary-key indexes.

### `admin_otp_verifications`

**Used by:** `backend/auth/helpers.py` (`SELECT *` also requires every column).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `admin_id` | `BIGINT` | required; none | FK to `admins.id` (`ON DELETE CASCADE`) |
| `purpose` | `TEXT` | required; none | One of `login`, `password_reset` |
| `otp_hash` | `VARCHAR(255)` | required; none | — |
| `expires_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; none | — |
| `attempt_count` | `SMALLINT` | required; `0` | Check `>= 0` |
| `is_used` | `BOOLEAN` | required; `FALSE` | — |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |

**Foreign keys:** `admin_id` references `admins.id`, cascading on delete.
**Indexes:** `(admin_id, purpose)` and primary-key index.

### `coach_sports`

**Used by:** `backend/app.py`, `backend/attendance.py`, and
`backend/performance.py`.

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `coach_id` | `BIGINT` | required; none | Composite primary key; FK to `users.id` (`ON DELETE CASCADE`) |
| `sport_id` | `BIGINT` | required; none | Composite primary key; FK to `sports.id` (`ON DELETE CASCADE`) |
| `assigned_by` | `BIGINT` | required; none | FK to `admins.id` |

**Unique keys:** composite primary key `(coach_id, sport_id)`. **Indexes:**
primary-key index.

### `student_sports`

**Used by:** `backend/app.py`, `backend/attendance.py`, and
`backend/performance.py`.

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `student_id` | `BIGINT` | required; none | Composite primary key; FK to `users.id` (`ON DELETE CASCADE`) |
| `sport_id` | `BIGINT` | required; none | Composite primary key; FK to `sports.id` (`ON DELETE CASCADE`) |

**Unique keys:** composite primary key `(student_id, sport_id)`. **Indexes:**
primary-key index.

### `physical_assessments`

**Used by:** `backend/performance.py` (`SELECT *` / `r.*` require every column).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `student_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `coach_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `assessment_date` | `DATE` | required; none | — |
| `speed` | `DECIMAL(7,2)` | nullable; none | — |
| `strength` | `DECIMAL(7,2)` | nullable; none | — |
| `endurance` | `DECIMAL(7,2)` | nullable; none | — |
| `agility` | `DECIMAL(7,2)` | nullable; none | — |
| `flexibility` | `DECIMAL(7,2)` | nullable; none | — |
| `reaction_time` | `DECIMAL(7,2)` | nullable; none | — |
| `overall_score` | `DECIMAL(7,2)` | nullable; none | — |
| `notes` | `TEXT` | nullable; none | — |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |
| `updated_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | Maintained by update trigger |

**Foreign keys:** both user references cascade on delete. **Indexes:**
`(student_id, assessment_date)`, primary-key index, and updated-at trigger.

### `training_sessions`

**Used by:** `backend/performance.py` (`SELECT *` / `r.*` require every column).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `student_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `coach_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `sport_id` | `BIGINT` | required; none | FK to `sports.id` |
| `session_date` | `DATE` | required; none | — |
| `training_type` | `VARCHAR(100)` | required; none | — |
| `duration_minutes` | `INTEGER` | required; none | — |
| `description` | `TEXT` | nullable; none | — |
| `performance_notes` | `TEXT` | nullable; none | — |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |
| `updated_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | Maintained by update trigger |

**Foreign keys:** student and coach reference `users.id` with cascade; sport
references `sports.id`. **Indexes:** `(student_id, session_date)`, primary-key
index, and updated-at trigger.

### `goals`

**Used by:** `backend/performance.py` (`SELECT *` / `r.*` require every column).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `student_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `coach_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `title` | `VARCHAR(150)` | required; none | — |
| `description` | `TEXT` | nullable; none | — |
| `target_value` | `DECIMAL(10,2)` | nullable; none | — |
| `current_value` | `DECIMAL(10,2)` | nullable; none | — |
| `start_date` | `DATE` | nullable; none | — |
| `target_date` | `DATE` | nullable; none | — |
| `status` | `TEXT` | required; `'active'` | One of `active`, `completed`, `cancelled` |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |
| `updated_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | Maintained by update trigger |

**Foreign keys:** both user references cascade on delete. **Indexes:**
`(student_id, status)`, primary-key index, and updated-at trigger.

### `coach_feedback`

**Used by:** `backend/performance.py` (`SELECT *` / `r.*` require every column).

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `student_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `coach_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `feedback` | `TEXT` | required; none | — |
| `rating` | `SMALLINT` | nullable; none | Check `rating IS NULL OR rating >= 0` |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |
| `updated_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | Maintained by update trigger |

**Foreign keys:** both user references cascade on delete. **Indexes:**
`(student_id, created_at)`, primary-key index, and updated-at trigger.

### `attendance_sessions`

**Used by:** `backend/attendance.py`.

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `id` | `BIGINT` | required; identity | Primary key |
| `coach_id` | `BIGINT` | required; none | FK to `users.id` (`ON DELETE CASCADE`) |
| `sport_id` | `BIGINT` | required; none | FK to `sports.id` (`ON DELETE CASCADE`) |
| `session_date` | `DATE` | required; none | — |
| `created_at` | `TIMESTAMP WITHOUT TIME ZONE` | required; `CURRENT_TIMESTAMP` | — |

**Unique keys:** `(coach_id, sport_id, session_date)`.
**Foreign keys:** coach and sport references as above. **Indexes:** unique
constraint index and `(session_date)`.

### `attendance_records`

**Used by:** `backend/attendance.py`.

| Column | Type expected | Null/default | Required constraint |
|---|---|---|---|
| `session_id` | `BIGINT` | required; none | Composite primary key; FK to `attendance_sessions.id` (`ON DELETE CASCADE`) |
| `student_id` | `BIGINT` | required; none | Composite primary key; FK to `users.id` (`ON DELETE CASCADE`) |
| `status` | `TEXT` | required; none | `status IN ('present', 'absent')` |

**Unique keys:** composite primary key `(session_id, student_id)`.
**Foreign keys:** both references cascade on delete. **Indexes:** primary-key
index and `(student_id, status)`.

## Views and schema-owned objects

- `student_details` is a PostgreSQL view in `backend/schema.sql`; current
  backend Python SQL does not query it.
- `set_updated_at()` and the four `updated_at` triggers are maintained by the
  schema, not directly by Python queries.
- The `sports` rows inserted by the schema are lookup data, not table
  requirements or application logic dependencies.

## Cross-table constraint summary

| Constraint kind | Required database rules |
|---|---|
| Primary keys | `users.id`, `admins.id`, `sports.id`, OTP IDs, pending-registration ID, performance-resource IDs, and the composite keys listed above |
| Unique keys | `users.email` and `LOWER(users.email)`, `admins.email` and `LOWER(admins.email)`, `pending_registrations.email` and `LOWER(pending_registrations.email)`, `sports.name`, `coach_sports(coach_id, sport_id)`, `student_sports(student_id, sport_id)`, `attendance_sessions(coach_id, sport_id, session_date)`, `attendance_records(session_id, student_id)` |
| Foreign keys | Preserve every relationship explicitly listed under the owning table; referenced IDs are `BIGINT` |
| Database checks | Role, coach status, OTP purposes/counters, registration status, goal status, attendance status, and nonnegative feedback rating as specified above |
| Database defaults | Identity values; booleans and counters; timestamps; default registration/goal states as listed above |
