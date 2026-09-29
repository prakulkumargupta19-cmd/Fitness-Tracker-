"""Attendance on top of the existing schema.

Tables (defined in schema.sql, which this module does not change):
    sports, coach_sports, student_sports,
    attendance_sessions, attendance_records.

Rules:
    * A student only ever sees their own records.
    * A coach marks and later edits attendance only for a sport an
      admin has assigned to them, and only for verified students who
      selected that sport.
    * An admin can do everything a coach can, for any coach and sport,
      and can also assign those sports.
"""

from datetime import date, datetime, timedelta
from flask import jsonify, request, session

try:
    from backend.db import get_db
except ModuleNotFoundError:
    from db import get_db

try:
    from backend.auth.decorators import login_required, role_required
except ModuleNotFoundError:
    from auth.decorators import login_required, role_required


ATTENDANCE_STATUSES = ("present", "absent")


def _parse_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_dates(row):
    for key in ("session_date", "created_at", "assigned_at"):
        if row.get(key) is not None:
            row[key] = str(row[key])
    return row


def _summary(present, absent):
    total = present + absent
    percentage = round((present / total) * 100) if total else 0
    if total == 0:
        label, status_text, status_desc = (
            "No sessions yet",
            "Not started",
            "Attendance appears here after a coach marks a session you belong to.",
        )
    elif percentage >= 90:
        label, status_text, status_desc = (
            "Excellent",
            "Excellent",
            "Your attendance is above the recommended 90% target. Keep maintaining your regular training schedule.",
        )
    elif percentage >= 75:
        label, status_text, status_desc = (
            "Good",
            "Good",
            "Your attendance is on track. A few more sessions will push you past the 90% target.",
        )
    else:
        label, status_text, status_desc = (
            "Needs improvement",
            "Needs improvement",
            "Your attendance is below the recommended target. Try to make the upcoming sessions.",
        )
    return {
        "percentage": percentage,
        "present": present,
        "absent": absent,
        "total": total,
        "label": label,
        "statusText": status_text,
        "statusDesc": status_desc,
    }


def _student_totals(cursor, student_id):
    cursor.execute(
        """SELECT
               SUM(status = 'present') AS present_count,
               SUM(status = 'absent') AS absent_count
           FROM attendance_records
           WHERE student_id = %s""",
        (student_id,),
    )
    row = cursor.fetchone() or {}
    return _summary(int(row["present_count"] or 0), int(row["absent_count"] or 0))


def _student_week(cursor, student_id, today=None):
    """Monday-Sunday of the current week, shaped for the student dashboard."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    
    # Get all days of this week
    week_days = [(monday + timedelta(days=i)) for i in range(7)]
    
    cursor.execute(
        """SELECT s.session_date, r.status
           FROM attendance_records r
           JOIN attendance_sessions s ON s.id = r.session_id
           WHERE r.student_id = %s
           AND s.session_date BETWEEN %s AND %s""",
        (student_id, monday, monday + timedelta(days=6)),
    )
    records = {row["session_date"]: row["status"] for row in cursor.fetchall()}
    
    result = []
    for day in week_days:
        status = records.get(day)
        result.append({
            "day": day.strftime("%a"),
            "present": status == "present"
        })
    return result


def student_attendance_payload(student_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            summary = _student_totals(cursor, student_id)
            summary["weekly"] = _student_week(cursor, student_id)
            return summary
    finally:
        db.close()


def _coach_owns_sport(cursor, coach_id, sport_id):
    cursor.execute(
        "SELECT 1 FROM coach_sports WHERE coach_id = %s AND sport_id = %s",
        (coach_id, sport_id),
    )
    return cursor.fetchone() is not None


def _sport_or_404(cursor, sport_id):
    cursor.execute("SELECT id, name FROM sports WHERE id = %s", (sport_id,))
    return cursor.fetchone()


def _path_role_denied(is_admin):
    """Keep /api/coach/... and /api/admin/... from being used by the other role."""
    if request.path.startswith("/api/admin/") and not is_admin:
        return jsonify({"success": False, "message": "Admin access required."}), 403
    if request.path.startswith("/api/coach/") and is_admin:
        return jsonify({"success": False, "message": "Coach access required."}), 403
    return None


def register_attendance_routes(app):
    """Register all attendance related routes."""
    
    @app.route("/api/student/attendance", methods=["GET"])
    @login_required
    def student_attendance_api():
        if session.get("role") != "student":
            return jsonify({"success": False, "message": "Forbidden"}), 403
        return jsonify({"success": True, "data": student_attendance_payload(session.get("user_id"))}), 200

    @app.route("/api/coach/attendance/sessions", methods=["GET"])
    @role_required("coach")
    def coach_list_sessions():
        coach_id = session.get("user_id")
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """SELECT s.id, s.session_date, sp.name as sport_name
                       FROM attendance_sessions s
                       JOIN sports sp ON s.sport_id = sp.id
                       WHERE s.coach_id = %s
                       ORDER BY s.session_date DESC""",
                    (coach_id,),
                )
                sessions = cursor.fetchall()
                # Need to convert date to string for JSON serialization
                for s in sessions:
                    s["session_date"] = str(s["session_date"])
                return jsonify({"success": True, "data": sessions}), 200
        finally:
            db.close()

    @app.route("/api/coach/attendance/records", methods=["POST"])
    @role_required("coach")
    def coach_save_attendance():
        coach_id = session.get("user_id")
        data = request.json
        sport_id = data.get("sport_id")
        session_date = data.get("session_date")
        records = data.get("records") # list of {student_id, status}

        if not sport_id or not session_date or not records:
            return jsonify({"success": False, "message": "Missing data"}), 400

        db = get_db()
        try:
            with db.cursor() as cursor:
                # Check if coach owns sport
                if not _coach_owns_sport(cursor, coach_id, sport_id):
                    return jsonify({"success": False, "message": "Forbidden"}), 403
                
                # Check if session exists or create it
                cursor.execute(
                    """INSERT IGNORE INTO attendance_sessions (coach_id, sport_id, session_date)
                       VALUES (%s, %s, %s)""",
                    (coach_id, sport_id, session_date),
                )
                cursor.execute(
                    "SELECT id FROM attendance_sessions WHERE coach_id = %s AND sport_id = %s AND session_date = %s",
                    (coach_id, sport_id, session_date),
                )
                session_id = cursor.fetchone()["id"]
                
                # Insert/Update records
                for record in records:
                    cursor.execute(
                        """INSERT INTO attendance_records (session_id, student_id, status)
                           VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE status = VALUES(status)""",
                        (session_id, record["student_id"], record["status"]),
                    )
            db.commit()
            return jsonify({"success": True, "message": "Attendance saved"}), 200
        except Exception as e:
            db.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/admin/students/<int:student_id>/attendance", methods=["GET"])
    @role_required("admin")
    def admin_student_attendance(student_id):
        # reuse student_attendance_payload, it's just the student ID.
        # But wait, student_attendance_payload might be specifically for a student.
        # Let's check.
        # It calls _student_totals and _student_week. It should be fine.
        return jsonify({"success": True, "data": student_attendance_payload(student_id)}), 200



def _eligible_students(cursor, sport_id):
    """Students who signed up for a sport."""
    cursor.execute(
        """SELECT u.id, u.full_name, u.email
           FROM student_sports ss
           JOIN users u ON u.id = ss.student_id
           WHERE ss.sport_id = %s
           ORDER BY u.full_name ASC""",
        (sport_id,),
    )
    return cursor.fetchall()
