"""Fit-Track reference feature APIs.

The reference project used a separate legacy login model. These routes keep
the root project's authenticated ``users`` and session model, while exposing
the reference project's sports operations as PostgreSQL resources.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from flask import jsonify, request, session

try:
    from backend.db import get_db
    from backend.auth.decorators import role_required
except ModuleNotFoundError:
    from db import get_db
    from auth.decorators import role_required


ADMIN = role_required("admin")
STAFF = role_required("admin", "coach")
ALL_USERS = role_required("admin", "coach", "student")


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows(rows):
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _row(row):
    return None if row is None else {key: _json_value(value) for key, value in row.items()}


def _body():
    return request.get_json(silent=True) or {}


def _required(data, *names):
    missing = [name for name in names if data.get(name) in (None, "")]
    if missing:
        return jsonify(success=False, message=f"Required fields: {', '.join(missing)}."), 400
    return None


def _commit(db):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _student_scope(cursor, user_id, role):
    if role == "student":
        return "u.id = %s", [user_id]
    if role == "coach":
        return (
            "u.id IN (SELECT ss.student_id FROM student_sports ss "
            "JOIN coach_sports cs ON cs.sport_id = ss.sport_id WHERE cs.coach_id = %s)",
            [user_id],
        )
    return "TRUE", []


def register_reference_feature_routes(app):
    @app.route("/api/fit-track/dashboard", methods=["GET"])
    @ALL_USERS
    def fit_track_dashboard():
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS count FROM sports WHERE is_active = TRUE")
                sports = cursor.fetchone()["count"]
                cursor.execute("SELECT COUNT(*) AS count FROM programmes WHERE active = TRUE")
                programmes = cursor.fetchone()["count"]
                cursor.execute("SELECT COUNT(*) AS count FROM tournaments WHERE status <> 'Completed'")
                tournaments = cursor.fetchone()["count"]
                cursor.execute("SELECT COUNT(*) AS count FROM matches WHERE status = 'Live'")
                live_matches = cursor.fetchone()["count"]
            return jsonify(success=True, data={
                "sports": sports,
                "programmes": programmes,
                "tournaments": tournaments,
                "live_matches": live_matches,
            })
        finally:
            db.close()

    @app.route("/api/fit-track/sports", methods=["GET"])
    @app.route("/api/sports/catalog", methods=["GET"])
    @ALL_USERS
    def fit_track_sports():
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM sports WHERE is_active = TRUE ORDER BY name")
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/sports", methods=["POST"])
    @ADMIN
    def fit_track_create_sport():
        data = _body()
        error = _required(data, "name")
        if error:
            return error
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO sports (name, activity_type, venue)
                       VALUES (%s, %s, %s) RETURNING *""",
                    (data["name"].strip(), data.get("activity_type") or "Activity", data.get("venue")),
                )
                row = _row(cursor.fetchone())
            _commit(db)
            return jsonify(success=True, data=row), 201
        except Exception as exc:
            db.rollback()
            return jsonify(success=False, message="Sport could not be created.", error_type=type(exc).__name__), 409
        finally:
            db.close()

    @app.route("/api/fit-track/sports/<int:sport_id>", methods=["PUT", "PATCH"])
    @ADMIN
    def fit_track_update_sport(sport_id):
        data = _body()
        allowed = {"name", "activity_type", "venue", "cover_path", "is_active"}
        updates = [(key, data[key]) for key in allowed if key in data]
        if not updates:
            return jsonify(success=False, message="No sport fields supplied."), 400
        db = get_db()
        try:
            with db.cursor() as cursor:
                assignments = ", ".join(f"{key} = %s" for key, _ in updates)
                cursor.execute(f"UPDATE sports SET {assignments} WHERE id = %s RETURNING *", tuple(value for _, value in updates) + (sport_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify(success=False, message="Sport not found."), 404
            _commit(db)
            return jsonify(success=True, data=_row(row))
        finally:
            db.close()

    @app.route("/api/fit-track/students", methods=["GET"])
    @app.route("/api/fit-track/students/<int:student_id>", methods=["GET"])
    @STAFF
    def fit_track_students(student_id=None):
        user_id = session.get("user_id")
        role = session.get("role")
        db = get_db()
        try:
            with db.cursor() as cursor:
                scope, params = _student_scope(cursor, user_id, role)
                if student_id is not None:
                    scope += " AND u.id = %s"
                    params.append(student_id)
                cursor.execute(
                    f"""SELECT u.id, u.full_name AS name, u.email, u.contact_number AS phone,
                               u.is_active, sp.*,
                               COALESCE(STRING_AGG(DISTINCT s.name, ', '), '') AS sports
                        FROM users u
                        LEFT JOIN student_profiles sp ON sp.user_id = u.id
                        LEFT JOIN student_sports ss ON ss.student_id = u.id
                        LEFT JOIN sports s ON s.id = ss.sport_id
                        WHERE u.role = 'student' AND {scope}
                        GROUP BY u.id, sp.user_id
                        ORDER BY u.full_name""",
                    tuple(params),
                )
                rows = _rows(cursor.fetchall())
            return jsonify(success=True, data=rows[0] if student_id is not None and rows else rows)
        finally:
            db.close()

    @app.route("/api/fit-track/students/<int:student_id>", methods=["PUT", "PATCH"])
    @ALL_USERS
    def fit_track_update_student(student_id):
        if session.get("role") == "student" and session.get("user_id") != student_id:
            return jsonify(success=False, message="You can only edit your own profile."), 403
        data = _body()
        user_fields = {"full_name", "contact_number"}
        profile_fields = {"date_of_birth", "emergency_contact", "height_cm", "weight_kg", "goal", "sport_activity", "department", "student_number", "semester", "bio", "blood_group", "medical_history", "address", "parent_name", "parent_phone", "parent_address", "passport_id", "photo_path"}
        db = get_db()
        try:
            with db.cursor() as cursor:
                user_updates = [(key, data[key]) for key in user_fields if key in data]
                if user_updates:
                    assignments = ", ".join(f"{key} = %s" for key, _ in user_updates)
                    cursor.execute(f"UPDATE users SET {assignments} WHERE id = %s AND role = 'student'", tuple(value for _, value in user_updates) + (student_id,))
                profile_updates = [(key, data[key]) for key in profile_fields if key in data]
                if profile_updates:
                    keys = [key for key, _ in profile_updates]
                    values = [value for _, value in profile_updates]
                    cursor.execute("SELECT user_id FROM student_profiles WHERE user_id = %s", (student_id,))
                    if cursor.fetchone():
                        assignments = ", ".join(f"{key} = %s" for key in keys)
                        cursor.execute(f"UPDATE student_profiles SET {assignments} WHERE user_id = %s", tuple(values) + (student_id,))
                    elif "date_of_birth" in data and "emergency_contact" in data:
                        cursor.execute("INSERT INTO student_profiles (user_id, date_of_birth, emergency_contact) VALUES (%s, %s, %s)", (student_id, data["date_of_birth"], data["emergency_contact"]))
                cursor.execute("SELECT u.id, u.full_name AS name, u.email, u.contact_number AS phone, sp.* FROM users u LEFT JOIN student_profiles sp ON sp.user_id = u.id WHERE u.id = %s AND u.role = 'student'", (student_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify(success=False, message="Student not found."), 404
            _commit(db)
            return jsonify(success=True, data=_row(row))
        finally:
            db.close()

    @app.route("/api/fit-track/programmes", methods=["GET"])
    @app.route("/api/programmes", methods=["GET"])
    @ALL_USERS
    def fit_track_programmes():
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("""SELECT p.*, s.name AS sport, u.full_name AS coach,
                                        COUNT(DISTINCT e.id) AS enrolment_count
                                 FROM programmes p JOIN sports s ON s.id=p.sport_id
                                 LEFT JOIN users u ON u.id=p.coach_id
                                 LEFT JOIN enrollments e ON e.programme_id=p.id
                                 GROUP BY p.id, s.name, u.full_name ORDER BY p.active DESC, p.name""")
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/programmes", methods=["POST"])
    @app.route("/api/programmes", methods=["POST"])
    @STAFF
    def fit_track_create_programme():
        data = _body()
        error = _required(data, "name", "sport_id")
        if error:
            return error
        coach_id = data.get("coach_id") or (session.get("user_id") if session.get("role") == "coach" else None)
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("""INSERT INTO programmes (name, sport_id, coach_id, schedule, venue)
                                   VALUES (%s, %s, %s, %s, %s) RETURNING *""", (data["name"], data["sport_id"], coach_id, data.get("schedule"), data.get("venue")))
                row = _row(cursor.fetchone())
            _commit(db)
            return jsonify(success=True, data=row), 201
        finally:
            db.close()

    @app.route("/api/fit-track/programmes/<int:programme_id>", methods=["PUT", "PATCH", "DELETE"])
    @app.route("/api/programmes/<int:programme_id>", methods=["PUT", "PATCH", "DELETE"])
    @STAFF
    def fit_track_manage_programme(programme_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "DELETE":
                    cursor.execute("DELETE FROM programmes WHERE id = %s", (programme_id,))
                    if cursor.rowcount == 0:
                        return jsonify(success=False, message="Programme not found."), 404
                    _commit(db)
                    return jsonify(success=True, message="Programme deleted.")
                data = _body()
                allowed = {"name", "sport_id", "coach_id", "schedule", "venue", "active"}
                updates = [(key, data[key]) for key in allowed if key in data]
                if not updates:
                    return jsonify(success=False, message="No programme fields supplied."), 400
                assignments = ", ".join(f"{key} = %s" for key, _ in updates) + ", updated_at = CURRENT_TIMESTAMP"
                cursor.execute(f"UPDATE programmes SET {assignments} WHERE id = %s RETURNING *", tuple(value for _, value in updates) + (programme_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify(success=False, message="Programme not found."), 404
            _commit(db)
            return jsonify(success=True, data=_row(row))
        finally:
            db.close()

    @app.route("/api/fit-track/programmes/<int:programme_id>/enrollments", methods=["GET", "POST"])
    @STAFF
    def fit_track_programme_enrolments(programme_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    data = _body()
                    error = _required(data, "student_id")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO enrollments (student_id, programme_id)
                                       VALUES (%s, %s)
                                       ON CONFLICT (student_id, programme_id) DO UPDATE SET status='Active'
                                       RETURNING *""", (data["student_id"], programme_id))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("""SELECT e.*, u.full_name AS student_name, u.email
                                 FROM enrollments e JOIN users u ON u.id=e.student_id
                                 WHERE e.programme_id=%s ORDER BY u.full_name""", (programme_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/schedule", methods=["GET", "POST"])
    @app.route("/api/coaching-schedule", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_schedule():
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") not in ("admin", "coach"):
                        return jsonify(success=False, message="Only staff can publish sessions."), 403
                    data = _body()
                    error = _required(data, "programme_id", "session_date", "start_time", "end_time")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO coaching_sessions
                                       (programme_id, session_date, start_time, end_time, venue, notes, status, created_by, updated_by)
                                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""", (data["programme_id"], data["session_date"], data["start_time"], data["end_time"], data.get("venue"), data.get("notes"), data.get("status") or "Scheduled", session.get("user_id"), session.get("user_id")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                month = request.args.get("month")
                query = """SELECT cs.*, p.name AS programme, s.name AS sport, u.full_name AS coach
                           FROM coaching_sessions cs JOIN programmes p ON p.id=cs.programme_id
                           JOIN sports s ON s.id=p.sport_id LEFT JOIN users u ON u.id=p.coach_id"""
                params = []
                if month and len(month) == 7:
                    query += " WHERE TO_CHAR(cs.session_date, 'YYYY-MM') = %s"
                    params.append(month)
                query += " ORDER BY cs.session_date, cs.start_time"
                cursor.execute(query, tuple(params))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/schedule/<int:session_id>", methods=["PUT", "PATCH", "DELETE"])
    @app.route("/api/coaching-schedule/<int:session_id>", methods=["PUT", "PATCH", "DELETE"])
    @STAFF
    def fit_track_manage_schedule(session_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "DELETE":
                    cursor.execute("DELETE FROM coaching_sessions WHERE id=%s", (session_id,))
                    if cursor.rowcount == 0:
                        return jsonify(success=False, message="Session not found."), 404
                    _commit(db)
                    return jsonify(success=True)
                data = _body()
                allowed = {"programme_id", "session_date", "start_time", "end_time", "venue", "notes", "status"}
                updates = [(key, data[key]) for key in allowed if key in data]
                if not updates:
                    return jsonify(success=False, message="No session fields supplied."), 400
                assignments = ", ".join(f"{key}=%s" for key, _ in updates) + ", updated_at=CURRENT_TIMESTAMP, updated_by=%s"
                values = tuple(value for _, value in updates) + (session.get("user_id"), session_id)
                cursor.execute(f"UPDATE coaching_sessions SET {assignments} WHERE id=%s RETURNING *", values)
                row = cursor.fetchone()
                if not row:
                    return jsonify(success=False, message="Session not found."), 404
            _commit(db)
            return jsonify(success=True, data=_row(row))
        finally:
            db.close()

    @app.route("/api/fit-track/assessments/daily", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_daily_assessments():
        user_id = session.get("user_id")
        role = session.get("role")
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if role not in ("admin", "coach"):
                        return jsonify(success=False, message="Only coaches can save assessments."), 403
                    data = _body()
                    error = _required(data, "enrollment_id", "session_date")
                    if error:
                        return error
                    fields = ["enrollment_id", "coach_id", "session_date", "attendance_status", "attendance_score", "skill_development", "passing", "dribbling", "shooting", "vision", "fitness", "overall_performance", "remarks"]
                    values = [data.get(field) for field in fields]
                    values[1] = data.get("coach_id") or user_id
                    cursor.execute(f"""INSERT INTO daily_assessments ({', '.join(fields)})
                                       VALUES ({', '.join(['%s'] * len(fields))})
                                       ON CONFLICT (enrollment_id, session_date) DO UPDATE SET
                                       {', '.join(f'{field}=EXCLUDED.{field}' for field in fields[1:])}, updated_at=CURRENT_TIMESTAMP
                                       RETURNING *""", tuple(values))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                scope, params = _student_scope(cursor, user_id, role)
                cursor.execute(f"""SELECT da.*, e.student_id, u.full_name AS student_name, p.name AS programme, s.name AS sport
                                 FROM daily_assessments da JOIN enrollments e ON e.id=da.enrollment_id
                                 JOIN users u ON u.id=e.student_id JOIN programmes p ON p.id=e.programme_id
                                 JOIN sports s ON s.id=p.sport_id
                                 WHERE {scope.replace('u.id', 'e.student_id')} ORDER BY da.session_date DESC, da.id DESC""", tuple(params))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/assessments/daily/<int:assessment_id>", methods=["PUT", "PATCH", "DELETE"])
    @STAFF
    def fit_track_manage_daily_assessment(assessment_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "DELETE":
                    cursor.execute("DELETE FROM daily_assessments WHERE id=%s", (assessment_id,))
                    _commit(db)
                    return jsonify(success=True)
                data = _body()
                allowed = {"session_date", "attendance_status", "attendance_score", "skill_development", "passing", "dribbling", "shooting", "vision", "fitness", "overall_performance", "remarks"}
                updates = [(key, data[key]) for key in allowed if key in data]
                if not updates:
                    return jsonify(success=False, message="No assessment fields supplied."), 400
                assignments = ", ".join(f"{key}=%s" for key, _ in updates) + ", updated_at=CURRENT_TIMESTAMP"
                cursor.execute(f"UPDATE daily_assessments SET {assignments} WHERE id=%s RETURNING *", tuple(value for _, value in updates) + (assessment_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify(success=False, message="Assessment not found."), 404
            _commit(db)
            return jsonify(success=True, data=_row(row))
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments", methods=["GET", "POST"])
    @app.route("/api/tournaments", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_tournaments():
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can create events."), 403
                    data = _body()
                    error = _required(data, "name", "sport_id", "start_date")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO tournaments (name, sport_id, start_date, end_date, venue, status, description, poster_path, registration_open)
                                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""", (data["name"], data["sport_id"], data["start_date"], data.get("end_date"), data.get("venue"), data.get("status") or "Upcoming", data.get("description"), data.get("poster_path"), data.get("registration_open", True)))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("""SELECT t.*, s.name AS sport, COUNT(DISTINCT r.id) AS registration_count
                                 FROM tournaments t JOIN sports s ON s.id=t.sport_id LEFT JOIN registrations r ON r.tournament_id=t.id
                                 GROUP BY t.id, s.name ORDER BY t.start_date DESC""")
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments/<int:tournament_id>", methods=["GET", "PUT", "PATCH"])
    @app.route("/api/tournaments/<int:tournament_id>", methods=["GET", "PUT", "PATCH"])
    @ALL_USERS
    def fit_track_tournament(tournament_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method != "GET":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can edit events."), 403
                    data = _body()
                    allowed = {"name", "sport_id", "start_date", "end_date", "venue", "status", "description", "poster_path", "registration_open"}
                    updates = [(key, data[key]) for key in allowed if key in data]
                    if not updates:
                        return jsonify(success=False, message="No event fields supplied."), 400
                    assignments = ", ".join(f"{key}=%s" for key, _ in updates) + ", updated_at=CURRENT_TIMESTAMP"
                    cursor.execute(f"UPDATE tournaments SET {assignments} WHERE id=%s RETURNING *", tuple(value for _, value in updates) + (tournament_id,))
                    row = cursor.fetchone()
                else:
                    cursor.execute("""SELECT t.*, s.name AS sport FROM tournaments t JOIN sports s ON s.id=t.sport_id WHERE t.id=%s""", (tournament_id,))
                    row = cursor.fetchone()
                if not row:
                    return jsonify(success=False, message="Event not found."), 404
            if request.method != "GET":
                _commit(db)
            return jsonify(success=True, data=_row(row))
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments/<int:tournament_id>/register", methods=["POST"])
    @app.route("/api/tournaments/<int:tournament_id>/register", methods=["POST"])
    @ALL_USERS
    def fit_track_register_tournament(tournament_id):
        data = _body()
        student_id = data.get("student_id") or session.get("user_id")
        if session.get("role") == "student" and student_id != session.get("user_id"):
            return jsonify(success=False, message="You can only register yourself."), 403
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("""INSERT INTO registrations (tournament_id, student_id, team_name)
                                   VALUES (%s,%s,%s) ON CONFLICT (tournament_id, student_id)
                                   DO UPDATE SET team_name=EXCLUDED.team_name, registration_status='Registered' RETURNING *""", (tournament_id, student_id, data.get("team_name")))
                row = _row(cursor.fetchone())
            _commit(db)
            return jsonify(success=True, data=row), 201
        finally:
            db.close()

    @app.route("/api/fit-track/matches", methods=["GET", "POST"])
    @app.route("/api/matches", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_matches():
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can create fixtures."), 403
                    data = _body()
                    error = _required(data, "tournament_id", "team_a", "team_b")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO matches (tournament_id, round_name, match_date, venue, category, team_a, team_b, status)
                                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""", (data["tournament_id"], data.get("round_name"), data.get("match_date"), data.get("venue"), data.get("category") or "Boys", data["team_a"], data["team_b"], data.get("status") or "Scheduled"))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("""SELECT m.*, t.name AS tournament, s.name AS sport
                                 FROM matches m JOIN tournaments t ON t.id=m.tournament_id JOIN sports s ON s.id=t.sport_id
                                 ORDER BY m.match_date NULLS LAST, m.id DESC""")
                matches = _rows(cursor.fetchall())
                for match in matches:
                    cursor.execute("SELECT * FROM match_live_stats WHERE match_id=%s ORDER BY stat_label", (match["id"],))
                    match["stats"] = _rows(cursor.fetchall())
                return jsonify(success=True, data=matches)
        finally:
            db.close()

    @app.route("/api/fit-track/matches/<int:match_id>", methods=["PUT", "PATCH"])
    @app.route("/api/matches/<int:match_id>", methods=["PUT", "PATCH"])
    @ADMIN
    def fit_track_update_match(match_id):
        data = _body()
        allowed = {"round_name", "match_date", "venue", "category", "team_a", "team_b", "score_a", "score_b", "status", "photo_path", "live_note"}
        updates = [(key, data[key]) for key in allowed if key in data]
        if not updates:
            return jsonify(success=False, message="No match fields supplied."), 400
        db = get_db()
        try:
            with db.cursor() as cursor:
                assignments = ", ".join(f"{key}=%s" for key, _ in updates) + ", updated_at=CURRENT_TIMESTAMP"
                cursor.execute(f"UPDATE matches SET {assignments} WHERE id=%s RETURNING *", tuple(value for _, value in updates) + (match_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify(success=False, message="Match not found."), 404
                for key in ("stat_key",):
                    if data.get(key):
                        cursor.execute("""INSERT INTO match_live_stats (match_id, stat_key, stat_label, stat_value)
                                           VALUES (%s,%s,%s,%s) ON CONFLICT (match_id, stat_key)
                                           DO UPDATE SET stat_label=EXCLUDED.stat_label, stat_value=EXCLUDED.stat_value""", (match_id, data[key], data.get("stat_label") or data[key], data.get("stat_value")))
            _commit(db)
            return jsonify(success=True, data=_row(row))
        finally:
            db.close()

    @app.route("/api/fit-track/gallery", methods=["GET", "POST"])
    @app.route("/api/gallery", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_gallery():
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can publish media."), 403
                    data = _body()
                    error = _required(data, "file_path")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO event_media (tournament_id, media_type, file_path, caption, uploaded_by)
                                       VALUES (%s,%s,%s,%s,%s) RETURNING *""", (data.get("tournament_id"), data.get("media_type") or "photo", data["file_path"], data.get("caption"), session.get("user_id")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("""SELECT em.*, t.name AS tournament FROM event_media em LEFT JOIN tournaments t ON t.id=em.tournament_id ORDER BY em.created_at DESC""")
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/announcements", methods=["GET", "POST"])
    @app.route("/api/announcements", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_announcements():
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can publish announcements."), 403
                    data = _body()
                    error = _required(data, "title", "message")
                    if error:
                        return error
                    cursor.execute("INSERT INTO announcements (title, message, image_path, created_by) VALUES (%s,%s,%s,%s) RETURNING *", (data["title"], data["message"], data.get("image_path"), session.get("user_id")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT * FROM announcements WHERE active=TRUE ORDER BY created_at DESC")
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/announcements/<int:announcement_id>", methods=["DELETE"])
    @app.route("/api/announcements/<int:announcement_id>", methods=["DELETE"])
    @ADMIN
    def fit_track_delete_announcement(announcement_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("UPDATE announcements SET active=FALSE WHERE id=%s", (announcement_id,))
            _commit(db)
            return jsonify(success=True)
        finally:
            db.close()

    @app.route("/api/fit-track/messages", methods=["GET", "POST"])
    @app.route("/api/chat/messages", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_messages():
        user_id = session.get("user_id")
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    data = _body()
                    error = _required(data, "receiver_user_id", "message")
                    if error:
                        return error
                    cursor.execute("INSERT INTO messages (sender_user_id, receiver_user_id, message) VALUES (%s,%s,%s) RETURNING *", (user_id, data["receiver_user_id"], data["message"].strip()))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                other = request.args.get("with_user_id")
                if other:
                    cursor.execute("""SELECT m.*, s.full_name AS sender_name, r.full_name AS receiver_name
                                     FROM messages m JOIN users s ON s.id=m.sender_user_id JOIN users r ON r.id=m.receiver_user_id
                                     WHERE (m.sender_user_id=%s AND m.receiver_user_id=%s) OR (m.sender_user_id=%s AND m.receiver_user_id=%s)
                                     ORDER BY m.created_at""", (user_id, other, other, user_id))
                else:
                    cursor.execute("""SELECT m.*, s.full_name AS sender_name, r.full_name AS receiver_name
                                     FROM messages m JOIN users s ON s.id=m.sender_user_id JOIN users r ON r.id=m.receiver_user_id
                                     WHERE m.sender_user_id=%s OR m.receiver_user_id=%s ORDER BY m.created_at DESC""", (user_id, user_id))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/reports", methods=["GET"])
    @app.route("/api/reports/fit-track", methods=["GET"])
    @ALL_USERS
    def fit_track_reports():
        db = get_db()
        try:
            with db.cursor() as cursor:
                scope, params = _student_scope(cursor, session.get("user_id"), session.get("role"))
                student_filter = " AND " + scope if session.get("role") == "student" else ""
                cursor.execute(f"SELECT COUNT(*) AS count FROM users u WHERE u.role='student' AND u.is_active=TRUE{student_filter}", tuple(params) if session.get("role") == "student" else ())
                students = cursor.fetchone()["count"]
                programme_filter = " WHERE p.active=TRUE"
                programme_params = []
                if session.get("role") == "student":
                    programme_filter += " AND p.id IN (SELECT e.programme_id FROM enrollments e WHERE e.student_id=%s)"
                    programme_params.append(session.get("user_id"))
                cursor.execute("SELECT COUNT(*) AS count FROM programmes p" + programme_filter, tuple(programme_params))
                programmes = cursor.fetchone()["count"]
                enrollment_filter = " WHERE status='Active'"
                enrollment_params = []
                if session.get("role") == "student":
                    enrollment_filter += " AND student_id=%s"
                    enrollment_params.append(session.get("user_id"))
                cursor.execute("SELECT COUNT(*) AS count FROM enrollments" + enrollment_filter, tuple(enrollment_params))
                enrollments = cursor.fetchone()["count"]
                assessment_filter = ""
                assessment_params = []
                if session.get("role") == "student":
                    assessment_filter = " WHERE e.student_id=%s"
                    assessment_params.append(session.get("user_id"))
                cursor.execute("SELECT COUNT(*) AS count FROM daily_assessments da JOIN enrollments e ON e.id=da.enrollment_id" + assessment_filter, tuple(assessment_params))
                assessments = cursor.fetchone()["count"]
                programme_rows_query = """SELECT p.name AS programme, s.name AS sport,
                                        COUNT(e.id) AS athletes,
                                        COALESCE(SUM(e.attendance), 0) AS present_sessions,
                                        COALESCE(SUM(e.total_sessions), 0) AS total_sessions
                                 FROM programmes p JOIN sports s ON s.id=p.sport_id
                                 LEFT JOIN enrollments e ON e.programme_id=p.id
                                 """
                if session.get("role") == "student":
                    programme_rows_query += " WHERE e.student_id=%s"
                    programme_rows_params = (session.get("user_id"),)
                else:
                    programme_rows_params = ()
                programme_rows_query += " GROUP BY p.id, p.name, s.name ORDER BY p.name"
                cursor.execute(programme_rows_query, programme_rows_params)
                by_programme = _rows(cursor.fetchall())
            return jsonify(success=True, data={"summary": {"students": students, "programmes": programmes, "enrollments": enrollments, "assessments": assessments}, "by_programme": by_programme})
        finally:
            db.close()

    @app.route("/api/fit-track/students/<int:student_id>/achievements", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_student_achievements(student_id):
        if session.get("role") == "student" and session.get("user_id") != student_id:
            return jsonify(success=False, message="You can only access your own records."), 403
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") not in ("admin", "coach"):
                        return jsonify(success=False, message="Only staff can add achievements."), 403
                    data = _body()
                    error = _required(data, "title")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO achievements (student_id, title, sport_id, level, achievement_year, description)
                                       VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""", (student_id, data["title"], data.get("sport_id"), data.get("level"), data.get("achievement_year") or data.get("year"), data.get("description")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("""SELECT a.*, s.name AS sport FROM achievements a LEFT JOIN sports s ON s.id=a.sport_id
                                 WHERE a.student_id=%s ORDER BY a.achievement_year DESC NULLS LAST, a.created_at DESC""", (student_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/students/<int:student_id>/certificates", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_student_certificates(student_id):
        if session.get("role") == "student" and session.get("user_id") != student_id:
            return jsonify(success=False, message="You can only access your own records."), 403
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") not in ("admin", "coach"):
                        return jsonify(success=False, message="Only staff can add certificates."), 403
                    data = _body()
                    error = _required(data, "title")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO certificates (student_id, title, issuer, issue_date, certificate_no, file_path)
                                       VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""", (student_id, data["title"], data.get("issuer"), data.get("issue_date"), data.get("certificate_no"), data.get("file_path")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT * FROM certificates WHERE student_id=%s ORDER BY issue_date DESC NULLS LAST, created_at DESC", (student_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/achievements/<int:achievement_id>", methods=["PUT", "PATCH", "DELETE"])
    @STAFF
    def fit_track_manage_achievement(achievement_id):
        return _manage_reference_record("achievements", achievement_id, {"title", "sport_id", "level", "achievement_year", "description"})

    @app.route("/api/fit-track/certificates/<int:certificate_id>", methods=["PUT", "PATCH", "DELETE"])
    @STAFF
    def fit_track_manage_certificate(certificate_id):
        return _manage_reference_record("certificates", certificate_id, {"title", "issuer", "issue_date", "certificate_no", "file_path"})

    @app.route("/api/fit-track/tournaments/<int:tournament_id>/details", methods=["GET"])
    @ALL_USERS
    def fit_track_tournament_details(tournament_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT t.*, s.name AS sport FROM tournaments t JOIN sports s ON s.id=t.sport_id WHERE t.id=%s", (tournament_id,))
                tournament = _row(cursor.fetchone())
                if not tournament:
                    return jsonify(success=False, message="Event not found."), 404
                cursor.execute("SELECT * FROM registrations WHERE tournament_id=%s ORDER BY registered_at DESC", (tournament_id,))
                registrations = _rows(cursor.fetchall())
                cursor.execute("SELECT * FROM matches WHERE tournament_id=%s ORDER BY match_date NULLS LAST, id", (tournament_id,))
                matches = _rows(cursor.fetchall())
                cursor.execute("SELECT * FROM event_participants WHERE tournament_id=%s ORDER BY name", (tournament_id,))
                participants = _rows(cursor.fetchall())
                cursor.execute("SELECT * FROM tournament_results WHERE tournament_id=%s ORDER BY category", (tournament_id,))
                results = _rows(cursor.fetchall())
            return jsonify(success=True, data={"tournament": tournament, "registrations": registrations, "matches": matches, "participants": participants, "results": results})
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments/<int:tournament_id>/participants", methods=["GET", "POST"])
    @ADMIN
    def fit_track_tournament_participants(tournament_id):
        data = _body()
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    error = _required(data, "name", "department", "category", "year")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO event_participants (tournament_id, student_id, name, department, category, year)
                                       VALUES (%s,%s,%s,%s,%s,%s)
                                       ON CONFLICT (tournament_id,name,department,category,year) DO UPDATE SET student_id=EXCLUDED.student_id
                                       RETURNING *""", (tournament_id, data.get("student_id"), data["name"], data["department"], data["category"], data["year"]))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT * FROM event_participants WHERE tournament_id=%s ORDER BY name", (tournament_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments/<int:tournament_id>/results", methods=["GET", "POST"])
    @ADMIN
    def fit_track_tournament_results(tournament_id):
        data = _body()
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    error = _required(data, "category", "winner", "runner_up")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO tournament_results (tournament_id, category, winner, runner_up, notes)
                                       VALUES (%s,%s,%s,%s,%s)
                                       ON CONFLICT (tournament_id,category) DO UPDATE SET winner=EXCLUDED.winner, runner_up=EXCLUDED.runner_up, notes=EXCLUDED.notes
                                       RETURNING *""", (tournament_id, data["category"], data["winner"], data["runner_up"], data.get("notes")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT * FROM tournament_results WHERE tournament_id=%s ORDER BY category", (tournament_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments/<int:tournament_id>/draws", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_tournament_draws(tournament_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can publish draws."), 403
                    data = _body()
                    error = _required(data, "category", "format_type", "file_path")
                    if error:
                        return error
                    cursor.execute("INSERT INTO draw_documents (tournament_id, category, format_type, file_path, uploaded_by) VALUES (%s,%s,%s,%s,%s) RETURNING *", (tournament_id, data["category"], data["format_type"], data["file_path"], session.get("user_id")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT * FROM draw_documents WHERE tournament_id=%s ORDER BY created_at DESC", (tournament_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments/<int:tournament_id>/certificate-templates", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_certificate_templates(tournament_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can publish certificate templates."), 403
                    data = _body()
                    error = _required(data, "certificate_type", "file_path")
                    if error:
                        return error
                    cursor.execute("""INSERT INTO certificate_templates (tournament_id, certificate_type, file_path, uploaded_by)
                                       VALUES (%s,%s,%s,%s) ON CONFLICT (tournament_id,certificate_type)
                                       DO UPDATE SET file_path=EXCLUDED.file_path, uploaded_by=EXCLUDED.uploaded_by RETURNING *""", (tournament_id, data["certificate_type"], data["file_path"], session.get("user_id")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT * FROM certificate_templates WHERE tournament_id=%s ORDER BY certificate_type", (tournament_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/tournaments/<int:tournament_id>/certificates/generate", methods=["POST"])
    @ADMIN
    def fit_track_generate_certificate(tournament_id):
        data = _body()
        error = _required(data, "recipient_name", "certificate_type", "file_path")
        if error:
            return error
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("""INSERT INTO generated_certificates
                                   (tournament_id, participant_id, student_id, certificate_type, recipient_name, achievement, certificate_no, file_path)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""", (tournament_id, data.get("participant_id"), data.get("student_id"), data["certificate_type"], data["recipient_name"], data.get("achievement"), data.get("certificate_no") or f"FT-{uuid4().hex[:12].upper()}", data["file_path"]))
                row = _row(cursor.fetchone())
            _commit(db)
            return jsonify(success=True, data=row), 201
        finally:
            db.close()

    @app.route("/api/fit-track/generated-certificates", methods=["GET"])
    @ALL_USERS
    def fit_track_generated_certificates():
        db = get_db()
        try:
            with db.cursor() as cursor:
                if session.get("role") == "student":
                    cursor.execute("SELECT * FROM generated_certificates WHERE student_id=%s ORDER BY created_at DESC", (session.get("user_id"),))
                else:
                    cursor.execute("SELECT * FROM generated_certificates ORDER BY created_at DESC")
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/matches/<int:match_id>/players", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_match_players(match_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can edit match players."), 403
                    data = _body()
                    error = _required(data, "side", "student_name")
                    if error:
                        return error
                    cursor.execute("INSERT INTO match_players (match_id, side, student_name, department, student_id) VALUES (%s,%s,%s,%s,%s) RETURNING *", (match_id, data["side"], data["student_name"], data.get("department"), data.get("student_id")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT * FROM match_players WHERE match_id=%s ORDER BY side, student_name", (match_id,))
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()

    @app.route("/api/fit-track/media/<int:media_id>", methods=["DELETE"])
    @app.route("/api/fit-track/draws/<int:draw_id>", methods=["DELETE"])
    @app.route("/api/fit-track/facility-media/<int:media_id>", methods=["DELETE"])
    @ADMIN
    def fit_track_delete_media(media_id=None, draw_id=None):
        table = "event_media" if request.path.startswith("/api/fit-track/media/") else "draw_documents" if request.path.startswith("/api/fit-track/draws/") else "facility_media"
        record_id = media_id if media_id is not None else draw_id
        return _manage_reference_record(table, record_id, set())

    @app.route("/api/fit-track/facilities", methods=["GET", "POST"])
    @ALL_USERS
    def fit_track_facilities():
        db = get_db()
        try:
            with db.cursor() as cursor:
                if request.method == "POST":
                    if session.get("role") != "admin":
                        return jsonify(success=False, message="Only admins can publish facilities."), 403
                    data = _body()
                    error = _required(data, "sport_id", "file_path")
                    if error:
                        return error
                    cursor.execute("INSERT INTO facility_media (sport_id, file_path, caption, uploaded_by) VALUES (%s,%s,%s,%s) RETURNING *", (data["sport_id"], data["file_path"], data.get("caption"), session.get("user_id")))
                    row = _row(cursor.fetchone())
                    _commit(db)
                    return jsonify(success=True, data=row), 201
                cursor.execute("SELECT fm.*, s.name AS sport FROM facility_media fm JOIN sports s ON s.id=fm.sport_id ORDER BY fm.created_at DESC")
                return jsonify(success=True, data=_rows(cursor.fetchall()))
        finally:
            db.close()


def _manage_reference_record(table, record_id, allowed):
    db = get_db()
    try:
        with db.cursor() as cursor:
            if request.method == "DELETE":
                cursor.execute(f"DELETE FROM {table} WHERE id=%s", (record_id,))
                if cursor.rowcount == 0:
                    return jsonify(success=False, message="Record not found."), 404
                _commit(db)
                return jsonify(success=True)
            data = _body()
            updates = [(key, data[key]) for key in allowed if key in data]
            if not updates:
                return jsonify(success=False, message="No fields supplied."), 400
            assignments = ", ".join(f"{key}=%s" for key, _ in updates)
            cursor.execute(f"UPDATE {table} SET {assignments} WHERE id=%s RETURNING *", tuple(value for _, value in updates) + (record_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify(success=False, message="Record not found."), 404
        _commit(db)
        return jsonify(success=True, data=_row(row))
    finally:
        db.close()
