from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import secrets
from datetime import datetime, timedelta
import os
import smtplib
import ssl
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)

DATABASE = "athlete_tracker.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# OTP GENERATOR
# =========================================================

def generate_otp():
    return f"{secrets.randbelow(1000000):06d}"


# =========================================================
# HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return "Backend server is working!"


# =========================================================
# REGISTER
# =========================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received"
        }), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Name, email and password are required"
        }), 400

    email = email.strip().lower()

    try:
        db = get_db()

        existing = db.execute(
            "SELECT id FROM users WHERE LOWER(email) = ?",
            (email,)
        ).fetchone()

        if existing:
            db.close()

            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 400

        count = db.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'player'"
        ).fetchone()[0]

        user_code = f"ATH{count + 1:03d}"

        db.execute(
            """
            INSERT INTO users (
                user_code,
                name,
                email,
                password_hash,
                role,
                sport,
                contact_number,
                gender,
                date_of_birth
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_code,
                name,
                email,
                generate_password_hash(password),
                "player",
                data.get("sport", ""),
                data.get("contact_number", ""),
                data.get("gender", ""),
                data.get("date_of_birth", "")
            )
        )

        db.commit()
        db.close()

        return jsonify({
            "success": True,
            "message": "Registered",
            "user_code": user_code
        }), 201

    except sqlite3.Error as error:
        print("REGISTER DATABASE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Database error"
        }), 500


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received"
        }), 400

    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "player")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    email = email.strip().lower()

    try:
        db = get_db()

        user = db.execute(
            """
            SELECT
                id,
                user_code,
                name,
                email,
                password_hash,
                role,
                sport
            FROM users
            WHERE LOWER(email) = ?
            AND role = ?
            """,
            (email, role)
        ).fetchone()

        db.close()

    except sqlite3.Error as error:
        print("LOGIN DATABASE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Database error"
        }), 500

    if user and check_password_hash(
        user["password_hash"],
        password
    ):
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "user_code": user["user_code"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "sport": user["sport"]
            }
        })

    return jsonify({
        "success": False,
        "message": "Invalid credentials"
    }), 401


# =========================================================
# FORGOT PASSWORD
# SEND OTP
# =========================================================

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received"
        }), 400

    email = data.get("email")

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required"
        }), 400

    email = email.strip().lower()

    try:
        db = get_db()

        user = db.execute(
            "SELECT id FROM users WHERE LOWER(email) = ?",
            (email,)
        ).fetchone()

        if not user:
            db.close()

            return jsonify({
                "success": True,
                "message": "If email exists, OTP sent"
            })

        otp = generate_otp()

        expires_at = datetime.now() + timedelta(minutes=10)

        db.execute(
            """
            INSERT INTO password_resets (
                email,
                otp,
                expires_at,
                used
            )
            VALUES (?, ?, ?, 0)
            """,
            (
                email,
                otp,
                expires_at.strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        db.commit()
        db.close()

        sender_email = os.getenv("MAIL_USERNAME")
        sender_password = os.getenv("MAIL_PASSWORD")

        if not sender_email or not sender_password:
            print("MAIL_USERNAME or MAIL_PASSWORD is missing")

            return jsonify({
                "success": False,
                "message": "Email service is not configured"
            }), 500

        message = EmailMessage()
        message["Subject"] = "Fitness Tracker - Password Reset OTP"
        message["From"] = sender_email
        message["To"] = email

        message.set_content(
            f"""Hello,

Your Fitness Tracker password reset OTP is:

{otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, please ignore this email.

Regards,
Fitness Tracker Team
"""
        )

        context = ssl.create_default_context()

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(message)

        print("OTP email sent successfully to:", email)

        return jsonify({
            "success": True,
            "message": "OTP sent to your email"
        })

    except sqlite3.Error as error:
        print("FORGOT PASSWORD DATABASE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Database error"
        }), 500

    except Exception as error:
        print("OTP EMAIL ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Unable to send OTP email"
        }), 500


# =========================================================
# VERIFY OTP
# =========================================================

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received"
        }), 400

    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return jsonify({
            "success": False,
            "message": "Email and OTP are required"
        }), 400

    email = email.strip().lower()
    otp = str(otp).strip()

    try:
        db = get_db()

        record = db.execute(
            """
            SELECT *
            FROM password_resets
            WHERE email = ?
            AND otp = ?
            AND used = 0
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email, otp)
        ).fetchone()

        if not record:
            db.close()

            return jsonify({
                "success": False,
                "message": "Invalid OTP"
            }), 400

        expires_at = datetime.strptime(
            record["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() > expires_at:
            db.close()

            return jsonify({
                "success": False,
                "message": "OTP expired"
            }), 400

        db.close()

        return jsonify({
            "success": True,
            "message": "OTP verified"
        })

    except sqlite3.Error as error:
        print("VERIFY OTP DATABASE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Database error"
        }), 500


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route("/api/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received"
        }), 400

    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")

    if not email or not otp or not new_password:
        return jsonify({
            "success": False,
            "message": "Email, OTP and new password are required"
        }), 400

    email = email.strip().lower()
    otp = str(otp).strip()

    try:
        db = get_db()

        record = db.execute(
            """
            SELECT *
            FROM password_resets
            WHERE email = ?
            AND otp = ?
            AND used = 0
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email, otp)
        ).fetchone()

        if not record:
            db.close()

            return jsonify({
                "success": False,
                "message": "Invalid request"
            }), 400

        expires_at = datetime.strptime(
            record["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() > expires_at:
            db.close()

            return jsonify({
                "success": False,
                "message": "OTP expired"
            }), 400

        db.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE LOWER(email) = ?
            """,
            (
                generate_password_hash(new_password),
                email
            )
        )

        db.execute(
            """
            UPDATE password_resets
            SET used = 1
            WHERE id = ?
            """,
            (record["id"],)
        )

        db.commit()
        db.close()

        return jsonify({
            "success": True,
            "message": "Password reset successful"
        })

    except sqlite3.Error as error:
        print("RESET PASSWORD DATABASE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Database error"
        }), 500


# =========================================================
# GET USERS
# TESTING
# =========================================================

@app.route("/api/users", methods=["GET"])
def get_users():

    try:
        db = get_db()

        users = db.execute(
            """
            SELECT
                id,
                user_code,
                name,
                email,
                role,
                sport
            FROM users
            """
        ).fetchall()

        db.close()

        return jsonify([dict(user) for user in users])

    except sqlite3.Error as error:
        print("USERS DATABASE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Database error"
        }), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":
    print("Server running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)