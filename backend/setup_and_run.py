import os
import re
import sys
import pymysql
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.absolute()
# The .env file resides in the backend directory, not the project root.
# Load environment variables from the local .env to avoid authentication failures.
load_dotenv(BASE_DIR.parent / ".env")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
SCHEMA_PATH = BASE_DIR / "schema.sql"

ROOT_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

APP_CONFIG = {
    **ROOT_CONFIG,
    "database": os.getenv("DB_NAME", "fitness_tracker_auth"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def db_exists():
    try:
        conn = pymysql.connect(**ROOT_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE %s", (APP_CONFIG["database"],))
            result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"[ERROR] Error checking database: {e}")
        return False


def tables_exist():
    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            existing = {next(iter(row.values())) for row in cursor.fetchall()}
        required = {
            "users", "student_profiles", "otp_verifications", "admin_otp_verifications", "admins", "sports",
            "pending_registrations",
            "coach_sports", "student_sports", "physical_assessments",
            "training_sessions", "goals", "coach_feedback", "attendance_sessions",
            "attendance_records",
        }
        return required.issubset(existing)
    except Exception:
        return False


def ensure_auth_schema_compatibility():
    """Add OTP purposes introduced after the initial schema version."""
    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""ALTER TABLE otp_verifications
                   MODIFY purpose ENUM('signup', 'login', 'password_reset') NOT NULL""")
            for table in ("otp_verifications", "admin_otp_verifications"):
                cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'attempt_count'")
                if cursor.fetchone() is None:
                    cursor.execute(
                        f"ALTER TABLE {table} ADD COLUMN attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0"
                    )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        print(f"[ERROR] Auth schema migration failed: {exc}")
        return False


def _ensure_student_profile_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM student_profiles LIKE 'department'")
    if cursor.fetchone() is None:
        cursor.execute(
            "ALTER TABLE student_profiles ADD COLUMN department VARCHAR(100) NULL"
        )


def ensure_profile_schema_compatibility():
    """Add profile columns expected by current routes without replacing data."""
    conn = None
    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            _ensure_student_profile_columns(cursor)
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS pending_registrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    role ENUM('student', 'coach') NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    contact_number VARCHAR(15),
                    otp_hash VARCHAR(255) NOT NULL,
                    otp_expires_at DATETIME NOT NULL,
                    otp_attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
                    otp_sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    otp_send_count TINYINT UNSIGNED NOT NULL DEFAULT 1,
                    status ENUM('pending_verification', 'pending_approval', 'rejected')
                        NOT NULL DEFAULT 'pending_verification',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    verified_at DATETIME NULL
                )"""
            )
            pending_columns = {
                "otp_attempts": "TINYINT UNSIGNED NOT NULL DEFAULT 0",
                "otp_sent_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
                "otp_send_count": "TINYINT UNSIGNED NOT NULL DEFAULT 1",
            }
            for column, definition in pending_columns.items():
                cursor.execute("SHOW COLUMNS FROM pending_registrations LIKE %s", (column,))
                if cursor.fetchone() is None:
                    cursor.execute(
                        f"ALTER TABLE pending_registrations ADD COLUMN {column} {definition}"
                    )
        conn.commit()
        return True
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"[ERROR] Student profile schema migration failed: {exc}")
        return False
    finally:
        if conn:
            conn.close()


def init_db():
    database_name = APP_CONFIG["database"]
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        print("[ERROR] DB_NAME may contain only letters, numbers, and underscores.")
        return False
    try:
        conn = pymysql.connect(**ROOT_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Database creation failed: {e}")
        return False

    if not SCHEMA_PATH.exists():
        print(f"[ERROR] schema.sql not found at {SCHEMA_PATH}")
        return False

    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
    except Exception as e:
        print(f"[ERROR] Reading schema.sql failed: {e}")
        return False

    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            # Remove line comments before splitting so punctuation such as a
            # semicolon inside documentation cannot split a SQL statement.
            schema_sql = re.sub(r"(?m)^\s*--[^\r\n]*", "", schema_sql)
            for stmt in [s.strip() for s in schema_sql.split(";") if s.strip()]:
                if not stmt or stmt.upper().startswith(("CREATE DATABASE", "USE ")):
                    continue
                if stmt.upper().startswith("CREATE TABLE "):
                    stmt = re.sub(r"(?i)^CREATE TABLE\s+", "CREATE TABLE IF NOT EXISTS ", stmt, count=1)
                elif stmt.upper().startswith("CREATE VIEW "):
                    stmt = re.sub(r"(?i)^CREATE VIEW\s+", "CREATE OR REPLACE VIEW ", stmt, count=1)
                elif stmt.upper().startswith("INSERT INTO SPORTS "):
                    stmt = re.sub(r"(?i)^INSERT INTO\s+", "INSERT IGNORE INTO ", stmt, count=1)
                try:
                    if stmt.upper().startswith("CREATE OR REPLACE VIEW STUDENT_DETAILS"):
                        _ensure_student_profile_columns(cursor)
                    cursor.execute(stmt)
                except pymysql.err.ProgrammingError as exc:
                    print(f"[ERROR] Schema statement failed: {exc}")
                    raise
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Schema application failed: {e}")
        return False


def ensure_builtin_admins():
    from werkzeug.security import generate_password_hash
    name = os.getenv("INITIAL_ADMIN_NAME", "").strip()
    email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if not (name and email and password):
        return True
    if len(password) < 12:
        print("[ERROR] INITIAL_ADMIN_PASSWORD must contain at least 12 characters.")
        return False

    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT IGNORE INTO admins
                   (full_name, email, password_hash, is_verified, created_at)
                   VALUES (%s, %s, %s, TRUE, NOW())""",
                (name, email, generate_password_hash(password)),
            )
        conn.commit()
        conn.close()
        return _assign_seed_coach_sports()
    except Exception as e:
        print(f"[ERROR] Error ensuring built-in admins: {e}")
        return False


def _assign_seed_coach_sports():
    """Give the approved demo coach the sports their seeded students play."""
    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM admins ORDER BY id ASC LIMIT 1"
            )
            admin = cursor.fetchone()
            cursor.execute(
                "SELECT id FROM users WHERE email = %s AND role = 'coach'",
                ("sharma@college.edu",),
            )
            coach = cursor.fetchone()
            if not admin or not coach:
                conn.close()
                return True
            cursor.execute(
                """INSERT IGNORE INTO coach_sports (coach_id, sport_id, assigned_by)
                   SELECT %s, id, %s FROM sports
                   WHERE name IN ('Athletics', 'Basketball', 'Football')""",
                (coach["id"], admin["id"]),
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Error assigning demo coach sports: {e}")
        return False


def main():
    init_only = "--init-only" in sys.argv
    if "--reset" in sys.argv:
        print("[ERROR] --reset is disabled because startup must preserve existing data.")
        sys.exit(2)

    needs_init = not db_exists() or not tables_exist()
    if needs_init:
        if not init_db():
            sys.exit(1)

    if not ensure_profile_schema_compatibility():
        sys.exit(1)

    if not ensure_auth_schema_compatibility():
        sys.exit(1)

    if not ensure_builtin_admins():
        sys.exit(1)

    if init_only:
        sys.exit(0)

    os.environ.setdefault("FITNESS_TEST_MODE", "false")
    os.environ["FLASK_DEBUG"] = os.environ.get("FLASK_DEBUG", "false")

    try:
        from app import app

        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
        app.run(
            debug=debug,
            host=os.getenv("FLASK_HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "5000")),
        )
    except Exception as e:
        print(f"[ERROR] Error starting Flask app: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
