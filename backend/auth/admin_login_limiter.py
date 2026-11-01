"""Persistent rate limiting for failed administrator password attempts."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256

try:
    from backend.db import get_db
except ImportError:  # Support direct execution of the backend package.
    from db import get_db


MAX_FAILED_ATTEMPTS = 5
WINDOW = timedelta(minutes=15)
LOCKOUT = timedelta(minutes=15)


def _email_key(email):
    normalized = str(email or "").strip().lower().encode("utf-8")
    return sha256(normalized).hexdigest()


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_datetime(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime.fromisoformat(str(value)).replace(tzinfo=None)


def get_admin_lockout_seconds(email):
    """Return the remaining lockout time, or zero when the account is clear."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT locked_until FROM admin_login_attempt_limits WHERE email_hash = %s",
                (_email_key(email),),
            )
            row = cursor.fetchone()
        if not row or not row["locked_until"]:
            return 0
        remaining = (_as_datetime(row["locked_until"]) - _utc_now()).total_seconds()
        return max(0, int(remaining + 0.999))
    finally:
        db.close()


def record_admin_login_failure(email):
    """Atomically count a failure and start a 15-minute lock after five tries."""
    now = _utc_now()
    window_start = now - WINDOW
    lock_until = now + LOCKOUT
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """DELETE FROM admin_login_attempt_limits
                   WHERE window_started_at <= %s
                     AND (locked_until IS NULL OR locked_until <= %s)""",
                (window_start, now),
            )
            cursor.execute(
                """INSERT INTO admin_login_attempt_limits
                       (email_hash, failed_attempts, window_started_at, locked_until)
                   VALUES (%s, 1, %s, NULL)
                   ON CONFLICT (email_hash) DO UPDATE SET
                       failed_attempts = CASE
                           WHEN admin_login_attempt_limits.window_started_at <= %s
                             OR (admin_login_attempt_limits.locked_until IS NOT NULL
                                 AND admin_login_attempt_limits.locked_until <= %s)
                           THEN 1
                           ELSE admin_login_attempt_limits.failed_attempts + 1
                       END,
                       window_started_at = CASE
                           WHEN admin_login_attempt_limits.window_started_at <= %s
                             OR (admin_login_attempt_limits.locked_until IS NOT NULL
                                 AND admin_login_attempt_limits.locked_until <= %s)
                           THEN %s
                           ELSE admin_login_attempt_limits.window_started_at
                       END,
                       locked_until = CASE
                           WHEN admin_login_attempt_limits.window_started_at <= %s
                             OR (admin_login_attempt_limits.locked_until IS NOT NULL
                                 AND admin_login_attempt_limits.locked_until <= %s)
                           THEN NULL
                           WHEN admin_login_attempt_limits.failed_attempts + 1 >= %s
                           THEN %s
                           ELSE admin_login_attempt_limits.locked_until
                       END
                   RETURNING failed_attempts""",
                (
                    _email_key(email), now,
                    window_start, now, window_start, now, now,
                    window_start, now, MAX_FAILED_ATTEMPTS, lock_until,
                ),
            )
            attempts = cursor.fetchone()["failed_attempts"]
        db.commit()
        return attempts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def clear_admin_login_failures(email):
    """Clear the failure counter after valid administrator credentials."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM admin_login_attempt_limits WHERE email_hash = %s",
                (_email_key(email),),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
