from unittest.mock import Mock

from backend.app import app
import attendance as attendance_module
import backend.auth.helpers as auth_helpers
import auth.decorators as auth_decorators
import backend.auth.decorators as backend_auth_decorators
import performance as performance_module


class FakeCursor:
    def __init__(self, *, one=None, many=None):
        self.one = one
        self.many = many or []
        self.statements = []
        self.lastrowid = 73

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.statements.append((query, params))

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_admin_user_lookup_uses_columns_present_in_admin_schema(monkeypatch):
    admin = {
        "id": 1_000_001,
        "full_name": "Test Admin",
        "email": "admin@example.test",
        "password_hash": "hash",
        "contact_number": None,
        "is_verified": 1,
        "role": "admin",
        "coach_status": None,
    }

    class LookupCursor(FakeCursor):
        def __init__(self):
            super().__init__()
            self.rows = [None, admin]

        def fetchone(self):
            return self.rows.pop(0)

    cursor = LookupCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(auth_helpers, "get_db", lambda: connection)

    result = auth_helpers.find_user_by_email("admin@example.test")

    assert result == admin
    admin_query = cursor.statements[1][0]
    assert "NULL AS contact_number" in admin_query
    assert "password_hash, contact_number" not in admin_query
    assert connection.closed


def test_unknown_and_wrong_method_api_routes_return_json():
    with app.test_client() as test_client:
        missing = test_client.get("/api/does-not-exist")
        wrong_method = test_client.get("/api/signup")

    assert missing.status_code == 404
    assert missing.is_json
    assert wrong_method.status_code == 405
    assert wrong_method.is_json


def set_authenticated_user(monkeypatch, user_id, role):
    user_lookup = lambda requested_id: {
        "id": requested_id,
        "role": role,
        "coach_status": "approved" if role == "coach" else None,
    }
    monkeypatch.setattr(auth_decorators, "get_user_by_id", user_lookup)
    monkeypatch.setattr(backend_auth_decorators, "get_user_by_id", user_lookup)


def test_profile_setup_synchronizes_normalized_sports(monkeypatch):
    cursor = FakeCursor(many=[
        {"id": 1, "name": "Football"},
        {"id": 2, "name": "Basketball"},
    ])
    connection = FakeConnection(cursor)
    monkeypatch.setattr("backend.app.get_db", lambda: connection)
    monkeypatch.setattr("backend.app.get_user_by_id", lambda user_id: {"id": 31, "role": "student", "is_verified": True})

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["pending_user_id"] = 31
        response = client.post("/api/profile/setup", json={
            "date_of_birth": "2005-03-12",
            "emergency_contact": "9876543210",
            "sports": ["Football", "Basketball", "Football"],
        })

    assert response.status_code == 200
    assert connection.committed
    inserts = [query for query, _ in cursor.statements if "INSERT INTO student_sports" in query]
    assert len(inserts) == 2
    assert any("sport_activity" in query for query, _ in cursor.statements)


def test_profile_setup_rejects_unknown_sport_without_commit(monkeypatch):
    cursor = FakeCursor(many=[{"id": 1, "name": "Football"}])
    connection = FakeConnection(cursor)
    monkeypatch.setattr("backend.app.get_db", lambda: connection)
    monkeypatch.setattr("backend.app.get_user_by_id", lambda user_id: {"id": 31, "role": "student", "is_verified": True})

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["pending_user_id"] = 31
        response = client.post("/api/profile/setup", json={
            "date_of_birth": "2005-03-12",
            "emergency_contact": "9876543210",
            "sports": ["Basketball"],
        })

    assert response.status_code == 400
    assert not connection.committed
    assert not any("INSERT INTO student_sports" in query for query, _ in cursor.statements)


def test_unverified_student_cannot_complete_profile(monkeypatch):
    monkeypatch.setattr("backend.app.get_user_by_id", lambda user_id: {"id": 31, "role": "student", "is_verified": False})
    monkeypatch.setattr("backend.app.get_db", Mock(side_effect=AssertionError("unverified profile must not reach DB")))

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["pending_user_id"] = 31
        response = client.post("/api/profile/setup", json={
            "date_of_birth": "2005-03-12",
            "emergency_contact": "9876543210",
            "sports": ["Football"],
        })

    assert response.status_code == 403


def test_coach_athlete_query_uses_session_and_sport_relationship(monkeypatch):
    coach_id = 73
    cursor = FakeCursor(many=[{
        "id": 19,
        "full_name": "Rahul Test",
        "email": "rahul@inspiria.edu.in",
        "sports": "Football",
    }])
    connection = FakeConnection(cursor)
    monkeypatch.setattr("backend.app.get_db", lambda: connection)
    set_authenticated_user(monkeypatch, coach_id, "coach")

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["user_id"] = coach_id
            state["role"] = "coach"
        response = client.get("/api/coach/athletes?coach_id=999")

    query, params = cursor.statements[0]
    assert response.status_code == 200
    assert response.get_json()["athletes"][0]["id"] == 19
    assert params == (coach_id,)
    assert "student_sports" in query
    assert "coach_sports" in query


def test_rejected_coach_session_cannot_access_coach_api(monkeypatch):
    rejected = lambda requested_id: {
        "id": requested_id, "role": "coach", "coach_status": "rejected",
    }
    monkeypatch.setattr(auth_decorators, "get_user_by_id", rejected)
    monkeypatch.setattr(backend_auth_decorators, "get_user_by_id", rejected)

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["user_id"] = 73
            state["role"] = "coach"
        response = client.get("/api/coach/athletes")

    assert response.status_code == 403
    assert "not approved" in response.get_json()["message"]


def test_attendance_rejects_non_binary_status_before_database(monkeypatch):
    set_authenticated_user(monkeypatch, 73, "coach")
    monkeypatch.setattr(
        attendance_module,
        "get_db",
        Mock(side_effect=AssertionError("database should not be opened for invalid status")),
    )

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["user_id"] = 73
            state["role"] = "coach"
        response = client.post("/api/coach/attendance/records", json={
            "sport_id": 4,
            "session_date": "2026-09-30",
            "records": [{"student_id": 19, "status": "tardy"}],
        })

    assert response.status_code == 400
    assert "present or absent" in response.get_json()["message"]


def test_performance_list_for_student_is_scoped_to_session_user(monkeypatch):
    student_id = 19
    cursor = FakeCursor(many=[{"id": 5, "student_id": student_id, "assessment_date": "2026-09-30"}])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(performance_module, "get_db", lambda: connection)
    set_authenticated_user(monkeypatch, student_id, "student")

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["user_id"] = student_id
            state["role"] = "student"
        response = client.get("/api/assessments")

    assert response.status_code == 200
    assert cursor.statements[0][1] == (student_id,)
    assert "WHERE student_id = %s" in cursor.statements[0][0]


def test_admin_student_list_returns_database_sports(monkeypatch):
    cursor = FakeCursor(many=[{
        "id": 19,
        "full_name": "Rahul Test",
        "email": "rahul@inspiria.edu.in",
        "contact_number": "9876543210",
        "is_verified": 1,
        "registration_date": "2026-09-30",
        "date_of_birth": "2005-03-12",
        "department": "Sports Science",
        "height_cm": 180,
        "weight_kg": 75,
        "sports": "Football, Basketball",
    }])
    connection = FakeConnection(cursor)
    monkeypatch.setattr("backend.app.get_db", lambda: connection)
    set_authenticated_user(monkeypatch, 1_000_001, "admin")

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["user_id"] = 1_000_001
            state["role"] = "admin"
        response = client.get("/api/admin/students")

    student = response.get_json()["students"][0]
    assert response.status_code == 200
    assert student["sports"] == ["Football", "Basketball"]
    assert student["is_verified"] is True


def test_admin_can_assign_sports_to_approved_coach(monkeypatch):
    cursor = FakeCursor(one={"id": 73}, many=[{"id": 4, "name": "Football"}])
    connection = FakeConnection(cursor)
    monkeypatch.setattr("backend.app.get_db", lambda: connection)
    set_authenticated_user(monkeypatch, 1_000_001, "admin")

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["user_id"] = 1_000_001
            state["role"] = "admin"
        response = client.put("/api/admin/coach-sports", json={
            "coach_id": 73,
            "sports": ["Football"],
        })

    assignment = next(item for item in cursor.statements if "INSERT INTO coach_sports" in item[0])
    assert response.status_code == 200
    assert assignment[1] == (73, 4, 1_000_001)
    assert connection.committed


def test_coach_can_save_present_and_absent_for_assigned_students(monkeypatch):
    cursor = FakeCursor(
        one={"id": 55},
        many=[{"id": 19}, {"id": 20}],
    )
    connection = FakeConnection(cursor)
    monkeypatch.setattr(attendance_module, "get_db", lambda: connection)
    set_authenticated_user(monkeypatch, 73, "coach")

    with app.test_client() as client:
        with client.session_transaction() as state:
            state["user_id"] = 73
            state["role"] = "coach"
        response = client.post("/api/coach/attendance/records", json={
            "sport_id": 4,
            "session_date": "2026-09-30",
            "records": [
                {"student_id": 19, "status": "present"},
                {"student_id": 20, "status": "absent"},
            ],
        })

    attendance_inserts = [item for item in cursor.statements if "INSERT INTO attendance_records" in item[0]]
    assert response.status_code == 200
    assert len(attendance_inserts) == 2
    assert attendance_inserts[0][1] == (55, 19, "present")
    assert attendance_inserts[1][1] == (55, 20, "absent")
    assert connection.committed
