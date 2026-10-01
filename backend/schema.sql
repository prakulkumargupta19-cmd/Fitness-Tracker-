-- ============================================================
-- Fitness Performance Tracker — Full Schema
-- Engine: MySQL 8+ (CHECK constraints require 8.0.16+)
--
-- Covers:
--   1-4. Auth — student/coach signup, login OTP, forgot-password,
--        admin approval of coaches
--   5.   Sports reference list (Football, Basketball, Volleyball,
--        Badminton, Cricket, Athletics, Kickboxing)
--   6.   Admin assigns sport(s) to a coach (many-to-many)
--   7.   Student selects sport(s) during signup/profile (many-to-many)
--   8-9. Coach takes attendance, scoped by sport
--
-- This is the single file backend/setup_and_run.py loads to
-- build the database from scratch.
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
-- sport_activity stays here as free text for backward compat —
-- student_sports (table 7) is the normalized, multi-sport source
-- of truth going forward.
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
    attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
    is_used    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_otp_user_purpose (user_id, purpose)
);

-- Signup drafts are not application accounts. Students are inserted into
-- users only after OTP verification; coaches only after OTP and admin approval.
CREATE TABLE pending_registrations (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    role           ENUM('student', 'coach') NOT NULL,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    contact_number VARCHAR(15),
    otp_hash       VARCHAR(255) NOT NULL,
    otp_expires_at DATETIME NOT NULL,
    otp_attempts   TINYINT UNSIGNED NOT NULL DEFAULT 0,
    otp_sent_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    otp_send_count TINYINT UNSIGNED NOT NULL DEFAULT 1,
    status         ENUM('pending_verification', 'pending_approval', 'rejected') NOT NULL DEFAULT 'pending_verification',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at    DATETIME NULL
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
    is_verified    BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at  DATETIME,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) AUTO_INCREMENT=1000000;

-- ------------------------------------------------------------
-- 5. SPORTS
-- Reference list, scoped to what the college actually offers.
-- Normalizing this matters: coach_sports, student_sports, and
-- attendance_sessions all need to agree on exactly what
-- "Basketball" means, which a free-text field can't guarantee.
-- ------------------------------------------------------------
CREATE TABLE sports (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Admin identities have a separate table and ID space, so their OTPs
-- must not reference users.id.
CREATE TABLE admin_otp_verifications (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    admin_id   INT NOT NULL,
    purpose    ENUM('login', 'password_reset') NOT NULL,
    otp_hash   VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
    is_used    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE,
    INDEX idx_admin_otp_purpose (admin_id, purpose)
);

INSERT INTO sports (name) VALUES
    ('Football'), ('Basketball'), ('Volleyball'), ('Badminton'),
    ('Cricket'), ('Athletics'), ('Kickboxing');

-- ------------------------------------------------------------
-- 6. COACH_SPORTS
-- Admin assigns one or more sports to a coach. Many-to-many:
-- a coach can cover more than one sport, and a sport can have
-- more than one coach.
--
-- The app layer must enforce that coach_id belongs to a
-- role = 'coach' user (and ideally coach_status = 'approved')
-- before inserting — same pattern role_required() already uses
-- elsewhere: the DB doesn't cross-check role, the app does.
-- ------------------------------------------------------------
CREATE TABLE coach_sports (
    coach_id    INT NOT NULL,
    sport_id    INT NOT NULL,
    assigned_by INT NOT NULL,
    -- admins.id of the admin who made the assignment
    PRIMARY KEY (coach_id, sport_id),
    FOREIGN KEY (coach_id)    REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (sport_id)    REFERENCES sports(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES admins(id)
);

-- ------------------------------------------------------------
-- 7. STUDENT_SPORTS
-- Which sport(s) each student plays — self-selected by the
-- student (unlike coach_sports, there's no admin approval step
-- here). Many-to-many: a student can play more than one sport,
-- which is exactly why this couldn't be a single sport_id column
-- on student_profiles.
--
-- This is what lets a coach taking Basketball attendance see only
-- students who actually play Basketball, instead of every
-- verified student:
--
--   SELECT u.id, u.full_name
--   FROM student_sports ss
--   JOIN users u ON u.id = ss.student_id
--   WHERE ss.sport_id = <the session's sport_id>
-- ------------------------------------------------------------
CREATE TABLE student_sports (
    student_id INT NOT NULL,
    sport_id   INT NOT NULL,
    PRIMARY KEY (student_id, sport_id),
    FOREIGN KEY (student_id) REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (sport_id)   REFERENCES sports(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 8. PERFORMANCE RECORDS
-- ------------------------------------------------------------
CREATE TABLE physical_assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    coach_id INT NOT NULL,
    assessment_date DATE NOT NULL,
    speed DECIMAL(7,2),
    strength DECIMAL(7,2),
    endurance DECIMAL(7,2),
    agility DECIMAL(7,2),
    flexibility DECIMAL(7,2),
    reaction_time DECIMAL(7,2),
    overall_score DECIMAL(7,2),
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_assessment_student_date (student_id, assessment_date)
);

CREATE TABLE training_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    coach_id INT NOT NULL,
    sport_id INT NOT NULL,
    session_date DATE NOT NULL,
    training_type VARCHAR(100) NOT NULL,
    duration_minutes INT NOT NULL,
    description TEXT,
    performance_notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (sport_id) REFERENCES sports(id),
    INDEX idx_training_student_date (student_id, session_date)
);

CREATE TABLE goals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    coach_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    target_value DECIMAL(10,2),
    current_value DECIMAL(10,2),
    start_date DATE,
    target_date DATE,
    status ENUM('active', 'completed', 'cancelled') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_goals_student_status (student_id, status)
);

CREATE TABLE coach_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    coach_id INT NOT NULL,
    feedback TEXT NOT NULL,
    rating TINYINT UNSIGNED,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_feedback_student_created (student_id, created_at)
);

-- ------------------------------------------------------------
-- 9. ATTENDANCE_SESSIONS
-- One row per class/practice a coach runs — one coach, one
-- sport, one date. The UNIQUE key stops a coach from accidentally
-- logging two sessions for the same sport on the same day.
-- ------------------------------------------------------------
CREATE TABLE attendance_sessions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    coach_id     INT NOT NULL,
    sport_id     INT NOT NULL,
    session_date DATE NOT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (coach_id) REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (sport_id) REFERENCES sports(id) ON DELETE CASCADE,
    UNIQUE KEY uq_coach_sport_date (coach_id, sport_id, session_date),
    INDEX idx_session_date (session_date)
);

-- ------------------------------------------------------------
-- 10. ATTENDANCE_RECORDS
-- One row per student per session. Everything about the session
-- itself (who ran it, what sport, what date) lives once, on
-- attendance_sessions — not repeated on every student's row.
-- ------------------------------------------------------------
CREATE TABLE attendance_records (
    session_id INT NOT NULL,
    student_id INT NOT NULL,
    status     ENUM('present', 'absent') NOT NULL,
    PRIMARY KEY (session_id, student_id),
    FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id)               ON DELETE CASCADE,
    -- for "my attendance history" lookups (optimized for filtering by status)
    INDEX idx_attendance_student_status (student_id, status)
);

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
