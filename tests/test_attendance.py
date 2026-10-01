import pytest
from backend.attendance import student_attendance_payload

def test_student_attendance_payload_empty(db_conn):
    """Test that the payload is correct when a student has no attendance."""
    # Assuming student ID 99 does not exist, so it should return empty
    payload = student_attendance_payload(99)
    assert payload["total"] == 0
    assert payload["label"] == "No sessions yet"
