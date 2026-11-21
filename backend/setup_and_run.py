"""Initialize the configured PostgreSQL schema or run the local Flask app."""

import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(PROJECT_ROOT / ".env")

from db import (  # noqa: E402
    database_backend,
    get_db,
    initialize_local_database,
)


SCHEMA_PATH = BASE_DIR / "schema.sql"

COACH_WORKFLOW_MIGRATION = (
    BASE_DIR
    / "migrations"
    / "005_coach_assignment_attendance_workflow.sql"
)

REFERENCE_FEATURE_MIGRATION = (
    BASE_DIR
    / "migrations"
    / "006_fit_track_reference_features.sql"
)

FIT_TRACK_INTEGRITY_MIGRATION = (
    BASE_DIR
    / "migrations"
    / "007_fit_track_integrity.sql"
)

DEPLOYMENT_MIGRATIONS = (
    ("Dashboard schedule migration 008", BASE_DIR / "migrations" / "008_dashboard_schedule.sql"),
    ("Student department migration 009", BASE_DIR / "migrations" / "009_student_department_choices.sql"),
    ("Schedule migration 010", BASE_DIR / "migrations" / "010_schedule_without_programmes.sql"),
    ("Admin login rate limit migration 011", BASE_DIR / "migrations" / "011_admin_login_rate_limit.sql"),
    ("Student deactivation migration 012", BASE_DIR / "migrations" / "012_student_deactivation.sql"),
    ("Event registration URL migration 013", BASE_DIR / "migrations" / "013_event_registration_url.sql"),
    ("Expired authentication data cleanup migration 014", BASE_DIR / "migrations" / "014_expired_auth_cleanup.sql"),
    ("Sport assessment schema migration", BASE_DIR / "migrations" / "20261109_add_assessment_schema.sql"),
    ("Legacy performance records removal migration 015", BASE_DIR / "migrations" / "015_remove_legacy_performance_records.sql"),
    ("Coach profile fields removal migration 016", BASE_DIR / "migrations" / "016_remove_coach_profile_fields.sql"),
    ("Not-held schedule status migration 017", BASE_DIR / "migrations" / "017_schedule_not_held_status.sql"),
)


def init_db():
    """Apply PostgreSQL schema and migrations without deleting existing data."""

    if database_backend() == "sqlite":
        try:
            path = initialize_local_database()
            print(f"[INFO] Local SQLite database ready: {path}")
            return True
        except Exception as error:
            print(f"[ERROR] Local SQLite initialization failed: {error}")
            traceback.print_exc()
            return False

    if not SCHEMA_PATH.is_file():
        print("[ERROR] backend/schema.sql is missing.")
        return False

    db = None

    try:
        # =========================================================
        # 1. CONNECT TO SUPABASE
        # =========================================================
        print("[INFO] Connecting to Supabase PostgreSQL...")

        db = get_db()

        print("[INFO] PostgreSQL connection successful.")

        # =========================================================
        # 2. APPLY BASE SCHEMA
        # =========================================================
        print("[INFO] Applying backend/schema.sql...")

        schema_sql = SCHEMA_PATH.read_text(
            encoding="utf-8"
        )

        with db.cursor() as cursor:
            cursor.execute(schema_sql)

        db.commit()

        print("[INFO] Base schema applied successfully.")

        # =========================================================
        # 3. UPDATE EXISTING STATUS ENUMS
        #
        # Existing Supabase databases may already have these enums.
        # Migration 005 requires the "declined" value.
        # =========================================================
        print("[INFO] Checking PostgreSQL status enums...")

        status_enums = [
            "pending_status_type",
            "coach_status_type",
        ]

        with db.cursor() as cursor:

            for enum_name in status_enums:

                cursor.execute(
                    """
                    SELECT 1
                    FROM pg_type
                    WHERE typname = %s
                    """,
                    (enum_name,),
                )

                enum_exists = cursor.fetchone()

                if enum_exists:

                    print(
                        f"[INFO] Adding 'declined' to "
                        f"{enum_name} if needed..."
                    )

                    # enum_name comes only from the hard-coded list above.
                    cursor.execute(
                        f"""
                        ALTER TYPE {enum_name}
                        ADD VALUE IF NOT EXISTS 'declined'
                        """
                    )

                else:

                    print(
                        f"[INFO] {enum_name} does not exist; "
                        f"skipping."
                    )

        db.commit()

        print(
            "[INFO] PostgreSQL status enums checked successfully."
        )

        # =========================================================
        # 4. APPLY COACH / ATTENDANCE MIGRATION
        # =========================================================
        if COACH_WORKFLOW_MIGRATION.is_file():

            print(
                "[INFO] Applying coach/attendance migration 005..."
            )

            migration_sql = (
                COACH_WORKFLOW_MIGRATION.read_text(
                    encoding="utf-8"
                )
            )

            with db.cursor() as cursor:
                cursor.execute(migration_sql)

            db.commit()

            print(
                "[INFO] Coach/attendance migration 005 "
                "applied successfully."
            )

        else:

            print(
                "[WARNING] Migration 005 file was not found; "
                "skipping."
            )

        if REFERENCE_FEATURE_MIGRATION.is_file():
            print("[INFO] Applying Fit-Track reference feature migration 006...")
            feature_sql = REFERENCE_FEATURE_MIGRATION.read_text(encoding="utf-8")
            with db.cursor() as cursor:
                cursor.execute(feature_sql)
            db.commit()
            print("[INFO] Fit-Track reference feature migration 006 applied successfully.")
        else:
            print("[WARNING] Migration 006 file was not found; skipping.")

        if FIT_TRACK_INTEGRITY_MIGRATION.is_file():
            print("[INFO] Applying Fit-Track integrity migration 007...")
            integrity_sql = FIT_TRACK_INTEGRITY_MIGRATION.read_text(encoding="utf-8")
            with db.cursor() as cursor:
                cursor.execute(integrity_sql)
            db.commit()
            print("[INFO] Fit-Track integrity migration 007 applied successfully.")
        else:
            print("[WARNING] Migration 007 file was not found; skipping.")

        # Reapply migration 010's idempotent column guards every startup. Some
        # deployments have already recorded the migration but still lack the
        # columns used by schedule writes after partial/manual schema upgrades.
        if SCHEDULE_WITHOUT_PROGRAMMES_MIGRATION.is_file():
            print("[INFO] Applying schedule migration 010 (sessions are sport-based)...")
            schedule_sql = SCHEDULE_WITHOUT_PROGRAMMES_MIGRATION.read_text(encoding="utf-8")
            with db.cursor() as cursor:
                cursor.execute(schedule_sql)
            db.commit()
            print("[INFO] Schedule migration 010 applied successfully.")
        else:
            print("[WARNING] Migration 010 file was not found; skipping.")

        if ADMIN_LOGIN_RATE_LIMIT_MIGRATION.is_file():
            print("[INFO] Applying administrator login rate limit migration 011...")
            rate_limit_sql = ADMIN_LOGIN_RATE_LIMIT_MIGRATION.read_text(encoding="utf-8")
            with db.cursor() as cursor:
                cursor.execute(rate_limit_sql)
            db.commit()
            print("[INFO] Administrator login rate limit migration applied successfully.")
        else:
            print("[WARNING] Migration 011 file was not found; skipping.")
        # Apply the migrations required by the current app after the base
        # schema. Run this initializer against staging before production.
        for migration_name, migration_path in DEPLOYMENT_MIGRATIONS:
            if not migration_path.is_file():
                print(f"[WARNING] {migration_name} was not found; skipping.")
                continue
            print(f"[INFO] Applying {migration_name}...")
            migration_sql = migration_path.read_text(encoding="utf-8")
            with db.cursor() as cursor:
                cursor.execute(migration_sql)
            db.commit()
            print(f"[INFO] {migration_name} applied successfully.")

        # Keep the programme-independent schema active when local SQLite starts too.
        from db import initialize_local_database
        if database_backend() == "sqlite":
            initialize_local_database()

        # =========================================================
        # 5. SUCCESS
        # =========================================================
        print()
        print(
            "[SUCCESS] PostgreSQL database initialization "
            "completed."
        )

        return True

    except Exception as error:

        print()
        print(
            "[ERROR] PostgreSQL schema initialization failed."
        )

        print(
            f"Error type : {type(error).__name__}"
        )

        print(
            f"Error      : {error}"
        )

        print()
        print("FULL TRACEBACK:")

        traceback.print_exc()

        if db is not None:

            try:
                db.rollback()
            except Exception:
                pass

        return False

    finally:

        if db is not None:

            try:
                db.close()
            except Exception:
                pass


def ensure_builtin_admin():
    """Ensure the configured built-in admin account exists."""

    admin_email = os.getenv("ADMIN_EMAIL") or os.getenv("INITIAL_ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD") or os.getenv("INITIAL_ADMIN_PASSWORD")

    if not admin_email or not admin_password:

        print(
            "[INFO] ADMIN_EMAIL / ADMIN_PASSWORD not configured; "
            "skipping built-in admin creation."
        )

        return True

    db = None

    try:

        db = get_db()

        password_hash = generate_password_hash(
            admin_password
        )

        with db.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO admins (
                    full_name,
                    email,
                    password_hash,
                    is_active
                )
                VALUES (%s, %s, %s, TRUE)

                ON CONFLICT (email)
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    is_active = TRUE
                """,
                (
                    os.getenv("ADMIN_NAME") or os.getenv("INITIAL_ADMIN_NAME", "Administrator"),
                    admin_email.strip().lower(),
                    password_hash,
                ),
            )

        db.commit()

        print(
            "[INFO] Built-in admin account checked successfully."
        )

        return True

    except Exception as error:

        print()
        print("[ERROR] Built-in admin setup failed.")

        print(
            f"Error type : {type(error).__name__}"
        )

        print(
            f"Error      : {error}"
        )

        traceback.print_exc()

        if db is not None:

            try:
                db.rollback()
            except Exception:
                pass

        return False

    finally:

        if db is not None:

            try:
                db.close()
            except Exception:
                pass


def run_app():
    """Start the Flask application."""

    try:

        from app import app

        print()
        print(
            "[INFO] Starting Fitness Tracker Flask server..."
        )

        print(
            "[INFO] Backend: http://127.0.0.1:5000"
        )

        print()

        app.run(
            host="0.0.0.0",
            port=int(
                os.getenv(
                    "PORT",
                    "5000"
                )
            ),
            debug=False,
            use_reloader=False,
        )

    except Exception as error:

        print()
        print(
            "[ERROR] Flask application failed to start."
        )

        print(
            f"Error type : {type(error).__name__}"
        )

        print(
            f"Error      : {error}"
        )

        traceback.print_exc()

        return False

    return True


def main():
    """Main entry point."""

    init_only = "--init-only" in sys.argv

    # ---------------------------------------------------------
    # Initialize database
    # ---------------------------------------------------------
    if not init_db():

        print()
        print(
            "[ERROR] Database initialization failed."
        )

        return 1

    # ---------------------------------------------------------
    # Ensure built-in admin
    # ---------------------------------------------------------
    if not ensure_builtin_admin():

        print()
        print(
            "[ERROR] Built-in admin setup failed."
        )

        return 1

    # ---------------------------------------------------------
    # Init-only mode
    # ---------------------------------------------------------
    if init_only:

        print()
        print(
            "[SUCCESS] Initialization finished. Exiting."
        )

        return 0

    # ---------------------------------------------------------
    # Start Flask
    # ---------------------------------------------------------
    return 0 if run_app() else 1


if __name__ == "__main__":
    raise SystemExit(main())
