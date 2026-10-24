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
import secrets
import sys
import re
import logging
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from flask import Flask, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.exceptions import HTTPException
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address



BASE_DIR = Path(__file__).parent.absolute()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from db import DatabaseConnectionError, get_db  # noqa: E402
from logging_config import configure_logging  # noqa: E402
from auth.helpers import (  # noqa: E402
    generate_otp,
    store_otp,
    verify_stored_otp,
    find_user_by_email,
    get_user_by_id,
    establish_session,
    is_valid_domain,
    OTP_MINUTES,
    store_admin_otp,
    verify_admin_otp,
)
from auth.emails import (  # noqa: E402
    smtp_settings,
    send_otp_email,
    send_account_created_email,
    send_coach_approval_email,
    send_password_reset_success_email,
)
from auth.decorators import login_required, role_required  # noqa: E402
from attendance import register_attendance_routes, student_attendance_payload  # noqa: E402
from announcements import register_announcement_routes  # noqa: E402
from dashboard_events import register_dashboard_event_routes  # noqa: E402
from performance import register_performance_routes  # noqa: E402
from reference_features import register_reference_feature_routes  # noqa: E402
from reference_extensions import register_reference_extension_routes  # noqa: E402

app = Flask(__name__)
is_production = os.getenv(
    "VERCEL_ENV",
    os.getenv("APP_ENV", "development"),
).lower() == "production"
configured_secret = os.getenv("SECRET_KEY")
if is_production and not configured_secret:
    raise RuntimeError("SECRET_KEY must be configured in production.")
app.secret_key = configured_secret or secrets.token_hex(32)
configure_logging(app)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = (
    is_production
    or os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("FIT_TRACK_MAX_UPLOAD_MB", "16")
) * 1024 * 1024

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

csrf = CSRFProtect(app)

@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """Endpoint for the frontend to fetch a CSRF token for the current session."""
    token = generate_csrf()
    return jsonify({"csrf_token": token}), 200

VALID_ROLES = ("student", "coach")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


def _safe_log(level, message, **fields):
    app.logger.log(
        level,
        message,
        extra={"event_data": fields},
    )


def _request_id():
    value = request.headers.get("X-Request-ID", "")
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        return value
    return str(uuid4())


@app.before_request
def start_request_tracking():
    g.request_id = _request_id()
    g.request_started_at = perf_counter()


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if is_production:
        allowed_origins = {frontend_url} if frontend_url else set()
    else:
        allowed_origins = {
            value.strip().rstrip("/")
            for value in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
            if value.strip()
        }
        allowed_origins.update({
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:5501",
            "http://127.0.0.1:5501",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        })
    if origin and origin.rstrip("/") in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With, X-Request-ID"
    )
    if request.path.startswith("/api/"):
        response.headers["X-Request-ID"] = g.get("request_id", _request_id())
        if response.status_code >= 400 and response.is_json:
            payload = response.get_json(silent=True)
            if isinstance(payload, dict):
                payload.setdefault("success", False)
                payload["request_id"] = g.get("request_id", _request_id())
                response.set_data(app.json.dumps(payload))
                response.content_type = "application/json"
        duration_ms = round(
            (perf_counter() - g.get("request_started_at", perf_counter())) * 1000,
            2,
        )
        log_level = (
            logging.INFO if response.status_code < 400
            else logging.ERROR if response.status_code >= 500
            else logging.WARNING
        )
        response_payload = response.get_json(silent=True)
        _safe_log(
            log_level,
            "API request",
            request_id=g.get("request_id"),
            route=request.path,
            method=request.method,
            status=response.status_code,
            duration_ms=duration_ms,
            success=(
                response_payload.get("success")
                if isinstance(response_payload, dict)
                else None
            ),
            user_id=session.get("user_id"),
        )
    return response


@app.errorhandler(CSRFError)
def api_csrf_errors(error):
    if request.path.startswith("/api/"):
        return jsonify({
            "success": False,
            "message": "Your security token is missing or expired. Refresh the page and try again.",
            "request_id": g.get("request_id"),
        }), 400
    return error.get_response()


@app.errorhandler(HTTPException)
def api_http_errors(error):
    if request.path.startswith("/api/"):
        messages = {
            400: "Bad request.",
            401: "Authentication required.",
            403: "Access denied.",
            404: "Resource not found.",
            405: "Method not allowed.",
            409: "Conflict.",
            422: "Invalid request.",
            429: "Too many requests.",
            500: "The request could not be completed.",
        }
        payload = {
            "success": False,
            "message": messages.get(error.code, "The request could not be completed."),
            "request_id": g.get("request_id"),
        }
        if error.code == 500:
            payload["error"] = "Internal server error"
        return jsonify(payload), error.code or 500
    return error


@app.errorhandler(DatabaseConnectionError)
def api_database_errors(error):
    """Return an actionable response when PostgreSQL is unavailable."""

    if request.path.startswith("/api/"):
        _safe_log(
            logging.ERROR,
            "Database connection error",
            request_id=g.get("request_id"),
            route=request.path,
            method=request.method,
        )
        return jsonify({
            "success": False,
            "error": "Database unavailable",
            "message": (
                "The database is unavailable. Check SUPABASE_DB_URL "
                "and try again."
            ),
            "request_id": g.get("request_id"),
        }), 503

    raise error


@app.errorhandler(Exception)
def api_unhandled_errors(error):
    if request.path.startswith("/api/"):
        _safe_log(
            logging.ERROR,
            "Unhandled API error",
            request_id=g.get("request_id"),
            route=request.path,
            method=request.method,
            error_type=type(error).__name__,
        )
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "The request could not be completed.",
            "request_id": g.get("request_id"),
        }), 500
    raise error


def _database_health():
    started_at = perf_counter()
    db = None
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT 1 AS healthy")
            cursor.fetchone()
        return "ok", round((perf_counter() - started_at) * 1000, 2)
    except Exception as error:
        _safe_log(
            logging.WARNING,
            "Database health check failed",
            request_id=g.get("request_id"),
            route=request.path,
            method=request.method,
            error_type=type(error).__name__,
        )
        return "error", None
    finally:
        if db is not None:
            db.close()


@app.route("/api/health", methods=["GET"])
def health_check():
    timestamp = datetime.now(timezone.utc).isoformat()
    database_status, latency_ms = _database_health()
    status = "ok" if database_status == "ok" else "degraded"
    payload = {
        "status": status,
        "application": "fitness-tracker",
        "database": database_status,
        "timestamp": timestamp,
        "version": APP_VERSION,
    }
    if latency_ms is not None:
        payload["database_latency_ms"] = latency_ms
    return jsonify(payload), 200 if status == "ok" else 503


@app.route("/api/admin/diagnostics", methods=["GET"])
@role_required("admin")
def admin_diagnostics():
    database_status, latency_ms = _database_health()
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        mail = smtp_settings()
        mail_configured = bool(mail["username"] and mail["password"])
        mail_security = mail["security"]
    except ValueError:
        mail_configured = False
        mail_security = "invalid"
    database_backend_name = os.getenv("DATABASE_BACKEND", "sqlite" if not is_production else "postgres")
    return jsonify({
        "success": True,
        "request_id": g.get("request_id"),
        "checks": {
            "backend": "ok",
            "api": "ok",
            "database": database_status,
            "database_latency_ms": latency_ms,
            "environment_configuration": "ok" if configured_secret else "warning",
            "email_service": "configured" if mail_configured else "not_configured",
            "email_security": mail_security,
            "authentication": "ok" if configured_secret else "warning",
            "database_backend": database_backend_name,
            "supabase_connectivity": database_status if database_backend_name == "postgres" else "not_used",
        },
        "version": APP_VERSION,
        "deployment_environment": os.getenv(
            "VERCEL_ENV",
            os.getenv("APP_ENV", "development"),
        ),
        "last_checked_at": timestamp,
    }), 200


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

    try:
        # These are no longer required, but we keep the try-block for general structure
        # if we ever needed to validate other numeric fields here.
        pass
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid input provided."}), 400

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
    if role == "coach" and (not contact_number):
        return jsonify({"success": False, "message": "Phone number is required for coach signup."}), 400
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
        if existing.get("role") != role:
            return jsonify({"success": False, "message": "An account with this email already exists."}), 409
        if existing.get("is_verified"):
            return jsonify({"success": False, "message": "An account with this email already exists."}), 409
        # Legacy pre-migration unverified users remain recoverable by OTP resend.
        otp = generate_otp()
        if not store_otp(existing["id"], "signup", otp):
            return jsonify({"success": False, "message": "Too many verification codes were requested. Try again in an hour."}), 429
        if not send_otp_email(email, existing["full_name"], "signup", otp):
            return jsonify({"success": False, "message": "This legacy signup is still unverified, but email delivery failed. Configure SMTP and resend the OTP."}), 503
        session["pending_user_id"] = existing["id"]
        return jsonify({"success": True, "message": "This unverified registration already exists. A fresh OTP was sent.", "email": email}), 200

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT status, otp_sent_at, otp_send_count
                   FROM pending_registrations WHERE email = %s""",
                (email,),
            )
            existing_registration = cursor.fetchone()
    finally:
        db.close()
    if existing_registration and existing_registration["status"] == "pending_approval":
        return jsonify({"success": False, "message": "This email is already verified and is awaiting admin approval."}), 409
    if existing_registration and existing_registration["status"] == "pending_verification":
        sent_at = existing_registration["otp_sent_at"]
        sent_recently = sent_at and sent_at >= datetime.now() - timedelta(hours=1)
        if sent_recently and existing_registration["otp_send_count"] >= 5:
            return jsonify({"success": False, "message": "Too many verification codes were requested. Try again in an hour."}), 429

    otp = generate_otp()
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pending_registrations
                       (role, full_name, email, password_hash, contact_number,
                        qualification, specialization, experience_years,
                        otp_hash, otp_expires_at, status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending_verification', NOW())
                   ON CONFLICT (email) DO UPDATE SET
                       role = EXCLUDED.role,
                       full_name = EXCLUDED.full_name,
                       password_hash = EXCLUDED.password_hash,
                       contact_number = EXCLUDED.contact_number,
                       qualification = EXCLUDED.qualification,
                       specialization = EXCLUDED.specialization,
                       experience_years = EXCLUDED.experience_years,
                       otp_hash = EXCLUDED.otp_hash,
                       otp_expires_at = EXCLUDED.otp_expires_at,
                       otp_attempts = 0,
                       otp_send_count = CASE
                           WHEN pending_registrations.otp_sent_at >= NOW() - INTERVAL '1 hour'
                           THEN pending_registrations.otp_send_count + 1
                           ELSE 1
                       END,
                       otp_sent_at = NOW(),
                       status = 'pending_verification',
                       verified_at = NULL""",
                (
                    role,
                    full_name,
                    email,
                    generate_password_hash(password),
                    contact_number or None,
                    qualification or None,
                    specialization or None,
                    experience_years,
                    generate_password_hash(otp),
                    datetime.now() + timedelta(minutes=OTP_MINUTES),
                ),
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"Signup failed: {exc}"}), 500
    finally:
        db.close()

    if not send_otp_email(email, full_name, "signup", otp):
        return jsonify({
            "success": False,
            "message": "Registration is pending, but no account was created because the OTP email could not be sent. Configure SMTP, then submit signup again to resend the OTP.",
        }), 503
    return jsonify({
        "success": True,
        "message": "Registration is pending email verification. No account is created until you verify the OTP.",
        "email": email,
    }), 202
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
    if not user:
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """SELECT password_hash, status FROM pending_registrations
                       WHERE email = %s AND role = 'coach'""",
                    (email,),
                )
                pending_coach = cursor.fetchone()
        finally:
            db.close()
        if pending_coach and check_password_hash(pending_coach["password_hash"], password):
            if pending_coach["status"] == "pending_approval":
                return jsonify({
                    "success": False,
                    "message": "Your account is awaiting admin approval.",
                }), 403
            if pending_coach["status"] in ("rejected", "declined"):
                return jsonify({
                    "success": False,
                    "message": "Your coach application was rejected by the admin.",
                }), 403
            return jsonify({
                "success": False,
                "message": "Please verify your email before logging in.",
            }), 403
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401
    if user.get("role") in ("coach", "student") and not user.get("is_active", True):
        return jsonify({"success": False, "message": "This account is inactive. Contact an administrator."}), 403

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
    if user["role"] == "coach" and user["coach_status"] in ("rejected", "declined"):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Your coach account was rejected by the admin.",
                }
            ),
            403,
        )

    if user["role"] in ("student", "coach"):
        _complete_login(user)
        return (
            jsonify(
                {
                    "success": True,
                    "otp_required": False,
                    "message": "Login successful.",
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

    otp = generate_otp()
    if not (store_admin_otp if user["role"] == "admin" else store_otp)(user["id"], "login", otp):
        return jsonify({"success": False, "message": "Too many login codes were requested. Try again in an hour."}), 429
    session.clear()
    session["pending_login_user_id"] = user["id"]
    session["pending_login_role"] = user["role"]
    if not send_otp_email(email, user["full_name"], "login", otp):
        return jsonify({"success": False, "message": "Login OTP could not be emailed. Configure SMTP and use resend OTP."}), 503
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


@app.route("/api/login/pending-otp", methods=["GET"])
def pending_login_otp():
    user_id = session.get("pending_login_user_id")
    pending_role = session.get("pending_login_role")
    user = get_user_by_id(user_id) if user_id else None
    if not user or user.get("role") != pending_role:
        return jsonify({
            "success": False,
            "message": "No active login verification. Please log in again.",
        }), 401
    return jsonify({
        "success": True,
        "role": user["role"],
        "email": user["email"],
    }), 200


def _complete_login(user):
    establish_session(user)
    db = get_db()
    try:
        with db.cursor() as cursor:
            table = "admins" if user["role"] == "admin" else "users"
            cursor.execute(
                f"UPDATE {table} SET last_login_at = NOW() WHERE id = %s", (user["id"],)
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
    verifier = verify_admin_otp if user["role"] == "admin" else verify_stored_otp
    valid, message = verifier(user["id"], "login", otp)
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
    if not (store_admin_otp if user["role"] == "admin" else store_otp)(user["id"], "login", otp):
        return jsonify({"success": False, "message": "Too many login codes were requested. Try again in an hour."}), 429
    if not send_otp_email(email, user["full_name"], "login", otp):
        return jsonify({"success": False, "message": "Login OTP could not be emailed. Check SMTP configuration and try again."}), 503
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
    if user["role"] == "coach" and (user.get("coach_status") != "approved" or not user.get("is_active", True)):
        session.clear()
        return jsonify({"success": False, "message": "Coach dashboard access is disabled for this account."}), 403
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
                """UPDATE student_profiles
                   SET passport_id = COALESCE(passport_id, %s)
                   WHERE user_id = %s""",
                (f"IKC-SP-{datetime.now().year}-{int(user_id):05d}", user_id),
            )
            db.commit()
            cursor.execute(
                """SELECT date_of_birth, emergency_contact, height_cm, weight_kg,
                          goal, sport_activity, department, student_number,
                          semester, gender, bio, blood_group, medical_history, address,
                          parent_name, parent_phone, parent_address,
                          passport_id, photo_path
                   FROM student_profiles WHERE user_id = %s""",
                (user_id,),
            )
            profile = cursor.fetchone()
            if profile is None:
                return None
            cursor.execute(
                """SELECT s.id, s.name FROM student_sports ss
                   JOIN sports s ON s.id = ss.sport_id
                   WHERE ss.student_id = %s ORDER BY s.name""",
                (user_id,),
            )
            profile["sports"] = cursor.fetchall()
            return profile
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

    selected_sports = data.get("sports")
    if selected_sports is None:
        legacy_sports = data.get("sport_activity") or data.get("activity") or ""
        selected_sports = [
            item.strip() for item in str(legacy_sports).split(",") if item.strip()
        ]
    if not isinstance(selected_sports, list):
        return "Sports must be provided as a list."
    selected_sports = list(dict.fromkeys(
        str(item).strip() for item in selected_sports if str(item).strip()
    ))
    if any(len(name) > 50 for name in selected_sports):
        return "One or more selected sports are invalid."

    db = get_db()
    try:
        with db.cursor() as cursor:
            sport_ids = []
            if selected_sports:
                placeholders = ", ".join(["%s"] * len(selected_sports))
                cursor.execute(
                    f"SELECT id, name FROM sports WHERE name IN ({placeholders})",
                    tuple(selected_sports),
                )
                sport_ids = cursor.fetchall()
                found_names = {sport["name"] for sport in sport_ids}
                if found_names != set(selected_sports):
                    db.rollback()
                    return "One or more selected sports do not exist."
            height_cm = data.get("height_cm")
            weight_kg = data.get("weight_kg")
            goal = data.get("goal")
            sport_activity = ",".join(selected_sports)
            department = data.get("department")
            cursor.execute(
                """INSERT INTO student_profiles
                       (user_id, date_of_birth, emergency_contact, height_cm,
                        weight_kg, goal, sport_activity, department, semester,
                        gender, student_number, blood_group, medical_history,
                        address, parent_name, parent_phone, parent_address)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (user_id) DO UPDATE SET
                       date_of_birth = EXCLUDED.date_of_birth,
                       emergency_contact = EXCLUDED.emergency_contact,
                       height_cm = EXCLUDED.height_cm,
                       weight_kg = EXCLUDED.weight_kg,
                       goal = EXCLUDED.goal,
                       sport_activity = EXCLUDED.sport_activity,
                       department = EXCLUDED.department,
                       semester = EXCLUDED.semester,
                       gender = EXCLUDED.gender,
                       student_number = EXCLUDED.student_number,
                       blood_group = EXCLUDED.blood_group,
                       medical_history = EXCLUDED.medical_history,
                       address = EXCLUDED.address,
                       parent_name = EXCLUDED.parent_name,
                       parent_phone = EXCLUDED.parent_phone,
                       parent_address = EXCLUDED.parent_address""",
                (user_id, date_of_birth, emergency_contact, height_cm, weight_kg,
                 goal, sport_activity, department,
                 str(data.get("semester") or "").strip() or None,
                 str(data.get("gender") or "").strip() or None,
                 str(data.get("student_id") or data.get("student_number") or "").strip() or None,
                 str(data.get("blood_group") or "").strip() or None,
                 str(data.get("medical_history") or "").strip() or None,
                 str(data.get("address") or "").strip() or None,
                 str(data.get("parent_name") or "").strip() or None,
                 str(data.get("parent_phone") or "").strip() or None,
                 str(data.get("parent_address") or "").strip() or None),
            )
            cursor.execute("DELETE FROM student_sports WHERE student_id = %s", (user_id,))
            for sport in sport_ids:
                cursor.execute(
                    "INSERT INTO student_sports (student_id, sport_id) VALUES (%s, %s)",
                    (user_id, sport["id"]),
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


@app.route("/api/sports", methods=["GET"])
def list_sports():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id, name FROM sports ORDER BY name")
            sports = cursor.fetchall()
        return jsonify({"success": True, "sports": sports}), 200
    finally:
        db.close()


@app.route("/api/student/sports", methods=["GET"])
@role_required("student")
def get_student_sports():
    student_id = session.get("user_id")
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id, name FROM sports ORDER BY name")
            catalog = cursor.fetchall()
            cursor.execute(
                """SELECT s.id, s.name FROM student_sports ss
                   JOIN sports s ON s.id = ss.sport_id
                   WHERE ss.student_id = %s ORDER BY s.name""",
                (student_id,),
            )
            selected = cursor.fetchall()
        return jsonify({"success": True, "sports": catalog, "selected": selected}), 200
    finally:
        db.close()


@app.route("/api/student/sports", methods=["POST", "PUT"])
@role_required("student")
def update_student_sports():
    data = request.get_json(silent=True) or {}
    sports = data.get("sports")
    if not isinstance(sports, list):
        return jsonify({"success": False, "message": "Sports must be provided as a list."}), 400
    names = list(dict.fromkeys(str(item).strip() for item in sports if str(item).strip()))
    student_id = session.get("user_id")
    db = get_db()
    try:
        with db.cursor() as cursor:
            ids = []
            if names:
                placeholders = ", ".join(["%s"] * len(names))
                cursor.execute(
                    f"SELECT id, name FROM sports WHERE name IN ({placeholders})",
                    tuple(names),
                )
                ids = cursor.fetchall()
                if {row["name"] for row in ids} != set(names):
                    db.rollback()
                    return jsonify({"success": False, "message": "Unknown sport selected."}), 400
            cursor.execute("DELETE FROM student_sports WHERE student_id = %s", (student_id,))
            for sport in ids:
                cursor.execute(
                    "INSERT INTO student_sports (student_id, sport_id) VALUES (%s, %s)",
                    (student_id, sport["id"]),
                )
            cursor.execute(
                "UPDATE student_profiles SET sport_activity = %s WHERE user_id = %s",
                (", ".join(names), student_id),
            )
        db.commit()
        return jsonify({"success": True, "sports": names}), 200
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.route("/api/student/sports/<int:sport_id>", methods=["DELETE"])
@role_required("student")
def delete_student_sport(sport_id):
    student_id = session.get("user_id")
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM student_sports WHERE student_id = %s AND sport_id = %s",
                (student_id, sport_id),
            )
            cursor.execute(
                """UPDATE student_profiles SET sport_activity = (
                       SELECT STRING_AGG(s.name, ', ' ORDER BY s.name)
                       FROM student_sports ss JOIN sports s ON s.id = ss.sport_id
                       WHERE ss.student_id = %s
                   ) WHERE user_id = %s""",
                (student_id, student_id),
            )
        db.commit()
        return jsonify({"success": True}), 200
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
    if not user.get("is_verified"):
        return jsonify({"success": False, "message": "Verify your email before completing your profile."}), 403
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
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""SELECT c.id, c.full_name, c.email, c.contact_number, c.specialization
                FROM student_sports ss
                JOIN coach_sports cs ON cs.sport_id=ss.sport_id
                JOIN users c ON c.id=cs.coach_id
                WHERE ss.student_id=%s AND c.role='coach'
                  AND c.coach_status='approved' AND c.is_active=TRUE
                ORDER BY c.full_name LIMIT 1""", (user["id"],))
            assigned_coach = cursor.fetchone()
    finally:
        db.close()
    return (
        jsonify(
            {
                "success": True,
                "name": user["full_name"],
                "email": user["email"],
                "profile": profile,
                "assigned_coach": assigned_coach,
                "attendance": student_attendance_payload(user["id"]),
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
    db = get_db()
    pending = None
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT id, role, full_name, status, otp_attempts,
                          otp_sent_at, otp_send_count
                   FROM pending_registrations WHERE email = %s""",
                (email,),
            )
            pending = cursor.fetchone()
    finally:
        db.close()
    if pending:
        if pending["status"] == "pending_approval":
            return jsonify({"success": False, "message": "Email verified. Your coach application is awaiting admin approval."}), 409
        if pending["status"] in ("rejected", "declined"):
            return jsonify({"success": False, "message": "This coach application was not approved."}), 403
        sent_at = pending["otp_sent_at"]
        sent_recently = sent_at and sent_at >= datetime.now() - timedelta(hours=1)
        if sent_recently and pending["otp_send_count"] >= 5:
            return jsonify({"success": False, "message": "Too many verification codes were requested. Try again in an hour."}), 429
        otp = generate_otp()
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """UPDATE pending_registrations
                       SET otp_hash = %s, otp_expires_at = %s, otp_attempts = 0,
                           otp_send_count = CASE
                               WHEN otp_sent_at >= NOW() - INTERVAL '1 hour'
                               THEN otp_send_count + 1
                               ELSE 1
                           END,
                           otp_sent_at = NOW()
                       WHERE id = %s AND status = 'pending_verification'""",
                    (generate_password_hash(otp), datetime.now() + timedelta(minutes=OTP_MINUTES), pending["id"]),
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        if not send_otp_email(email, pending["full_name"], "signup", otp):
            return jsonify({"success": False, "message": "OTP email delivery failed. Configure SMTP and try resend again."}), 503
        return jsonify({"success": True, "message": "Verification OTP sent to your email."}), 200

    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "message": "No pending registration found for this email."}), 404
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
    if not store_otp(user["id"], "signup", otp):
        return jsonify({"success": False, "message": "Too many verification codes were requested. Try again in an hour."}), 429
    if not send_otp_email(email, user["full_name"], "signup", otp):
        return jsonify({"success": False, "message": "OTP email delivery failed. Configure SMTP and try resend again."}), 503
    return (
        jsonify({"success": True, "message": "Verification OTP sent to your email."}),
        200,
    )


@app.route("/api/account-verification/verify", methods=["POST"])
def verify_account():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    otp = str(data.get("otp") or "").strip()
    if not otp:
        return jsonify({"success": False, "message": "OTP is required."}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM pending_registrations
                   WHERE email = %s AND status = 'pending_verification'""",
                (email,),
            )
            pending = cursor.fetchone()
            if pending:
                if pending.get("otp_attempts", 0) >= 5:
                    return jsonify({"success": False, "message": "Too many incorrect codes. Request a new OTP."}), 429
                if pending["otp_expires_at"] < datetime.now():
                    return jsonify({"success": False, "message": "OTP has expired. Request a new one."}), 400
                if not check_password_hash(pending["otp_hash"], otp):
                    attempts = int(pending.get("otp_attempts", 0)) + 1
                    expires_at = datetime.now() if attempts >= 5 else pending["otp_expires_at"]
                    cursor.execute(
                        """UPDATE pending_registrations
                           SET otp_attempts = %s, otp_expires_at = %s
                           WHERE id = %s""",
                        (attempts, expires_at, pending["id"]),
                    )
                    db.commit()
                    return jsonify({"success": False, "message": "Invalid OTP code."}), 400
                if pending["role"] == "student":
                    cursor.execute(
                        """INSERT INTO users
                           (role, full_name, email, password_hash, contact_number, is_verified, coach_status)
                           VALUES ('student', %s, %s, %s, %s, TRUE, NULL)
                           RETURNING id""",
                        (pending["full_name"], pending["email"], pending["password_hash"], pending["contact_number"]),
                    )
                    student_id = cursor.fetchone()["id"]
                    cursor.execute("DELETE FROM pending_registrations WHERE id = %s", (pending["id"],))
                    db.commit()
                    session["pending_user_id"] = student_id
                    session["pending_registration_email"] = email
                    return jsonify({
                        "success": True,
                        "role": "student",
                        "message": "Email verified. Continue completing your student profile.",
                    }), 200
                cursor.execute(
                    """UPDATE pending_registrations
                       SET status = 'pending_approval', verified_at = NOW()
                       WHERE id = %s""",
                    (pending["id"],),
                )
                db.commit()
                session["pending_coach_email"] = email
                return jsonify({
                    "success": True,
                    "role": "coach",
                    "message": "Email verified. Your coach application is awaiting admin approval. No coach account exists until approval.",
                }), 200
    except Exception as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"Verification failed: {exc}"}), 500
    finally:
        db.close()

    # Compatibility for accounts created by the previous signup implementation.
    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "message": "No pending registration found with this email."}), 404

    valid, message = verify_stored_otp(user["id"], "signup", otp)
    if not valid:
        return jsonify({"success": False, "message": message}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET is_verified = TRUE WHERE id = %s", (user["id"],)
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
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM pending_registrations WHERE email = %s AND role = 'coach'",
                (email,),
            )
            pending = cursor.fetchone()
        if pending:
            return jsonify({
                "success": True,
                "email_verified": pending["status"] != "pending_verification",
                "coach_status": "pending" if pending["status"] == "pending_approval" else pending["status"],
            }), 200
    finally:
        db.close()
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
        app.logger.warning("Password reset requested for an unknown account")
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
    if not (store_admin_otp if user["role"] == "admin" else store_otp)(user["id"], "password_reset", otp):
        return jsonify({"success": False, "message": "Too many reset code requests. Please try again later."}), 429
    if not send_otp_email(email, user["full_name"], "password_reset", otp):
        app.logger.error("Password reset OTP email could not be sent")
        return jsonify({"success": False, "message": "Unable to send the reset code right now. Please try again later."}), 503
    app.logger.info("Password reset OTP accepted by the mail server")
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

    verifier = verify_admin_otp if user["role"] == "admin" else verify_stored_otp
    valid, message = verifier(user["id"], "password_reset", otp)
    if not valid:
        return jsonify({"success": False, "message": message}), 400

    session["reset_email"] = email
    session["reset_verified"] = True
    reset_signer = URLSafeTimedSerializer(app.secret_key, salt="password-reset")
    reset_token = reset_signer.dumps({
        "user_id": user["id"],
        "email": email,
        "role": user["role"],
        "password_fingerprint": hmac.new(
            app.secret_key.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    })
    return (
        jsonify(
            {
                "success": True,
                "message": "OTP verified. You can now reset your password.",
                "reset_token": reset_token,
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
    session_verified = (
        session.get("reset_verified")
        and session.get("reset_email") == email
    )
    token_verified = False
    reset_token = str(data.get("reset_token") or "")
    if reset_token:
        try:
            claims = URLSafeTimedSerializer(
                app.secret_key, salt="password-reset"
            ).loads(reset_token, max_age=600)
            expected_fingerprint = hmac.new(
                app.secret_key.encode("utf-8"),
                user["password_hash"].encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            token_verified = (
                claims.get("user_id") == user["id"]
                and claims.get("email") == email
                and claims.get("role") == user["role"]
                and hmac.compare_digest(
                    str(claims.get("password_fingerprint") or ""),
                    expected_fingerprint,
                )
            )
        except (BadSignature, SignatureExpired):
            token_verified = False
    if not session_verified and not token_verified:
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
            table = "admins" if user["role"] == "admin" else "users"
            cursor.execute(
                f"UPDATE {table} SET password_hash = %s WHERE id = %s",
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
                "role": user["role"]
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
                           last_login_at, created_at, is_active, qualification, specialization, experience_years
                    FROM users
                    UNION
                    SELECT id, 'admin' as role, full_name, email, NULL AS contact_number, is_verified,
                           NULL as coach_status, last_login_at, created_at, TRUE AS is_active,
                           NULL AS qualification, NULL AS specialization, NULL AS experience_years
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
    finally:
        db.close()


@app.route("/api/admin/coaches/pending", methods=["GET"])
@role_required("admin")
def admin_pending_coaches():
    db = get_db()
    try:
        with db.cursor() as cursor:
                 cursor.execute(
                  """SELECT id AS user_id, NULL AS registration_id, full_name, email,
                         contact_number, qualification, specialization, experience_years,
                         coach_status, created_at, TRUE AS is_verified
                       FROM users WHERE role = 'coach' AND coach_status = 'pending' AND is_verified = TRUE
                     UNION ALL
                     SELECT NULL AS user_id, id AS registration_id, full_name, email,
                         contact_number, qualification, specialization, experience_years,
                         'pending' AS coach_status, created_at, TRUE AS is_verified
                     FROM pending_registrations
                     WHERE role = 'coach' AND status = 'pending_approval'
                     ORDER BY created_at ASC"""
                 )
                 coaches = cursor.fetchall()
        for c in coaches:
            if c.get("created_at"):
                c["created_at"] = str(c["created_at"])
        return jsonify({"success": True, "coaches": coaches}), 200
    finally:
        db.close()


@app.route("/api/admin/students", methods=["GET"])
@role_required("admin")
def admin_list_students():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT u.id, u.full_name, u.email, u.contact_number,
                          u.is_verified, u.created_at AS registration_date,
                          sp.date_of_birth, sp.department, sp.height_cm, sp.weight_kg,
                          STRING_AGG(DISTINCT s.name, ', ' ORDER BY s.name) AS sports
                   FROM users u
                   LEFT JOIN student_profiles sp ON sp.user_id = u.id
                   LEFT JOIN student_sports ss ON ss.student_id = u.id
                   LEFT JOIN sports s ON s.id = ss.sport_id
                   WHERE u.role = 'student'
                   GROUP BY u.id, sp.user_id
                   ORDER BY u.created_at DESC"""
            )
            students = cursor.fetchall()
        for student in students:
            student["is_verified"] = bool(student["is_verified"])
            for key in ("registration_date", "date_of_birth"):
                if student.get(key) is not None:
                    student[key] = str(student[key])
            student["sports"] = student["sports"].split(", ") if student["sports"] else []
        return jsonify({"success": True, "students": students}), 200
    finally:
        db.close()


@app.route("/api/admin/coach-sports", methods=["GET", "POST", "PUT"])
@role_required("admin")
def admin_coach_sports():
    data = request.get_json(silent=True) or {}
    coach_id = request.args.get("coach_id") or data.get("coach_id")
    db = get_db()
    try:
        with db.cursor() as cursor:
            if request.method == "GET":
                query = """SELECT cs.coach_id, u.full_name AS coach_name,
                                   s.id AS sport_id, s.name AS sport_name
                            FROM coach_sports cs
                            JOIN users u ON u.id = cs.coach_id
                            JOIN sports s ON s.id = cs.sport_id"""
                params = ()
                if coach_id:
                    query += " WHERE cs.coach_id = %s"
                    params = (coach_id,)
                query += " ORDER BY u.full_name, s.name"
                cursor.execute(query, params)
                return jsonify({"success": True, "assignments": cursor.fetchall()}), 200

            sports = data.get("sports")
            if not coach_id or not isinstance(sports, list):
                return jsonify({"success": False, "message": "coach_id and a sports list are required."}), 400
            cursor.execute(
                "SELECT id FROM users WHERE id = %s AND role = 'coach' AND coach_status = 'approved'",
                (coach_id,),
            )
            coach = cursor.fetchone()
            if not coach:
                return jsonify({"success": False, "message": "An approved coach is required."}), 400
            names = list(dict.fromkeys(str(item).strip() for item in sports if str(item).strip()))
            if names:
                placeholders = ", ".join(["%s"] * len(names))
                cursor.execute(f"SELECT id, name FROM sports WHERE name IN ({placeholders})", tuple(names))
                found = cursor.fetchall()
                if {row["name"] for row in found} != set(names):
                    return jsonify({"success": False, "message": "Unknown sport selected."}), 400
            else:
                found = []
            if request.method == "PUT":
                cursor.execute("DELETE FROM coach_sports WHERE coach_id = %s", (coach_id,))
            for sport in found:
                cursor.execute(
                    """INSERT INTO coach_sports (coach_id, sport_id, assigned_by)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (coach_id, sport_id)
                       DO UPDATE SET assigned_by = EXCLUDED.assigned_by""",
                    (coach_id, sport["id"], session.get("user_id")),
                )
        db.commit()
        return jsonify({"success": True, "sports": names}), 200
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.route("/api/admin/coach-sports/<int:coach_id>/<int:sport_id>", methods=["DELETE"])
@role_required("admin")
def admin_remove_coach_sport(coach_id, sport_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM coach_sports WHERE coach_id = %s AND sport_id = %s",
                (coach_id, sport_id),
            )
        db.commit()
        return jsonify({"success": True}), 200
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.route("/api/coach/athletes", methods=["GET"])
@role_required("coach")
def coach_list_athletes():
    coach_id = session.get("user_id")
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""SELECT u.id, u.full_name, u.email, u.contact_number,
                          sp.date_of_birth, sp.height_cm, sp.weight_kg, sp.goal,
                          STRING_AGG(DISTINCT assigned_sport.name, ', ' ORDER BY assigned_sport.name) AS sports
                   FROM coach_sports cs
                   JOIN users coach ON coach.id=cs.coach_id AND coach.role='coach'
                        AND coach.coach_status='approved' AND coach.is_active=TRUE
                   JOIN student_sports ss ON ss.sport_id=cs.sport_id
                   JOIN users u ON u.id=ss.student_id AND u.role='student' AND u.is_verified=TRUE
                   LEFT JOIN student_profiles sp ON sp.user_id=u.id
                   JOIN sports assigned_sport ON assigned_sport.id=ss.sport_id
                   WHERE cs.coach_id=%s
                   GROUP BY u.id, sp.user_id
                   ORDER BY u.full_name ASC""", (coach_id,))
            athletes = cursor.fetchall()
        for athlete in athletes:
            athlete["name"] = athlete.pop("full_name")
            athlete["sports"] = athlete["sports"].split(", ") if athlete["sports"] else []
            athlete["sport"] = ", ".join(athlete["sports"])
            athlete["position"] = ""
        return jsonify({"success": True, "athletes": athletes}), 200
    finally:
        db.close()


@app.route("/api/admin/dashboard-stats", methods=["GET"])
@role_required("admin")
def admin_dashboard_stats():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""SELECT
                COUNT(*) FILTER (WHERE role='coach') AS total_coaches,
                COUNT(*) FILTER (WHERE role='coach' AND coach_status='pending') AS pending_coaches,
                COUNT(*) FILTER (WHERE role='student') AS total_athletes,
                COUNT(*) FILTER (WHERE role='coach' AND coach_status='approved' AND is_active) AS active_coaches
                FROM users""")
            row = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) AS staged_pending FROM pending_registrations WHERE role='coach' AND status='pending_approval'")
            staged_pending = int((cursor.fetchone() or {}).get("staged_pending") or 0)
            cursor.execute("""SELECT
                COUNT(*) FILTER (WHERE status='present' AND session_date=CURRENT_DATE) AS present_today,
                COUNT(*) FILTER (WHERE status='absent' AND session_date=CURRENT_DATE) AS absent_today,
                COUNT(*) FILTER (WHERE session_date=CURRENT_DATE) AS today_total,
                COUNT(*) FILTER (WHERE status='present') AS present_all,
                COUNT(*) AS total_all FROM attendance_records""")
            attendance = cursor.fetchone()
        attendance.update({key: int(value or 0) for key, value in row.items()})
        attendance["pending_coaches"] += staged_pending
        attendance["overall_attendance_percent"] = round(attendance["present_all"] * 100 / attendance["total_all"]) if attendance["total_all"] else 0
        return jsonify({"success": True, "stats": attendance}), 200
    finally:
        db.close()


@app.route("/api/admin/coaches", methods=["GET"])
@role_required("admin")
def admin_list_coaches():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""SELECT c.id, c.full_name, c.email, c.contact_number,
                    c.specialization, c.qualification, c.experience_years, c.coach_status,
                    c.coach_decided_at AS decision_at, c.coach_decision_reason AS decision_reason,
                    c.is_active, COUNT(DISTINCT st.id)::INTEGER AS athlete_count
                FROM users c
                LEFT JOIN coach_sports cs ON cs.coach_id=c.id
                LEFT JOIN student_sports ss ON ss.sport_id=cs.sport_id
                LEFT JOIN users st ON st.id=ss.student_id AND st.role='student' AND st.is_verified=TRUE
                WHERE c.role='coach' GROUP BY c.id ORDER BY c.full_name""")
            coaches = cursor.fetchall()
            cursor.execute("""SELECT id, full_name, email, contact_number, specialization, qualification,
                    experience_years, CASE WHEN status='rejected' THEN 'declined' ELSE status END AS coach_status,
                    decision_at, decision_reason, TRUE AS is_active, 0 AS athlete_count
                FROM pending_registrations WHERE role='coach' AND status IN ('declined','rejected')""")
            coaches.extend(cursor.fetchall())
        for coach in coaches:
            if coach.get("decision_at") is not None:
                coach["decision_at"] = str(coach["decision_at"])
        return jsonify({"success": True, "coaches": coaches}), 200
    finally:
        db.close()


@app.route("/api/admin/coaches/<int:coach_id>/active", methods=["PUT"])
@role_required("admin")
def admin_set_coach_active(coach_id):
    data = request.get_json(silent=True) or {}
    active = data.get("active")
    if not isinstance(active, bool):
        return jsonify({"success": False, "message": "active must be true or false."}), 400
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("UPDATE users SET is_active=%s WHERE id=%s AND role='coach' AND coach_status='approved'", (active, coach_id))
            if not cursor.rowcount:
                return jsonify({"success": False, "message": "Approved coach not found."}), 404
        db.commit()
        return jsonify({"success": True}), 200
    finally:
        db.close()


@app.route("/api/student/coach", methods=["GET"])
@role_required("student")
def student_assigned_coach():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""SELECT c.id, c.full_name, c.email, c.contact_number, c.specialization
                FROM student_sports ss
                JOIN coach_sports cs ON cs.sport_id=ss.sport_id
                JOIN users c ON c.id=cs.coach_id
                WHERE ss.student_id=%s AND c.role='coach'
                  AND c.is_active=TRUE AND c.coach_status='approved'
                ORDER BY c.full_name LIMIT 1""", (session.get("user_id"),))
            coach = cursor.fetchone()
        return jsonify({"success": True, "coach": coach}), 200
    finally:
        db.close()


@app.route("/api/admin/coaches/approve", methods=["POST"])
@role_required("admin")
def admin_approve_coach():
    data = request.get_json(silent=True) or {}
    registration_id = data.get("registration_id")
    if registration_id:
        return _approve_staged_coach(
            registration_id,
            data.get("sports"),
            data.get("email"),
        )
    user_id = data.get("user_id") or data.get("id")
    names = list(dict.fromkeys(str(name).strip() for name in (data.get("sports") or []) if str(name).strip()))
    if names:
        db = get_db()
        try:
            with db.cursor() as cursor:
                marks = ",".join(["%s"] * len(names))
                cursor.execute(f"SELECT id, name FROM sports WHERE name IN ({marks})", tuple(names))
                selected = cursor.fetchall()
                if {item["name"] for item in selected} != set(names):
                    return jsonify({"success": False, "message": "Unknown sport selected."}), 400
        finally:
            db.close()
    result = _set_coach_status(user_id, "approved")
    if names and isinstance(result, tuple) and result[1] == 200:
        db = get_db()
        try:
            with db.cursor() as cursor:
                for sport_name in names:
                    cursor.execute("SELECT id FROM sports WHERE name=%s", (sport_name,))
                    sport = cursor.fetchone()
                    cursor.execute("""INSERT INTO coach_sports(coach_id,sport_id,assigned_by)
                        VALUES(%s,%s,%s) ON CONFLICT(coach_id,sport_id) DO NOTHING""",
                        (user_id, sport["id"], session.get("user_id")))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    return result


@app.route("/api/admin/coaches/reject", methods=["POST"])
@role_required("admin")
def admin_reject_coach():
    data = request.get_json(silent=True) or {}
    registration_id = data.get("registration_id")
    if registration_id:
        return _reject_staged_coach(registration_id, data.get("email"), data.get("reason"))
    user_id = data.get("user_id") or data.get("id")
    return _set_coach_status(user_id, "rejected")


def _pending_coach_identity(email, registration_id):
    email = str(email or "").strip().lower()
    if email:
        return "LOWER(email) = %s", (email,)
    return "id = %s", (registration_id,)


def _approve_staged_coach(registration_id, sports, email=None):
    if not isinstance(sports, list) or not sports:
        return jsonify({"success": False, "message": "Select at least one sport before approving the coach."}), 400
    names = list(dict.fromkeys(str(name).strip() for name in sports if str(name).strip()))
    db = get_db()
    try:
        with db.cursor() as cursor:
            identity_filter, identity_params = _pending_coach_identity(
                email,
                registration_id,
            )
            cursor.execute(
                f"""SELECT * FROM pending_registrations
                    WHERE {identity_filter}
                      AND role = 'coach' AND status = 'pending_approval'
                    FOR UPDATE""",
                identity_params,
            )
            draft = cursor.fetchone()
            if not draft:
                return jsonify({"success": False, "message": "Verified pending coach request not found."}), 404
            placeholders = ", ".join(["%s"] * len(names))
            cursor.execute(f"SELECT id, name FROM sports WHERE name IN ({placeholders})", tuple(names))
            selected_sports = cursor.fetchall()
            if {row["name"] for row in selected_sports} != set(names):
                return jsonify({"success": False, "message": "Unknown sport selected."}), 400
            cursor.execute(
                """INSERT INTO users
                   (role, full_name, email, password_hash, contact_number, is_verified, coach_status,
                    qualification, specialization, experience_years, coach_decided_at)
                   VALUES ('coach', %s, %s, %s, %s, TRUE, 'approved', %s, %s, %s, NOW())
                   RETURNING id""",
                (draft["full_name"], draft["email"], draft["password_hash"], draft["contact_number"],
                 draft.get("qualification"), draft.get("specialization"), draft.get("experience_years")),
            )
            coach_id = cursor.fetchone()["id"]
            for sport in selected_sports:
                cursor.execute(
                    """INSERT INTO coach_sports (coach_id, sport_id, assigned_by)
                       VALUES (%s, %s, %s)""",
                    (coach_id, sport["id"], session.get("user_id")),
                )
            cursor.execute(
                "DELETE FROM pending_registrations WHERE id = %s",
                (draft["id"],),
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"Coach approval failed: {exc}"}), 500
    finally:
        db.close()
    send_coach_approval_email(draft["email"], draft["full_name"], "approved")
    return jsonify({"success": True, "coach_id": coach_id, "sports": names, "message": "Coach approved and account created."}), 200


def _reject_staged_coach(registration_id, email=None, reason=None):
    db = get_db()
    try:
        with db.cursor() as cursor:
            identity_filter, identity_params = _pending_coach_identity(
                email,
                registration_id,
            )
            cursor.execute(
                f"""UPDATE pending_registrations SET status = 'declined', decision_at = NOW(), decision_reason = %s
                    WHERE {identity_filter}
                      AND role = 'coach' AND status = 'pending_approval'""",
                (str(reason or "").strip() or None, *identity_params),
            )
            if cursor.rowcount == 0:
                return jsonify({"success": False, "message": "Verified pending coach request not found."}), 404
            cursor.execute(
                f"SELECT email, full_name FROM pending_registrations WHERE {identity_filter}",
                identity_params,
            )
            draft = cursor.fetchone()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    send_coach_approval_email(draft["email"], draft["full_name"], "rejected")
    return jsonify({"success": True, "message": "Coach application rejected; no account was created."}), 200


@app.route("/api/coaches/<int:user_id>/approval", methods=["POST"])
@role_required("admin")
def review_coach_approval(user_id):
    data = request.get_json(silent=True) or {}
    decision = str(data.get("decision") or "").strip().lower()
    if decision not in ("approve", "reject", "decline"):
        return (
            jsonify(
                {"success": False, "message": "Decision must be approve or reject."}
            ),
            400,
        )
    return _set_coach_status(
        user_id, "approved" if decision == "approve" else "declined"
    )


def _set_coach_status(user_id, status):
    if not user_id:
        return jsonify({"success": False, "message": "user_id is required."}), 400
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    if user["role"] != "coach":
        return jsonify({"success": False, "message": "This user is not a coach."}), 400

    if status == "rejected":
        status = "declined"
    reason = str((request.get_json(silent=True) or {}).get("reason") or "").strip() or None
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET coach_status = %s, coach_decided_at = NOW(), coach_decision_reason = %s WHERE id = %s",
                (status, reason, user_id),
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"Update failed: {exc}"}), 500
    finally:
        db.close()
    action = "approved" if status == "approved" else "declined"
    send_coach_approval_email(user["email"], user["full_name"], "rejected" if status == "declined" else status)
    return jsonify({"success": True, "message": f"Coach {action} successfully."}), 200


register_attendance_routes(app)
register_announcement_routes(app)
register_dashboard_event_routes(app)
register_performance_routes(app)
register_reference_feature_routes(app)
register_reference_extension_routes(app)
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
        use_reloader=False,
    )
