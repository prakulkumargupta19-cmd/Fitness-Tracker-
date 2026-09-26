-- ============================================================
-- Fitness Performance Tracker — Auth Workflow Schema
-- Scope: ONLY the signup / login / forgot-password / admin-approval
-- flow from the workflow diagram. No assessments, sessions, etc.
-- Engine: MySQL 8+ (CHECK constraints require 8.0.16+)
-- ============================================================

CREATE DATABASE IF NOT EXISTS fitness_tracker_auth
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE fitness_tracker_auth;

-- ------------------------------------------------------------
-- 1. USERS
-- Shared identity table for student and coach roles — this is the
-- "basic info" step for both student and coach signup.
--
--   is_verified  → only meaningful for a student (signup OTP).
--                  TRUE by default for coach, who don't
--                  go through that step in this workflow.
--   coach_status → only set when role = 'coach'. NULL for
--                  student. Captures "approval by admin?
--                  yes / no" — pending until an admin decides.
-- ------------------------------------------------------------
CREATE TABLE users (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    role           ENUM('student', 'coach') NOT NULL,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    contact_number VARCHAR(15),
    is_verified    BOOLEAN NOT NULL DEFAULT TRUE,
    coach_status   ENUM('pending', 'approved', 'rejected') DEFAULT NULL,
    last_login_at  DATETIME,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_coach_status CHECK (
        (role = 'coach' AND coach_status IS NOT NULL)
        OR (role <> 'coach' AND coach_status IS NULL)
    )
);

-- ------------------------------------------------------------
-- 2. STUDENT_PROFILES
-- The "personal info" step. One row per student, 1:1 with users.
-- date_of_birth is stored — NOT age. Age is calculated at query
-- time (see the view below), so it's always correct.
-- ------------------------------------------------------------
CREATE TABLE student_profiles (
    user_id           INT PRIMARY KEY,
    date_of_birth     DATE NOT NULL,
    emergency_contact VARCHAR(15) NOT NULL,
    height_cm         DECIMAL(5,2),
    weight_kg         DECIMAL(5,2),
    goal              VARCHAR(255),
    sport_activity    VARCHAR(100),
    department        VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 3. OTP_VERIFICATIONS
-- Covers both OTP moments in the diagram:
--   purpose = 'signup'          → student only, flips is_verified
--   purpose = 'password_reset'  → any role, the "forgot pwd" branch
-- ------------------------------------------------------------
CREATE TABLE otp_verifications (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    purpose    ENUM('signup', 'login', 'password_reset') NOT NULL,
    otp_hash   VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    is_used    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_otp_user_purpose (user_id, purpose)
);

-- ------------------------------------------------------------
-- 4. ADMINS
-- Admin users table
-- ------------------------------------------------------------
CREATE TABLE admins (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    contact_number VARCHAR(15),
    is_verified    BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at  DATETIME,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) AUTO_INCREMENT=1000000;

-- ------------------------------------------------------------
-- Optional convenience view: surfaces a student's age without
-- ever storing it as a column.
-- ------------------------------------------------------------
CREATE VIEW student_details AS
SELECT
    u.id, u.full_name, u.email, u.contact_number,
    sp.date_of_birth,
    TIMESTAMPDIFF(YEAR, sp.date_of_birth, CURDATE()) AS age,
    sp.emergency_contact, sp.height_cm, sp.weight_kg, sp.department,
    sp.goal, sp.sport_activity
FROM users u
JOIN student_profiles sp ON sp.user_id = u.id
WHERE u.role = 'student';