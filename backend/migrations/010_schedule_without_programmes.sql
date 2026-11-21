-- Coaching sessions belong directly to a sport; programmes are unrelated.
-- Existing deployments may have recorded the old migration as applied, so
-- startup also reapplies these idempotent column guards on every initialization.
ALTER TABLE coaching_sessions
    ADD COLUMN IF NOT EXISTS session_type TEXT NOT NULL DEFAULT 'practice';
ALTER TABLE coaching_sessions
    ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE coaching_sessions
    ADD COLUMN IF NOT EXISTS updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'coaching_sessions' AND column_name = 'programme_id'
    ) THEN
        ALTER TABLE coaching_sessions ADD COLUMN IF NOT EXISTS sport_id BIGINT REFERENCES sports(id) ON DELETE CASCADE;
        ALTER TABLE coaching_sessions ADD COLUMN IF NOT EXISTS coach_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
        UPDATE coaching_sessions cs
        SET sport_id = p.sport_id, coach_id = p.coach_id
        FROM programmes p
        WHERE cs.programme_id = p.id AND cs.sport_id IS NULL;
        IF EXISTS (SELECT 1 FROM coaching_sessions WHERE sport_id IS NULL) THEN
            RAISE EXCEPTION 'Cannot migrate coaching sessions: some rows have no matching programme/sport';
        END IF;
        ALTER TABLE coaching_sessions ALTER COLUMN sport_id SET NOT NULL;
        ALTER TABLE coaching_sessions DROP CONSTRAINT IF EXISTS coaching_sessions_programme_id_fkey;
        ALTER TABLE coaching_sessions DROP COLUMN programme_id;
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'coaching_sessions' AND column_name = 'sport_id'
    ) THEN
        ALTER TABLE coaching_sessions ADD COLUMN IF NOT EXISTS coach_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
    ELSE
        ALTER TABLE coaching_sessions ADD COLUMN sport_id BIGINT REFERENCES sports(id) ON DELETE CASCADE;
        ALTER TABLE coaching_sessions ADD COLUMN coach_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
        ALTER TABLE coaching_sessions ALTER COLUMN sport_id SET NOT NULL;
    END IF;
END $$;
DROP INDEX IF EXISTS idx_coaching_sessions_programme;
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_date ON coaching_sessions(session_date, start_time);
CREATE INDEX IF NOT EXISTS idx_coaching_sessions_sport_date ON coaching_sessions(sport_id, session_date);