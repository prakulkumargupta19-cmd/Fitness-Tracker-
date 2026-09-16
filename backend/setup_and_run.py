import os
import sys
import pymysql
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
SCHEMA_PATH = BASE_DIR / "schema.sql"

ROOT_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Prakul@2006",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

APP_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Prakul@2006",
    "database": "fitness_tracker_auth",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def db_exists():
    try:
        conn = pymysql.connect(**ROOT_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE 'fitness_tracker_auth'")
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
            cursor.execute("SHOW TABLES LIKE 'users'")
            result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception:
        return False


def users_seeded():
    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            count = cursor.fetchone()["cnt"]
        conn.close()
        return count > 0
    except Exception:
        return False


def ensure_auth_schema_compatibility():
    """Add OTP purposes introduced after the initial schema version."""
    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(
                """ALTER TABLE otp_verifications
                   MODIFY purpose ENUM('signup', 'login', 'password_reset') NOT NULL"""
            )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        print(f"[ERROR] Auth schema migration failed: {exc}")
        return False


def init_db():
    try:
        conn = pymysql.connect(**ROOT_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("DROP DATABASE IF EXISTS fitness_tracker_auth")
            cursor.execute("CREATE DATABASE fitness_tracker_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
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
            for stmt in [s.strip() for s in schema_sql.split(";") if s.strip()]:
                try:
                    cursor.execute(stmt)
                except Exception:
                    pass
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Schema application failed: {e}")
        return False


def seed_admins():
    from werkzeug.security import generate_password_hash

    demo_users = [
        ("admin", "Gareema Kumari Gupta", "gareema.k.gupta@gmail.com", generate_password_hash("Sample@1234"), "9876543210", True, None),
        ("admin", "Prakul Gupta", "guptaaprakul18@gmail.com", generate_password_hash("Secure@1234"), "9876543220", True, None),
        ("coach", "Coach Verma", "verma@college.edu", generate_password_hash("Coach@1234"), "9876543211", True, "pending"),
        ("coach", "Coach Sharma", "sharma@college.edu", generate_password_hash("Coach@1234"), "9876543212", True, "approved"),
        ("student", "Arjun Roy", "arjun@college.edu", generate_password_hash("Student@1234"), "9876543213", True, None),
        ("student", "Sneha Gupta", "sneha@college.edu", generate_password_hash("Student@1234"), "9876543214", True, None),
        ("student", "Kabir Ali", "kabir@college.edu", generate_password_hash("Student@1234"), "9876543215", True, None),
        ("student", "Meera Das", "meera@college.edu", generate_password_hash("Student@1234"), "9876543216", True, None),
        ("student", "Rohan Singh", "rohan@college.edu", generate_password_hash("Student@1234"), "9876543217", True, None),
    ]

    try:
        conn = pymysql.connect(**APP_CONFIG)
        cursor = conn.cursor()
        user_ids = {}
        for role, full_name, email, password_hash, contact_number, is_verified, coach_status in demo_users:
            cursor.execute(
                """INSERT INTO users (role, full_name, email, password_hash, contact_number, is_verified, coach_status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
                (role, full_name, email, password_hash, contact_number, is_verified, coach_status),
            )
            user_ids[email] = cursor.lastrowid

        students_profiles = [
            ("arjun@college.edu", "2005-03-12", "9876543220", 178.5, 72.0, "Win nationals in 100m sprint", "Athletics"),
            ("sneha@college.edu", "2004-07-21", "9876543221", 162.0, 58.0, "Improve overall fitness & stamina", "Basketball"),
            ("kabir@college.edu", "2003-11-18", "9876543222", 182.0, 78.0, "Build strength and endurance", "Football"),
            ("meera@college.edu", "2006-02-02", "9876543223", 165.0, 62.0, "Increase endurance", "Athletics"),
            ("rohan@college.edu", "2004-09-30", "9876543224", 180.0, 75.0, "Improve speed", "Basketball"),
        ]

        for email, dob, emergency_contact, height, weight, goal, sport in students_profiles:
            cursor.execute(
                """INSERT INTO student_profiles (user_id, date_of_birth, emergency_contact, height_cm, weight_kg, goal, sport_activity)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (user_ids[email], dob, emergency_contact, height, weight, goal, sport),
            )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Error seeding demo accounts: {e}")
        return False


def ensure_builtin_admins():
    from werkzeug.security import generate_password_hash

    builtin_admins = [
        ("Gareema Kumari Gupta", "gareema.k.gupta@gmail.com", "Sample@1234", "9876543210"),
        ("Prakul Gupta", "guptaaprakul18@gmail.com", "Secure@1234", "9876543220"),
    ]

    try:
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            for full_name, email, password, contact_number in builtin_admins:
                cursor.execute(
                    """INSERT IGNORE INTO users
                       (role, full_name, email, password_hash, contact_number, is_verified, coach_status, created_at)
                       VALUES ('admin', %s, %s, %s, %s, TRUE, NULL, NOW())""",
                    (full_name, email, generate_password_hash(password), contact_number),
                )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Error ensuring built-in admins: {e}")
        return False


def main():
    init_only = "--init-only" in sys.argv
    force_reset = "--reset" in sys.argv

    needs_init = force_reset or not db_exists() or not tables_exist()
    if needs_init:
        if not init_db():
            sys.exit(1)

    if not ensure_auth_schema_compatibility():
        sys.exit(1)

    if force_reset or not users_seeded():
        if not seed_admins():
            sys.exit(1)
    elif not ensure_builtin_admins():
        sys.exit(1)

    if init_only:
        sys.exit(0)

    os.environ.setdefault("FITNESS_TEST_MODE", "false")
    os.environ["FLASK_DEBUG"] = os.environ.get("FLASK_DEBUG", "false")

    try:
        from app import app
        app.run(debug=True, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"[ERROR] Error starting Flask app: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
