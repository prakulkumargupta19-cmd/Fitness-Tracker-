from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from backend.app import app
import backend.auth.helpers as auth_helpers
import backend.auth.emails as auth_emails


class Cursor:
    def __init__(self, row=None):
        self.row = row
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.statements.append((query, params))

    def fetchone(self):
        return self.row


class Connection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_admin_otp_storage_uses_admin_table_and_hashes_code(monkeypatch):
    cursor = Cursor()
    connection = Connection(cursor)
    monkeypatch.setattr(auth_helpers, "get_db", lambda: connection)

    auth_helpers.store_admin_otp(1_000_001, "login", "123456")

    insert_query, params = cursor.statements[-1]
    assert "INSERT INTO admin_otp_verifications" in insert_query
    assert params[0] == 1_000_001
    assert params[1] == "login"
    assert check_password_hash(params[2], "123456")
    assert connection.committed and connection.closed


def test_admin_otp_verification_consumes_unexpired_code(monkeypatch):
    cursor = Cursor({
        "id": 8,
        "otp_hash": generate_password_hash("654321"),
        "expires_at": datetime.now() + timedelta(minutes=5),
    })
    connection = Connection(cursor)
    monkeypatch.setattr(auth_helpers, "get_db", lambda: connection)

    valid, _ = auth_helpers.verify_admin_otp(1_000_001, "login", "654321")

    assert valid
    assert any("SET is_used = 1" in query for query, _ in cursor.statements)
    assert connection.committed and connection.closed


def test_admin_otp_attempts_are_capped(monkeypatch):
    cursor = Cursor({
        "id": 8,
        "otp_hash": generate_password_hash("654321"),
        "expires_at": datetime.now() + timedelta(minutes=5),
        "attempt_count": 4,
    })
    connection = Connection(cursor)
    monkeypatch.setattr(auth_helpers, "get_db", lambda: connection)

    valid, message = auth_helpers.verify_admin_otp(1_000_001, "login", "wrong")

    assert not valid and message == "Invalid OTP code."
    update = next(item for item in cursor.statements if "SET attempt_count" in item[0])
    assert update[1] == (5, 5, 8)
    assert connection.committed


def test_admin_login_otp_uses_admin_account_table(monkeypatch):
    statements = []

    class LoginCursor(Cursor):
        def execute(self, query, params=()):
            statements.append((query, params))

    connection = Connection(LoginCursor())
    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: {
        "id": 1_000_001, "role": "admin", "full_name": "Admin",
        "email": "admin@example.test", "contact_number": None,
        "is_verified": True, "coach_status": None,
        "password_hash": generate_password_hash("a-secure-password"),
    })
    monkeypatch.setattr("backend.app.store_admin_otp", lambda *args: True)
    monkeypatch.setattr("backend.app.send_otp_email", lambda *args: True)
    monkeypatch.setattr("backend.app.get_db", lambda: connection)

    with app.test_client() as client:
        response = client.post("/api/admin/login", json={
            "email": "admin@example.test", "password": "a-secure-password",
            "role": "admin",
        })

    assert response.status_code == 200
    assert response.get_json()["otp_required"]
    assert statements == []  # Last-login time is updated only after OTP verification.


def test_development_terminal_otp_also_sends_email(monkeypatch, capsys):
    monkeypatch.setattr(auth_emails, "OTP_LOG_TO_TERMINAL", True)
    monkeypatch.setattr(auth_emails, "TEST_MODE", False)
    sent = []
    monkeypatch.setattr(auth_emails, "send_email", lambda *args: sent.append(args) or True)

    with app.app_context():
        delivered = auth_emails.send_otp_email(
            "student@inspiria.edu.in", "Student", "signup", "481205"
        )

    assert delivered is True
    assert "481205" in capsys.readouterr().out
    assert len(sent) == 1
    assert sent[0][0] == "student@inspiria.edu.in"
    assert "481205" in sent[0][2]


def test_admin_login_verification_uses_admin_otp_and_updates_admin(monkeypatch):
    statements = []

    class LoginCursor(Cursor):
        def execute(self, query, params=()):
            statements.append((query, params))

    connection = Connection(LoginCursor())
    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: {
        "id": 1_000_001, "role": "admin", "full_name": "Admin",
        "email": "admin@example.test", "contact_number": None,
        "is_verified": True, "coach_status": None,
    })
    monkeypatch.setattr("backend.app.verify_admin_otp", lambda *args: (True, "Verified"))
    monkeypatch.setattr("backend.app.get_db", lambda: connection)

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["pending_login_user_id"] = 1_000_001
            state["pending_login_role"] = "admin"
        response = client.post("/api/admin/login/verify-otp", json={
            "otp": "123456",
        })

    assert response.status_code == 200
    assert any("UPDATE admins SET last_login_at" in query for query, _ in statements)


def test_login_otp_uses_pending_session_identity_not_submitted_email(monkeypatch):
    user = {
        "id": 42,
        "role": "student",
        "full_name": "Student",
        "email": "student@example.test",
        "contact_number": None,
        "is_verified": True,
        "coach_status": None,
    }
    lookups = []
    verified = []

    class LoginCursor(Cursor):
        def execute(self, query, params=()):
            lookups.append((query, params))

    connection = Connection(LoginCursor())
    monkeypatch.setattr("backend.app.get_user_by_id", lambda user_id, role=None: user if (user_id, role) in ((42, "student"), (42, None)) else None)
    monkeypatch.setattr("backend.app.find_user_by_email", lambda email: pytest.fail("email must not select the OTP account"))
    monkeypatch.setattr("backend.app.verify_stored_otp", lambda user_id, purpose, otp: verified.append((user_id, purpose, otp)) or (True, "Verified"))
    monkeypatch.setattr("backend.app.get_db", lambda: connection)

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["pending_login_user_id"] = 42
            state["pending_login_role"] = "student"
        response = client.post("/api/login/verify-otp", json={
            "email": "someone-else@example.test",
            "role": "admin",
            "otp": "123456",
        })
        session_response = client.get("/api/session")

    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "student"
    assert verified == [(42, "login", "123456")]
    assert session_response.get_json()["user"]["role"] == "student"
    assert any("UPDATE users SET last_login_at" in query for query, _ in lookups)


def test_pending_login_details_come_from_server_session(monkeypatch):
    user = {"id": 42, "role": "coach", "email": "coach@example.test"}
    lookups = []
    monkeypatch.setattr("backend.app.get_user_by_id", lambda user_id, role: lookups.append((user_id, role)) or user)

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["pending_login_user_id"] = 42
            state["pending_login_role"] = "coach"
        response = client.get("/api/login/pending-otp")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "role": "coach",
        "email": "c***@example.test",
    }
    assert lookups == [(42, "coach")]


def test_login_otp_resend_uses_pending_account_email(monkeypatch):
    user = {
        "id": 42,
        "role": "student",
        "full_name": "Student",
        "email": "student@example.test",
    }
    sent = []
    monkeypatch.setattr("backend.app.get_user_by_id", lambda user_id, role: user if (user_id, role) == (42, "student") else None)
    monkeypatch.setattr("backend.app.generate_otp", lambda: "123456")
    monkeypatch.setattr("backend.app.store_otp", lambda *args: True)
    monkeypatch.setattr("backend.app.send_otp_email", lambda *args: sent.append(args) or True)

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["pending_login_user_id"] = 42
            state["pending_login_role"] = "student"
        response = client.post("/api/login/resend-otp", json={
            "email": "attacker@example.test",
        })

    assert response.status_code == 200
    assert sent == [("student@example.test", "Student", "login", "123456")]
