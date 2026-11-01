CREATE TABLE IF NOT EXISTS admin_login_attempt_limits (
    email_hash CHAR(64) PRIMARY KEY,
    failed_attempts SMALLINT NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    window_started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    locked_until TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_admin_login_attempt_window
    ON admin_login_attempt_limits (window_started_at);
