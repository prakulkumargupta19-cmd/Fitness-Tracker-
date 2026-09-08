import sqlite3

DB_PATH = "athlete_tracker.db"

new_email = input("Enter the email address you want to use for ADM001: ").strip().lower()

if not new_email:
    print("Email cannot be empty.")
    raise SystemExit

db = sqlite3.connect(DB_PATH)

cursor = db.execute(
    """
    UPDATE users
    SET email = ?
    WHERE user_code = 'ADM001' AND role = 'admin'
    """,
    (new_email,)
)

db.commit()

if cursor.rowcount == 1:
    print(f"Admin email successfully changed to: {new_email}")
else:
    print("ADM001 admin account was not found.")

db.close()