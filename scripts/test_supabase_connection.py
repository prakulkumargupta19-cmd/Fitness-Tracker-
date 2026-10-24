"""Safely verify the configured Supabase PostgreSQL connection and required tables."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from time import perf_counter

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TABLES = (
    "users",
    "admins",
    "student_profiles",
    "otp_verifications",
    "pending_registrations",
    "sports",
    "admin_otp_verifications",
    "coach_sports",
    "student_sports",
    "physical_assessments",
    "training_sessions",
    "goals",
    "coach_feedback",
    "attendance_sessions",
    "attendance_records",
)


def main() -> int:
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("SUPABASE_DB_URL")
    connection = None
    connection_ok = False
    query_ok = False
    schema_checked = False
    latency_ms: float | None = None
    table_status = {name: None for name in REQUIRED_TABLES}
    error_type = None

    if database_url:
        try:
            connection = psycopg.connect(
                database_url,
                connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
            )
            connection_ok = True
            started_at = perf_counter()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                query_ok = cursor.fetchone() == (1,)
            latency_ms = round((perf_counter() - started_at) * 1000, 2)

            if query_ok:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = current_schema()
                          AND table_type = 'BASE TABLE'
                        """
                    )
                    present_tables = {row[0] for row in cursor.fetchall()}
                table_status = {
                    name: name in present_tables for name in REQUIRED_TABLES
                }
                schema_checked = True
        except (psycopg.Error, ValueError, TypeError) as error:
            error_type = type(error).__name__
        finally:
            if connection is not None:
                connection.close()
    else:
        error_type = "SUPABASE_DB_URL is not configured"

    print("SUPABASE CONNECTION TEST")
    print("========================")
    print(f"Connection: {'PASS' if connection_ok else 'FAIL'}")
    print(f"Database Query: {'PASS' if query_ok else 'FAIL'}")
    print(f"Latency: {latency_ms:.2f} ms" if latency_ms is not None else "Latency: N/A")
    print()
    print("Required Tables:")
    for name, present in table_status.items():
        result = "PASS" if present else "FAIL" if schema_checked else "UNKNOWN"
        print(f"{name:<24}{result}")

    if not schema_checked:
        print("Schema verification: UNKNOWN (database query was not available).")
    if error_type:
        print(f"Diagnostic error: {error_type}")

    return 0 if connection_ok and query_ok and all(table_status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
