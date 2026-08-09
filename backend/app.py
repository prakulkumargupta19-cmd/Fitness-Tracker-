from flask import Flask, request, jsonify
import sqlite3
import hashlib

app = Flask(__name__)

DB_NAME = "athlete_tracker.db"


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.route("/")
def home():
    return "Backend server is working!"


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

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    password_hash = hash_password(password)

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        """
        SELECT id, user_code, name, email, role, sport
        FROM users
        WHERE email = ? AND password_hash = ?
        """,
        (email, password_hash)
    ).fetchone()

    conn.close()

    if user:
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
        "message": "Invalid email or password"
    }), 401


if __name__ == "__main__":
    app.run(debug=True)