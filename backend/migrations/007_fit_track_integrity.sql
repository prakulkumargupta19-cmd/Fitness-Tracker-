-- Fit-Track integrity and relationship rules.
-- This migration is additive. It does not alter users, admins, OTP tables, or
-- any existing authentication/session columns.

-- Safe indexes for the relationship-heavy queries used by the API.
CREATE INDEX IF NOT EXISTS idx_fit_track_enrollments_student
    ON enrollments (student_id, status, programme_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_enrollments_programme
    ON enrollments (programme_id, status, student_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_attendance_enrollment_date
    ON attendance (enrollment_id, session_date);
CREATE INDEX IF NOT EXISTS idx_fit_track_assessments_enrollment_date
    ON daily_assessments (enrollment_id, session_date DESC);
CREATE INDEX IF NOT EXISTS idx_fit_track_assessments_coach
    ON daily_assessments (coach_id, session_date DESC);
CREATE INDEX IF NOT EXISTS idx_fit_track_registrations_student
    ON registrations (student_id, tournament_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_participants_student
    ON event_participants (student_id, tournament_id);
CREATE INDEX IF NOT EXISTS idx_fit_track_match_players_match_side
    ON match_players (match_id, side, student_name);
CREATE INDEX IF NOT EXISTS idx_fit_track_achievements_student
    ON achievements (student_id, achievement_year DESC);
CREATE INDEX IF NOT EXISTS idx_fit_track_certificates_student
    ON certificates (student_id, issue_date DESC);
CREATE INDEX IF NOT EXISTS idx_fit_track_generated_certificates_student
    ON generated_certificates (student_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fit_track_facility_media_sport
    ON facility_media (sport_id, created_at DESC);

-- Domain checks are NOT VALID so an existing installation is not blocked by
-- legacy rows. PostgreSQL still enforces them for all new and changed rows.
DO $$
BEGIN
    ALTER TABLE matches ADD CONSTRAINT fit_track_matches_category_check
        CHECK (category IN ('Boys', 'Girls')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE event_participants ADD CONSTRAINT fit_track_participant_category_check
        CHECK (category IN ('Boys', 'Girls')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE match_players ADD CONSTRAINT fit_track_match_player_side_check
        CHECK (side IN ('A', 'B')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE coaching_sessions ADD CONSTRAINT fit_track_session_status_check
        CHECK (status IN ('Scheduled', 'Rescheduled', 'Cancelled', 'Completed')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE tournaments ADD CONSTRAINT fit_track_tournament_date_check
        CHECK (end_date IS NULL OR end_date >= start_date) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE coaching_sessions ADD CONSTRAINT fit_track_session_time_check
        CHECK (end_time > start_time) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE messages ADD CONSTRAINT fit_track_message_not_self_check
        CHECK (sender_user_id <> receiver_user_id) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Cross-table role relationships cannot be represented by a normal CHECK
-- constraint, so enforce them with small, focused triggers.
CREATE OR REPLACE FUNCTION fit_track_validate_roles()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_TABLE_NAME = 'programmes' AND NEW.coach_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM users
            WHERE id = NEW.coach_id AND role = 'coach'
        ) THEN
            RAISE EXCEPTION 'programme coach_id must reference a coach';
        END IF;
    ELSIF TG_TABLE_NAME = 'enrollments' THEN
        IF NOT EXISTS (
            SELECT 1 FROM users
            WHERE id = NEW.student_id AND role = 'student'
        ) THEN
            RAISE EXCEPTION 'enrollment student_id must reference a student';
        END IF;
    ELSIF TG_TABLE_NAME = 'registrations' THEN
        IF NOT EXISTS (
            SELECT 1 FROM users
            WHERE id = NEW.student_id AND role = 'student'
        ) THEN
            RAISE EXCEPTION 'registration student_id must reference a student';
        END IF;
    ELSIF TG_TABLE_NAME = 'daily_assessments' AND NEW.coach_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM users
            WHERE id = NEW.coach_id AND role = 'coach'
        ) THEN
            RAISE EXCEPTION 'assessment coach_id must reference a coach';
        END IF;
    ELSIF TG_TABLE_NAME IN ('achievements', 'certificates', 'generated_certificates', 'event_participants', 'match_players')
          AND NEW.student_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM users
            WHERE id = NEW.student_id AND role = 'student'
        ) THEN
            RAISE EXCEPTION '% student_id must reference a student', TG_TABLE_NAME;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_fit_track_programmes_roles ON programmes;
CREATE TRIGGER trg_fit_track_programmes_roles
    BEFORE INSERT OR UPDATE ON programmes
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_enrollments_roles ON enrollments;
CREATE TRIGGER trg_fit_track_enrollments_roles
    BEFORE INSERT OR UPDATE ON enrollments
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_registrations_roles ON registrations;
CREATE TRIGGER trg_fit_track_registrations_roles
    BEFORE INSERT OR UPDATE ON registrations
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_assessments_roles ON daily_assessments;
CREATE TRIGGER trg_fit_track_assessments_roles
    BEFORE INSERT OR UPDATE ON daily_assessments
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_participants_roles ON event_participants;
CREATE TRIGGER trg_fit_track_participants_roles
    BEFORE INSERT OR UPDATE ON event_participants
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_match_players_roles ON match_players;
CREATE TRIGGER trg_fit_track_match_players_roles
    BEFORE INSERT OR UPDATE ON match_players
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_achievements_roles ON achievements;
CREATE TRIGGER trg_fit_track_achievements_roles
    BEFORE INSERT OR UPDATE ON achievements
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_certificates_roles ON certificates;
CREATE TRIGGER trg_fit_track_certificates_roles
    BEFORE INSERT OR UPDATE ON certificates
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

DROP TRIGGER IF EXISTS trg_fit_track_generated_certificates_roles ON generated_certificates;
CREATE TRIGGER trg_fit_track_generated_certificates_roles
    BEFORE INSERT OR UPDATE ON generated_certificates
    FOR EACH ROW EXECUTE FUNCTION fit_track_validate_roles();

-- A fixture squad is optional, but each side is capped at 15 students.
CREATE OR REPLACE FUNCTION fit_track_limit_match_squad()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF (
        SELECT COUNT(*) FROM match_players
        WHERE match_id = NEW.match_id
          AND side = NEW.side
          AND (TG_OP = 'INSERT' OR id <> NEW.id)
    ) >= 15 THEN
        RAISE EXCEPTION 'a fixture side may contain at most 15 players';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_fit_track_match_squad_limit ON match_players;
CREATE TRIGGER trg_fit_track_match_squad_limit
    BEFORE INSERT OR UPDATE ON match_players
    FOR EACH ROW EXECUTE FUNCTION fit_track_limit_match_squad();

-- Keep modified timestamps correct for mutable Fit-Track records.
CREATE OR REPLACE FUNCTION fit_track_touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_fit_track_programmes_updated_at ON programmes;
CREATE TRIGGER trg_fit_track_programmes_updated_at
    BEFORE UPDATE ON programmes
    FOR EACH ROW EXECUTE FUNCTION fit_track_touch_updated_at();

DROP TRIGGER IF EXISTS trg_fit_track_assessments_updated_at ON daily_assessments;
CREATE TRIGGER trg_fit_track_assessments_updated_at
    BEFORE UPDATE ON daily_assessments
    FOR EACH ROW EXECUTE FUNCTION fit_track_touch_updated_at();

DROP TRIGGER IF EXISTS trg_fit_track_tournaments_updated_at ON tournaments;
CREATE TRIGGER trg_fit_track_tournaments_updated_at
    BEFORE UPDATE ON tournaments
    FOR EACH ROW EXECUTE FUNCTION fit_track_touch_updated_at();

DROP TRIGGER IF EXISTS trg_fit_track_matches_updated_at ON matches;
CREATE TRIGGER trg_fit_track_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION fit_track_touch_updated_at();

DROP TRIGGER IF EXISTS trg_fit_track_coaching_sessions_updated_at ON coaching_sessions;
CREATE TRIGGER trg_fit_track_coaching_sessions_updated_at
    BEFORE UPDATE ON coaching_sessions
    FOR EACH ROW EXECUTE FUNCTION fit_track_touch_updated_at();
