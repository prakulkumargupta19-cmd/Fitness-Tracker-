import sqlite3
from pathlib import Path

import pytest

from backend.db import database_backend


LOCAL_SCHEMA = Path(__file__).resolve().parents[1] / "backend" / "local_schema.sql"


def test_vercel_preview_uses_configured_postgres(monkeypatch):
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://example.test/db")

    assert database_backend() == "postgres"


@pytest.fixture
def fit_track_db(tmp_path):
    connection = sqlite3.connect(tmp_path / "fit-track.sqlite3")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(LOCAL_SCHEMA.read_text(encoding="utf-8"))
    connection.executemany(
        """INSERT INTO users
           (role, full_name, email, password_hash, is_verified, coach_status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("student", "Student One", "student@example.test", "hash", 1, None),
            ("student", "Student Two", "student2@example.test", "hash", 1, None),
            ("coach", "Coach One", "coach@example.test", "hash", 1, "approved"),
        ],
    )
    connection.execute("INSERT INTO coach_profiles (user_id) VALUES (3)")
    connection.execute(
        "INSERT INTO admins (id, full_name, email, password_hash) VALUES (?, ?, ?, ?)",
        (1, "Admin One", "admin@example.test", "hash"),
    )
    connection.execute("INSERT INTO sports (name, activity_type, venue) VALUES (?, ?, ?)", ("Tennis", "Coached", "Court"))
    sport_id = connection.execute("SELECT id FROM sports WHERE name = ?", ("Tennis",)).fetchone()[0]
    connection.execute("INSERT INTO coach_sports (coach_id, sport_id, assigned_by) VALUES (?, ?, ?)", (3, sport_id, 1))
    connection.commit()
    try:
        yield connection
    finally:
        connection.close()


def test_fit_track_relationships_reject_wrong_roles(fit_track_db):
    db = fit_track_db
    sport_id = db.execute("SELECT id FROM sports WHERE name = ?", ("Tennis",)).fetchone()[0]

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO programmes (name, sport_id, coach_id) VALUES (?, ?, ?)",
            ("Invalid Programme", sport_id, 1),
        )

    db.execute(
        "INSERT INTO programmes (name, sport_id, coach_id) VALUES (?, ?, ?)",
        ("Tennis Programme", sport_id, 3),
    )
    programme_id = db.execute("SELECT id FROM programmes").fetchone()[0]

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO enrollments (student_id, programme_id) VALUES (?, ?)",
            (3, programme_id),
        )


def test_fit_track_fixture_squad_is_capped_at_fifteen(fit_track_db):
    db = fit_track_db
    sport_id = db.execute("SELECT id FROM sports WHERE name = ?", ("Tennis",)).fetchone()[0]
    db.execute(
        "INSERT INTO tournaments (name, sport_id, start_date) VALUES (?, ?, ?)",
        ("Tennis Open", sport_id, "2026-10-21"),
    )
    db.execute(
        "INSERT INTO matches (tournament_id, category, team_a, team_b) VALUES (?, ?, ?, ?)",
        (1, "Boys", "A", "B"),
    )
    for number in range(15):
        db.execute(
            "INSERT INTO match_players (match_id, side, student_name) VALUES (?, ?, ?)",
            (1, "A", f"Player {number}"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO match_players (match_id, side, student_name) VALUES (?, ?, ?)",
            (1, "A", "Player 16"),
        )


def test_fit_track_schedule_and_message_integrity(fit_track_db):
    db = fit_track_db
    sport_id = db.execute("SELECT id FROM sports WHERE name = ?", ("Tennis",)).fetchone()[0]
    db.execute(
        "INSERT INTO programmes (name, sport_id, coach_id) VALUES (?, ?, ?)",
        ("Tennis Programme", sport_id, 3),
    )
    programme_id = db.execute("SELECT id FROM programmes").fetchone()[0]

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """INSERT INTO coaching_sessions
               (programme_id, session_date, start_time, end_time, status)
               VALUES (?, ?, ?, ?, ?)""",
            (programme_id, "2026-10-21", "18:00", "17:00", "Scheduled"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO messages (sender_user_id, receiver_user_id, message) VALUES (?, ?, ?)",
            (1, 1, "self-message"),
        )
