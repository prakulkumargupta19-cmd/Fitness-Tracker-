"""Authentication helper utilities for Supabase PostgreSQL."""

import secrets
from datetime import datetime, timedelta

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from backend.db import get_db
except ModuleNotFoundError:
    from db import get_db


OTP_MINUTES = 3


def generate_otp():
    """Generate a 6-digit numeric OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def find_user_by_email(email):
    """Retrieve a student, coach, or admin by email."""
    if not email:
        return None

    email = str(email).strip().lower()
    db = get_db()

    try:
        with db.cursor() as cursor:

            # Student / Coach
            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1
                """,
                (email,),
            )

            user = cursor.fetchone()

            if user:
                return user

            # Admin
            cursor.execute(
                """
                SELECT
                    id,
                    full_name,
                    email,
                    password_hash,
                    NULL AS contact_number,
                    is_verified,
                    NULL AS last_login_at,
                    created_at,
                    'admin' AS role,
                    NULL AS coach_status
                FROM admins
                WHERE LOWER(email) = %s
                LIMIT 1
                """,
                (email,),
            )

            return cursor.fetchone()

    finally:
        db.close()


def get_user_by_id(user_id):
    """Retrieve a student, coach, or admin by ID."""
    if not user_id:
        return None

    db = get_db()

    try:
        with db.cursor() as cursor:

            # Student / Coach
            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )

            user = cursor.fetchone()

            if user:
                return user

            # Admin
            cursor.execute(
                """
                SELECT
                    id,
                    full_name,
                    email,
                    password_hash,
                    NULL AS contact_number,
                    is_verified,
                    NULL AS last_login_at,
                    created_at,
                    'admin' AS role,
                    NULL AS coach_status
                FROM admins
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )

            return cursor.fetchone()

    finally:
        db.close()


def store_otp(user_id, purpose, otp, minutes=OTP_MINUTES):
    """Store a hashed OTP for a student/coach."""
    db = get_db()

    try:
        with db.cursor() as cursor:

            # Maximum 5 OTPs in the last hour
            cursor.execute(
                """
                SELECT COUNT(*) AS sent_count
                FROM otp_verifications
                WHERE user_id = %s
                  AND purpose = %s
                  AND created_at >= NOW() - INTERVAL '1 hour'
                """,
                (user_id, purpose),
            )

            sent = cursor.fetchone() or {}

            if sent.get("sent_count", 0) >= 5:
                return False

            # Invalidate previous unused OTPs
            cursor.execute(
                """
                UPDATE otp_verifications
                SET is_used = TRUE
                WHERE user_id = %s
                  AND purpose = %s
                  AND is_used = FALSE
                """,
                (user_id, purpose),
            )

            expires_at = datetime.now() + timedelta(minutes=minutes)

            cursor.execute(
                """
                INSERT INTO otp_verifications
                    (
                        user_id,
                        purpose,
                        otp_hash,
                        expires_at,
                        is_used,
                        created_at
                    )
                VALUES (%s, %s, %s, %s, FALSE, NOW())
                """,
                (
                    user_id,
                    purpose,
                    generate_password_hash(otp),
                    expires_at,
                ),
            )

        db.commit()
        return True

    finally:
        db.close()


def verify_stored_otp(user_id, purpose, otp):
    """Verify a student/coach OTP."""
    db = get_db()

    try:
        with db.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM otp_verifications
                WHERE user_id = %s
                  AND purpose = %s
                  AND is_used = FALSE
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, purpose),
            )

            record = cursor.fetchone()

            if not record:
                return False, "OTP expired or invalid. Please request a new OTP."

            if record.get("attempt_count", 0) >= 5:
                return False, "Too many incorrect codes. Request a new OTP."

            if record["expires_at"] < datetime.now():
                return False, "OTP has expired. Please request a new OTP."

            if not check_password_hash(record["otp_hash"], otp):

                attempts = record.get("attempt_count", 0) + 1

                cursor.execute(
                    """
                    UPDATE otp_verifications
                    SET
                        attempt_count = %s,
                        is_used = CASE
                            WHEN %s >= 5 THEN TRUE
                            ELSE is_used
                        END
                    WHERE id = %s
                    """,
                    (
                        attempts,
                        attempts,
                        record["id"],
                    ),
                )

                db.commit()

                return False, "Invalid OTP code."

            cursor.execute(
                """
                UPDATE otp_verifications
                SET is_used = TRUE
                WHERE id = %s
                """,
                (record["id"],),
            )

        db.commit()

        return True, "OTP verified successfully."

    finally:
        db.close()


def store_admin_otp(admin_id, purpose, otp, minutes=OTP_MINUTES):
    """Store an administrator OTP."""
    db = get_db()

    try:
        with db.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*) AS sent_count
                FROM admin_otp_verifications
                WHERE admin_id = %s
                  AND purpose = %s
                  AND created_at >= NOW() - INTERVAL '1 hour'
                """,
                (admin_id, purpose),
            )

            sent = cursor.fetchone() or {}

            if sent.get("sent_count", 0) >= 5:
                return False

            # Invalidate previous unused admin OTPs
            cursor.execute(
                """
                UPDATE admin_otp_verifications
                SET is_used = TRUE
                WHERE admin_id = %s
                  AND purpose = %s
                  AND is_used = FALSE
                """,
                (admin_id, purpose),
            )

            cursor.execute(
                """
                INSERT INTO admin_otp_verifications
                    (
                        admin_id,
                        purpose,
                        otp_hash,
                        expires_at,
                        is_used,
                        created_at
                    )
                VALUES (%s, %s, %s, %s, FALSE, NOW())
                """,
                (
                    admin_id,
                    purpose,
                    generate_password_hash(otp),
                    datetime.now() + timedelta(minutes=minutes),
                ),
            )

        db.commit()
        return True

    finally:
        db.close()


def verify_admin_otp(admin_id, purpose, otp):
    """Verify and consume an administrator OTP."""
    db = get_db()

    try:
        with db.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    otp_hash,
                    expires_at,
                    attempt_count
                FROM admin_otp_verifications
                WHERE admin_id = %s
                  AND purpose = %s
                  AND is_used = FALSE
                ORDER BY id DESC
                LIMIT 1
                """,
                (admin_id, purpose),
            )

            record = cursor.fetchone()

            if not record:
                return False, "OTP expired or invalid. Please request a new OTP."

            if record.get("attempt_count", 0) >= 5:
                return False, "Too many incorrect codes. Request a new OTP."

            if record["expires_at"] < datetime.now():
                return False, "OTP has expired. Please request a new OTP."

            if not check_password_hash(record["otp_hash"], otp):

                attempts = record.get("attempt_count", 0) + 1

                cursor.execute(
                    """
                    UPDATE admin_otp_verifications
                    SET
                        attempt_count = %s,
                        is_used = CASE
                            WHEN %s >= 5 THEN TRUE
                            ELSE is_used
                        END
                    WHERE id = %s
                    """,
                    (
                        attempts,
                        attempts,
                        record["id"],
                    ),
                )

                db.commit()

                return False, "Invalid OTP code."

            cursor.execute(
                """
                UPDATE admin_otp_verifications
                SET is_used = TRUE
                WHERE id = %s
                """,
                (record["id"],),
            )

        db.commit()

        return True, "OTP verified successfully."

    finally:
        db.close()


def establish_session(user):
    """Set standard session keys for an authenticated user."""
    session.clear()
    session.permanent = True

    session.update(
        user_id=user["id"],
        role=user["role"],
        full_name=user["full_name"],
        email=user["email"],
    )


def canonical_role(role):
    """Normalize role names."""
    value = str(role or "").strip().lower()

    if value in ("player", "athlete", "students", "student"):
        return "student"

    if value in ("coaches", "coach"):
        return "coach"

    if value in ("admins", "admin"):
        return "admin"

    return value


def is_valid_domain(email):
    """Check whether an email belongs to the allowed college domain."""
    return str(email).strip().lower().endswith("@inspiria.edu.in")