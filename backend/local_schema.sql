-- SQLite schema used by the local-only development mode.
-- This is intentionally additive and is safe to run on every startup.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    contact_number TEXT,
    is_verified BOOLEAN NOT NULL DEFAULT 1,
    coach_status TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    coach_decided_at TIMESTAMP,
    coach_decision_reason TEXT,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON users (LOWER(email));

CREATE TABLE IF NOT EXISTS student_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    date_of_birth DATE NOT NULL,
    emergency_contact TEXT NOT NULL,
    height_cm REAL,
    weight_kg REAL,
    goal TEXT,
    sport_activity TEXT,
    department TEXT,
    student_number TEXT,
    semester TEXT,
    gender TEXT,
    bio TEXT,
    blood_group TEXT,
    medical_history TEXT,
    address TEXT,
    parent_name TEXT,
    parent_phone TEXT,
    parent_address TEXT,
    passport_id TEXT,
    photo_path TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_student_profiles_student_number
    ON student_profiles(student_number) WHERE student_number IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_student_profiles_passport_id
    ON student_profiles(passport_id) WHERE passport_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS otp_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    is_used BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    contact_number TEXT,
    otp_hash TEXT NOT NULL,
    otp_expires_at TIMESTAMP NOT NULL,
    otp_attempts INTEGER NOT NULL DEFAULT 0,
    otp_sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    otp_send_count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending_verification',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    decision_at TIMESTAMP,
    decision_reason TEXT
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_admins_email_lower ON admins (LOWER(email));

CREATE TABLE IF NOT EXISTS sports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    activity_type TEXT NOT NULL DEFAULT 'Activity',
    venue TEXT,
    cover_path TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1
);

INSERT OR IGNORE INTO sports(name) VALUES
    ('Football'), ('Basketball'), ('Volleyball'), ('Badminton'),
    ('Cricket'), ('Athletics'), ('Kickboxing');

CREATE TABLE IF NOT EXISTS admin_otp_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    is_used BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coach_sports (
    coach_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sport_id INTEGER NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
    assigned_by INTEGER NOT NULL REFERENCES admins(id),
    PRIMARY KEY(coach_id, sport_id)
);

CREATE TABLE IF NOT EXISTS student_sports (
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sport_id INTEGER NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
    PRIMARY KEY(student_id, sport_id)
);

CREATE TABLE IF NOT EXISTS physical_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coach_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL,
    speed REAL, strength REAL, endurance REAL, agility REAL,
    flexibility REAL, reaction_time REAL, overall_score REAL, notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS training_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coach_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sport_id INTEGER NOT NULL REFERENCES sports(id),
    session_date DATE NOT NULL,
    training_type TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    description TEXT,
    performance_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coach_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    target_value REAL,
    current_value REAL,
    start_date DATE,
    target_date DATE,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coach_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coach_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feedback TEXT NOT NULL,
    rating INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coach_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sport_id INTEGER NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(coach_id, sport_id, session_date)
);

CREATE TABLE IF NOT EXISTS attendance_records (
    session_id INTEGER NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    session_date DATE NOT NULL,
    marked_by_role TEXT, marked_by_id INTEGER,
    updated_by_role TEXT, updated_by_id INTEGER,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(session_id, student_id)
);

CREATE TABLE IF NOT EXISTS coach_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    designation TEXT, photo_path TEXT, bio TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS programmes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, sport_id INTEGER NOT NULL REFERENCES sports(id),
    coach_id INTEGER REFERENCES users(id), schedule TEXT, venue TEXT,
    assigned_dates INTEGER NOT NULL DEFAULT 5,
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    programme_id INTEGER NOT NULL REFERENCES programmes(id) ON DELETE CASCADE,
    attendance INTEGER NOT NULL DEFAULT 0, total_sessions INTEGER NOT NULL DEFAULT 0,
    joined_on DATE NOT NULL DEFAULT CURRENT_DATE,
    status TEXT NOT NULL DEFAULT 'Active', UNIQUE(student_id, programme_id)
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    session_date DATE NOT NULL, present BOOLEAN NOT NULL DEFAULT 1,
    UNIQUE(enrollment_id, session_date)
);

CREATE TABLE IF NOT EXISTS daily_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    coach_id INTEGER REFERENCES users(id), session_date DATE NOT NULL,
    attendance_status TEXT NOT NULL DEFAULT 'Present', attendance_score INTEGER,
    skill_development INTEGER, passing INTEGER, dribbling INTEGER, shooting INTEGER,
    vision INTEGER, fitness INTEGER, overall_performance INTEGER, remarks TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(enrollment_id, session_date)
);

CREATE TABLE IF NOT EXISTS assessment_metric_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL REFERENCES daily_assessments(id) ON DELETE CASCADE,
    metric_key TEXT NOT NULL, metric_label TEXT NOT NULL, score INTEGER NOT NULL,
    UNIQUE(assessment_id, metric_key)
);

CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, sport_id INTEGER NOT NULL REFERENCES sports(id),
    start_date DATE NOT NULL, end_date DATE, venue TEXT,
    status TEXT NOT NULL DEFAULT 'Upcoming', description TEXT, poster_path TEXT,
    registration_open BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_name TEXT, registration_status TEXT NOT NULL DEFAULT 'Registered',
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, student_id)
);

CREATE TABLE IF NOT EXISTS dashboard_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, description TEXT NOT NULL,
    event_date TIMESTAMP NOT NULL, venue TEXT,
    created_by INTEGER REFERENCES users(id),
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dashboard_event_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES dashboard_events(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL, email TEXT NOT NULL, contact_number TEXT,
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, student_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    round_name TEXT, match_date TIMESTAMP, venue TEXT,
    category TEXT NOT NULL DEFAULT 'Boys', team_a TEXT NOT NULL, team_b TEXT NOT NULL,
    score_a TEXT NOT NULL DEFAULT '0', score_b TEXT NOT NULL DEFAULT '0',
    status TEXT NOT NULL DEFAULT 'Scheduled', photo_path TEXT, live_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL, sport_id INTEGER REFERENCES sports(id), level TEXT,
    achievement_year TEXT, description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL, issuer TEXT, issue_date DATE, certificate_no TEXT,
    file_path TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER REFERENCES tournaments(id), media_type TEXT NOT NULL DEFAULT 'photo',
    file_path TEXT NOT NULL, caption TEXT, uploaded_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS match_live_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    stat_key TEXT NOT NULL, stat_label TEXT NOT NULL, stat_value TEXT,
    UNIQUE(match_id, stat_key)
);

CREATE TABLE IF NOT EXISTS event_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES users(id), name TEXT NOT NULL, department TEXT NOT NULL,
    category TEXT NOT NULL, year TEXT NOT NULL, imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, name, department, category, year)
);

CREATE TABLE IF NOT EXISTS match_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    side TEXT NOT NULL, student_name TEXT NOT NULL, department TEXT, student_id INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tournament_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    category TEXT NOT NULL, winner TEXT NOT NULL, runner_up TEXT NOT NULL, notes TEXT,
    UNIQUE(tournament_id, category)
);

CREATE TABLE IF NOT EXISTS draw_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    category TEXT NOT NULL, format_type TEXT NOT NULL, file_path TEXT NOT NULL,
    uploaded_by INTEGER REFERENCES users(id), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, message TEXT NOT NULL, image_path TEXT,
    created_by INTEGER REFERENCES users(id), active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS certificate_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    certificate_type TEXT NOT NULL, file_path TEXT NOT NULL,
    uploaded_by INTEGER REFERENCES users(id), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, certificate_type)
);

CREATE TABLE IF NOT EXISTS generated_certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    participant_id INTEGER REFERENCES event_participants(id), student_id INTEGER REFERENCES users(id),
    certificate_type TEXT NOT NULL, recipient_name TEXT NOT NULL, achievement TEXT,
    certificate_no TEXT NOT NULL UNIQUE, file_path TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS facility_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sport_id INTEGER NOT NULL REFERENCES sports(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL, caption TEXT, uploaded_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coaching_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    programme_id INTEGER NOT NULL REFERENCES programmes(id) ON DELETE CASCADE,
    session_date DATE NOT NULL, start_time TIME NOT NULL, end_time TIME NOT NULL,
    venue TEXT, notes TEXT, status TEXT NOT NULL DEFAULT 'Scheduled',
    session_type TEXT NOT NULL DEFAULT 'practice' CHECK (session_type IN ('practice', 'assessment')),
    created_by INTEGER REFERENCES users(id), updated_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coaching_session_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    programme_id INTEGER NOT NULL REFERENCES programmes(id) ON DELETE CASCADE,
    coach_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_date DATE NOT NULL, start_time TIME NOT NULL, end_time TIME NOT NULL,
    venue TEXT, notes TEXT, session_type TEXT NOT NULL CHECK (session_type IN ('practice', 'assessment')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by INTEGER REFERENCES users(id), reviewed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Fit-Track relationship indexes. These are additive and do not touch the
-- users/admins/OTP tables used by authentication.
CREATE INDEX IF NOT EXISTS idx_fit_track_enrollments_student
    ON enrollments(student_id, status, programme_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_enrollments_programme
    ON enrollments(programme_id, status, student_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_attendance_enrollment_date
    ON attendance(enrollment_id, session_date);
CREATE INDEX IF NOT EXISTS idx_fit_track_assessments_enrollment_date
    ON daily_assessments(enrollment_id, session_date);
CREATE INDEX IF NOT EXISTS idx_fit_track_assessments_coach
    ON daily_assessments(coach_id, session_date);
CREATE INDEX IF NOT EXISTS idx_fit_track_registrations_student
    ON registrations(student_id, tournament_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_participants_student
    ON event_participants(student_id, tournament_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_match_players_match_side
    ON match_players(match_id, side, student_name);
CREATE INDEX IF NOT EXISTS idx_fit_track_achievements_student
    ON achievements(student_id, achievement_year);
CREATE INDEX IF NOT EXISTS idx_fit_track_certificates_student
    ON certificates(student_id, issue_date);
CREATE INDEX IF NOT EXISTS idx_fit_track_generated_certificates_student
    ON generated_certificates(student_id, created_at);
CREATE INDEX IF NOT EXISTS idx_fit_track_facility_media_sport
    ON facility_media(sport_id, created_at);

-- SQLite uses triggers for cross-table integrity rules that PostgreSQL adds
-- through constraints/functions. New and changed rows are checked without
-- rebuilding existing tables, preserving local databases and auth records.
CREATE TRIGGER IF NOT EXISTS trg_fit_track_programmes_coach_role_insert
BEFORE INSERT ON programmes
WHEN NEW.coach_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.coach_id), '') <> 'coach'
BEGIN
    SELECT RAISE(ABORT, 'programme coach_id must reference a coach');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_programmes_coach_role_update
BEFORE UPDATE OF coach_id ON programmes
WHEN NEW.coach_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.coach_id), '') <> 'coach'
BEGIN
    SELECT RAISE(ABORT, 'programme coach_id must reference a coach');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_enrollments_student_role_insert
BEFORE INSERT ON enrollments
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'enrollment student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_enrollments_student_role_update
BEFORE UPDATE OF student_id ON enrollments
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'enrollment student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_registrations_student_role_insert
BEFORE INSERT ON registrations
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'registration student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_registrations_student_role_update
BEFORE UPDATE OF student_id ON registrations
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'registration student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_assessments_coach_role_insert
BEFORE INSERT ON daily_assessments
WHEN NEW.coach_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.coach_id), '') <> 'coach'
BEGIN
    SELECT RAISE(ABORT, 'assessment coach_id must reference a coach');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_assessments_coach_role_update
BEFORE UPDATE OF coach_id ON daily_assessments
WHEN NEW.coach_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.coach_id), '') <> 'coach'
BEGIN
    SELECT RAISE(ABORT, 'assessment coach_id must reference a coach');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_participants_student_role_insert
BEFORE INSERT ON event_participants
WHEN NEW.student_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'participant student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_participants_student_role_update
BEFORE UPDATE OF student_id ON event_participants
WHEN NEW.student_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'participant student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_players_student_role_insert
BEFORE INSERT ON match_players
WHEN NEW.student_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'match player student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_players_student_role_update
BEFORE UPDATE OF student_id ON match_players
WHEN NEW.student_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'match player student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_achievements_student_role_insert
BEFORE INSERT ON achievements
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'achievement student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_achievements_student_role_update
BEFORE UPDATE OF student_id ON achievements
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'achievement student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_certificates_student_role_insert
BEFORE INSERT ON certificates
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'certificate student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_certificates_student_role_update
BEFORE UPDATE OF student_id ON certificates
WHEN COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'certificate student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_generated_certificates_student_role_insert
BEFORE INSERT ON generated_certificates
WHEN NEW.student_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'generated certificate student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_generated_certificates_student_role_update
BEFORE UPDATE OF student_id ON generated_certificates
WHEN NEW.student_id IS NOT NULL AND COALESCE((SELECT role FROM users WHERE id = NEW.student_id), '') <> 'student'
BEGIN
    SELECT RAISE(ABORT, 'generated certificate student_id must reference a student');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_category_insert
BEFORE INSERT ON matches
WHEN NEW.category NOT IN ('Boys', 'Girls')
BEGIN
    SELECT RAISE(ABORT, 'match category must be Boys or Girls');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_category_update
BEFORE UPDATE OF category ON matches
WHEN NEW.category NOT IN ('Boys', 'Girls')
BEGIN
    SELECT RAISE(ABORT, 'match category must be Boys or Girls');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_participant_category_insert
BEFORE INSERT ON event_participants
WHEN NEW.category NOT IN ('Boys', 'Girls')
BEGIN
    SELECT RAISE(ABORT, 'participant category must be Boys or Girls');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_participant_category_update
BEFORE UPDATE OF category ON event_participants
WHEN NEW.category NOT IN ('Boys', 'Girls')
BEGIN
    SELECT RAISE(ABORT, 'participant category must be Boys or Girls');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_tournament_dates_insert
BEFORE INSERT ON tournaments
WHEN NEW.end_date IS NOT NULL AND NEW.end_date < NEW.start_date
BEGIN
    SELECT RAISE(ABORT, 'tournament end_date cannot be before start_date');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_tournament_dates_update
BEFORE UPDATE OF start_date, end_date ON tournaments
WHEN NEW.end_date IS NOT NULL AND NEW.end_date < NEW.start_date
BEGIN
    SELECT RAISE(ABORT, 'tournament end_date cannot be before start_date');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_session_status_insert
BEFORE INSERT ON coaching_sessions
WHEN NEW.status NOT IN ('Scheduled', 'Rescheduled', 'Cancelled', 'Completed')
  OR NEW.end_time <= NEW.start_time
BEGIN
    SELECT RAISE(ABORT, 'invalid coaching session status or time range');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_session_status_update
BEFORE UPDATE OF status, start_time, end_time ON coaching_sessions
WHEN NEW.status NOT IN ('Scheduled', 'Rescheduled', 'Cancelled', 'Completed')
  OR NEW.end_time <= NEW.start_time
BEGIN
    SELECT RAISE(ABORT, 'invalid coaching session status or time range');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_players_side_insert
BEFORE INSERT ON match_players
WHEN NEW.side NOT IN ('A', 'B')
BEGIN
    SELECT RAISE(ABORT, 'match player side must be A or B');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_players_side_update
BEFORE UPDATE OF side ON match_players
WHEN NEW.side NOT IN ('A', 'B')
BEGIN
    SELECT RAISE(ABORT, 'match player side must be A or B');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_squad_limit_insert
BEFORE INSERT ON match_players
WHEN (SELECT COUNT(*) FROM match_players WHERE match_id = NEW.match_id AND side = NEW.side) >= 15
BEGIN
    SELECT RAISE(ABORT, 'a fixture side may contain at most 15 players');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_match_squad_limit_update
BEFORE UPDATE OF match_id, side ON match_players
WHEN (SELECT COUNT(*) FROM match_players WHERE match_id = NEW.match_id AND side = NEW.side AND id <> OLD.id) >= 15
BEGIN
    SELECT RAISE(ABORT, 'a fixture side may contain at most 15 players');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_message_not_self_insert
BEFORE INSERT ON messages
WHEN NEW.sender_user_id = NEW.receiver_user_id
BEGIN
    SELECT RAISE(ABORT, 'messages cannot be sent to yourself');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_message_not_self_update
BEFORE UPDATE OF sender_user_id, receiver_user_id ON messages
WHEN NEW.sender_user_id = NEW.receiver_user_id
BEGIN
    SELECT RAISE(ABORT, 'messages cannot be sent to yourself');
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_programmes_updated_at
AFTER UPDATE ON programmes
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE programmes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_assessments_updated_at
AFTER UPDATE ON daily_assessments
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE daily_assessments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_tournaments_updated_at
AFTER UPDATE ON tournaments
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tournaments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_matches_updated_at
AFTER UPDATE ON matches
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE matches SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_fit_track_coaching_sessions_updated_at
AFTER UPDATE ON coaching_sessions
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE coaching_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
