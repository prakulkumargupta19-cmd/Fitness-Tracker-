-- Select the configured application database before applying this migration.

CREATE TABLE IF NOT EXISTS physical_assessments (
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

CREATE TABLE IF NOT EXISTS training_sessions (
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

CREATE TABLE IF NOT EXISTS goals (
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

CREATE TABLE IF NOT EXISTS coach_feedback (
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