-- ============================================
-- ATHLETE FITNESS TRACKER - DATABASE SCHEMA
-- Based on Professor's BBA-SM Fitness Tracker
-- SQLite Version (for rapid prototyping)
-- ============================================

-- Drop old tables if they exist (clean start)
DROP TABLE IF EXISTS coach_feedback;
DROP TABLE IF EXISTS goals;
DROP TABLE IF EXISTS training_sessions;
DROP TABLE IF EXISTS physical_assessments;
DROP TABLE IF EXISTS coach_athletes;
DROP TABLE IF EXISTS users;

-- ============================================
-- TABLE 1: users
-- Stores ALL login accounts: Admin, Coach, Player
-- ============================================
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'coach', 'player')),
    sport TEXT,
    contact_number TEXT UNIQUE,
    gender TEXT,
    date_of_birth TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE 2: coach_athletes
-- Links which coach trains which athlete
-- ============================================
CREATE TABLE coach_athletes (
    coach_id INTEGER NOT NULL,
    athlete_id INTEGER NOT NULL,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (coach_id, athlete_id),
    FOREIGN KEY (coach_id) REFERENCES users(id),
    FOREIGN KEY (athlete_id) REFERENCES users(id)
);

-- ============================================
-- TABLE 3: physical_assessments
-- Coach records athlete body metrics
-- ============================================
CREATE TABLE physical_assessments (
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
    FOREIGN KEY (athlete_id) REFERENCES users(id),
    FOREIGN KEY (coach_id) REFERENCES users(id)
);

-- ============================================
-- TABLE 4: training_sessions
-- Coach records workout/training data
-- ============================================
CREATE TABLE training_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,
    session_date TEXT NOT NULL,
    sport_type TEXT,
    duration_minutes INTEGER,
    intensity_level TEXT CHECK(intensity_level IN ('Low', 'Medium', 'High')),
    rpe INTEGER CHECK(rpe BETWEEN 1 AND 10),
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
    attendance TEXT CHECK(attendance IN ('Present', 'Absent')),
    completion_pct INTEGER,
    missed_session_reason TEXT,
    session_observation TEXT,
    technical_feedback TEXT,
    training_recommendation TEXT,
    next_session_focus TEXT,
    FOREIGN KEY (athlete_id) REFERENCES users(id),
    FOREIGN KEY (coach_id) REFERENCES users(id)
);

-- ============================================
-- TABLE 5: goals
-- Coach sets goals, player tracks progress
-- ============================================
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,
    goal_title TEXT NOT NULL,
    goal_type TEXT CHECK(goal_type IN ('Skill', 'Fitness', 'Competition', 'Recovery')),
    goal_description TEXT,
    baseline_value TEXT,
    target_value TEXT,
    current_value TEXT,
    progress_pct INTEGER,
    goal_status TEXT CHECK(goal_status IN ('Not Started', 'In Progress', 'Achieved', 'Delayed')),
    start_date TEXT,
    target_date TEXT,
    review_date TEXT,
    injury_status TEXT,
    injury_area TEXT,
    expected_recovery_date TEXT,
    current_limitation TEXT,
    training_restriction TEXT,
    rehabilitation_exercise TEXT,
    recovery_progress_pct INTEGER,
    self_rating INTEGER CHECK(self_rating BETWEEN 1 AND 10),
    confidence_level TEXT,
    effort_level TEXT,
    challenges_faced TEXT,
    goal_achieved_date TEXT,
    final_result TEXT,
    next_goal TEXT,
    FOREIGN KEY (athlete_id) REFERENCES users(id),
    FOREIGN KEY (coach_id) REFERENCES users(id)
);

-- ============================================
-- TABLE 6: coach_feedback
-- Coach writes feedback, player reads it
-- ============================================
CREATE TABLE coach_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,
    feedback_date TEXT,
    session_reference TEXT,
    technical_strengths TEXT,
    technical_corrections TEXT,
    skill_execution_rating INTEGER CHECK(skill_execution_rating BETWEEN 1 AND 10),
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
    overall_rating INTEGER CHECK(overall_rating BETWEEN 1 AND 10),
    key_strength TEXT,
    key_improvement_area TEXT,
    performance_summary TEXT,
    immediate_action TEXT,
    home_practice_task TEXT,
    next_session_focus TEXT,
    follow_up_date TEXT,
    FOREIGN KEY (athlete_id) REFERENCES users(id),
    FOREIGN KEY (coach_id) REFERENCES users(id)
);