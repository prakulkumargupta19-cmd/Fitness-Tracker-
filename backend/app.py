"""Fitness Performance Tracker - Flask Backend.

Aligned with the ``fitness_tracker_auth`` schema:
    users, student_profiles, otp_verifications, student_details.

Endpoints cover the auth workflow:
    signup -> OTP verification -> login
    forgot password -> OTP -> reset password
    admin coach approval
    student profile management
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).parent.absolute()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from db import get_db  # noqa: E402
from auth.helpers import (  # noqa: E402
    generate_otp,
    store_otp,
    verify_stored_otp,
    find_user_by_email,
    get_user_by_id,
    establish_session,
    is_valid_domain,
)
from auth.emails import (  # noqa: E402
    send_otp_email,
    send_account_created_email,
    send_coach_approval_email,
    send_password_reset_success_email,
)
from auth.decorators import login_required, role_required  # noqa: E402
from attendance import register_attendance_routes, student_attendance_payload  # noqa: E402

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fitness-tracker-secret-key-2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

VALID_ROLES = ("student", "coach")


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With"
    )
    return response


# =====================================================================
#  AUTH: SIGNUP
# =====================================================================
@app.route("/api/signup", methods=["POST"])
@app.route("/api/register", methods=["POST"])
def signup():
    """Basic-info step for student/coach signup."""
    data = request.get_json(silent=True) or {}
    role = str(data.get("role") or "").strip().lower()
    full_name = str(
        data.get("full_name") or data.get("fullName") or data.get("name") or ""
    ).strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    contact_number = str(
        data.get("contact_number") or data.get("contact") or ""
    ).strip()

    if role not in ("student", "coach"):
        return (
            jsonify(
                {"success": False, "message": "Role must be 'student' or 'coach'."}
            ),
            400,
        )
    if not full_name or not email or not password:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Full name, email and password are required.",
                }
            ),
            400,
        )
    if not is_valid_domain(email):
        return (
            jsonify(
                {"success": False, "message": "Only @inspiria.edu.in emails are allowed."}
            ),
            400,
        )

    if len(password) < 8:
        return (
            jsonify(
                {"success": False, "message": "Password must be at least 8 characters."}
            ),
            400,
        )

    existing = find_user_by_email(email)
    if existing:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An account with this email already exists.",
                }
            ),
            409,
        )

    db = get_db()
    try:
        with db.cursor() as cursor:
            is_verified = 0
            coach_status = "pending" if role == "coach" else None
            cursor.execute(
                """INSERT INTO users
                       (role, full_name, email, password_hash, contact_number, is_verified, coach_status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    role,
                    full_name,
                    email,
                    generate_password_hash(password),
                    contact_number or None,
                    is_verified,
                    coach_status,
                ),
            )
            user_id = cursor.lastrowid
        db.commit()

        otp = generate_otp()
        store_otp(user_id, "signup", otp)
        send_otp_email(email, full_name, "signup", otp)
        message = "Registration received. An OTP has been sent to verify your email."

        session["pending_user_id"] = user_id
        return (
            jsonify(
                {
                    "success": True,
                    "message": message,
                    "user_id": user_id,
                    "email": email,
                }
            ),
            201,
        )
    except Exception as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"Signup failed: {exc}"}), 500
    finally:
        db.close()
    if not is_valid_domain(email):
        return jsonify({"success": False, "message": "Only @inspiria.edu.in emails are allowed."}), 400



# =====================================================================
#  AUTH: LOGIN / LOGOUT / SESSION
# =====================================================================
@app.route("/api/login", methods=["POST"])
@app.route("/api/auth/login", methods=["POST"])
@app.route("/api/admin-login", methods=["POST"])
@app.route("/api/admin/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    requested_role = str(data.get("role") or "").strip().lower()
    if not email or not password:
        return (
            jsonify({"success": False, "message": "Email and password are required."}),
            400,
        )

    user = find_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    expected_role = "student" if requested_role == "player" else requested_role
    if expected_role and user["role"] != expected_role:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "This account does not belong to this login page.",
                }
            ),
            403,
        )

    if user["role"] == "student" and not user["is_verified"]:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Please verify your email before logging in.",
                }
            ),
            403,
        )

    if user["role"] == "coach" and user["coach_status"] == "pending":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Your coach account is awaiting admin approval.",
                }
            ),
            403,
        )
    if user["role"] == "coach" and user["coach_status"] == "rejected":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Your coach account was rejected by the admin.",
                }
            ),
            403,
        )

    otp = generate_otp()
    store_otp(user["id"], "login", otp)
    send_otp_email(email, user["full_name"], "login", otp)
    session.clear()
    session["pending_login_user_id"] = user["id"]
    session["pending_login_role"] = user["role"]
    return (
        jsonify(
            {
                "success": True,
                "otp_required": True,
                "message": "A login OTP has been sent to your email.",
                "user": {
                    "id": user["id"],
                    "role": user["role"],
                    "full_name": user["full_name"],
                    "email": user["email"],
                    "contact_number": user["contact_number"],
                    "is_verified": bool(user["is_verified"]),
                    "coach_status": user["coach_status"],
                },
            }
        ),
        200,
    )


def _complete_login(user):
    establish_session(user)
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = %s", (user["id"],)
            )
        db.commit()
    finally:
        db.close()


@app.route("/api/login/verify-otp", methods=["POST"])
@app.route("/api/admin-login/verify-otp", methods=["POST"])
@app.route("/api/admin/login/verify-otp", methods=["POST"])
def verify_login_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    otp = str(data.get("otp") or "").strip()
    user = find_user_by_email(email)
    if not user:
        return (
            jsonify({"success": False, "message": "No account found with this email."}),
            404,
        )
    if session.get("pending_login_user_id") != user["id"]:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Login attempt expired. Please log in again.",
                }
            ),
            400,
        )
    valid, message = verify_stored_otp(user["id"], "login", otp)
    if not valid:
        return jsonify({"success": False, "message": message}), 400
    _complete_login(user)
    return (
        jsonify(
            {
                "success": True,
                "message": "Login OTP verified.",
                "user": {
                    "id": user["id"],
                    "role": user["role"],
                    "full_name": user["full_name"],
                    "email": user["email"],
                },
            }
        ),
        200,
    )


@app.route("/api/login/resend-otp", methods=["POST"])
@app.route("/api/admin-login/resend-otp", methods=["POST"])
@app.route("/api/admin/login/resend-otp", methods=["POST"])
def resend_login_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    user = find_user_by_email(email)
    if not user or session.get("pending_login_user_id") != (user or {}).get("id"):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Login attempt expired. Please log in again.",
                }
            ),
            400,
        )
    otp = generate_otp()
    store_otp(user["id"], "login", otp)
    send_otp_email(email, user["full_name"], "login", otp)
    return jsonify({"success": True, "message": "A new login OTP has been sent."}), 200


@app.route("/api/logout", methods=["GET", "POST"])
@app.route("/api/auth/logout", methods=["GET", "POST"])
@app.route("/api/admin/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200


@app.route("/session", methods=["GET"])
@app.route("/api/session", methods=["GET"])
@app.route("/api/auth/me", methods=["GET"])
@login_required
def current_session():
    user = get_user_by_id(session.get("user_id"))
    if not user:
        session.clear()
        return jsonify({"success": False, "message": "Session expired."}), 401
    response_user = {
        "id": user["id"],
        "role": user["role"],
        "full_name": user["full_name"],
        "name": user["full_name"],
        "email": user["email"],
        "contact_number": user["contact_number"],
        "is_verified": bool(user["is_verified"]),
        "coach_status": user["coach_status"],
    }
    return (
        jsonify(
            {
                "success": True,
                "authenticated": True,
                "user": response_user,
                "admin": response_user,
            }
        ),
        200,
    )


# =====================================================================
#  PROFILE: STUDENT ONBOARDING / DASHBOARD
# =====================================================================
def _profile_response(user_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT date_of_birth, emergency_contact, height_cm, weight_kg,
                          goal, sport_activity
                   FROM student_profiles WHERE user_id = %s""",
                (user_id,),
            )
            return cursor.fetchone()
    finally:
        db.close()


@app.route("/api/admin/session", methods=["GET"])
@role_required("admin")
def admin_session():
    """Return the current session for an authenticated administrator."""
    return current_session()


@app.route("/api/profile", methods=["GET"])
@login_required
def get_profile():
    user = get_user_by_id(session.get("user_id"))
    if not user:
        return jsonify({"success": False, "message": "Session expired."}), 401
    return (
        jsonify(
            {
                "success": True,
                "user": {
                    "id": user["id"],
                    "role": user["role"],
                    "full_name": user["full_name"],
                    "email": user["email"],
                    "contact_number": user["contact_number"],
                },
                "profile": _profile_response(user["id"]),
            }
        ),
        200,
    )


def _save_student_profile(user_id, data):
    date_of_birth = str(data.get("date_of_birth") or data.get("dob") or "").strip()
    emergency_contact = str(
        data.get("emergency_contact") or data.get("emergency-phone") or ""
    ).strip()
    if not date_of_birth or not emergency_contact:
        return "Date of birth and emergency contact are required."

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO student_profiles
                       (user_id, date_of_birth, emergency_contact, height_cm,
                        weight_kg, goal, sport_activity)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                       date_of_birth = VALUES(date_of_birth),
                       emergency_contact = VALUES(emergency_contact),
                       height_cm = VALUES(height_cm),
                       weight_kg = VALUES(weight_kg),
                       goal = VALUES(goal),
                       sport_activity = VALUES(sport_activity)""",
                (
                    user_id,
                    date_of_birth,
                    emergency_contact,
                    data.get("height_cm"),
                    data.get("weight_kg"),
                    data.get("goal"),
                    data.get("sport_activity") or data.get("activity"),
                ),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.route("/api/profile", methods=["PUT", "PATCH"])
@login_required
def update_profile():
    user = get_user_by_id(session.get("user_id"))
    if not user or user["role"] != "student":
        return (
            jsonify(
                {"success": False, "message": "Only students can update this profile."}
            ),
            403,
        )
    data = request.get_json(silent=True) or {}
    if (
        request.method == "PATCH"
        and data.get("current_password")
        and data.get("password")
    ):
        if not check_password_hash(
            user["password_hash"], str(data["current_password"])
        ):
            return (
                jsonify(
                    {"success": False, "message": "Current password is incorrect."}
                ),
                400,
            )
        password = str(data["password"])
        if len(password) < 8:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Password must be at least 8 characters.",
                    }
                ),
                400,
            )
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (generate_password_hash(password), user["id"]),
                )
            db.commit()
        finally:
            db.close()
        return (
            jsonify({"success": True, "message": "Password updated successfully."}),
            200,
        )
    error = _save_student_profile(user["id"], data)
    if error:
        return jsonify({"success": False, "message": error}), 400
    return (
        jsonify(
            {
                "success": True,
                "message": "Profile saved successfully.",
                "profile": _profile_response(user["id"]),
            }
        ),
        200,
    )


@app.route("/api/profile/setup", methods=["POST"])
def setup_pending_student_profile():
    user_id = session.get("pending_user_id")
    user = get_user_by_id(user_id) if user_id else None
    if not user or user["role"] != "student":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Signup session expired. Please register again.",
                }
            ),
            401,
        )
    data = request.get_json(silent=True) or {}
    error = _save_student_profile(user["id"], data)
    if error:
        return jsonify({"success": False, "message": error}), 400
    return jsonify({"success": True, "message": "Profile details saved."}), 200


@app.route("/api/student/dashboard", methods=["GET"])
@login_required
def student_dashboard():
    user = get_user_by_id(session.get("user_id"))
    if not user or user["role"] != "student":
        return jsonify({"success": False, "message": "Student access required."}), 403
    profile = _profile_response(user["id"])
    return (
        jsonify(
            {
                "success": True,
                "name": user["full_name"],
                "email": user["email"],
                "profile": profile,
                "overallScore": 0,
                "benchmarks": {"labels": [], "current": [], "target": []},
                "attributes": {"labels": [], "scores": []},
                "progression": {"weeks": [], "history": []},
                "attendance": student_attendance_payload(user["id"]),
                "goals": [],
                "feedback": [],
            }
        ),
        200,
    )


# =====================================================================
#  ACCOUNT VERIFICATION (signup OTP)
# =====================================================================
@app.route("/api/account-verification/send", methods=["POST"])
def send_verification_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    user = find_user_by_email(email)
    if not user:
        return (
            jsonify({"success": False, "message": "No account found with this email."}),
            404,
        )
    if user["role"] not in ("student", "coach"):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "This account does not use signup verification.",
                }
            ),
            400,
        )
    if user["is_verified"]:
        return (
            jsonify({"success": False, "message": "This email is already verified."}),
            400,
        )

    otp = generate_otp()
    store_otp(user["id"], "signup", otp)
    send_otp_email(email, user["full_name"], "signup", otp)
    return (
        jsonify({"success": True, "message": "Verification OTP sent to your email."}),
        200,
    )


@app.route("/api/account-verification/verify", methods=["POST"])
def verify_account():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    otp = str(data.get("otp") or "").strip()
    user = find_user_by_email(email)
    if not user:
        return (
            jsonify({"success": False, "message": "No account found with this email."}),
            404,
        )
    if not otp:
        return jsonify({"success": False, "message": "OTP is required."}), 400

    valid, message = verify_stored_otp(user["id"], "signup", otp)
    if not valid:
        return jsonify({"success": False, "message": message}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_verified = 1 WHERE id = %s", (user["id"],)
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        return (
            jsonify({"success": False, "message": f"Verification failed: {exc}"}),
            500,
        )
    finally:
        db.close()

    if user["role"] == "coach":
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Email verified. Your coach application is waiting for admin approval.",
                }
            ),
            200,
        )
    send_account_created_email(email, user["full_name"], user["role"])
    return (
        jsonify(
            {
                "success": True,
                "message": "Email verified successfully. You can now log in.",
            }
        ),
        200,
    )


@app.route("/api/coach/status", methods=["GET"])
def coach_registration_status():
    email = str(request.args.get("email") or "").strip().lower()
    user = find_user_by_email(email)
    if not user or user["role"] != "coach":
        return (
            jsonify({"success": False, "message": "Coach registration not found."}),
            404,
        )
    return (
        jsonify(
            {
                "success": True,
                "email_verified": bool(user["is_verified"]),
                "coach_status": user["coach_status"],
            }
        ),
        200,
    )


# =====================================================================
#  FORGOT PASSWORD FLOW
# =====================================================================
@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    user = find_user_by_email(email)
    if not user:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "If this email exists, a reset OTP has been sent.",
                }
            ),
            200,
        )

    otp = generate_otp()
    store_otp(user["id"], "password_reset", otp)
    send_otp_email(email, user["full_name"], "password_reset", otp)
    session["reset_email"] = email
    return (
        jsonify({"success": True, "message": "Password reset OTP sent to your email."}),
        200,
    )


@app.route("/api/forgot-password/resend-otp", methods=["POST"])
def resend_reset_otp():
    return forgot_password()


@app.route("/api/forgot-password/verify-otp", methods=["POST"])
def verify_reset_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    otp = str(data.get("otp") or "").strip()
    user = find_user_by_email(email)
    if not user:
        return (
            jsonify({"success": False, "message": "No account found with this email."}),
            404,
        )

    valid, message = verify_stored_otp(user["id"], "password_reset", otp)
    if not valid:
        return jsonify({"success": False, "message": message}), 400

    session["reset_email"] = email
    session["reset_verified"] = True
    return (
        jsonify(
            {
                "success": True,
                "message": "OTP verified. You can now reset your password.",
            }
        ),
        200,
    )


@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or data.get("new_password") or "")

    if not email or not password:
        return (
            jsonify(
                {"success": False, "message": "Email and new password are required."}
            ),
            400,
        )
    if len(password) < 8:
        return (
            jsonify(
                {"success": False, "message": "Password must be at least 8 characters."}
            ),
            400,
        )

    user = find_user_by_email(email)
    if not user:
        return (
            jsonify({"success": False, "message": "No account found with this email."}),
            404,
        )
    if session.get("reset_email") != email or not session.get("reset_verified"):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Verify the reset OTP before choosing a new password.",
                }
            ),
            403,
        )

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(password), user["id"]),
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        return (
            jsonify({"success": False, "message": f"Password reset failed: {exc}"}),
            500,
        )
    finally:
        db.close()

    session.pop("reset_email", None)
    session.pop("reset_verified", None)
    send_password_reset_success_email(email, user["full_name"])
    return (
        jsonify(
            {
                "success": True,
                "message": "Password reset successful. You can now log in.",
            }
        ),
        200,
    )


# =====================================================================
#  ADMIN: USERS + COACH APPROVAL
# =====================================================================
@app.route("/api/admin/users", methods=["GET"])
@app.route("/api/users", methods=["GET"])
@role_required("admin")
def admin_list_users():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT id, role, full_name, email, contact_number, is_verified, coach_status,
                           last_login_at, created_at
                    FROM users
                    UNION
                    SELECT id, 'admin' as role, full_name, email, contact_number, is_verified,
                           NULL as coach_status, last_login_at, created_at
                    FROM admins
                    ORDER BY created_at DESC"""
            )
            users = cursor.fetchall()
        for u in users:
            u["is_verified"] = bool(u["is_verified"])
            if u.get("last_login_at"):
                u["last_login_at"] = str(u["last_login_at"])
            if u.get("created_at"):
                u["created_at"] = str(u["created_at"])
        return jsonify({"success": True, "users": users}), 200
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT id, role, full_name, email, contact_number, is_verified, coach_status,
                          last_login_at, created_at
                   FROM users ORDER BY created_at DESC"""
            )
            users = cursor.fetchall()
        for u in users:
            u["is_verified"] = bool(u["is_verified"])
            if u.get("last_login_at"):
                u["last_login_at"] = str(u["last_login_at"])
            if u.get("created_at"):
                u["created_at"] = str(u["created_at"])
        return jsonify({"success": True, "users": users}), 200
    finally:
        db.close()


@app.route("/api/admin/coaches/pending", methods=["GET"])
@role_required("admin")
def admin_pending_coaches():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT id, full_name, email, contact_number, coach_status, created_at
                   FROM users WHERE role = 'coach' AND coach_status = 'pending' ORDER BY created_at ASC"""
            )
            coaches = cursor.fetchall()
        for c in coaches:
            if c.get("created_at"):
                c["created_at"] = str(c["created_at"])
        return jsonify({"success": True, "coaches": coaches}), 200
    finally:
        db.close()


@app.route("/api/coach/athletes", methods=["GET"])
@role_required("coach")
def coach_athletes():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""SELECT u.id, u.full_name, u.email, u.contact_number,
                          sp.date_of_birth, sp.sport_activity, sp.height_cm,
                          sp.weight_kg, sp.goal
                   FROM users u
                   LEFT JOIN student_profiles sp ON sp.user_id = u.id
                   WHERE u.role = 'student' AND u.is_verified = 1
                   ORDER BY u.full_name ASC""")
            athletes = cursor.fetchall()
        for athlete in athletes:
            athlete["name"] = athlete.pop("full_name")
            athlete["sport"] = athlete.pop("sport_activity") or ""
        return jsonify({"success": True, "athletes": athletes}), 200
    finally:
        db.close()


@app.route("/api/admin/coaches/approve", methods=["POST"])
@role_required("admin")
def admin_approve_coach():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or data.get("id")
    return _set_coach_status(user_id, "approved")


@app.route("/api/admin/coaches/reject", methods=["POST"])
@role_required("admin")
def admin_reject_coach():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or data.get("id")
    return _set_coach_status(user_id, "rejected")


@app.route("/api/coaches/<int:user_id>/approval", methods=["POST"])
@role_required("admin")
def review_coach_approval(user_id):
    data = request.get_json(silent=True) or {}
    decision = str(data.get("decision") or "").strip().lower()
    if decision not in ("approve", "reject"):
        return (
            jsonify(
                {"success": False, "message": "Decision must be approve or reject."}
            ),
            400,
        )
    return _set_coach_status(
        user_id, "approved" if decision == "approve" else "rejected"
    )


def _set_coach_status(user_id, status):
    if not user_id:
        return jsonify({"success": False, "message": "user_id is required."}), 400
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    if user["role"] != "coach":
        return jsonify({"success": False, "message": "This user is not a coach."}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET coach_status = %s WHERE id = %s", (status, user_id)
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"Update failed: {exc}"}), 500
    finally:
        db.close()
    action = "approved" if status == "approved" else "rejected"
    send_coach_approval_email(user["email"], user["full_name"], status)
    return jsonify({"success": True, "message": f"Coach {action} successfully."}), 200


register_attendance_routes(app)

