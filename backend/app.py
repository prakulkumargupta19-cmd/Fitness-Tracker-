"""Athlete Tracker — Production-hardened Flask backend.

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
import json, os, secrets, smtplib, sqlite3, ssl
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "athlete_tracker.db")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend1")
OTP_MINUTES = 3
OTP_RESEND_SECONDS = 60

def load_local_env():
    """Load a local .env without adding credentials to source control.

    Existing process environment values always win, which keeps production
    deployment configuration authoritative.
    """
    for path in (os.path.join(os.path.dirname(BASE_DIR), ".env"), os.path.join(BASE_DIR, ".env")):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_local_env()

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

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints
    return db

def now():
    return datetime.now(timezone.utc)

def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"

def canonical_role(role):
    r = str(role or "").lower()
    return "player" if r == "student" else r

def display_role(role):
    return "Student" if role == "player" else role.capitalize()

def valid_password(password):
    return len(password) >= 8

def valid_email(email):
    return "@" in email and "." in email.rsplit("@", 1)[-1] and len(email) <= 254

def init_db():
    """Create tables on first startup ONLY. Never drops existing data."""
    schema_path = os.path.join(BASE_DIR, "schema.sql")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")

    with sqlite3.connect(DATABASE) as db:
        # Check if database is already initialized
        existing = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()

        if not existing:
            # First run — safe to run full schema (including any DROPs for clean start)
            with open(schema_path, "r", encoding="utf-8") as f:
                db.executescript(f.read())
            print("[INIT] Database created from schema.sql")
        else:
            # Already initialized — only add missing tables (migrations)
            # Ensure otp_requests exists (backward compatibility)
            db.execute("""
                CREATE TABLE IF NOT EXISTS otp_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    otp_hash TEXT NOT NULL,
                    payload TEXT,
                    expires_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    verified INTEGER NOT NULL DEFAULT 0,
                    used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_otp_requests_lookup ON otp_requests(email, purpose, used)")
            columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
            if "account_status" not in columns:
                db.execute("ALTER TABLE users ADD COLUMN account_status TEXT NOT NULL DEFAULT 'active'")
            # This application never persists a new unverified user: registrations
            # stay only in otp_requests until verification succeeds. Thus rows with
            # email_verified=0 here are legacy accounts from before that design.
            db.execute("UPDATE users SET email_verified=1 WHERE email_verified=0")
            db.commit()
            print("[INIT] Database already exists — skipped destructive schema.")

# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(recipient, subject, body):
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    if not username or not password:
        app.logger.warning("Email not configured: set MAIL_USERNAME and MAIL_PASSWORD in .env")
        return False
    server_name = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    try:
        port = int(os.getenv("MAIL_PORT", "587"))
    except ValueError:
        app.logger.error("Email delivery failed: MAIL_PORT must be a number")
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.getenv("MAIL_FROM", username)
    message["To"] = recipient
    message.set_content(body)
    try:
        use_ssl = os.getenv("MAIL_USE_SSL", "false").lower() == "true" or port == 465
        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(server_name, port, timeout=15, context=ssl.create_default_context()) if use_ssl else smtp_class(server_name, port, timeout=15) as server:
            if not use_ssl:
                server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException, ValueError) as error:
        app.logger.error("Email delivery failed: %s", error)
        return False

def send_otp_email(email, name, purpose, otp):
    action = {
        "password_reset": "password reset",
        "login": "login verification",
        "signup": "account verification",
    }.get(purpose, "verification")
    return send_email(
        email,
        f"Athlete Tracker – {action.title()} OTP",
        f"Hello {name},\n\nYour Athlete Tracker {action} OTP is:\n\n{otp}\n\n"
        f"This OTP expires in {OTP_MINUTES} minutes.\n\nThank you,\nAthlete Tracker Team",
    )

def send_account_created_email(email, name, role):
    return send_email(
        email,
        "Athlete Tracker Account Created Successfully",
        f"Hello {name},\n\nCongratulations!\n\nYour Athlete Tracker account has been created.\n"
        f"Account Type: {display_role(role)}\n\nYou can now log in.\n\nThank you,\nAthlete Tracker Team",
    )

def send_password_reset_success_email(email, name):
    return send_email(
        email,
        "Password Reset Successful",
        f"Hello {name},\n\nYour password has been reset successfully.\n"
        f"If you did not perform this action, contact the administrator.\n\nThank you,\nAthlete Tracker Team",
    )

# ── OTP storage ───────────────────────────────────────────────────────────────
def save_otp(email, purpose, otp, payload=""):
    db = get_db()
    try:
        db.execute(
            "UPDATE otp_requests SET used=1 WHERE email=? AND purpose=? AND used=0",
            (email, purpose),
        )
        db.execute(
            "INSERT INTO otp_requests (email,purpose,otp_hash,payload,expires_at,created_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                email,
                purpose,
                generate_password_hash(otp),
                payload,
                (now() + timedelta(minutes=OTP_MINUTES)).isoformat(),
                now().isoformat(),
            ),
        )
        db.commit()
    finally:
        db.close()

def can_resend_otp(email, purpose):
    """Apply a server-side resend cooldown before invalidating the current OTP."""
    record = get_otp(email, purpose)
    if not record:
        return False, None
    age = (now() - datetime.fromisoformat(record["created_at"])).total_seconds()
    return age >= OTP_RESEND_SECONDS, record

def get_otp(email, purpose):
    db = get_db()
    try:
        return db.execute(
            "SELECT * FROM otp_requests WHERE email=? AND purpose=? AND used=0 "
            "ORDER BY id DESC LIMIT 1",
            (email, purpose),
        ).fetchone()
    finally:
        db.close()

def verify_otp(email, purpose, otp, consume=False):
    record = get_otp(email, purpose)
    if not record or datetime.fromisoformat(record["expires_at"]) < now():
        return None, "OTP expired. Please request a new OTP."
    if record["attempts"] >= 5:
        return None, "Too many incorrect attempts. Please request a new OTP."
    if not check_password_hash(record["otp_hash"], otp):
        db = get_db()
        try:
            db.execute("UPDATE otp_requests SET attempts=attempts+1 WHERE id=?", (record["id"],))
            db.commit()
        finally:
            db.close()
        return None, "Invalid OTP"
    db = get_db()
    try:
        db.execute(
            "UPDATE otp_requests SET verified=1,used=? WHERE id=?",
            (1 if consume else 0, record["id"]),
        )
        db.commit()
    finally:
        db.close()
    return record, None

# ── User code generator ───────────────────────────────────────────────────────
def new_code(db, role):
    prefix = {"admin": "ADM", "coach": "COA", "player": "ATH"}[role]
    existing = {r[0] for r in db.execute("SELECT user_code FROM users WHERE user_code LIKE ?", (prefix + "%",))}
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
        db = get_db()
        try:
            user = db.execute("SELECT role, email_verified, account_status FROM users WHERE id=?", (session["user_id"],)).fetchone()
        finally:
            db.close()
        if not user or not user["email_verified"] or user["account_status"] != "active":
            session.clear()
            return jsonify(success=False, message="Unauthorized — account is unavailable"), 401
        session["role"] = user["role"]
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify(success=False, message="Unauthorized"), 401
            db = get_db()
            try:
                user = db.execute("SELECT role, email_verified, account_status FROM users WHERE id=?", (session["user_id"],)).fetchone()
            finally:
                db.close()
            if not user or not user["email_verified"] or user["account_status"] != "active":
                session.clear()
                return jsonify(success=False, message="Unauthorized — account is unavailable"), 401
            session["role"] = user["role"]
            if user["role"] not in roles:
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

# Protect dashboard documents themselves as well as their APIs.  The catch-all
# static route below remains appropriate for public pages and static assets.
@app.get("/admin/admin-dashboard.html")
@role_required("admin")
def admin_dashboard():
    return send_from_directory(FRONTEND_DIR, "admin/admin-dashboard.html")

@app.get("/coach/coach-dashboard.html")
@role_required("coach")
def coach_dashboard():
    return send_from_directory(FRONTEND_DIR, "coach/coach-dashboard.html")

@app.get("/student/student-dashboard.html")
@role_required("player")
def student_dashboard():
    return send_from_directory(FRONTEND_DIR, "student/student-dashboard.html")

@app.get("/<path:asset_path>")
def frontend_asset(asset_path):
    return send_from_directory(FRONTEND_DIR, asset_path)

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
def signup(data, forced_role=None, allow_admin=False):
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirm_password", ""))
    role = forced_role or canonical_role(data.get("role"))
    # SECURITY: public registration is limited to student and coach accounts.
    if role == "admin" and not allow_admin:
        return None, (jsonify(success=False, message="Admin accounts cannot be created through public registration."), 403)
    if password != confirm_password:
        return None, (jsonify(success=False, message="Passwords do not match."), 400)
    permitted_roles = {"player", "coach", "admin"} if allow_admin else {"player", "coach"}
    if not name or not valid_email(email) or not valid_password(password) or role not in permitted_roles:
        return None, (jsonify(success=False, message="Enter a valid name, email, and password (min 8 chars)."), 400)
    db = get_db()
    try:
        # Enforce one email address -> one account role.
        existing_user = db.execute(
            "SELECT role FROM users WHERE lower(email)=? LIMIT 1",
            (email,),
        ).fetchone()

        if existing_user:
            role_names = {
                "player": "Student",
                "coach": "Coach",
                "admin": "Admin",
            }
            existing_role_name = role_names.get(
                existing_user["role"],
                str(existing_user["role"]).capitalize(),
            )
            return None, (
                jsonify(
                    success=False,
                    message=(
                        f"This email is already registered as a "
                        f"{existing_role_name}. "
                        "One email can only be used for one account."
                    ),
                ),
                409,
            )

        # Also block the same email while a signup OTP is still pending.
        pending_signup = db.execute(
            """
            SELECT payload
            FROM otp_requests
            WHERE lower(email)=?
              AND purpose='signup'
              AND used=0
            ORDER BY id DESC
            LIMIT 1
            """,
            (email,),
        ).fetchone()
    finally:
        db.close()

    if pending_signup:
        try:
            pending_payload = json.loads(pending_signup["payload"])
            pending_role = pending_payload.get("role")
        except (TypeError, json.JSONDecodeError):
            pending_role = None

        if pending_role:
            role_names = {
                "player": "Student",
                "coach": "Coach",
                "admin": "Admin",
            }
            pending_role_name = role_names.get(
                pending_role,
                str(pending_role).capitalize(),
            )

            if pending_role != role:
                return None, (
                    jsonify(
                        success=False,
                        message=(
                            f"This email already has a pending "
                            f"{pending_role_name} registration. "
                            f"The same email cannot be registered as a "
                            f"{display_role(role)}."
                        ),
                    ),
                    409,
                )

            return None, (
                jsonify(
                    success=False,
                    message=(
                        f"A {pending_role_name} registration is already "
                        "in progress for this email. Please complete "
                        "the OTP verification."
                    ),
                ),
                409,
            )
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

@app.post("/api/admin-signup")
def admin_signup():
    return jsonify(success=False, message="Admin accounts must be provisioned by an existing administrator."), 403

@app.post("/api/admin/users")
@role_required("admin")
def provision_admin():
    """Existing admins may provision another admin through the same email OTP flow."""
    _, error = signup(request.get_json(silent=True) or {}, forced_role="admin", allow_admin=True)
    return error or (jsonify(success=True, message="Admin verification OTP sent to the provided email."), 201)

@app.post("/api/account-verification/send")
@app.post("/api/admin-signup/resend-otp")
def resend_signup_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    allowed, record = can_resend_otp(email, "signup")
    if not record:
        return jsonify(success=False, message="Signup session expired. Please register again."), 400
    if not allowed:
        return jsonify(success=False, message=f"Please wait {OTP_RESEND_SECONDS} seconds before requesting another OTP."), 429
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
        if db.execute("SELECT 1 FROM users WHERE lower(email)=?", (email,)).fetchone():
            return jsonify(success=False, message="Email already registered."), 400
        code = new_code(db, payload["role"])
        cursor = db.execute(
            "INSERT INTO users (user_code,name,email,password_hash,role,sport,contact_number,gender,date_of_birth,email_verified,account_status) "
            "VALUES (?,?,?,?,?,?,?,?,?,1,'active')",
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
        user = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
    except sqlite3.Error as error:
        db.rollback()
        app.logger.error("Signup database error: %s", error)
        return jsonify(success=False, message="Unable to create account."), 500
    finally:
        db.close()
    establish_session(user)
    confirmation_sent = send_account_created_email(email, user["name"], user["role"])
    return jsonify(
        success=True,
        message=("Account verified successfully. A confirmation email has been sent."
                 if confirmation_sent else
                 "Account verified successfully, but the confirmation email could not be sent."),
        user_code=user["user_code"],
        user={k: user[k] for k in ("id", "name", "email", "role", "user_code")},
    )

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE lower(email)=?", (email,)).fetchone()
    finally:
        db.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(success=False, message="Invalid email or password."), 401
    if not user["email_verified"]:
        return jsonify(success=False, message="Email verification is required before login."), 403
    if user["account_status"] != "active":
        return jsonify(success=False, message="Account has been deactivated or is unavailable."), 403
    otp = generate_otp()
    save_otp(email, "login", otp, str(user["id"]))
    if not send_otp_email(email, user["name"], "login", otp):
        return jsonify(success=False, message="Email service unavailable. Please try again later."), 503
    return jsonify(success=True, message="A verification code has been sent to your email.", role=user["role"], expires_in=OTP_MINUTES * 60)

@app.post("/api/admin-login")
def admin_login():
    return login()

@app.post("/api/admin-login/verify-otp")
def verify_admin_login():
    return verify_login()

@app.post("/api/login/verify-otp")
def verify_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    record, error = verify_otp(email, "login", otp, True)
    if error:
        return jsonify(success=False, message=error), 400
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id=?", (record["payload"],)).fetchone()
    finally:
        db.close()
    if not user or not user["email_verified"] or user["account_status"] != "active":
        return jsonify(success=False, message="Account is unavailable."), 401
    establish_session(user)
    return jsonify(
        success=True,
        message="Login successful.",
        user={k: user[k] for k in ("id", "name", "email", "role", "user_code")},
    )

@app.post("/api/admin-login/resend-otp")
def resend_admin_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    allowed, record = can_resend_otp(email, "login")
    if not record:
        return jsonify(success=False, message="Login OTP expired. Please log in again."), 400
    if not allowed:
        return jsonify(success=False, message=f"Please wait {OTP_RESEND_SECONDS} seconds before requesting another OTP."), 429
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id=?", (record["payload"],)).fetchone()
    finally:
        db.close()
    otp = generate_otp()
    save_otp(email, "login", otp, record["payload"])
    if not user or not send_otp_email(email, user["name"], "login", otp):
        return jsonify(success=False, message="Email delivery failed."), 503
    return jsonify(success=True, message="New OTP sent to your email.")

@app.post("/api/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE lower(email)=?", (email,)).fetchone()
    finally:
        db.close()
    if not user or user["account_status"] != "active":
        return jsonify(success=True, message="If an account exists for this email, a verification code has been sent.")
    otp = generate_otp()
    save_otp(email, "password_reset", otp, str(user["id"]))
    if not send_otp_email(email, user["name"], "password_reset", otp):
        return jsonify(success=False, message="Email service unavailable."), 503
    return jsonify(success=True, message="If an account exists for this email, a verification code has been sent.", expires_in=OTP_MINUTES * 60)

@app.post("/api/forgot-password/resend-otp")
def resend_reset():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    allowed, record = can_resend_otp(email, "password_reset")
    if not record:
        return jsonify(success=False, message="Reset session expired. Please request a new OTP."), 400
    if not allowed:
        return jsonify(success=False, message=f"Please wait {OTP_RESEND_SECONDS} seconds before requesting another OTP."), 429
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id=?", (record["payload"],)).fetchone()
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
    record, error = verify_otp(email, "password_reset", otp, True)
    if error:
        return jsonify(success=False, message=error), 400
    session["password_reset_user_id"] = record["payload"]
    session["password_reset_expires_at"] = (now() + timedelta(minutes=10)).isoformat()
    return jsonify(success=True, message="OTP verified successfully."), 200

@app.post("/api/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("new_password", data.get("password", "")))
    confirm = str(data.get("confirm_password", password))
    if password != confirm or not valid_password(password):
        return jsonify(success=False, message="Passwords must match and be at least 8 characters."), 400
    reset_user_id = session.get("password_reset_user_id")
    reset_expiry = session.get("password_reset_expires_at")
    if not reset_user_id or not reset_expiry or datetime.fromisoformat(reset_expiry) < now():
        return jsonify(success=False, message="Verify your password reset OTP before choosing a new password."), 403
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id=? AND lower(email)=?", (reset_user_id, email)).fetchone()
        if not user:
            return jsonify(success=False, message="User account not found."), 404
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(password), user["id"]))
        db.commit()
    finally:
        db.close()
    send_password_reset_success_email(email, user["name"])
    session.pop("password_reset_user_id", None)
    session.pop("password_reset_expires_at", None)
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
        rows = db.execute(
            "SELECT id,user_code,name,email,role,sport,contact_number,gender,date_of_birth,created_at,email_verified,account_status "
            "FROM users ORDER BY id DESC"
        ).fetchall()
    finally:
        db.close()
    return jsonify(success=True, users=[dict(row) for row in rows])

@app.patch("/api/users/<int:user_id>/status")
@role_required("admin")
def update_user_status(user_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).lower()
    if status not in {"active", "deactivated", "deleted"}:
        return jsonify(success=False, message="Invalid account status."), 400
    if user_id == session["user_id"] and status != "active":
        return jsonify(success=False, message="You cannot deactivate your own administrator account."), 400
    db = get_db()
    try:
        if not db.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            return jsonify(success=False, message="User not found."), 404
        db.execute("UPDATE users SET account_status=? WHERE id=?", (status, user_id))
        db.commit()
    finally:
        db.close()
    return jsonify(success=True, message="Account status updated.")

@app.get("/api/profile")
@login_required
def profile():
    db = get_db()
    try:
        user = db.execute(
            "SELECT id,user_code,name,email,role,sport,contact_number,gender,date_of_birth,created_at FROM users WHERE id=?",
            (session["user_id"],),
        ).fetchone()
    finally:
        db.close()
    return jsonify(success=True, user=dict(user))

# ═══════════════════════════════════════════════════════════════════════════════
#  DATA ENDPOINTS — Role-based access
# ═══════════════════════════════════════════════════════════════════════════════

def get_athlete_ids_for_coach(coach_id, db):
    """Return list of athlete IDs assigned to this coach."""
    rows = db.execute("SELECT athlete_id FROM coach_athletes WHERE coach_id=?", (coach_id,)).fetchall()
    return [r["athlete_id"] for r in rows]

def athlete_filter_clause(role, user_id, coach_athlete_ids):
    """Return SQL WHERE fragment and params for role-based athlete data filtering."""
    if role == "admin":
        return "", ()
    if role == "coach":
        if not coach_athlete_ids:
            return " AND 1=0", ()  # No athletes assigned → empty result
        placeholders = ",".join("?" for _ in coach_athlete_ids)
        return f" AND athlete_id IN ({placeholders})", tuple(coach_athlete_ids)
    # player
    return " AND athlete_id=?", (user_id,)

def _validate_coach_owns_athlete(coach_id, athlete_id):
    """Return error response tuple if coach is not assigned to athlete, else None."""
    db = get_db()
    try:
        assigned = db.execute(
            "SELECT 1 FROM coach_athletes WHERE coach_id=? AND athlete_id=?",
            (coach_id, athlete_id)
        ).fetchone()
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
        rows = db.execute(
            f"SELECT * FROM physical_assessments WHERE 1=1{where} ORDER BY assessment_date DESC", params
        ).fetchall()
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
        rows = db.execute(
            f"SELECT * FROM training_sessions WHERE 1=1{where} ORDER BY session_date DESC", params
        ).fetchall()
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
        rows = db.execute(
            f"SELECT * FROM goals WHERE 1=1{where} ORDER BY target_date DESC", params
        ).fetchall()
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
        rows = db.execute(
            f"SELECT * FROM coach_feedback WHERE 1=1{where} ORDER BY feedback_date DESC", params
        ).fetchall()
        return jsonify(success=True, feedback=[dict(r) for r in rows])
    finally:
        db.close()

@app.get("/api/coach/athletes")
@role_required("coach")
def get_coach_athletes():
    db = get_db()
    try:
        rows = db.execute(
            "SELECT u.id, u.user_code, u.name, u.email, u.role, u.sport, u.contact_number, u.gender, u.date_of_birth, u.created_at "
            "FROM users u "
            "JOIN coach_athletes ca ON u.id = ca.athlete_id "
            "WHERE ca.coach_id=?",
            (session["user_id"],),
        ).fetchall()
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
        db.execute(
            "INSERT INTO physical_assessments (athlete_id,coach_id,assessment_date,height_cm,weight_kg,bmi,assessment_remarks) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                athlete_id,
                session["user_id"],
                data.get("assessment_date", now().isoformat()),
                data.get("height_cm"),
                data.get("weight_kg"),
                data.get("bmi"),
                data.get("assessment_remarks"),
            ),
        )
        db.commit()
        return jsonify(success=True, message="Assessment recorded."), 201
    except sqlite3.Error as e:
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
        db.execute(
            "INSERT INTO training_sessions (athlete_id,coach_id,session_date,sport_type,duration_minutes,intensity_level) "
            "VALUES (?,?,?,?,?,?)",
            (
                athlete_id,
                session["user_id"],
                data.get("session_date", now().isoformat()),
                data.get("sport_type"),
                data.get("duration_minutes"),
                data.get("intensity_level"),
            ),
        )
        db.commit()
        return jsonify(success=True, message="Training session recorded."), 201
    except sqlite3.Error as e:
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
        db.execute(
            "INSERT INTO goals (athlete_id,coach_id,goal_title,goal_type,target_value,target_date) "
            "VALUES (?,?,?,?,?,?)",
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
    except sqlite3.Error as e:
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
        db.execute(
            "INSERT INTO coach_feedback (athlete_id,coach_id,feedback_date,performance_summary,overall_rating) "
            "VALUES (?,?,?,?,?)",
            (
                athlete_id,
                session["user_id"],
                data.get("feedback_date", now().isoformat()),
                data.get("performance_summary"),
                data.get("overall_rating"),
            ),
        )
        db.commit()
        return jsonify(success=True, message="Feedback submitted."), 201
    except sqlite3.Error as e:
        db.rollback()
        return jsonify(success=False, message="Database error."), 500
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
