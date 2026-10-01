-- Apply to the configured application database to enable admin OTP login
-- and password reset on databases created before this table was introduced.
CREATE TABLE IF NOT EXISTS admin_otp_verifications (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    admin_id   INT NOT NULL,
    purpose    ENUM('login', 'password_reset') NOT NULL,
    otp_hash   VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    is_used    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE,
    INDEX idx_admin_otp_purpose (admin_id, purpose)
);
