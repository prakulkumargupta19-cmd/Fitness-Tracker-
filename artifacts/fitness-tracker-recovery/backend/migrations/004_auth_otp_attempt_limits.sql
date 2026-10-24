-- Safe to run repeatedly against PostgreSQL.
ALTER TABLE otp_verifications
    ADD COLUMN IF NOT EXISTS attempt_count SMALLINT NOT NULL DEFAULT 0;

ALTER TABLE admin_otp_verifications
    ADD COLUMN IF NOT EXISTS attempt_count SMALLINT NOT NULL DEFAULT 0;
