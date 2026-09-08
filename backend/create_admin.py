import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "athlete_tracker.db"

name = "PRAKUL"
email = "guptaaprakul18@gmail.com"
password = "Prakul@2006"
user_code = "ADMIN001"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

password_hash = generate_password_hash(password)

try:
    cursor.execute("""
        INSERT INTO users (
            user_code,
            name,
            email,
            password_hash,
            email_verified,
            account_status,
            role
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_code,
        name,
        email,
        password_hash,
        1,
        "active",
        "admin"
    ))

    conn.commit()

    print("Admin created successfully!")
    print("Name:", name)
    print("Email:", email)
    print("Role: admin")

except sqlite3.IntegrityError as e:
    print("Could not create admin.")
    print("Reason:", e)

finally:
    conn.close()