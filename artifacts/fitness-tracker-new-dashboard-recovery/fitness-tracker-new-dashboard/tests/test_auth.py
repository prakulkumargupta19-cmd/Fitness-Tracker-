import pytest
from backend.app import app
from werkzeug.security import generate_password_hash

def test_signup_domain_restriction():
    with app.test_client() as client:
        response = client.post("/api/signup", json={
            "role": "student",
            "full_name": "Test User",
            "email": "test@gmail.com",
            "password": "Password123"
        })
        assert response.status_code == 400
        assert "Only @inspiria.edu.in emails are allowed." in response.get_json()["message"]

def test_signup_creates_user_and_sends_verification(monkeypatch):
    statements = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params):
            statements.append((query, params))

        def fetchone(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: None)
    monkeypatch.setattr("backend.app.get_db", Connection)
    monkeypatch.setattr("backend.app.send_otp_email", lambda *args: True)
    with app.test_client() as client:
        response = client.post("/api/signup", json={
            "role": "student",
            "full_name": "New Test Student",
            "email": "new.student@inspiria.edu.in",
            "password": "Password123"
        })
    assert response.status_code == 202
    assert "pending email verification" in response.get_json()["message"]
    assert any("INSERT INTO pending_registrations" in query for query, _ in statements)
    assert not any("INSERT INTO users" in query for query, _ in statements)


def test_signup_does_not_create_account_when_mail_fails(monkeypatch):
    statements = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params):
            statements.append(query)

        def fetchone(self):
            return None

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: None)
    monkeypatch.setattr("backend.app.get_db", Connection)
    monkeypatch.setattr("backend.app.send_otp_email", lambda *args: False)
    with app.test_client() as client:
        response = client.post("/api/signup", json={
            "role": "student",
            "full_name": "Mail Pending Student",
            "email": "mail.pending@inspiria.edu.in",
            "password": "Password123",
        })

    assert response.status_code == 503
    assert "no account was created" in response.get_json()["message"]
    assert any("pending_registrations" in query for query in statements)
    assert not any("INSERT INTO users" in query for query in statements)


def test_forgot_password_reports_email_delivery_failure(monkeypatch):
    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: {
        "id": 42,
        "full_name": "Test User",
        "email": email,
        "role": "student",
    })
    monkeypatch.setattr("backend.app.store_otp", lambda *args: True)
    monkeypatch.setattr("backend.app.send_otp_email", lambda *args: False)

    with app.test_client() as client:
        response = client.post("/api/forgot-password", json={"email": "test@example.test"})

    assert response.status_code == 503
    assert response.get_json()["success"] is False
    assert "Unable to send" in response.get_json()["message"]


def test_forgot_password_reports_otp_request_limit(monkeypatch):
    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: {
        "id": 42,
        "full_name": "Test User",
        "email": email,
        "role": "student",
    })
    monkeypatch.setattr("backend.app.store_otp", lambda *args: False)
    monkeypatch.setattr("backend.app.send_otp_email", lambda *args: True)

    with app.test_client() as client:
        response = client.post("/api/forgot-password", json={"email": "test@example.test"})

    assert response.status_code == 429
    assert response.get_json()["success"] is False
    assert "Too many" in response.get_json()["message"]


def test_forgot_password_otp_verification_allows_token_reset(monkeypatch):
    user = {
        "id": 42,
        "full_name": "Test User",
        "email": "test@example.test",
        "role": "student",
        "password_hash": generate_password_hash("OldPassword123!"),
    }

    class Cursor:
        def __init__(self):
            self.statements = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params=()):
            self.statements.append((query, params))

    class Connection:
        def __init__(self):
            self.cursor_instance = Cursor()

        def cursor(self):
            return self.cursor_instance

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    connection = Connection()
    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: user)
    monkeypatch.setattr("backend.app.verify_stored_otp", lambda *args: (True, "OTP verified successfully."))
    monkeypatch.setattr("backend.app.get_db", lambda: connection)
    monkeypatch.setattr("backend.app.send_password_reset_success_email", lambda *args: True)

    with app.test_client() as client:
        verified = client.post("/api/forgot-password/verify-otp", json={
            "email": user["email"],
            "otp": "123456",
        })
        assert verified.status_code == 200
        reset_token = verified.get_json()["reset_token"]

        reset = client.post("/api/reset-password", json={
            "email": user["email"],
            "password": "NewPassword123!",
            "reset_token": reset_token,
        })

    assert reset.status_code == 200
    assert reset.get_json()["success"] is True
    assert any("UPDATE users SET password_hash" in query for query, _ in connection.cursor_instance.statements)
