from dotenv import load_dotenv
load_dotenv()

"""Athlete Tracker — Production-hardened Flask backend (MySQL).

API Contract (for frontend developers):
- All endpoints return JSON: {"success": bool, "message": str, ...data}
- Auth endpoints set Flask session cookie automatically
- All data endpoints require active session (401 if missing)
- Role-based access: player sees own data, coach sees assigned athletes, admin sees all
- Base URL: use relative paths (e.g., "/api/login") — never hardcode localhost:5000
"""
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
import json, os, secrets, smtplib, pymysql, ssl
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
OTP_MINUTES = 10

# ── MySQL Configuration ─────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "fitness_user"),
    "password": os.getenv("DB_PASSWORD", "StrongPassword123!"),
    "database": os.getenv("DB_NAME", "athlete_tracker"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

# ── Flask setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)

# SECURITY: No hardcoded fallback secret. Fail fast in production.
_secret = os.getenv("SECRET_KEY")
if not _secret:
    raise RuntimeError(
        "SECRET_KEY environment variable is required.\n"
        "For local dev:  set SECRET_KEY=dev-secret-key-32-chars-long\n"
        "For production: use a strong random string."
    )
app.config.update(
    SECRET_KEY=_secret,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.getenv("FLASK_SECURE_COOKIE", "false").lower() == "true",
)
CORS(app, supports_credentials=True)

# Test mode: prints OTP to console instead of sending email
TEST_MODE = False

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_db():
    """Return a fresh MySQL connection."""
    return pymysql.connect(**DB_CONFIG)

def now():
    return datetime.now(timezone.utc)

def now_sql():
    """Return MySQL-compatible DATETIME string."""
    return now().strftime("%Y-%m-%d %H:%M:%S")

def today_sql():
    """Return MySQL-compatible DATE string."""
    return now().strftime("%Y-%m-%d")

def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"

def canonical_role(role):
    r = str(role or "").lower()
    return "player" if r == "student" else r

def display_role(role):
    return "Student" if role == "player" else role.capitalize()

def valid_password(password):
    return len(password) >= 8

def email_exists(email):
    """Check if an email is already registered in the database."""
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM users WHERE lower(email)=%s", (email,))
        return cursor.fetchone() is not None
    finally:
        db.close()

def init_db():
    """Create tables on first startup ONLY. Never drops existing data."""
    schema_path = os.path.join(BASE_DIR, "schema.sql")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")

    # 1. Ensure database exists
    temp_cfg = {k: v for k, v in DB_CONFIG.items() if k not in ("database", "cursorclass")}
    temp_cfg["cursorclass"] = pymysql.cursors.DictCursor
    temp_conn = pymysql.connect(**temp_cfg)
    try:
        with temp_conn.cursor() as cursor:
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS athlete_tracker "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        temp_conn.commit()
    finally:
        temp_conn.close()

    # 2. Run schema (idempotent)
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE \'users\'")
            existing = cursor.fetchone()

            if not existing:
                with open(schema_path, "r", encoding="utf-8") as f:
                    statements = f.read().split(";")
                    for stmt in statements:
                        stmt = stmt.strip()
                        if stmt and not stmt.startswith("--") and len(stmt) > 5:
                            cursor.execute(stmt + ";")
                db.commit()
                print("[INIT] Database created from schema.sql")
            else:
                # Backward compatibility: ensure otp_requests exists
                cursor.execute("""
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
                """)
                db.commit()
                print("[INIT] Database already exists — skipped destructive schema.")
    finally:
        db.close()

# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(recipient, subject, body):
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    if not username or not password:
        app.logger.warning("Email not configured: set MAIL_USERNAME and MAIL_PASSWORD")
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.getenv("MAIL_FROM", username)
    message["To"] = recipient
    message.set_content(body)
    try:
        with smtplib.SMTP(
            os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            int(os.getenv("MAIL_PORT", "587")),
            timeout=15,
        ) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException, ValueError) as error:
        app.logger.error("Email delivery failed: %s", error)
        return False

def send_otp_email(email, name, purpose, otp):
    action = "password reset" if purpose == "password_reset" else "account verification"
    if TEST_MODE:
        print(f"\n[TEST MODE] OTP for {email} ({purpose}): {otp}\n")
        return True
    return send_email(
        email,
        f"Athlete Tracker – {action.title()} OTP",
        f"Hello {name},\n\nYour Athlete Tracker {action} OTP is:\n\n{otp}\n\n"
        f"This OTP expires in {OTP_MINUTES} minutes.\n\nThank you,\nAthlete Tracker Team",
    )

def send_account_created_email(email, name, role):
    if TEST_MODE:
        print(f"[TEST MODE] Account created for {email} as {role}")
        return True
    return send_email(
        email,
        "Athlete Tracker Account Created Successfully",
        f"Hello {name},\n\nCongratulations!\n\nYour Athlete Tracker account has been created.\n"
        f"Account Type: {display_role(role)}\n\nYou can now log in.\n\nThank you,\nAthlete Tracker Team",
    )

def send_password_reset_success_email(email, name):
    if TEST_MODE:
        print(f"[TEST MODE] Password reset successful for {email}")
        return True
    return send_email(
        email,
        "Password Reset Successful",
        f"Hello {name},\n\nYour password has been reset successfully.\n"
        f"If you did not perform this action, contact the administrator.\n\nThank you,\nAthlete Tracker Team",
    )

def send_signup_confirmation_email(email, name, user_code):
    """Send account creation confirmation email."""
    if TEST_MODE:
        print(f"[TEST MODE] Signup confirmation sent to {email}")
        return True
    return send_email(
        email,
        "Welcome to Athlete Tracker — Account Created Successfully",
        f"Hello {name},\n\n"
        f"Welcome to Athlete Tracker! Your account has been successfully created.\n\n"
        f"Your Athlete Code: {user_code}\n"
        f"Email: {email}\n\n"
        f"You can now log in to your dashboard and start tracking your fitness performance.\n\n"
        f"Thank you,\nAthlete Tracker Team",
    )

def send_password_reset_confirmation_email(email, name):
    """Send password reset confirmation email."""
    if TEST_MODE:
        print(f"[TEST MODE] Password reset confirmation sent to {email}")
        return True
    return send_email(
        email,
        "Password Reset Confirmation",
        f"Hello {name},\n\n"
        f"Your Athlete Tracker password has been successfully reset.\n\n"
        f"If you did not perform this action, please contact the administrator immediately.\n\n"
        f"Thank you,\nAthlete Tracker Team",
    )

# ── OTP storage ───────────────────────────────────────────────────────────────
def save_otp(email, purpose, otp, payload=""):
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE otp_requests SET used=1 WHERE email=%s AND purpose=%s AND used=0",
            (email, purpose),
        )
        cursor.execute(
            "INSERT INTO otp_requests (email,purpose,otp_hash,payload,expires_at,created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
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
            "SELECT * FROM otp_requests WHERE email=%s AND purpose=%s AND used=0 "
            "ORDER BY id DESC LIMIT 1",
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
    # Make expires_at offset-aware if it's naive (MySQL returns naive datetimes)
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
            "UPDATE otp_requests SET verified=1,used=%s WHERE id=%s",
            (1 if consume else 0, record["id"]),
        )
        db.commit()
    finally:
        db.close()
    return record, None

# ── User code generator ───────────────────────────────────────────────────────
def new_code(db, role):
    prefix = {"admin": "ADM", "coach": "COA", "player": "ATH"}[role]
    cursor = db.cursor()
    cursor.execute("SELECT user_code FROM users WHERE user_code LIKE %s", (prefix + "%",))
    existing = {r["user_code"] for r in cursor.fetchall()}
    number = 1
    while f"{prefix}{number:03d}" in existing:
        number += 1
    return f"{prefix}{number:03d}"

# ── Session ───────────────────────────────────────────────────────────────────
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

# ── Auth decorators ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(success=False, message="Unauthorized — please log in"), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify(success=False, message="Unauthorized"), 401
            if session.get("role") not in roles:
                return jsonify(success=False, message="Forbidden — insufficient privileges"), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ═══════════════════════════════════════════════════════════════════════════════
#  STATIC FILES
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.get("/<path:asset_path>")
def frontend_asset(asset_path):
    return send_from_directory(FRONTEND_DIR, asset_path)

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
def signup(data, forced_role=None):
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = forced_role or canonical_role(data.get("role"))
    # SECURITY: Public registration cannot create admins
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
    # Check if email already exists (Google-style error)
    if email_exists(email):
        return None, (jsonify(success=False, message="An account already exists with this email. Try signing in instead."), 400)

    # Check if there's a pending signup OTP for this email
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

@app.post("/api/register")
def register():
    _, error = signup(request.get_json(silent=True) or {})
    return error or (jsonify(success=True, message="OTP sent to your email."), 201)


@app.post("/api/account-verification/send")
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
            "INSERT INTO users (user_code,name,email,password_hash,role,sport,contact_number,gender,date_of_birth,email_verified) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1)",
            (
                code,
                payload["name"],
                email,
                payload["password_hash"],
                payload["role"],
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
    # SECURITY: Admin must use /api/admin-login with OTP
    if role == "admin":
        return jsonify(success=False, message="Admins must log in through the admin portal."), 403
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(success=False, message="Please enter a valid email address."), 400
    # Google-style: check if email exists at all before password check
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
    # Google-style: check if email exists before sending OTP
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

@app.post("/api/forgot-password/verify-otp")
@app.post("/api/verify-otp")
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

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT (SECURED)
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/users")
@role_required("admin")
def users():
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT id,user_code,name,email,role,sport,contact_number,gender,date_of_birth,created_at,email_verified "
            "FROM users ORDER BY id DESC"
        )
        rows = cursor.fetchall()
    finally:
        db.close()
    return jsonify(success=True, users=[dict(row) for row in rows])

# ═══════════════════════════════════════════════════════════════════════════════
#  DATA ENDPOINTS — Role-based access
# ═══════════════════════════════════════════════════════════════════════════════

def get_athlete_ids_for_coach(coach_id, db):
    """Return list of athlete IDs assigned to this coach."""
    cursor = db.cursor()
    cursor.execute("SELECT athlete_id FROM coach_athletes WHERE coach_id=%s", (coach_id,))
    rows = cursor.fetchall()
    return [r["athlete_id"] for r in rows]

def athlete_filter_clause(role, user_id, coach_athlete_ids):
    """Return SQL WHERE fragment and params for role-based athlete data filtering."""
    if role == "admin":
        return "", ()
    if role == "coach":
        if not coach_athlete_ids:
            return " AND 1=0", ()  # No athletes assigned → empty result
        placeholders = ",".join("%s" for _ in coach_athlete_ids)
        return f" AND athlete_id IN ({placeholders})", tuple(coach_athlete_ids)
    # player
    return " AND athlete_id=%s", (user_id,)

def _validate_coach_owns_athlete(coach_id, athlete_id):
    """Return error response tuple if coach is not assigned to athlete, else None."""
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT 1 FROM coach_athletes WHERE coach_id=%s AND athlete_id=%s",
            (coach_id, athlete_id)
        )
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
        cursor.execute(
            f"SELECT * FROM physical_assessments WHERE 1=1{where} ORDER BY assessment_date DESC", params
        )
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
        cursor.execute(
            f"SELECT * FROM training_sessions WHERE 1=1{where} ORDER BY session_date DESC", params
        )
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
        cursor.execute(
            f"SELECT * FROM goals WHERE 1=1{where} ORDER BY target_date DESC", params
        )
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
        cursor.execute(
            f"SELECT * FROM coach_feedback WHERE 1=1{where} ORDER BY feedback_date DESC", params
        )
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
            "SELECT u.id, u.user_code, u.name, u.email, u.role, u.sport, u.contact_number, u.gender, u.date_of_birth, u.created_at "
            "FROM users u "
            "JOIN coach_athletes ca ON u.id = ca.athlete_id "
            "WHERE ca.coach_id=%s",
            (session["user_id"],),
        )
        rows = cursor.fetchall()
        return jsonify(success=True, athletes=[dict(r) for r in rows])
    finally:
        db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  WRITE ENDPOINTS (Coach only, with assignment validation)
# ═══════════════════════════════════════════════════════════════════════════════
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
            "INSERT INTO physical_assessments (athlete_id,coach_id,assessment_date,height_cm,weight_kg,bmi,assessment_remarks) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
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
            "INSERT INTO training_sessions (athlete_id,coach_id,session_date,sport_type,duration_minutes,intensity_level) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
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
    except pymysql.Error as e:
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
            "INSERT INTO goals (athlete_id,coach_id,goal_title,goal_type,target_value,target_date) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
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
    except pymysql.Error as e:
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
            "INSERT INTO coach_feedback (athlete_id,coach_id,feedback_date,performance_summary,overall_rating) "
            "VALUES (%s,%s,%s,%s,%s)",
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
    except pymysql.Error as e:
        db.rollback()
        return jsonify(success=False, message="Database error."), 500
    finally:
        db.close()
        # ============================================================
# ADMIN - COACH / ATHLETE ASSIGNMENTS
# ============================================================

@app.route("/api/coach-athletes", methods=["GET"])
@role_required("admin")
def get_admin_coach_athlete_assignments():
    db = get_db()

    try:
        cursor = db.cursor()

        cursor.execute("""
            SELECT
                ca.coach_id,
                ca.athlete_id,
                ca.assigned_date,
                c.name AS coach_name,
                c.user_code AS coach_code,
                a.name AS athlete_name,
                a.user_code AS athlete_code
            FROM coach_athletes ca
            JOIN users c ON c.id = ca.coach_id
            JOIN users a ON a.id = ca.athlete_id
            ORDER BY ca.assigned_date DESC
        """)

        assignments = cursor.fetchall()

        return jsonify(
            success=True,
            assignments=assignments
        )

    finally:
        db.close()


@app.route("/api/coach-athletes", methods=["POST"])
@role_required("admin")
def assign_coach_athlete():
    data = request.get_json() or {}

    coach_id = data.get("coach_id")
    athlete_id = data.get("athlete_id")

    if not coach_id or not athlete_id:
        return jsonify(
            success=False,
            message="coach_id and athlete_id are required."
        ), 400

    db = get_db()

    try:
        cursor = db.cursor()

        # Check coach exists and has coach role
        cursor.execute("""
            SELECT id, name
            FROM users
            WHERE id=%s AND role='coach'
        """, (coach_id,))

        coach = cursor.fetchone()

        if not coach:
            return jsonify(
                success=False,
                message="Invalid coach."
            ), 404

        # Check athlete exists and has player role
        cursor.execute("""
            SELECT id, name
            FROM users
            WHERE id=%s AND role='player'
        """, (athlete_id,))

        athlete = cursor.fetchone()

        if not athlete:
            return jsonify(
                success=False,
                message="Invalid athlete."
            ), 404

        # Check whether assignment already exists
        cursor.execute("""
            SELECT 1
            FROM coach_athletes
            WHERE coach_id=%s AND athlete_id=%s
        """, (coach_id, athlete_id))

        existing = cursor.fetchone()

        if existing:
            return jsonify(
                success=False,
                message="Coach is already assigned to this athlete."
            ), 409

        # Create assignment
        cursor.execute("""
            INSERT INTO coach_athletes
            (coach_id, athlete_id)
            VALUES (%s, %s)
        """, (coach_id, athlete_id))

        db.commit()

        return jsonify(
            success=True,
            message="Coach assigned to athlete successfully."
        ), 201

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.route("/api/coach-athletes", methods=["DELETE"])
@role_required("admin")
def remove_coach_athlete():
    data = request.get_json() or {}

    coach_id = data.get("coach_id")
    athlete_id = data.get("athlete_id")

    if not coach_id or not athlete_id:
        return jsonify(
            success=False,
            message="coach_id and athlete_id are required."
        ), 400

    db = get_db()

    try:
        cursor = db.cursor()

        # Check assignment exists
        cursor.execute("""
            SELECT 1
            FROM coach_athletes
            WHERE coach_id=%s AND athlete_id=%s
        """, (coach_id, athlete_id))

        assignment = cursor.fetchone()

        if not assignment:
            return jsonify(
                success=False,
                message="Assignment does not exist."
            ), 404

        # Remove assignment
        cursor.execute("""
            DELETE FROM coach_athletes
            WHERE coach_id=%s AND athlete_id=%s
        """, (coach_id, athlete_id))

        db.commit()

        return jsonify(
            success=True,
            message="Coach assignment removed successfully."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ═══════════════════════════════════════════════════════════════════════════════
init_db()

if __name__ == "__main__":
    # SECURITY: debug only when explicitly enabled
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)