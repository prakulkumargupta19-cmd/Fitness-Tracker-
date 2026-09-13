import os
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# Import authentication decorators from the auth package.
# Handle both direct module import (tests) and package import contexts.
try:
    from backend.auth.decorators import login_required, role_required
except ModuleNotFoundError:
    from auth.decorators import login_required, role_required

# Import authentication helpers from the auth package.
try:
    from backend.auth.helpers import (
        now, now_sql, generate_otp, email_exists, new_code,
        save_otp, get_otp, verify_otp, establish_session,
        canonical_role, valid_password
    )
except ModuleNotFoundError:
    from auth.helpers import (
        now, now_sql, generate_otp, email_exists, new_code,
        save_otp, get_otp, verify_otp, establish_session,
        canonical_role, valid_password
    )

# Import authentication email helpers from the auth package.
try:
    from backend.auth.emails import (
        display_role, send_email, send_otp_email,
        send_account_created_email, send_password_reset_success_email,
        send_signup_confirmation_email, send_password_reset_confirmation_email,
    )
except ModuleNotFoundError:
    from auth.emails import (
        display_role, send_email, send_otp_email,
        send_account_created_email, send_password_reset_success_email,
        send_signup_confirmation_email, send_password_reset_confirmation_email,
    )

# Import the self-service registration workflow from the auth package.
try:
    from backend.auth.registration import signup
except ModuleNotFoundError:
    from auth.registration import signup
import json
import secrets
import smtplib
import ssl

import pymysql
from dotenv import load_dotenv
import os
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

frontend_candidates = []
configured_frontend = os.getenv("FRONTEND_DIR")
if configured_frontend:
    frontend_candidates.append(os.path.abspath(configured_frontend))
frontend_candidates.extend([
    os.path.join(os.path.dirname(BASE_DIR), "frontend"),
    os.path.join(os.path.dirname(BASE_DIR), "frontend1"),
])
FRONTEND_DIR = next((path for path in frontend_candidates if path and os.path.isdir(path)), os.path.join(os.path.dirname(BASE_DIR), "frontend1"))
OTP_MINUTES = 10

# Import DB configuration and helper from shared module
# The test suite imports this module as a top‑level module (``import app``)
# from the ``backend`` directory, so we use a plain import.
import db
DB_CONFIG = db.DB_CONFIG
get_db = db.get_db

app = Flask(__name__)

_secret = os.getenv("SECRET_KEY")
if not _secret and os.getenv("FITNESS_ALLOW_DEV_SECRET", "false").lower() == "true":
    _secret = "dev-secret-key-32-chars-long"
if not _secret:
    raise RuntimeError(
        "SECRET_KEY environment variable is required.\n"
        "For local dev: set SECRET_KEY=dev-secret-key-32-chars-long\n"
        "For production: use a strong random string."
    )

app.config.update(
    SECRET_KEY=_secret,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.getenv("FLASK_SECURE_COOKIE", "false").lower() == "true",
)
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if allowed_origins:
    CORS(app, origins=allowed_origins, supports_credentials=True)
else:
    CORS(app, resources={r"/api/*": {"origins": []}}, supports_credentials=True)
TEST_MODE = os.getenv("FITNESS_TEST_MODE", "true").lower() == "true"
# Import CSRF validation helper from the new common module.
try:
    from backend.auth.common import validate_csrf_token, CSRF_EXEMPT_PATHS
except ModuleNotFoundError:
    from auth.common import validate_csrf_token, CSRF_EXEMPT_PATHS

@app.before_request
def before_request_csrf():
    """Delegate CSRF validation to :func:`backend.auth.common.validate_csrf_token`.

    The function simply calls the helper and returns its result.  This
    keeps the original behaviour identical while moving the logic to a
    shared module.
    """
    return validate_csrf_token()


# The get_db function is now provided by backend.db; this placeholder is removed.



def today_sql():
    return now().strftime("%Y-%m-%d")



def init_db():
    schema_path = os.path.join(BASE_DIR, "schema.sql")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")

    temp_cfg = {k: v for k, v in DB_CONFIG.items() if k not in ("database", "cursorclass")}
    temp_cfg["cursorclass"] = pymysql.cursors.DictCursor
    temp_conn = pymysql.connect(**temp_cfg)
    try:
        with temp_conn.cursor() as cursor:
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS athlete_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        temp_conn.commit()
    finally:
        temp_conn.close()

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users'")
            existing = cursor.fetchone()
            if not existing:
                with open(schema_path, "r", encoding="utf-8") as f:
                    script = f.read()
                statements = []
                for part in script.split(";"):
                    stmt = part.strip()
                    if not stmt or stmt.startswith("--"):
                        continue
                    statements.append(stmt)
                for stmt in statements:
                    try:
                        cursor.execute(stmt + ";")
                    except pymysql.Error as exc:
                        app.logger.warning("Skipping schema statement due to compatibility: %s | %s", exc, stmt[:200])
                db.commit()
                print("[INIT] Database created from schema.sql")
            else:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS otp_requests (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        email VARCHAR(255) NOT NULL,
                        purpose VARCHAR(50) NOT NULL,
                        otp_hash VARCHAR(255) NOT NULL,
                        payload TEXT,
                        expires_at DATETIME NOT NULL,
                        attempts INT NOT NULL DEFAULT 0,
                        verified TINYINT NOT NULL DEFAULT 0,
                        used TINYINT NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL
                    ) ENGINE=InnoDB
                    """
                )
                db.commit()
                print("[INIT] Database already exists — skipped destructive schema.")
    finally:
        db.close()


def ensure_user_status_column():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM users LIKE 'status'")
            if cursor.fetchone() is None:
                cursor.execute("ALTER TABLE users ADD COLUMN status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'approved' AFTER role")
                db.commit()
    finally:
        db.close()


def count_users():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            row = cursor.fetchone()
            return int((row or {}).get("cnt", 0))
    finally:
        db.close()


def reset_database():
    temp_cfg = {k: v for k, v in DB_CONFIG.items() if k not in ("database", "cursorclass")}
    temp_cfg["cursorclass"] = pymysql.cursors.DictCursor
    temp_conn = pymysql.connect(**temp_cfg)
    try:
        with temp_conn.cursor() as cursor:
            cursor.execute("DROP DATABASE IF EXISTS athlete_tracker")
            cursor.execute("CREATE DATABASE athlete_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        temp_conn.commit()
    finally:
        temp_conn.close()

    init_db()
    ensure_user_status_column()
    ensure_demo_seed()


def ensure_demo_seed():
    if count_users() > 0:
        return

    db = get_db()
    try:
        with db.cursor() as cursor:
            demo_users = [
                ("ADM001", "Admin Kumar", "admin@college.edu", generate_password_hash("1234"), "admin", None, "9876543210", None, None, "approved"),
                ("COA001", "Coach Verma", "verma@college.edu", generate_password_hash("1234"), "coach", "Athletics", "9876543211", "Male", "1985-03-15", "approved"),
                ("COA002", "Coach Sharma", "sharma@college.edu", generate_password_hash("1234"), "coach", "Basketball", "9876543212", "Male", "1982-07-22", "approved"),
                ("ATH001", "Arjun Roy", "arjun@college.edu", generate_password_hash("1234"), "player", "Athletics", "9876543213", "Male", "2005-03-12", "approved"),
                ("ATH002", "Sneha Gupta", "sneha@college.edu", generate_password_hash("1234"), "player", "Basketball", "9876543214", "Female", "2004-07-21", "approved"),
                ("ATH003", "Kabir Ali", "kabir@college.edu", generate_password_hash("1234"), "player", "Football", "9876543215", "Male", "2003-11-18", "approved"),
                ("ATH004", "Meera Das", "meera@college.edu", generate_password_hash("1234"), "player", "Athletics", "9876543216", "Female", "2006-02-02", "approved"),
                ("ATH005", "Rohan Singh", "rohan@college.edu", generate_password_hash("1234"), "player", "Basketball", "9876543217", "Male", "2004-09-30", "approved"),
            ]

            cursor.execute("SELECT user_code, email FROM users")
            existing_codes = {str(row["user_code"]).upper() for row in cursor.fetchall() if row["user_code"]}
            existing_emails = {str(row["email"]).lower() for row in cursor.fetchall() if row["email"]}

            for user in demo_users:
                user_code, name, email, password_hash, role, sport, contact_number, gender, date_of_birth, status = user
                if str(email).lower() in existing_emails:
                    continue
                if user_code.upper() in existing_codes:
                    user_code = new_code(cursor.connection, role)
                cursor.execute(
                    """
                    INSERT INTO users (user_code, name, email, password_hash, role, status, sport, contact_number, gender, date_of_birth)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (user_code, name, email, password_hash, role, status, sport, contact_number, gender, date_of_birth),
                )
                existing_codes.add(user_code.upper())
                existing_emails.add(str(email).lower())

            cursor.execute("SELECT id, email FROM users")
            user_map = {str(row["email"]).lower(): row["id"] for row in cursor.fetchall() if row["email"]}

            assignments = [
                ("verma@college.edu", "arjun@college.edu"),
                ("verma@college.edu", "meera@college.edu"),
                ("sharma@college.edu", "sneha@college.edu"),
                ("sharma@college.edu", "rohan@college.edu"),
                ("verma@college.edu", "kabir@college.edu"),
            ]
            for coach_email, athlete_email in assignments:
                if coach_email not in user_map or athlete_email not in user_map:
                    continue
                coach_id = user_map[coach_email]
                athlete_id = user_map[athlete_email]
                cursor.execute(
                    "SELECT 1 FROM coach_athletes WHERE coach_id=%s AND athlete_id=%s",
                    (coach_id, athlete_id),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO coach_athletes (coach_id, athlete_id) VALUES (%s, %s)",
                        (coach_id, athlete_id),
                    )
        db.commit()
        print("[INIT] Demo accounts ensured.")
    finally:
        db.close()



@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:asset_path>")
def frontend_asset(asset_path):
    return send_from_directory(FRONTEND_DIR, asset_path)


@app.post("/api/register")
def register():
    _, error = signup(request.get_json(silent=True) or {})
    return error or (jsonify(success=True, message="OTP sent to your email."), 201)


@app.post("/api/admin-signup")
def admin_signup():
    return jsonify(success=False, message="Admin accounts are created only by system administrators."), 403


@app.post("/api/account-verification/send")
@app.post("/api/account-verification/resend")
@app.post("/api/admin-signup/resend-otp")
@app.post("/api/verify-otp/resend")
def resend_signup_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    record = get_otp(email, "signup")
    if not record:
        return jsonify(success=False, message="Signup session expired. Please register again."), 400
    payload = json.loads(record["payload"])
    otp = generate_otp()
    save_otp(email, "signup", otp, record["payload"])
    if not send_otp_email(email, payload["name"], "signup", otp):
        return jsonify(success=False, message="Email service unavailable."), 503
    return jsonify(success=True, message="New OTP sent to your email.")


@app.post("/api/account-verification/verify")
@app.post("/api/admin-signup/verify-otp")
def verify_signup_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    if not email or len(otp) != 6:
        return jsonify(success=False, message="Email and 6-digit OTP are required."), 400
    record, error = verify_otp(email, "signup", otp, True)
    if error:
        return jsonify(success=False, message=error), 400
    payload = json.loads(record["payload"])
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM users WHERE lower(email)=%s", (email,))
        if cursor.fetchone():
            return jsonify(success=False, message="Email already registered."), 400
        code = new_code(db, payload["role"])
        cursor.execute(
            "INSERT INTO users (user_code,name,email,password_hash,role,status,sport,contact_number,gender,date_of_birth,email_verified) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
            (
                code,
                payload["name"],
                email,
                payload["password_hash"],
                payload["role"],
                payload.get("status", "approved"),
                payload["sport"],
                payload["contact_number"],
                payload["gender"],
                payload["date_of_birth"],
            ),
        )
        db.commit()
        cursor.execute("SELECT * FROM users WHERE id=%s", (cursor.lastrowid,))
        user = cursor.fetchone()
    except pymysql.Error as error:
        db.rollback()
        app.logger.error("Signup database error: %s", error)
        return jsonify(success=False, message="Unable to create account."), 500
    finally:
        db.close()
    if user["role"] == "coach" and (user.get("status") or "pending") == "pending":
        return jsonify(
            success=True,
            message="Coach account created successfully. Awaiting admin approval before login is allowed.",
            user_code=user["user_code"],
            user={k: user[k] for k in ("id", "name", "email", "role", "user_code")},
        )

    establish_session(user)
    send_account_created_email(email, user["name"], user["role"])
    send_signup_confirmation_email(email, user["name"], user["user_code"])
    return jsonify(
        success=True,
        message="Account verified successfully.",
        user_code=user["user_code"],
        user={k: user[k] for k in ("id", "name", "email", "role", "user_code")},
    )


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = canonical_role(data.get("role", "player"))
    if role == "admin":
        return jsonify(success=False, message="Admins must log in through the admin portal."), 403
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(success=False, message="Please enter a valid email address."), 400
    if not email_exists(email):
        return jsonify(success=False, message="Couldn't find your account. Please check your email or sign up."), 401
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE lower(email)=%s AND role=%s", (email, role))
        user = cursor.fetchone()
    finally:
        db.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(success=False, message="Invalid email or password."), 401

    status = (user.get("status") or "approved").lower()
    if role == "coach" and status != "approved":
        message = "Your coach account is pending admin approval." if status == "pending" else "Your coach account has been rejected."
        return jsonify(success=False, message=message), 403

    establish_session(user)
    return jsonify(
        success=True,
        message="Login successful.",
        user={k: user[k] for k in ("id", "name", "email", "role", "user_code")},
    )


@app.post("/api/admin-login")
def admin_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(success=False, message="Please enter a valid email address."), 400
    if not email_exists(email):
        return jsonify(success=False, message="Couldn't find your admin account."), 401
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE lower(email)=%s AND role='admin'", (email,))
        user = cursor.fetchone()
    finally:
        db.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(success=False, message="Invalid admin email or password."), 401
    otp = generate_otp()
    save_otp(email, "admin_login", otp, str(user["id"]))
    if not send_otp_email(email, user["name"], "admin login", otp):
        return jsonify(success=False, message="Email service unavailable."), 503
    return jsonify(success=True, message="OTP sent to your email.")


@app.post("/api/admin-login/verify-otp")
def verify_admin_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    record, error = verify_otp(email, "admin_login", otp, True)
    if error:
        return jsonify(success=False, message=error), 400
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s AND role='admin'", (record["payload"],))
        user = cursor.fetchone()
    finally:
        db.close()
    if not user:
        return jsonify(success=False, message="Admin account not found."), 401
    establish_session(user)
    return jsonify(
        success=True,
        message="Admin login successful.",
        admin={k: user[k] for k in ("id", "name", "email", "role", "user_code")},
    )


@app.post("/api/admin-login/resend-otp")
def resend_admin_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    record = get_otp(email, "admin_login")
    if not record:
        return jsonify(success=False, message="Login OTP expired. Please log in again."), 400
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (record["payload"],))
        user = cursor.fetchone()
    finally:
        db.close()
    otp = generate_otp()
    save_otp(email, "admin_login", otp, record["payload"])
    if not user or not send_otp_email(email, user["name"], "admin login", otp):
        return jsonify(success=False, message="Email delivery failed."), 503
    return jsonify(success=True, message="New OTP sent to your email.")


@app.post("/api/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(success=False, message="Please enter a valid email address."), 400
    if not email_exists(email):
        return jsonify(success=False, message="Couldn't find your account. Please check your email or sign up."), 404
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE lower(email)=%s", (email,))
        user = cursor.fetchone()
    finally:
        db.close()
    if not user:
        return jsonify(success=False, message="Couldn't find your account."), 404
    otp = generate_otp()
    save_otp(email, "password_reset", otp, str(user["id"]))
    if not send_otp_email(email, user["name"], "password_reset", otp):
        return jsonify(success=False, message="Email service unavailable."), 503
    return jsonify(success=True, message="OTP sent to your email.")


@app.post("/api/forgot-password/resend-otp")
def resend_reset():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    record = get_otp(email, "password_reset")
    if not record:
        return jsonify(success=False, message="Reset session expired. Please request a new OTP."), 400
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (record["payload"],))
        user = cursor.fetchone()
    finally:
        db.close()
    otp = generate_otp()
    save_otp(email, "password_reset", otp, record["payload"])
    if not user or not send_otp_email(email, user["name"], "password_reset", otp):
        return jsonify(success=False, message="Email delivery failed."), 503
    return jsonify(success=True, message="New OTP sent to your email.")


@app.post("/api/verify-otp")
def verify_signup_alias():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    record, error = verify_otp(email, "signup", otp, True)
    if error:
        return jsonify(success=False, message=error), 400
    return jsonify(success=True, message="OTP verified successfully.", email=email, signup_record=bool(record)), 200


@app.post("/api/forgot-password/verify-otp")
def verify_reset():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    _, error = verify_otp(email, "password_reset", otp)
    return (jsonify(success=False, message=error), 400) if error else (jsonify(success=True, message="OTP verified successfully.", email=email), 200)


@app.post("/api/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    password = str(data.get("new_password", data.get("password", "")))
    confirm = str(data.get("confirm_password", password))
    if password != confirm or not valid_password(password):
        return jsonify(success=False, message="Passwords must match and be at least 8 characters."), 400
    record, error = verify_otp(email, "password_reset", otp, True)
    if error:
        return jsonify(success=False, message=error), 400
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (record["payload"],))
        user = cursor.fetchone()
        if not user:
            return jsonify(success=False, message="User account not found."), 404
        cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(password), user["id"]))
        db.commit()
    finally:
        db.close()
    send_password_reset_success_email(email, user["name"])
    send_password_reset_confirmation_email(email, user["name"])
    return jsonify(success=True, message="Password reset successfully.")


@app.get("/api/session")
@login_required
def current_session():
    return jsonify(
        success=True,
        authenticated=True,
        user={
            "id": session["user_id"],
            "name": session.get("user_name"),
            "email": session.get("user_email"),
            "role": session.get("role"),
            "user_code": session.get("user_code"),
        },
    )


@app.get("/api/csrf-token")
def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return jsonify(success=True, csrf_token=token)


@app.get("/api/admin/session")
@role_required("admin")
def admin_session():
    return jsonify(
        success=True,
        authenticated=True,
        admin={
            "id": session["user_id"],
            "user_code": session.get("user_code"),
            "name": session.get("user_name"),
            "email": session.get("user_email"),
            "role": "admin",
        },
    )


@app.post("/api/logout")
@app.post("/api/admin/logout")
def logout():
    session.clear()
    return jsonify(success=True, message="Logged out successfully.")


@app.get("/api/users")
@role_required("admin")
def users():
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT id,user_code,name,email,role,status,sport,contact_number,gender,date_of_birth,created_at,email_verified FROM users ORDER BY id DESC"
        )
        rows = cursor.fetchall()
    finally:
        db.close()

    users_payload = []
    for row in rows:
        user = dict(row)
        status = str(user.get("status") or user.get("account_status") or "approved").strip().lower()
        if status not in {"pending", "approved", "rejected"}:
            status = "approved"
        user["status"] = status
        user["account_status"] = status
        users_payload.append(user)

    return jsonify(success=True, users=users_payload)


@app.patch("/api/users/<int:user_id>/status")
@role_required("admin")
def update_user_status(user_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or "").strip().lower()
    if not status:
        return jsonify(success=False, message="status is required."), 400

    status_map = {
        "active": "approved",
        "approved": "approved",
        "deactivated": "rejected",
        "rejected": "rejected",
        "pending": "pending",
    }
    mapped_status = status_map.get(status)
    if not mapped_status:
        return jsonify(success=False, message="Unsupported status."), 400

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET status=%s WHERE id=%s", (mapped_status, user_id))
        db.commit()
    finally:
        db.close()
    return jsonify(success=True, message="User status updated.")


@app.post("/api/admin/coach-approve")
@role_required("admin")
def approve_coach():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "") or data.get("user_email", "")).strip().lower()
    coach_id = data.get("coach_id")

    if not email and not coach_id:
        return jsonify(success=False, message="coach_id or email is required."), 400

    db = get_db()
    try:
        cursor = db.cursor()
        if coach_id:
            cursor.execute("SELECT * FROM users WHERE id=%s AND role='coach'", (coach_id,))
        else:
            cursor.execute("SELECT * FROM users WHERE lower(email)=%s AND role='coach'", (email,))
        coach = cursor.fetchone()
        if not coach:
            return jsonify(success=False, message="Coach not found."), 404
        cursor.execute("UPDATE users SET status='approved' WHERE id=%s", (coach["id"],))
        db.commit()
    finally:
        db.close()
    return jsonify(success=True, message="Coach account approved.")


@app.post("/api/admin/coach-reject")
@role_required("admin")
def reject_coach():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "") or data.get("user_email", "")).strip().lower()
    coach_id = data.get("coach_id")

    if not email and not coach_id:
        return jsonify(success=False, message="coach_id or email is required."), 400

    db = get_db()
    try:
        cursor = db.cursor()
        if coach_id:
            cursor.execute("SELECT * FROM users WHERE id=%s AND role='coach'", (coach_id,))
        else:
            cursor.execute("SELECT * FROM users WHERE lower(email)=%s AND role='coach'", (email,))
        coach = cursor.fetchone()
        if not coach:
            return jsonify(success=False, message="Coach not found."), 404
        cursor.execute("UPDATE users SET status='rejected' WHERE id=%s", (coach["id"],))
        db.commit()
    finally:
        db.close()
    return jsonify(success=True, message="Coach account rejected.")


def get_athlete_ids_for_coach(coach_id, db):
    cursor = db.cursor()
    cursor.execute("SELECT athlete_id FROM coach_athletes WHERE coach_id=%s", (coach_id,))
    rows = cursor.fetchall()
    return [r["athlete_id"] for r in rows]


def athlete_filter_clause(role, user_id, coach_athlete_ids):
    if role == "admin":
        return "", ()
    if role == "coach":
        if not coach_athlete_ids:
            return " AND 1=0", ()
        placeholders = ",".join("%s" for _ in coach_athlete_ids)
        return f" AND athlete_id IN ({placeholders})", tuple(coach_athlete_ids)
    return " AND athlete_id=%s", (user_id,)


def _validate_coach_owns_athlete(coach_id, athlete_id):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM coach_athletes WHERE coach_id=%s AND athlete_id=%s", (coach_id, athlete_id))
        assigned = cursor.fetchone()
    finally:
        db.close()
    if not assigned:
        return jsonify(success=False, message="You are not assigned to this athlete."), 403
    return None


@app.get("/api/assessments")
@login_required
def get_assessments():
    db = get_db()
    try:
        coach_ids = get_athlete_ids_for_coach(session["user_id"], db) if session["role"] == "coach" else []
        where, params = athlete_filter_clause(session["role"], session["user_id"], coach_ids)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM physical_assessments WHERE 1=1{where} ORDER BY assessment_date DESC", params)
        rows = cursor.fetchall()
        return jsonify(success=True, assessments=[dict(r) for r in rows])
    finally:
        db.close()


@app.get("/api/training-sessions")
@login_required
def get_training_sessions():
    db = get_db()
    try:
        coach_ids = get_athlete_ids_for_coach(session["user_id"], db) if session["role"] == "coach" else []
        where, params = athlete_filter_clause(session["role"], session["user_id"], coach_ids)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM training_sessions WHERE 1=1{where} ORDER BY session_date DESC", params)
        rows = cursor.fetchall()
        return jsonify(success=True, sessions=[dict(r) for r in rows])
    finally:
        db.close()


@app.get("/api/goals")
@login_required
def get_goals():
    db = get_db()
    try:
        coach_ids = get_athlete_ids_for_coach(session["user_id"], db) if session["role"] == "coach" else []
        where, params = athlete_filter_clause(session["role"], session["user_id"], coach_ids)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM goals WHERE 1=1{where} ORDER BY target_date DESC", params)
        rows = cursor.fetchall()
        return jsonify(success=True, goals=[dict(r) for r in rows])
    finally:
        db.close()


@app.get("/api/feedback")
@login_required
def get_feedback():
    db = get_db()
    try:
        coach_ids = get_athlete_ids_for_coach(session["user_id"], db) if session["role"] == "coach" else []
        where, params = athlete_filter_clause(session["role"], session["user_id"], coach_ids)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM coach_feedback WHERE 1=1{where} ORDER BY feedback_date DESC", params)
        rows = cursor.fetchall()
        return jsonify(success=True, feedback=[dict(r) for r in rows])
    finally:
        db.close()


@app.get("/api/coach/athletes")
@role_required("coach")
def get_coach_athletes():
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT u.id, u.user_code, u.name, u.email, u.role, u.sport, u.contact_number, u.gender, u.date_of_birth, u.created_at FROM users u JOIN coach_athletes ca ON u.id = ca.athlete_id WHERE ca.coach_id=%s",
            (session["user_id"],),
        )
        rows = cursor.fetchall()
        return jsonify(success=True, athletes=[dict(r) for r in rows])
    finally:
        db.close()


@app.post("/api/assessments")
@role_required("coach")
def create_assessment():
    data = request.get_json(silent=True) or {}
    athlete_id = data.get("athlete_id")
    if not athlete_id:
        return jsonify(success=False, message="athlete_id is required."), 400
    err = _validate_coach_owns_athlete(session["user_id"], athlete_id)
    if err:
        return err
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO physical_assessments (athlete_id,coach_id,assessment_date,height_cm,weight_kg,bmi,assessment_remarks) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                athlete_id,
                session["user_id"],
                data.get("assessment_date", today_sql()),
                data.get("height_cm"),
                data.get("weight_kg"),
                data.get("bmi"),
                data.get("assessment_remarks"),
            ),
        )
        db.commit()
        return jsonify(success=True, message="Assessment recorded."), 201
    except pymysql.Error as e:
        db.rollback()
        app.logger.error("Assessment insert error: %s", e)
        return jsonify(success=False, message="Database error."), 500
    finally:
        db.close()


@app.post("/api/training-sessions")
@role_required("coach")
def create_training_session():
    data = request.get_json(silent=True) or {}
    athlete_id = data.get("athlete_id")
    if not athlete_id:
        return jsonify(success=False, message="athlete_id is required."), 400
    err = _validate_coach_owns_athlete(session["user_id"], athlete_id)
    if err:
        return err
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO training_sessions (athlete_id,coach_id,session_date,sport_type,duration_minutes,intensity_level) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                athlete_id,
                session["user_id"],
                data.get("session_date", today_sql()),
                data.get("sport_type"),
                data.get("duration_minutes"),
                data.get("intensity_level"),
            ),
        )
        db.commit()
        return jsonify(success=True, message="Training session recorded."), 201
    except pymysql.Error:
        db.rollback()
        return jsonify(success=False, message="Database error."), 500
    finally:
        db.close()


@app.post("/api/goals")
@role_required("coach")
def create_goal():
    data = request.get_json(silent=True) or {}
    athlete_id = data.get("athlete_id")
    goal_title = str(data.get("goal_title", "")).strip()
    if not athlete_id:
        return jsonify(success=False, message="athlete_id is required."), 400
    if not goal_title:
        return jsonify(success=False, message="goal_title is required."), 400
    err = _validate_coach_owns_athlete(session["user_id"], athlete_id)
    if err:
        return err
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO goals (athlete_id,coach_id,goal_title,goal_type,target_value,target_date) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                athlete_id,
                session["user_id"],
                goal_title,
                data.get("goal_type"),
                data.get("target_value"),
                data.get("target_date"),
            ),
        )
        db.commit()
        return jsonify(success=True, message="Goal created."), 201
    except pymysql.Error:
        db.rollback()
        return jsonify(success=False, message="Database error."), 500
    finally:
        db.close()


@app.post("/api/feedback")
@role_required("coach")
def create_feedback():
    data = request.get_json(silent=True) or {}
    athlete_id = data.get("athlete_id")
    if not athlete_id:
        return jsonify(success=False, message="athlete_id is required."), 400
    err = _validate_coach_owns_athlete(session["user_id"], athlete_id)
    if err:
        return err
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO coach_feedback (athlete_id,coach_id,feedback_date,performance_summary,overall_rating) VALUES (%s,%s,%s,%s,%s)",
            (
                athlete_id,
                session["user_id"],
                data.get("feedback_date", today_sql()),
                data.get("performance_summary"),
                data.get("overall_rating"),
            ),
        )
        db.commit()
        return jsonify(success=True, message="Feedback submitted."), 201
    except pymysql.Error:
        db.rollback()
        return jsonify(success=False, message="Database error."), 500
    finally:
        db.close()


@app.get("/api/coach-athletes")
@role_required("admin")
def get_admin_coach_athlete_assignments():
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT ca.coach_id, ca.athlete_id, ca.assigned_date,
                   c.name AS coach_name, c.user_code AS coach_code,
                   a.name AS athlete_name, a.user_code AS athlete_code
            FROM coach_athletes ca
            JOIN users c ON c.id = ca.coach_id
            JOIN users a ON a.id = ca.athlete_id
            ORDER BY ca.assigned_date DESC
            """
        )
        assignments = cursor.fetchall()
        return jsonify(success=True, assignments=assignments)
    finally:
        db.close()


@app.post("/api/coach-athletes")
@role_required("admin")
def assign_coach_athlete():
    data = request.get_json(silent=True) or {}
    coach_id = data.get("coach_id")
    athlete_id = data.get("athlete_id")

    if not coach_id or not athlete_id:
        return jsonify(success=False, message="coach_id and athlete_id are required."), 400

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, name FROM users WHERE id=%s AND role='coach'", (coach_id,))
        coach = cursor.fetchone()
        if not coach:
            return jsonify(success=False, message="Invalid coach."), 404

        cursor.execute("SELECT id, name FROM users WHERE id=%s AND role='player'", (athlete_id,))
        athlete = cursor.fetchone()
        if not athlete:
            return jsonify(success=False, message="Invalid athlete."), 404

        cursor.execute("SELECT 1 FROM coach_athletes WHERE coach_id=%s AND athlete_id=%s", (coach_id, athlete_id))
        if cursor.fetchone():
            return jsonify(success=False, message="Coach is already assigned to this athlete."), 409

        cursor.execute("INSERT INTO coach_athletes (coach_id, athlete_id) VALUES (%s, %s)", (coach_id, athlete_id))
        db.commit()
        return jsonify(success=True, message="Coach assigned to athlete successfully."), 201
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.delete("/api/coach-athletes")
@role_required("admin")
def remove_coach_athlete():
    data = request.get_json(silent=True) or {}
    coach_id = data.get("coach_id")
    athlete_id = data.get("athlete_id")

    if not coach_id or not athlete_id:
        return jsonify(success=False, message="coach_id and athlete_id are required."), 400

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM coach_athletes WHERE coach_id=%s AND athlete_id=%s", (coach_id, athlete_id))
        if not cursor.fetchone():
            return jsonify(success=False, message="Assignment does not exist."), 404

        cursor.execute("DELETE FROM coach_athletes WHERE coach_id=%s AND athlete_id=%s", (coach_id, athlete_id))
        db.commit()
        return jsonify(success=True, message="Coach assignment removed successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


init_db()
ensure_user_status_column()
ensure_demo_seed()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)