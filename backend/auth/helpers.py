"""Authentication helper utilities.

This module contains authentication-related helper functions extracted from
backend.app to support the auth package without creating circular imports.
"""

import secrets
from datetime import datetime, timedelta, timezone
from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from backend.db import get_db
except ModuleNotFoundError:
    from db import get_db

OTP_MINUTES = 10


def now():
    return datetime.now(timezone.utc)


def now_sql():
    return now().strftime("%Y-%m-%d %H:%M:%S")


def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def email_exists(email):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM users WHERE lower(email)=%s", (str(email or "").strip().lower(),))
        return cursor.fetchone() is not None
    finally:
        db.close()


def new_code(db, role):
    prefix = {"admin": "ADM", "coach": "COA", "player": "ATH"}.get(role, "ATH")
    cursor = db.cursor()
    cursor.execute("SELECT user_code FROM users WHERE user_code LIKE %s", (prefix + "%",))
    existing = {row["user_code"] for row in cursor.fetchall()}
    number = 1
    while f"{prefix}{number:03d}" in existing:
        number += 1
    return f"{prefix}{number:03d}"


def save_otp(email, purpose, otp, payload=""):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE otp_requests SET used=1 WHERE email=%s AND purpose=%s AND used=0",
            (email, purpose),
        )
        cursor.execute(
            "INSERT INTO otp_requests (email,purpose,otp_hash,payload,expires_at,created_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                email,
                purpose,
                generate_password_hash(otp),
                payload,
                (now() + timedelta(minutes=OTP_MINUTES)).strftime("%Y-%m-%d %H:%M:%S"),
                now_sql(),
            ),
        )
        db.commit()
    finally:
        db.close()


def get_otp(email, purpose):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM otp_requests WHERE email=%s AND purpose=%s AND used=0 ORDER BY id DESC LIMIT 1",
            (email, purpose),
        )
        return cursor.fetchone()
    finally:
        db.close()


def verify_otp(email, purpose, otp, consume=False):
    record = get_otp(email, purpose)
    if not record:
        return None, "OTP expired. Please request a new OTP."
    expires_at = record["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now():
        return None, "OTP expired. Please request a new OTP."
    if record["attempts"] >= 5:
        return None, "Too many incorrect attempts. Please request a new OTP."
    if not check_password_hash(record["otp_hash"], otp):
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute("UPDATE otp_requests SET attempts=attempts+1 WHERE id=%s", (record["id"],))
            db.commit()
        finally:
            db.close()
        return None, "Invalid OTP"
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE otp_requests SET verified=1, used=%s WHERE id=%s",
            (1 if consume else 0, record["id"]),
        )
        db.commit()
    finally:
        db.close()
    return record, None


def establish_session(user):
    session.clear()
    session.permanent = True
    session.update(
        user_id=user["id"],
        user_code=user["user_code"],
        user_name=user["name"],
        user_email=user["email"],
        role=user["role"],
    )


def canonical_role(role):
    value = str(role or "").strip().lower()
    if value == "student":
        return "player"
    return value


def valid_password(password):
    return len(str(password or "")) >= 8
