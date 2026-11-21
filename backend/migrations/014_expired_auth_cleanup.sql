-- Keep this migration safe to reapply: it replaces the function and the
-- single named hourly job instead of accumulating duplicate cron jobs.
CREATE EXTENSION IF NOT EXISTS pg_cron;

CREATE INDEX IF NOT EXISTS idx_otp_verifications_expires_at
    ON public.otp_verifications (expires_at);
CREATE INDEX IF NOT EXISTS idx_admin_otp_verifications_expires_at
    ON public.admin_otp_verifications (expires_at);
CREATE INDEX IF NOT EXISTS idx_pending_registrations_expired_verification
    ON public.pending_registrations (otp_expires_at)
    WHERE status = 'pending_verification';

CREATE OR REPLACE FUNCTION public.cleanup_expired_auth_data()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $cleanup$
DECLARE
    otp_rows_deleted BIGINT := 0;
    admin_otp_rows_deleted BIGINT := 0;
    pending_rows_deleted BIGINT := 0;
BEGIN
    -- Prevent overlapping executions if an earlier run is still working.
    IF NOT pg_try_advisory_xact_lock(731204, 14) THEN
        RAISE LOG 'Fit Track auth cleanup skipped: another run holds the lock';
        RETURN;
    END IF;

    DELETE FROM public.otp_verifications
    WHERE expires_at <= CURRENT_TIMESTAMP;
    GET DIAGNOSTICS otp_rows_deleted = ROW_COUNT;

    DELETE FROM public.admin_otp_verifications
    WHERE expires_at <= CURRENT_TIMESTAMP;
    GET DIAGNOSTICS admin_otp_rows_deleted = ROW_COUNT;

    -- Only never-verified registrations past their OTP deadline qualify.
    -- A matching account is an additional safeguard against deleting staged
    -- rows that may belong to a successfully verified user.
    DELETE FROM public.pending_registrations AS pending
    WHERE pending.status = 'pending_verification'
      AND pending.otp_expires_at <= CURRENT_TIMESTAMP
      AND NOT EXISTS (
          SELECT 1
          FROM public.users AS account
          WHERE LOWER(account.email) = LOWER(pending.email)
            AND account.role = pending.role
      );
    GET DIAGNOSTICS pending_rows_deleted = ROW_COUNT;

    RAISE LOG 'Fit Track auth cleanup completed: otp_verifications=%, admin_otp_verifications=%, pending_registrations=%',
        otp_rows_deleted, admin_otp_rows_deleted, pending_rows_deleted;
EXCEPTION
    WHEN OTHERS THEN
        -- The exception block rolls back this function's work before logging;
        -- the cron worker records the failed job and continues operating.
        RAISE LOG 'Fit Track auth cleanup failed: SQLSTATE %, error %', SQLSTATE, SQLERRM;
        RAISE;
END;
$cleanup$;

REVOKE ALL ON FUNCTION public.cleanup_expired_auth_data() FROM PUBLIC;

DO $schedule$
BEGIN
    -- Serialize simultaneous app-start migrations. cron.schedule's named
    -- overload updates the existing job, so each deployment keeps one job.
    PERFORM pg_advisory_xact_lock(731204, 15);
    PERFORM cron.schedule(
        'fit-track-auth-expiry-cleanup',
        '0 * * * *',
        'SELECT public.cleanup_expired_auth_data()'
    );
END;
$schedule$;
