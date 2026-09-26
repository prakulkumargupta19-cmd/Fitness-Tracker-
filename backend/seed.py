"""
Database Seeding Script - Fitness Tracker Auth

Seeds the fitness_tracker_auth database with:
- 2 admin accounts (pre-seeded; no signup form)
- 2 coach accounts (pending/approved status)
- 5 student accounts with full profiles

Workflow:
- Students sign up and verify email via OTP
- Coaches sign up and await admin approval
- Admins are pre-seeded only (no signup)
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


def hash_password(password):
    """Hash a password using Werkzeug."""
    return generate_password_hash(password)


def ensure_builtin_admins(cursor):
    """Ensure the two built-in admin accounts exist."""

    builtin_admins = [
        (
            "Gareema Kumari Gupta",
            "gareema.k.gupta@gmail.com",
            "Sample@1234",
            "9876543210",
        ),
        (
            "Prakul Gupta",
            "guptaaprakul18@gmail.com",
            "Secure@1234",
            "9876543220",
        ),
    ]

    for full_name, email, password, contact_number in builtin_admins:
        cursor.execute(
            """
            INSERT IGNORE INTO admins
            (
                full_name,
                email,
                password_hash,
                contact_number,
                is_verified,
                created_at
            )
            VALUES (%s, %s, %s, %s, TRUE, NOW())
            """,
            (
                full_name,
                email,
                hash_password(password),
                contact_number,
            ),
        )


def main():
    """Seed the database with demo accounts and student profiles."""

    conn = None

    try:
        conn = pymysql.connect(**DB_CONFIG)

        with conn.cursor() as cursor:

            # ---------------------------------------------------------
            # 1. Check whether users already exist
            # ---------------------------------------------------------
            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            user_count = cursor.fetchone()["cnt"]

            # If database already contains users, make sure the
            # built-in admin accounts still exist and stop.
            if user_count > 0:
                ensure_builtin_admins(cursor)
                conn.commit()

                print("Database already contains users.")
                print("Built-in admin accounts have been checked.")
                return

            # ---------------------------------------------------------
            # 2. Demo users
            # ---------------------------------------------------------
            demo_users = [
                # Coaches
                (
                    "coach",
                    "Coach Verma",
                    "verma@college.edu",
                    "Coach@1234",
                    "9876543211",
                    True,
                    "pending",
                ),
                (
                    "coach",
                    "Coach Sharma",
                    "sharma@college.edu",
                    "Coach@1234",
                    "9876543212",
                    True,
                    "approved",
                ),

                # Students
                (
                    "student",
                    "Arjun Roy",
                    "arjun@college.edu",
                    "Student@1234",
                    "9876543213",
                    True,
                    None,
                ),
                (
                    "student",
                    "Sneha Gupta",
                    "sneha@college.edu",
                    "Student@1234",
                    "Student@1234",
                    "9876543214",
                    True,
                    None,
                ),
                (
                    "student",
                    "Kabir Ali",
                    "kabir@college.edu",
                    "Student@1234",
                    "9876543215",
                    True,
                    None,
                ),
                (
                    "student",
                    "Meera Das",
                    "meera@college.edu",
                    "Student@1234",
                    "9876543216",
                    True,
                    None,
                ),
                (
                    "student",
                    "Rohan Singh",
                    "rohan@college.edu",
                    "Student@1234",
                    "9876543217",
                    True,
                    None,
                ),
            ]

            # ---------------------------------------------------------
            # 3. Insert users and store their IDs
            # ---------------------------------------------------------
            user_ids = {}

            for (
                role,
                full_name,
                email,
                password,
                contact_number,
                is_verified,
                coach_status,
            ) in demo_users:

                cursor.execute(
                    """
                    INSERT INTO users
                    (
                        role,
                        full_name,
                        email,
                        password_hash,
                        contact_number,
                        is_verified,
                        coach_status,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        role,
                        full_name,
                        email,
                        hash_password(password),
                        contact_number,
                        is_verified,
                        coach_status,
                    ),
                )

                user_ids[email] = cursor.lastrowid

            # Built-in admins live in the admins table, not users.
            ensure_builtin_admins(cursor)

            # ---------------------------------------------------------
            # 4. Student profile data
            # ---------------------------------------------------------
            student_profiles = [
                (
                    "arjun@college.edu",
                    "2005-03-12",
                    "9876543220",
                    178.5,
                    72.0,
                    "Win nationals",
                    "Athletics",
                    "Computer Science",
                ),
                (
                    "sneha@college.edu",
                    "2004-07-21",
                    "9876543221",
                    162.0,
                    58.0,
                    "Improve fitness",
                    "Basketball",
                    "Mechanical Engineering",
                ),
                (
                    "kabir@college.edu",
                    "2003-11-18",
                    "9876543222",
                    182.0,
                    78.0,
                    "Build strength",
                    "Football",
                    "Electrical Engineering",
                ),
                (
                    "meera@college.edu",
                    "2006-02-02",
                    "9876543223",
                    165.0,
                    62.0,
                    "Increase endurance",
                    "Athletics",
                    "Business Administration",
                ),
                (
                    "rohan@college.edu",
                    "2004-09-30",
                    "9876543224",
                    180.0,
                    75.0,
                    "Improve speed",
                    "Basketball",
                    "Mathematics",
                ),
            ]

            # ---------------------------------------------------------
            # 5. Insert student profiles
            # ---------------------------------------------------------
            for (
                email,
                dob,
                emergency_contact,
                height,
                weight,
                goal,
                sport,
                department,
            ) in student_profiles:

                cursor.execute(
                    """
                    INSERT INTO student_profiles
                    (
                        user_id,
                        date_of_birth,
                        emergency_contact,
                        height_cm,
                        weight_kg,
                        goal,
                        sport_activity,
                        department
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_ids[email],
                        dob,
                        emergency_contact,
                        height,
                        weight,
                        goal,
                        sport,
                        department,
                    ),
                )

        # ---------------------------------------------------------
        # 6. Commit everything
        # ---------------------------------------------------------
        conn.commit()

        print("Database seeding completed successfully!")
        print("Created:")
        print("- 2 admin accounts")
        print("- 2 coach accounts")
        print("- 5 student accounts")
        print("- 5 student profiles")

    except pymysql.MySQLError as e:
        if conn:
            conn.rollback()

        print("Database error occurred:")
        print(e)

    except Exception as e:
        if conn:
            conn.rollback()

        print("Unexpected error occurred:")
        print(e)

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
