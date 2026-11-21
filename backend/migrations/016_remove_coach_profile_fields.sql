ALTER TABLE users
    DROP COLUMN IF EXISTS qualification,
    DROP COLUMN IF EXISTS specialization,
    DROP COLUMN IF EXISTS experience_years;

ALTER TABLE pending_registrations
    DROP COLUMN IF EXISTS qualification,
    DROP COLUMN IF EXISTS specialization,
    DROP COLUMN IF EXISTS experience_years;
