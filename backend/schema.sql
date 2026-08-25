-- ============================================================
-- ATHLETE TRACKER - DATABASE SCHEMA
-- ============================================================
-- SQLite database schema for:
--   1. User authentication
--   2. Email OTP workflows
--   3. Coach-athlete assignments
--   4. Physical assessments
--   5. Training sessions
--   6. Daily performance
--   7. Goals
--   8. Coach feedback
--
-- IMPORTANT:
-- This file is intentionally SAFE to run multiple times.
-- It uses CREATE TABLE IF NOT EXISTS and does NOT delete data.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 0
        CHECK (email_verified IN (0, 1)),
    role TEXT NOT NULL
        CHECK (role IN ('admin', 'coach', 'player')),
    sport TEXT,
    contact_number TEXT UNIQUE,
    gender TEXT,
    date_of_birth TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. COACH <-> ATHLETE ASSIGNMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS coach_athletes (
    coach_id INTEGER NOT NULL,
    athlete_id INTEGER NOT NULL,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (coach_id, athlete_id),

    FOREIGN KEY (coach_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (athlete_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- 3. PHYSICAL ASSESSMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS physical_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,

    assessment_date TEXT NOT NULL,

    height_cm REAL,
    weight_kg REAL,
    bmi REAL,
    body_fat_pct REAL,

    waist_circumference REAL,
    hip_circumference REAL,
    chest_circumference REAL,
    thigh_circumference REAL,
    arm_circumference REAL,

    flexibility_score TEXT,
    mobility_score TEXT,
    posture_assessment TEXT,

    injury_status TEXT,
    injury_notes TEXT,
    medical_restrictions TEXT,

    previous_measurement TEXT,
    current_measurement TEXT,
    change_value TEXT,

    assessment_remarks TEXT,
    next_assessment_date TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (coach_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- 4. TRAINING SESSIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS training_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,

    session_date TEXT NOT NULL,
    sport_type TEXT,

    duration_minutes INTEGER,

    intensity_level TEXT
        CHECK (intensity_level IN ('Low', 'Medium', 'High')),

    rpe INTEGER
        CHECK (rpe BETWEEN 1 AND 10),

    exercises_performed TEXT,
    sets_reps_weights TEXT,

    squat_load REAL,
    deadlift_load REAL,
    bench_press_load REAL,

    pushups_count INTEGER,
    pullups_count INTEGER,
    plank_time TEXT,

    running_distance REAL,
    sprint_time TEXT,
    shuttle_run_time TEXT,
    agility_test_score TEXT,

    vertical_jump_height REAL,
    broad_jump_distance REAL,

    sleep_hours REAL,
    fatigue_level TEXT,
    muscle_soreness_level TEXT,

    attendance TEXT
        CHECK (attendance IN ('Present', 'Absent')),

    completion_pct INTEGER
        CHECK (completion_pct BETWEEN 0 AND 100),

    missed_session_reason TEXT,
    session_observation TEXT,
    technical_feedback TEXT,
    training_recommendation TEXT,
    next_session_focus TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (coach_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- 5. DAILY PERFORMANCE RECORDS
-- ============================================================
CREATE TABLE IF NOT EXISTS performance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    session_id INTEGER,

    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,

    sport TEXT NOT NULL,
    performance_date TEXT NOT NULL,

    passing_accuracy REAL,
    dribbling_control REAL,
    shooting_accuracy REAL,
    ball_control REAL,
    speed_agility REAL,
    defensive_positioning REAL,
    team_coordination REAL,

    effort_level REAL,
    discipline REAL,
    endurance_stamina REAL,

    daily_sport_score REAL,
    coach_remark TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id)
        REFERENCES training_sessions(id)
        ON DELETE SET NULL,

    FOREIGN KEY (athlete_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (coach_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- 6. GOALS
-- ============================================================
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,

    goal_title TEXT NOT NULL,

    goal_type TEXT
        CHECK (
            goal_type IN
            ('Skill', 'Fitness', 'Competition', 'Recovery')
        ),

    goal_description TEXT,

    baseline_value TEXT,
    target_value TEXT,
    current_value TEXT,

    progress_pct INTEGER
        CHECK (progress_pct BETWEEN 0 AND 100),

    goal_status TEXT
        CHECK (
            goal_status IN
            ('Not Started', 'In Progress', 'Achieved', 'Delayed')
        ),

    start_date TEXT,
    target_date TEXT,
    review_date TEXT,

    injury_status TEXT,
    injury_area TEXT,
    expected_recovery_date TEXT,

    current_limitation TEXT,
    training_restriction TEXT,
    rehabilitation_exercise TEXT,

    recovery_progress_pct INTEGER
        CHECK (recovery_progress_pct BETWEEN 0 AND 100),

    self_rating INTEGER
        CHECK (self_rating BETWEEN 1 AND 10),

    confidence_level TEXT,
    effort_level TEXT,
    challenges_faced TEXT,

    goal_achieved_date TEXT,
    final_result TEXT,
    next_goal TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (coach_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- 7. COACH FEEDBACK
-- ============================================================
CREATE TABLE IF NOT EXISTS coach_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,

    feedback_date TEXT,
    session_reference TEXT,

    technical_strengths TEXT,
    technical_corrections TEXT,

    skill_execution_rating INTEGER
        CHECK (skill_execution_rating BETWEEN 1 AND 10),

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

    overall_rating INTEGER
        CHECK (overall_rating BETWEEN 1 AND 10),

    key_strength TEXT,
    key_improvement_area TEXT,
    performance_summary TEXT,

    immediate_action TEXT,
    home_practice_task TEXT,
    next_session_focus TEXT,
    follow_up_date TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (athlete_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (coach_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- 8. OTP REQUESTS
-- ============================================================
-- This table is required by the current Flask authentication
-- backend. It supports:
--   signup
--   admin_login
--   password_reset
--
-- otp_hash stores the HASH, not the real OTP.
-- ============================================================
CREATE TABLE IF NOT EXISTS otp_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    email TEXT NOT NULL,
    purpose TEXT NOT NULL,

    otp_hash TEXT NOT NULL,

    -- Signup stores temporary registration data here.
    -- Login/reset stores the related user ID here.
    payload TEXT,

    expires_at TEXT NOT NULL,

    attempts INTEGER NOT NULL DEFAULT 0,

    verified INTEGER NOT NULL DEFAULT 0
        CHECK (verified IN (0, 1)),

    used INTEGER NOT NULL DEFAULT 0
        CHECK (used IN (0, 1)),

    created_at TEXT NOT NULL
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_users_email
ON users(email);

CREATE INDEX IF NOT EXISTS idx_users_role
ON users(role);

CREATE INDEX IF NOT EXISTS idx_coach_athletes_coach
ON coach_athletes(coach_id);

CREATE INDEX IF NOT EXISTS idx_coach_athletes_athlete
ON coach_athletes(athlete_id);

CREATE INDEX IF NOT EXISTS idx_assessments_athlete
ON physical_assessments(athlete_id);

CREATE INDEX IF NOT EXISTS idx_assessments_coach
ON physical_assessments(coach_id);

CREATE INDEX IF NOT EXISTS idx_sessions_athlete
ON training_sessions(athlete_id);

CREATE INDEX IF NOT EXISTS idx_sessions_coach
ON training_sessions(coach_id);

CREATE INDEX IF NOT EXISTS idx_sessions_date
ON training_sessions(session_date);

CREATE INDEX IF NOT EXISTS idx_performance_athlete
ON performance_records(athlete_id);

CREATE INDEX IF NOT EXISTS idx_performance_coach
ON performance_records(coach_id);

CREATE INDEX IF NOT EXISTS idx_performance_date
ON performance_records(performance_date);

CREATE INDEX IF NOT EXISTS idx_goals_athlete
ON goals(athlete_id);

CREATE INDEX IF NOT EXISTS idx_goals_coach
ON goals(coach_id);

CREATE INDEX IF NOT EXISTS idx_feedback_athlete
ON coach_feedback(athlete_id);

CREATE INDEX IF NOT EXISTS idx_feedback_coach
ON coach_feedback(coach_id);

CREATE INDEX IF NOT EXISTS idx_otp_requests_lookup
ON otp_requests(email, purpose, used);

-- ============================================================
-- END OF SCHEMA
-- ============================================================
