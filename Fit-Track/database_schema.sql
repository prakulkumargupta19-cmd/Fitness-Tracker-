-- Inspiria Digital Sports Passport V7
-- Reference schema. app.py also performs safe column upgrades and seed data.

CREATE TABLE IF NOT EXISTS sports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        activity_type TEXT NOT NULL DEFAULT 'Activity',
        venue TEXT,
        is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        student_id TEXT UNIQUE NOT NULL,
        email TEXT,
        phone TEXT,
        department TEXT,
        semester TEXT,
        sports TEXT,
        bio TEXT,
        emergency_contact TEXT,
        blood_group TEXT,
        medical_history TEXT,
        address TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        parent_address TEXT,
        passport_id TEXT,
        photo_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS coaches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sport TEXT NOT NULL,
        email TEXT,
        username TEXT UNIQUE,
        photo_path TEXT
    );
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        designation TEXT,
        role TEXT NOT NULL,
        coach_id INTEGER,
        student_id INTEGER,
        active INTEGER DEFAULT 1,
        FOREIGN KEY(coach_id) REFERENCES coaches(id) ON DELETE SET NULL,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS programmes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sport TEXT NOT NULL,
        coach_id INTEGER,
        schedule TEXT,
        venue TEXT,
        active INTEGER DEFAULT 1,
        FOREIGN KEY(coach_id) REFERENCES coaches(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        programme_id INTEGER NOT NULL,
        attendance INTEGER DEFAULT 0,
        total_sessions INTEGER DEFAULT 0,
        joined_on TEXT DEFAULT CURRENT_DATE,
        status TEXT DEFAULT 'Active',
        UNIQUE(student_id, programme_id),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY(programme_id) REFERENCES programmes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER NOT NULL,
        session_date TEXT NOT NULL,
        present INTEGER DEFAULT 1,
        UNIQUE(enrollment_id, session_date),
        FOREIGN KEY(enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS daily_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER NOT NULL,
        coach_id INTEGER,
        session_date TEXT NOT NULL,
        attendance_status TEXT DEFAULT 'Present',
        attendance_score INTEGER,
        skill_development INTEGER,
        passing INTEGER,
        dribbling INTEGER,
        shooting INTEGER,
        vision INTEGER,
        fitness INTEGER,
        overall_performance INTEGER,
        remarks TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(enrollment_id, session_date),
        FOREIGN KEY(enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE,
        FOREIGN KEY(coach_id) REFERENCES coaches(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS assessment_metric_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL,
        metric_key TEXT NOT NULL,
        metric_label TEXT NOT NULL,
        score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 10),
        UNIQUE(assessment_id, metric_key),
        FOREIGN KEY(assessment_id) REFERENCES daily_assessments(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sport TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        venue TEXT,
        status TEXT DEFAULT 'Upcoming',
        description TEXT,
        poster_path TEXT,
        registration_open INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        team_name TEXT,
        name TEXT,
        department TEXT,
        semester TEXT,
        phone TEXT,
        emergency_contact TEXT,
        blood_group TEXT,
        medical_history TEXT,
        registration_status TEXT DEFAULT 'Registered',
        registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tournament_id, student_id),
        FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL,
        round_name TEXT,
        match_date TEXT,
        venue TEXT,
        team_a TEXT NOT NULL,
        team_b TEXT NOT NULL,
        score_a TEXT DEFAULT '0',
        score_b TEXT DEFAULT '0',
        status TEXT DEFAULT 'Scheduled',
        photo_path TEXT,
        live_note TEXT,
        FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        sport TEXT,
        level TEXT,
        year TEXT,
        description TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        issuer TEXT,
        issue_date TEXT,
        certificate_no TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_user_id INTEGER NOT NULL,
        receiver_user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        read_at TEXT,
        FOREIGN KEY(sender_user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(receiver_user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS event_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER,
        media_type TEXT NOT NULL DEFAULT 'photo',
        file_path TEXT NOT NULL,
        caption TEXT,
        uploaded_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE SET NULL,
        FOREIGN KEY(uploaded_by) REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS match_live_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        stat_key TEXT NOT NULL,
        stat_label TEXT NOT NULL,
        stat_value TEXT,
        UNIQUE(match_id, stat_key),
        FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE
    );

-- V6 safe upgrade columns applied by app.py:
-- students.passport_id TEXT UNIQUE (via filtered unique index)
-- students.photo_path TEXT
-- coaches.photo_path TEXT
-- matches.category TEXT DEFAULT 'Boys'
-- sports.cover_path TEXT
-- announcements.image_path TEXT

CREATE TABLE IF NOT EXISTS event_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    student_id INTEGER,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    category TEXT NOT NULL,
    year TEXT NOT NULL,
    imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id,name,department,category,year),
    FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS match_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    side TEXT NOT NULL,
    student_name TEXT NOT NULL,
    department TEXT,
    student_id INTEGER,
    FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS tournament_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    winner TEXT NOT NULL,
    runner_up TEXT NOT NULL,
    notes TEXT,
    UNIQUE(tournament_id,category),
    FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS draw_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    format_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    image_path TEXT,
    created_by INTEGER,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS certificate_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    certificate_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id,certificate_type),
    FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS generated_certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    participant_id INTEGER,
    student_id INTEGER,
    certificate_type TEXT NOT NULL,
    recipient_name TEXT NOT NULL,
    achievement TEXT,
    certificate_no TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    FOREIGN KEY(participant_id) REFERENCES event_participants(id) ON DELETE SET NULL,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS facility_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sport_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    caption TEXT,
    uploaded_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sport_id) REFERENCES sports(id) ON DELETE CASCADE
);

-- V7 Coaching Schedule
CREATE TABLE IF NOT EXISTS coaching_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    programme_id INTEGER NOT NULL,
    session_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    venue TEXT,
    notes TEXT,
    status TEXT DEFAULT 'Scheduled',
    created_by INTEGER,
    updated_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(programme_id) REFERENCES programmes(id) ON DELETE CASCADE,
    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY(updated_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_date ON coaching_sessions(session_date,start_time);
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_programme ON coaching_sessions(programme_id,session_date);
