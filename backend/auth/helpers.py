"""Authentication helper utilities aligned with fitness_tracker_auth schema."""

import secrets
from datetime import datetime, timedelta
from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from backend.db import get_db
except ModuleNotFoundError:
    from db import get_db

OTP_MINUTES = 10


def generate_otp():
    """Generate 6-digit numeric OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def find_user_by_email(email):
    """Retrieve user dictionary by email."""
    if not email:
        return None
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s", (str(email).strip().lower(),))
            return cursor.fetchone()
    finally:
        db.close()


def get_user_by_id(user_id):
    """Retrieve user dictionary by user ID."""
    if not user_id:
        return None
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        db.close()


def store_otp(user_id, purpose, otp, minutes=OTP_MINUTES):
    """Store OTP hash in otp_verifications."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Mark previous unused OTPs for same user and purpose as used
            cursor.execute(
                "UPDATE otp_verifications SET is_used = 1 WHERE user_id = %s AND purpose = %s AND is_used = 0",
                (user_id, purpose),
            )
            expires_at = datetime.now() + timedelta(minutes=minutes)
            cursor.execute(
                """INSERT INTO otp_verifications (user_id, purpose, otp_hash, expires_at, is_used, created_at)
                   VALUES (%s, %s, %s, %s, 0, NOW())""",
                (user_id, purpose, generate_password_hash(otp), expires_at),
            )
        db.commit()
        return True
    finally:
        db.close()


def verify_stored_otp(user_id, purpose, otp):
    """Verify submitted OTP for a given user and purpose."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM otp_verifications 
                   WHERE user_id = %s AND purpose = %s AND is_used = 0 
                   ORDER BY id DESC LIMIT 1""",
                (user_id, purpose),
            )
            record = cursor.fetchone()
            if not record:
                return False, "OTP expired or invalid. Please request a new OTP."
            
            if record["expires_at"] < datetime.now():
                return False, "OTP has expired. Please request a new OTP."
            
            if not check_password_hash(record["otp_hash"], otp):
                return False, "Invalid OTP code."
            
            cursor.execute("UPDATE otp_verifications SET is_used = 1 WHERE id = %s", (record["id"],))
        db.commit()
        return True, "OTP verified successfully."
    finally:
        db.close()


def establish_session(user):
    """Set standard session keys for authenticated user."""
    session.clear()
    session.permanent = True
    session.update(
        user_id=user["id"],
        role=user["role"],
        full_name=user["full_name"],
        email=user["email"],
    )


def canonical_role(role):
    """Map display role strings to schema role ENUM."""
    val = str(role or "").strip().lower()
    if val in ("player", "athlete", "students", "student"):
        return "student"
    if val in ("coaches", "coach"):
        return "coach"
    if val in ("admins", "admin"):
        return "admin"
    return val

