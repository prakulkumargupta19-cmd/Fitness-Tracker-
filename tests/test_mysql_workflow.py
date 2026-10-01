"""Real MySQL coverage for the signup, approval, sport, performance, and attendance flow."""

from uuid import uuid4

import os
import pytest
from werkzeug.security import generate_password_hash

from backend.app import app
from backend.db import get_db


@pytest.mark.skipif(
    os.getenv("RUN_MYSQL_TESTS", "false").lower() != "true",
    reason="Set RUN_MYSQL_TESTS=true to use an isolated disposable MySQL database.",
)
def test_student_coach_admin_workflow_persists_in_mysql(monkeypatch):
    suffix = uuid4().hex[:12]
    student_email = f"student.{suffix}@inspiria.edu.in"
    coach_email = f"coach.{suffix}@inspiria.edu.in"
    abuse_email = f"abuse.{suffix}@inspiria.edu.in"
    admin_email = f"admin.{suffix}@example.test"
    password = "Valid-Test-Password-123"
    delivered_otps = {}
    monkeypatch.setattr(
        "backend.app.send_otp_email",
        lambda email, _name, purpose, otp: delivered_otps.__setitem__((email, purpose), otp) or True,
    )
    monkeypatch.setattr("backend.app.send_coach_approval_email", lambda *args: True)

    with app.test_client() as abuse_client:
        response = abuse_client.post("/api/signup", json={
            "role": "student", "full_name": "OTP Limit Check",
            "email": abuse_email, "password": password,
        })
        assert response.status_code == 202
        for _ in range(4):
            response = abuse_client.post("/api/account-verification/send", json={"email": abuse_email})
            assert response.status_code == 200
        response = abuse_client.post("/api/account-verification/send", json={"email": abuse_email})
        assert response.status_code == 429
        for _ in range(5):
            response = abuse_client.post("/api/account-verification/verify", json={
                "email": abuse_email, "otp": "invalid-code",
            })
            assert response.status_code == 400
        response = abuse_client.post("/api/account-verification/verify", json={
            "email": abuse_email, "otp": "invalid-code",
        })
        assert response.status_code == 429

    with app.test_client() as student:
        response = student.post("/api/signup", json={
            "role": "student", "full_name": "Rahul Test",
            "email": student_email, "password": password,
        })
        assert response.status_code == 202
        response = student.post("/api/account-verification/verify", json={
            "email": student_email, "otp": delivered_otps[(student_email, "signup")],
        })
        assert response.status_code == 200
        response = student.post("/api/profile/setup", json={
            "date_of_birth": "2005-03-12", "emergency_contact": "9876543210",
            "sports": ["Football", "Football"],
        })
        assert response.status_code == 200

        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (student_email,))
                student_id = cursor.fetchone()["id"]
                cursor.execute(
                    """SELECT s.name FROM student_sports ss JOIN sports s ON s.id = ss.sport_id
                       WHERE ss.student_id = %s""",
                    (student_id,),
                )
                assert [row["name"] for row in cursor.fetchall()] == ["Football"]
        finally:
            db.close()

        response = student.post("/api/login", json={
            "role": "student", "email": student_email, "password": password,
        })
        assert response.status_code == 200
        response = student.post("/api/login/verify-otp", json={
            "email": student_email, "otp": delivered_otps[(student_email, "login")],
        })
        assert response.status_code == 200

    with app.test_client() as coach_signup:
        response = coach_signup.post("/api/signup", json={
            "role": "coach", "full_name": "Amit Test",
            "email": coach_email, "password": password,
        })
        assert response.status_code == 202
        response = coach_signup.post("/api/account-verification/verify", json={
            "email": coach_email, "otp": delivered_otps[(coach_email, "signup")],
        })
        assert response.status_code == 200
        response = coach_signup.post("/api/login", json={
            "role": "coach", "email": coach_email, "password": password,
        })
        assert response.status_code == 403
        assert response.get_json()["message"] == "Your account is awaiting admin approval."

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO admins (full_name, email, password_hash) VALUES (%s, %s, %s)",
                ("Integration Admin", admin_email, generate_password_hash(password)),
            )
            admin_id = cursor.lastrowid
            cursor.execute(
                "SELECT id FROM pending_registrations WHERE email = %s", (coach_email,),
            )
            registration_id = cursor.fetchone()["id"]
        db.commit()
    finally:
        db.close()

    with app.test_client() as admin:
        response = admin.post("/api/admin/login", json={
            "role": "admin", "email": admin_email, "password": password,
        })
        assert response.status_code == 200, response.get_json()
        response = admin.post("/api/admin/login/verify-otp", json={
            "email": admin_email,
            "otp": delivered_otps[(admin_email, "login")],
        })
        assert response.status_code == 200
        response = admin.get("/api/admin/coaches/pending")
        assert response.status_code == 200
        assert any(row["email"] == coach_email for row in response.get_json()["coaches"])
        response = admin.post("/api/admin/coaches/approve", json={
            "registration_id": registration_id, "sports": ["Football"],
        })
        assert response.status_code == 200
        coach_id = response.get_json()["coach_id"]

    with app.test_client() as coach:
        with coach.session_transaction() as state:
            state["user_id"] = coach_id
            state["role"] = "coach"
        response = coach.get("/api/coach/athletes")
        assert response.status_code == 200
        assert [row["id"] for row in response.get_json()["athletes"]] == [student_id]
        response = coach.post("/api/assessments", json={
            "student_id": student_id, "assessment_date": "2026-09-30",
            "overall_score": 88,
        })
        assert response.status_code == 201
        response = coach.post("/api/coach/attendance/records", json={
            "sport_id": 1, "session_date": "2026-09-30",
            "records": [{"student_id": student_id, "status": "present"}],
        })
        assert response.status_code == 200

    with app.test_client() as student:
        with student.session_transaction() as state:
            state["user_id"] = student_id
            state["role"] = "student"
        assert student.get("/api/assessments").get_json()["data"][0]["overall_score"] == 88
        assert student.get("/api/student/attendance").get_json()["data"]["present"] == 1

    with app.test_client() as admin:
        with admin.session_transaction() as state:
            state["user_id"] = admin_id
            state["role"] = "admin"
        response = admin.post("/api/admin/coaches/reject", json={"user_id": coach_id})
        assert response.status_code == 200

    with app.test_client() as coach:
        with coach.session_transaction() as state:
            state["user_id"] = coach_id
            state["role"] = "coach"
        response = coach.get("/api/coach/athletes")
        assert response.status_code == 403
