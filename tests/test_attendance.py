import pytest
from backend.attendance import student_attendance_payload

def test_student_attendance_payload_empty(db_conn):
    """Test that the payload is correct when a student has no attendance."""
    payload = student_attendance_payload(-999999)
    assert payload["total"] == 0
    assert payload["label"] == "No sessions yet"
