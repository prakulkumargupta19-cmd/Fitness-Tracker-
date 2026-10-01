-- Apply to the configured application database for existing installations.
ALTER TABLE pending_registrations
    ADD COLUMN otp_attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
    ADD COLUMN otp_sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN otp_send_count TINYINT UNSIGNED NOT NULL DEFAULT 1;
