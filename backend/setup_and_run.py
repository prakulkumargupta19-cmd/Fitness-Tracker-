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

from db import get_db  # noqa: E402


SCHEMA_PATH = BASE_DIR / "schema.sql"

COACH_WORKFLOW_MIGRATION = (
    BASE_DIR
    / "migrations"
    / "005_coach_assignment_attendance_workflow.sql"
)


def init_db():
    """Apply PostgreSQL schema and migrations without deleting existing data."""

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

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

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
                    os.getenv(
                        "ADMIN_NAME",
                        "Administrator"
                    ),
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