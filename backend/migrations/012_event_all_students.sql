-- Events may target every student without being tied to one sport.
ALTER TABLE tournaments ALTER COLUMN sport_id DROP NOT NULL;
