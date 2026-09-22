"""
Database Seeding Script - Fitness Tracker Auth

Seeds the fitness_tracker_auth database with:
- 2 admin accounts (no signup form)
- 2 coach accounts (pending/approved status)
- 5 student accounts with full profiles

The workflow per schema.sql:
- Students sign up and verify email via OTP
- Coaches sign up and await admin approval
- Admins are pre-seeded only (no signup)
"""

import os
import pymysql
from pymysql.cursors import DictCursor
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
    return generate_password_hash(password)


def ensure_builtin_admins(cursor):
    builtin_admins = [
        ('Gareema Kumari Gupta', 'gareema.k.gupta@gmail.com', 'Sample@1234', '9876543210'),
        ('Prakul Gupta', 'guptaaprakul18@gmail.com', 'Secure@1234', '9876543220'),
    ]
    for full_name, email, password, contact_number in builtin_admins:
        cursor.execute(
            """INSERT IGNORE INTO users
               (role, full_name, email, password_hash, contact_number, is_verified, coach_status, created_at)
               VALUES ('admin', %s, %s, %s, %s, TRUE, NULL, NOW())""",
            (full_name, email, hash_password(password), contact_number),
        )


def main():
    """Seed database with demo accounts: 2 admins, 2 coaches, 5 students"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) AS cnt FROM users')
    if cursor.fetchone()['cnt'] > 0:
        ensure_builtin_admins(cursor)
        conn.commit()
        conn.close()
        return

    demo_users = [
        ('admin', 'Gareema Kumari Gupta', 'gareema.k.gupta@gmail.com', hash_password('Sample@1234'), '9876543210', True, None),
        ('admin', 'Prakul Gupta', 'guptaaprakul18@gmail.com', hash_password('Secure@1234'), '9876543220', True, None),
        ('coach', 'Coach Verma', 'verma@college.edu', hash_password('Coach@1234'), '9876543211', True, 'pending'),
        ('coach', 'Coach Sharma', 'sharma@college.edu', hash_password('Coach@1234'), '9876543212', True, 'approved'),
        ('student', 'Arjun Roy', 'arjun@college.edu', hash_password('Student@1234'), '9876543213', True, None),
        ('student', 'Sneha Gupta', 'sneha@college.edu', hash_password('Student@1234'), '9876543214', True, None),
        ('student', 'Kabir Ali', 'kabir@college.edu', hash_password('Student@1234'), '9876543215', True, None),
        ('student', 'Meera Das', 'meera@college.edu', hash_password('Student@1234'), '9876543216', True, None),
        ('student', 'Rohan Singh', 'rohan@college.edu', hash_password('Student@1234'), '9876543217', True, None),
    ]

    user_ids = {}
    for role, full_name, email, password_hash, contact_number, is_verified, coach_status in demo_users:
        cursor.execute(
            """INSERT INTO users (role, full_name, email, password_hash, contact_number, is_verified, coach_status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
            (role, full_name, email, password_hash, contact_number, is_verified, coach_status),
        )
        user_ids[email] = cursor.lastrowid

    students_profiles = [
        ('arjun@college.edu', '2005-03-12', '9876543220', 178.5, 72.0, 'Win nationals', 'Athletics'),
        ('sneha@college.edu', '2004-07-21', '9876543221', 162.0, 58.0, 'Improve fitness', 'Basketball'),
        ('kabir@college.edu', '2003-11-18', '9876543222', 182.0, 78.0, 'Build strength', 'Football'),
        ('meera@college.edu', '2006-02-02', '9876543223', 165.0, 62.0, 'Increase endurance', 'Athletics'),
        ('rohan@college.edu', '2004-09-30', '9876543224', 180.0, 75.0, 'Improve speed', 'Basketball'),
    ]

    for email, dob, emergency_contact, height, weight, goal, sport in students_profiles:
        cursor.execute(
            """INSERT INTO student_profiles (user_id, date_of_birth, emergency_contact, height_cm, weight_kg, goal, sport_activity)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_ids[email], dob, emergency_contact, height, weight, goal, sport),
        )

    conn.commit()
    conn.close()


if __name__ == '__main__':
    main()
