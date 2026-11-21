-- Reversible soft deactivation metadata. Existing is_active remains the
-- authorization source of truth and is synchronized by the application.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS account_status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deactivated_by BIGINT;
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS reactivated_at TIMESTAMP WITHOUT TIME ZONE;

UPDATE users
SET account_status = CASE WHEN is_active THEN 'active' ELSE 'deactivated' END
WHERE role = 'student';

CREATE INDEX IF NOT EXISTS idx_users_student_account_status
    ON users (account_status, created_at) WHERE role = 'student';
