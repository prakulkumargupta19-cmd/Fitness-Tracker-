from datetime import datetime, timedelta

from backend import app as app_module


class _HealthCursor:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query):
        assert query == "SELECT 1 AS healthy"

    def fetchone(self):
        return {"healthy": 1}

    def fetchall(self):
        return []


class _HealthConnection:
    def cursor(self):
        return _HealthCursor()

    def close(self):
        pass


def test_health_returns_database_status_and_request_id(monkeypatch):
    monkeypatch.setattr(app_module, "get_db", _HealthConnection)
    client = app_module.app.test_client()

    response = client.get("/api/health", headers={"X-Request-ID": "health-check-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "health-check-1"
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["database"] == "ok"
    assert response.get_json()["application"] == "fitness-tracker"


def test_health_is_degraded_without_database(monkeypatch):
    def unavailable_database():
        raise RuntimeError("connection URL must not be returned")

    monkeypatch.setattr(app_module, "get_db", unavailable_database)
    response = app_module.app.test_client().get("/api/health")

    assert response.status_code == 503
    assert response.get_json()["status"] == "degraded"
    assert response.get_json()["database"] == "error"
    assert "connection URL" not in response.get_data(as_text=True)


def test_verified_coach_registration_is_marked_pending_approval(monkeypatch):
    statements = []
    pending = {
        "id": 29,
        "role": "coach",
        "otp_attempts": 0,
        "otp_expires_at": datetime.now() + timedelta(minutes=2),
        "otp_hash": "test-hash",
    }

    class VerificationCursor(_HealthCursor):
        def execute(self, query, params=()):
            statements.append((query, params))

        def fetchone(self):
            return pending

    class VerificationConnection(_HealthConnection):
        def __init__(self):
            self.committed = False

        def cursor(self):
            return VerificationCursor()

        def commit(self):
            self.committed = True

    connection = VerificationConnection()
    monkeypatch.setattr(app_module, "get_db", lambda: connection)
    monkeypatch.setattr(app_module, "check_password_hash", lambda *_args: True)

    response = app_module.app.test_client().post(
        "/api/account-verification/verify",
        json={"email": "coach@inspiria.edu.in", "otp": "123456"},
    )

    assert response.status_code == 200
    assert response.get_json()["role"] == "coach"
    assert any(
        "SET status = 'pending_approval'" in query and params == (29,)
        for query, params in statements
    )
    assert connection.committed


def test_admin_diagnostics_requires_authenticated_admin(monkeypatch):
    monkeypatch.setattr(
        "auth.decorators.get_user_by_id",
        lambda _user_id: None,
    )
    client = app_module.app.test_client()
    with client.session_transaction() as state:
        state["user_id"] = 123
        state["role"] = "admin"

    response = client.get("/api/admin/diagnostics")

    assert response.status_code == 401
    assert response.headers["X-Request-ID"]


def test_admin_pending_coaches_includes_verified_staged_registrations(monkeypatch):
    expected = {
        "user_id": None,
        "registration_id": 29,
        "full_name": "Pending Coach",
        "email": "pending.coach@inspiria.edu.in",
        "contact_number": "1234567890",
        "coach_status": "pending",
        "created_at": "2026-10-02T12:00:00",
        "is_verified": True,
    }

    class PendingCursor(_HealthCursor):
        def execute(self, query):
            assert "FROM pending_registrations" in query
            assert "status = 'pending_approval'" in query

        def fetchall(self):
            return [expected]

    class PendingConnection(_HealthConnection):
        def cursor(self):
            return PendingCursor()

    monkeypatch.setattr(
        "auth.decorators.get_user_by_id",
        lambda _user_id: {"role": "admin"},
    )
    monkeypatch.setattr(app_module, "get_db", PendingConnection)
    client = app_module.app.test_client()
    with client.session_transaction() as state:
        state["user_id"] = 123
        state["role"] = "admin"

    response = client.get("/api/admin/coaches/pending")

    assert response.status_code == 200
    assert response.get_json()["coaches"] == [expected]


def test_pending_coach_lookup_prefers_email_to_stale_registration_id():
    identity_filter, params = app_module._pending_coach_identity(
        "Coach@Inspiria.edu.in",
        registration_id=999,
    )

    assert identity_filter == "LOWER(email) = %s"
    assert params == ("coach@inspiria.edu.in",)


def test_admin_diagnostics_returns_status_without_exposing_secrets(monkeypatch):
    monkeypatch.setattr(
        "auth.decorators.get_user_by_id",
        lambda _user_id: {"role": "admin"},
    )
    monkeypatch.setattr(app_module, "get_db", _HealthConnection)
    monkeypatch.setenv(
        "SUPABASE_DB_URL",
        "postgresql://diagnostic-user:diagnostic-db-secret@example.test/db",
    )
    monkeypatch.setenv("MAIL_USERNAME", "diagnostic-mail-user")
    monkeypatch.setenv("MAIL_PASSWORD", "diagnostic-mail-secret")
    client = app_module.app.test_client()
    with client.session_transaction() as state:
        state["user_id"] = 123
        state["role"] = "admin"

    response = client.get("/api/admin/diagnostics")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["checks"]["backend"] == "ok"
    assert payload["checks"]["api"] == "ok"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["email_service"] == "configured"
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["last_checked_at"]
    assert "diagnostic-db-secret" not in response.get_data(as_text=True)
    assert "diagnostic-mail-secret" not in response.get_data(as_text=True)


def test_cors_only_allows_configured_production_origin(monkeypatch):
    monkeypatch.setattr(app_module, "is_production", True)
    monkeypatch.setenv("FRONTEND_URL", "https://fitness.example")
    monkeypatch.setattr(app_module, "get_db", _HealthConnection)
    client = app_module.app.test_client()

    allowed = client.get(
        "/api/health",
        headers={"Origin": "https://fitness.example"},
    )
    denied = client.get(
        "/api/health",
        headers={"Origin": "https://other.example"},
    )

    assert allowed.headers["Access-Control-Allow-Origin"] == "https://fitness.example"
    assert "Access-Control-Allow-Origin" not in denied.headers


def test_cors_allows_local_static_frontend_on_port_8000(monkeypatch):
    monkeypatch.setattr(app_module, "is_production", False)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    monkeypatch.setattr(app_module, "get_db", _HealthConnection)
    client = app_module.app.test_client()

    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:8000"},
    )

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:8000"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
