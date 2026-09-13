"""Self-service registration workflow.

This module contains the signup orchestration extracted from ``backend.app``.
It depends only on the auth package modules (``helpers``, ``emails``),
``backend.db``, Flask's ``jsonify``, and standard library / Werkzeug
utilities.  It never imports ``backend.app``.
"""

import json

from flask import jsonify
from werkzeug.security import generate_password_hash

try:
    from backend.db import get_db
except ModuleNotFoundError:
    from db import get_db

try:
    from backend.auth.helpers import (
        canonical_role, valid_password, email_exists,
        generate_otp, save_otp,
    )
except ModuleNotFoundError:
    from auth.helpers import (
        canonical_role, valid_password, email_exists,
        generate_otp, save_otp,
    )

try:
    from backend.auth.emails import send_otp_email
except ModuleNotFoundError:
    from auth.emails import send_otp_email


def signup(data, forced_role=None):
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = forced_role or canonical_role(data.get("role"))

    if not forced_role and role == "admin":
        return None, (jsonify(success=False, message="Admin accounts cannot be created through public registration."), 403)
    if not name:
        return None, (jsonify(success=False, message="Please enter your name."), 400)
    if "@" not in email or "." not in email.split("@")[-1]:
        return None, (jsonify(success=False, message="Please enter a valid email address."), 400)
    if not valid_password(password):
        return None, (jsonify(success=False, message="Password must be at least 8 characters long."), 400)
    if role not in {"player", "coach", "admin"}:
        return None, (jsonify(success=False, message="Please select a valid role."), 400)
    if email_exists(email):
        return None, (jsonify(success=False, message="An account already exists with this email. Try signing in instead."), 400)

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM otp_requests WHERE email=%s AND purpose='signup' AND used=0 AND expires_at > NOW()", (email,))
        if cursor.fetchone():
            return None, (jsonify(success=False, message="An OTP was already sent to this email. Please check your inbox or wait before requesting a new one."), 429)
    finally:
        db.close()

    payload = json.dumps(
        {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "role": role,
            "status": "pending" if role == "coach" else "approved",
            "sport": data.get("sport") or None,
            "contact_number": data.get("contact_number") or None,
            "gender": data.get("gender") or None,
            "date_of_birth": data.get("date_of_birth") or None,
        }
    )
    otp = generate_otp()
    save_otp(email, "signup", otp, payload)
    if not send_otp_email(email, name, "signup", otp):
        return None, (jsonify(success=False, message="Email service unavailable. OTP delivery failed."), 503)
    return email, None