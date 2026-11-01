import pytest
from datetime import date

from backend.attendance import _student_history, _student_week, _summary, student_attendance_payload


def test_late_counts_as_attended_and_excused_is_removed_from_rate():
    payload = _summary(present=6, absent=2, late=2, excused=1)

    assert payload["late"] == 2
    assert payload["excused"] == 1
    assert payload["total"] == 11
    assert payload["percentage"] == 80


def test_student_week_displays_late_excused_and_empty_days():
    class Cursor:
        def execute(self, _query, _params):
            pass

        def fetchall(self):
            return [
                {"session_date": date(2026, 10, 26), "status": "present"},
                {"session_date": date(2026, 10, 27), "status": "late"},
                {"session_date": date(2026, 10, 28), "status": "excused"},
            ]

    week = _student_week(Cursor(), 12, date(2026, 10, 31))

    assert [day["status"] for day in week] == [
        "present", "late", "excused", "none", "none", "none", "none"
    ]
    assert week[1]["present"] is True


def test_student_history_orders_by_session_key_not_record_id():
    class Cursor:
        query = ""

        def execute(self, query, _params):
            self.query = query

        def fetchall(self):
            return [{
                "session_date": date(2026, 10, 31),
                "sport_name": "Cricket",
                "status": "late",
            }]

    cursor = Cursor()
    history = _student_history(cursor, 12)

    assert "ORDER BY a.session_date DESC, a.id DESC" in cursor.query
    assert "r.id" not in cursor.query
    assert history[0]["status"] == "late"
    assert history[0]["sport_name"] == "Cricket"

def test_student_attendance_payload_empty(db_conn):
    """Test that the payload is correct when a student has no attendance."""
    # Assuming student ID 99 does not exist, so it should return empty
    payload = student_attendance_payload(99)
    assert payload["total"] == 0
    assert payload["label"] == "No sessions yet"
