"""
Reset the athlete_tracker database using Python/pymysql.
Run from backend folder:  python reset_db.py
"""
import pymysql

DB_CONFIG = {
    "host": "localhost",
    "user": "fitness_user",
    "password": "StrongPassword123!",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

conn = pymysql.connect(**DB_CONFIG)
try:
    with conn.cursor() as cursor:
        cursor.execute("DROP DATABASE IF EXISTS athlete_tracker")
        cursor.execute("CREATE DATABASE athlete_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    print("[OK] Database 'athlete_tracker' reset successfully.")
finally:
    conn.close()