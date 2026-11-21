ALTER TABLE tournaments
    ADD COLUMN IF NOT EXISTS registration_url TEXT;
