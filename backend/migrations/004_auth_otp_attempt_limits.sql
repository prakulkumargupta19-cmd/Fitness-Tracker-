-- Apply to the configured application database for existing installations.
ALTER TABLE otp_verifications
    ADD COLUMN attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0;

ALTER TABLE admin_otp_verifications
    ADD COLUMN attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0;
