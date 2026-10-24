-- Extend the existing auth, coach, and attendance model for reviewed coaches
-- and auditable attendance updates. Coach/student sport roles drive rosters.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attendance_status_type') THEN
        EXECUTE 'ALTER TYPE attendance_status_type ADD VALUE IF NOT EXISTS ''late''';
        EXECUTE 'ALTER TYPE attendance_status_type ADD VALUE IF NOT EXISTS ''excused''';
    END IF;
END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS qualification VARCHAR(255);

ALTER TABLE users ADD COLUMN IF NOT EXISTS specialization VARCHAR(255);

ALTER TABLE users ADD COLUMN IF NOT EXISTS experience_years INTEGER;

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE users ADD COLUMN IF NOT EXISTS coach_decided_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE users ADD COLUMN IF NOT EXISTS coach_decision_reason TEXT;

ALTER TABLE pending_registrations ADD COLUMN IF NOT EXISTS qualification VARCHAR(255);

ALTER TABLE pending_registrations ADD COLUMN IF NOT EXISTS specialization VARCHAR(255);

ALTER TABLE pending_registrations ADD COLUMN IF NOT EXISTS experience_years INTEGER;

ALTER TABLE pending_registrations ADD COLUMN IF NOT EXISTS decision_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE pending_registrations ADD COLUMN IF NOT EXISTS decision_reason TEXT;

ALTER TABLE pending_registrations
DROP CONSTRAINT IF EXISTS pending_registrations_status_check;

ALTER TABLE pending_registrations
ADD CONSTRAINT pending_registrations_status_check
CHECK (
    status IN (
        'pending_verification',
        'pending_approval',
        'rejected',
        'declined'
    )
);

ALTER TABLE users
DROP CONSTRAINT IF EXISTS chk_coach_status;

ALTER TABLE users
ADD CONSTRAINT chk_coach_status
CHECK (
    (
        role = 'coach'
        AND coach_status IS NOT NULL
        AND coach_status IN (
            'pending',
            'approved',
            'rejected',
            'declined'
        )
    )
    OR
    (
        role = 'student'
        AND coach_status IS NULL
    )
);

ALTER TABLE attendance_records
ADD COLUMN IF NOT EXISTS session_date DATE;

ALTER TABLE attendance_records
ADD COLUMN IF NOT EXISTS marked_by_role TEXT;

ALTER TABLE attendance_records
ADD COLUMN IF NOT EXISTS marked_by_id BIGINT;

ALTER TABLE attendance_records
ADD COLUMN IF NOT EXISTS updated_by_role TEXT;

ALTER TABLE attendance_records
ADD COLUMN IF NOT EXISTS updated_by_id BIGINT;

ALTER TABLE attendance_records
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE
    NOT NULL DEFAULT CURRENT_TIMESTAMP;

UPDATE attendance_records r
SET session_date = s.session_date
FROM attendance_sessions s
WHERE s.id = r.session_id
  AND r.session_date IS NULL;

UPDATE attendance_records
SET marked_by_role = 'coach'
WHERE marked_by_role IS NULL;

ALTER TABLE attendance_records
ALTER COLUMN session_date SET NOT NULL;

DO $$
DECLARE
    attendance_status_column_type TEXT;
BEGIN
    SELECT udt_name INTO attendance_status_column_type
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'attendance_records'
      AND column_name = 'status';

    IF attendance_status_column_type = 'text' THEN
        ALTER TABLE attendance_records
        DROP CONSTRAINT IF EXISTS attendance_records_status_check;
        ALTER TABLE attendance_records
        ADD CONSTRAINT attendance_records_status_check
        CHECK (status IN ('present', 'absent', 'late', 'excused'));
    ELSE
        ALTER TABLE attendance_records
        DROP CONSTRAINT IF EXISTS attendance_records_status_check;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_attendance_date_status
    ON attendance_records(session_date, status);
