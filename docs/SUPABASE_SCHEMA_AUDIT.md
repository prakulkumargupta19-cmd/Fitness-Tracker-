# Supabase PostgreSQL Schema Audit

## Audit result

**Live Supabase comparison: UNKNOWN / BLOCKED.** The safe connection check was
run on 2026-10-02. It reported `SUPABASE_DB_URL is not configured`, so the
Supabase catalog could not be read. This is not evidence that any Supabase
table or column is missing. No credentials or connection strings were printed.

The expected application contract is documented in
[`DATABASE_REQUIREMENTS.md`](./DATABASE_REQUIREMENTS.md). The canonical local
PostgreSQL DDL is [`backend/schema.sql`](./backend/schema.sql). The statuses
below distinguish static comparison against that DDL from live comparison.

## MATCH

### Application SQL against the canonical local schema

- The 15 required base tables and their referenced columns are present in
  `backend/schema.sql`; the column types, nullability, defaults, primary keys,
  declared unique keys, checks, foreign keys, and indexes are inventoried in
  `DATABASE_REQUIREMENTS.md`.
- Observed conflict targets have corresponding local unique constraints:
  `student_profiles(user_id)`, `pending_registrations(email)`,
  `coach_sports(coach_id, sport_id)`,
  `attendance_sessions(coach_id, sport_id, session_date)`, and
  `attendance_records(session_id, student_id)`.
- Generated IDs are declared as identity columns and application insert paths
  that need the IDs use PostgreSQL `RETURNING`.
- Case-insensitive email uniqueness is now declared with unique expression
  indexes on `LOWER(email)` for users, admins, and pending registrations, in
  addition to the original exact-value unique constraints.
- SQL forms reviewed as PostgreSQL-compatible include parameter placeholders
  (`%s`, psycopg adaptation), `ON CONFLICT`, `EXCLUDED`, `RETURNING`,
  `STRING_AGG`, filtered aggregates, booleans, `NOW()`, and PostgreSQL interval
  expressions.

These are source-to-DDL checks only. They do not establish that the same
objects exist in the hosted database.

## MISSING

- **Live Supabase objects:** none can be confirmed missing while the connection
  is unavailable. Each required table's live presence is **UNKNOWN** (see the
  table below).
- **Missing from the local DDL:** none identified in the static table/column
  inventory.

## INCORRECT

- No incorrect live Supabase definition can be confirmed without catalog
  access. A static mismatch in the earlier local DDL (case-sensitive-only
  email uniqueness despite case-insensitive lookups) was corrected by adding
  unique expression indexes to the canonical DDL.

## UNKNOWN

### Required table presence in the live Supabase database

| Required table | Live status |
|---|---|
| `users` | UNKNOWN |
| `admins` | UNKNOWN |
| `student_profiles` | UNKNOWN |
| `otp_verifications` | UNKNOWN |
| `pending_registrations` | UNKNOWN |
| `sports` | UNKNOWN |
| `admin_otp_verifications` | UNKNOWN |
| `coach_sports` | UNKNOWN |
| `student_sports` | UNKNOWN |
| `physical_assessments` | UNKNOWN |
| `training_sessions` | UNKNOWN |
| `goals` | UNKNOWN |
| `coach_feedback` | UNKNOWN |
| `attendance_sessions` | UNKNOWN |
| `attendance_records` | UNKNOWN |

The view `student_details`, trigger function `set_updated_at()`, and four
`updated_at` triggers are schema-owned objects as well; their live state is
also **UNKNOWN**.

### Live schema properties not verified

Because `information_schema` was not accessible, the following cannot be
compared with Supabase yet:

- Required columns, PostgreSQL types, precision/length, and generated identity
  properties.
- Primary keys, foreign keys and delete actions, unique constraints, checks,
  defaults, nullable settings, and indexes.
- Schema ownership/search path and presence of the view/function/triggers.
- Whether the current Supabase project contains existing data or
  case-insensitive email duplicates.
- Actual connection/query latency and PostgreSQL runtime execution.
- Whether the live database has the case-insensitive email indexes now declared
  by the local schema. Before applying them to an existing database, inspect
  and resolve any case-folded duplicates; no data-changing cleanup was
  attempted without database access.

### Re-run the live check

Set `SUPABASE_DB_URL` in the process environment (or in the local root `.env`
file) to the intended Supabase PostgreSQL connection URL, then run:

```powershell
.\.venv\Scripts\python.exe scripts\test_supabase_connection.py
```

The script reports only connection/query status, latency, required table
presence, and sanitized exception type. It never prints the configured URL or
credentials. A `PASS` for required tables checks base-table presence only; it
does not certify column definitions or constraints.

## PostgreSQL/MySQL compatibility review

The required-pattern scan over `backend/`, `scripts/`, and `tests/` found no
runtime use of PyMySQL, MySQL connector, `ON DUPLICATE KEY UPDATE`,
`GROUP_CONCAT`, `cursor.lastrowid`, `AUTO_INCREMENT`, `TIMESTAMPDIFF`,
`DATE_FORMAT`, or `INSERT IGNORE`. The only such token occurrences in scanned
Python files are literals in `scripts/verify_vercel.py`, where they form the
static check's forbidden-pattern list. `NOW()` remains in SQL and is valid
PostgreSQL syntax; it is not treated as a MySQL-only construct.

Remaining references to MySQL in documentation describe the old implementation
or explicitly state that MySQL data migration is separate. The application
connection helper uses psycopg and `SUPABASE_DB_URL`; no production MySQL
connection path is configured.

## Verification performed

- Safe live connection script: **connection unavailable** because
  `SUPABASE_DB_URL` is not configured; no credentials were emitted.
- Static PostgreSQL/Vercel compatibility check: pass before this audit.
- Application tests: 32 passed, 2 skipped during this audit; the opt-in
  PostgreSQL integration workflow remains skipped unless configured with a
  dedicated test database.
- A successful static scan and DB-free tests do not substitute for a live
  Supabase schema comparison.
