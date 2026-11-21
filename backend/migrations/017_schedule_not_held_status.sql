ALTER TABLE coaching_sessions
    DROP CONSTRAINT IF EXISTS fit_track_session_status_check;

ALTER TABLE coaching_sessions
    ADD CONSTRAINT fit_track_session_status_check
    CHECK (status IN ('Scheduled', 'Rescheduled', 'Cancelled', 'Completed', 'Not Held'))
    NOT VALID;
