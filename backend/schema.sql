-- ============================================
-- ATHLETE FITNESS TRACKER — UNIFIED SCHEMA
-- MySQL (single source of truth)
-- ============================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS coach_feedback;
DROP TABLE IF EXISTS goals;
DROP TABLE IF EXISTS training_sessions;
DROP TABLE IF EXISTS physical_assessments;
DROP TABLE IF EXISTS coach_athletes;
DROP TABLE IF EXISTS otp_requests;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- TABLE 1: users
-- ============================================
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email_verified TINYINT DEFAULT 0,
    role ENUM('admin', 'coach', 'player') NOT NULL,
    sport VARCHAR(100),
    contact_number VARCHAR(20) UNIQUE,
    gender VARCHAR(20),
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- TABLE 2: otp_requests
-- ============================================
CREATE TABLE otp_requests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    purpose VARCHAR(50) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    payload TEXT,
    expires_at DATETIME NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    verified TINYINT NOT NULL DEFAULT 0,
    used TINYINT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB;
CREATE INDEX idx_otp_requests_lookup ON otp_requests(email, purpose, used);

-- ============================================
-- TABLE 3: coach_athletes
-- ============================================
CREATE TABLE coach_athletes (
    coach_id INT NOT NULL,
    athlete_id INT NOT NULL,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (coach_id, athlete_id),
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (athlete_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- TABLE 4: physical_assessments
-- ============================================
CREATE TABLE physical_assessments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    athlete_id INT NOT NULL,
    coach_id INT NOT NULL,
    assessment_date DATE NOT NULL,
    height_cm FLOAT,
    weight_kg FLOAT,
    bmi FLOAT,
    body_fat_pct FLOAT,
    waist_circumference FLOAT,
    hip_circumference FLOAT,
    chest_circumference FLOAT,
    thigh_circumference FLOAT,
    arm_circumference FLOAT,
    flexibility_score VARCHAR(50),
    mobility_score VARCHAR(50),
    posture_assessment VARCHAR(255),
    injury_status VARCHAR(255),
    injury_notes TEXT,
    medical_restrictions TEXT,
    previous_measurement VARCHAR(50),
    current_measurement VARCHAR(50),
    change_value VARCHAR(50),
    assessment_remarks TEXT,
    next_assessment_date DATE,
    FOREIGN KEY (athlete_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- TABLE 5: training_sessions
-- ============================================
CREATE TABLE training_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    athlete_id INT NOT NULL,
    coach_id INT NOT NULL,
    session_date DATE NOT NULL,
    sport_type VARCHAR(100),
    duration_minutes INT,
    intensity_level ENUM('Low', 'Medium', 'High'),
    rpe INT CHECK(rpe BETWEEN 1 AND 10),
    exercises_performed TEXT,
    sets_reps_weights TEXT,
    squat_load FLOAT,
    deadlift_load FLOAT,
    bench_press_load FLOAT,
    pushups_count INT,
    pullups_count INT,
    plank_time VARCHAR(50),
    running_distance FLOAT,
    sprint_time VARCHAR(50),
    shuttle_run_time VARCHAR(50),
    agility_test_score VARCHAR(50),
    vertical_jump_height FLOAT,
    broad_jump_distance FLOAT,
    sleep_hours FLOAT,
    fatigue_level VARCHAR(50),
    muscle_soreness_level VARCHAR(50),
    attendance ENUM('Present', 'Absent'),
    completion_pct INT,
    missed_session_reason TEXT,
    session_observation TEXT,
    technical_feedback TEXT,
    training_recommendation TEXT,
    next_session_focus TEXT,
    FOREIGN KEY (athlete_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- TABLE 6: goals
-- ============================================
CREATE TABLE goals (
    id INT PRIMARY KEY AUTO_INCREMENT,
    athlete_id INT NOT NULL,
    coach_id INT NOT NULL,
    goal_title VARCHAR(255) NOT NULL,
    goal_type ENUM('Skill', 'Fitness', 'Competition', 'Recovery'),
    goal_description TEXT,
    baseline_value VARCHAR(255),
    target_value VARCHAR(255),
    current_value VARCHAR(255),
    progress_pct INT,
    goal_status ENUM('Not Started', 'In Progress', 'Achieved', 'Delayed'),
    start_date DATE,
    target_date DATE,
    review_date DATE,
    injury_status VARCHAR(255),
    injury_area VARCHAR(255),
    expected_recovery_date DATE,
    current_limitation TEXT,
    training_restriction TEXT,
    rehabilitation_exercise TEXT,
    recovery_progress_pct INT,
    self_rating INT CHECK(self_rating BETWEEN 1 AND 10),
    confidence_level VARCHAR(50),
    effort_level VARCHAR(50),
    challenges_faced TEXT,
    goal_achieved_date DATE,
    final_result TEXT,
    next_goal TEXT,
    FOREIGN KEY (athlete_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- TABLE 7: coach_feedback
-- ============================================
CREATE TABLE coach_feedback (
    id INT PRIMARY KEY AUTO_INCREMENT,
    athlete_id INT NOT NULL,
    coach_id INT NOT NULL,
    feedback_date DATE,
    session_reference VARCHAR(255),
    technical_strengths TEXT,
    technical_corrections TEXT,
    skill_execution_rating INT CHECK(skill_execution_rating BETWEEN 1 AND 10),
    fitness_observation TEXT,
    endurance_observation TEXT,
    strength_observation TEXT,
    flexibility_mobility_observation TEXT,
    decision_making TEXT,
    positioning TEXT,
    game_awareness TEXT,
    discipline TEXT,
    communication TEXT,
    confidence TEXT,
    focus_concentration TEXT,
    teamwork TEXT,
    overall_rating INT CHECK(overall_rating BETWEEN 1 AND 10),
    key_strength TEXT,
    key_improvement_area TEXT,
    performance_summary TEXT,
    immediate_action TEXT,
    home_practice_task TEXT,
    next_session_focus TEXT,
    follow_up_date DATE,
    FOREIGN KEY (athlete_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coach_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;