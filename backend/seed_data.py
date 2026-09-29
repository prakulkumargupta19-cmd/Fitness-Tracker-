"""
Database Demo Data - Fitness Tracker
Seeds the database with valid @inspiria.edu.in accounts.
"""

import pymysql
from werkzeug.security import generate_password_hash

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "password@1234",
    "database": "fitness_tracker_auth",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

def seed():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # Seed coach
            cursor.execute(
                """INSERT IGNORE INTO users (full_name, email, password_hash, role, is_verified, coach_status)
                   VALUES (%s, %s, %s, 'coach', 1, 'approved')""",
                ("Coach Demo", "coach@inspiria.edu.in", generate_password_hash("Coach@1234")),
            )
            # Seed student
            cursor.execute(
                """INSERT IGNORE INTO users (full_name, email, password_hash, role, is_verified)
                   VALUES (%s, %s, %s, 'student', 1)""",
                ("Student Demo", "student@inspiria.edu.in", generate_password_hash("Student@1234")),
            )
        conn.commit()
        print("Demo data seeded successfully.")
    except Exception as e:
        print(f"Error seeding: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed()
