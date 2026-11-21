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

from datetime import date, datetime, time, timedelta
from flask import jsonify, request, session

try:
    from backend.db import database_backend, get_db
except ModuleNotFoundError:
    from db import database_backend, get_db

try:
    from backend.auth.decorators import login_required, role_required
except ModuleNotFoundError:
    from auth.decorators import login_required, role_required


ATTENDANCE_STATUSES = ("present", "absent", "late", "excused")


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
    for key in ("session_date", "start_time", "end_time", "created_at", "assigned_at"):
        if row.get(key) is not None:
            row[key] = str(row[key])
    return row


def _schedule_attendance_session(cursor, schedule_session):
    query = """SELECT a.id, a.coach_id, COUNT(r.student_id) AS record_count
               FROM attendance_sessions a
               LEFT JOIN attendance_records r ON r.session_id = a.id
               WHERE a.sport_id = %s AND a.session_date = %s"""
    params = [schedule_session["sport_id"], schedule_session["session_date"]]
    if schedule_session.get("coach_id") is not None:
        query += " AND a.coach_id = %s"
        params.append(schedule_session["coach_id"])
    query += " GROUP BY a.id, a.coach_id ORDER BY record_count DESC, a.id DESC LIMIT 1"
    cursor.execute(query, tuple(params))
    return cursor.fetchone()


def _summary(present, absent, late=0, excused=0):
    total = present + absent + late + excused
    eligible = total - excused
    percentage = round(((present + late) / eligible) * 100) if eligible else 0
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
        "late": late,
        "excused": excused,
        "total": total,
        "label": label,
        "statusText": status_text,
        "statusDesc": status_desc,
    }


def _student_totals(cursor, student_id):
    cursor.execute(
        """SELECT
               COUNT(*) FILTER (WHERE status = 'present') AS present_count,
               COUNT(*) FILTER (WHERE status = 'absent') AS absent_count,
               COUNT(*) FILTER (WHERE status = 'late') AS late_count,
               COUNT(*) FILTER (WHERE status = 'excused') AS excused_count
           FROM attendance_records
           WHERE student_id = %s""",
        (student_id,),
    )
    row = cursor.fetchone() or {}
    return _summary(
        int(row["present_count"] or 0),
        int(row["absent_count"] or 0),
        int(row["late_count"] or 0),
        int(row["excused_count"] or 0),
    )


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
    records_by_day = {}
    for row in cursor.fetchall():
        day_key = str(row["session_date"])[:10]
        records_by_day.setdefault(day_key, set()).add(str(row["status"]).lower())
    
    result = []
    for day in week_days:
        statuses = sorted(
            records_by_day.get(day.isoformat(), set()),
            key=lambda value: ("present", "late", "absent", "excused").index(value)
            if value in {"present", "late", "absent", "excused"}
            else 99,
        )
        status = statuses[0] if len(statuses) == 1 else "mixed" if statuses else "none"
        result.append({
            "day": day.strftime("%a"),
            "status": status,
            "statuses": statuses,
            "present": any(value in ("present", "late") for value in statuses),
        })
    return result


def _student_history(cursor, student_id):
    cursor.execute(
        """SELECT a.session_date, s.name AS sport_name, r.status
           FROM attendance_records r
           JOIN attendance_sessions a ON a.id = r.session_id
           JOIN sports s ON s.id = a.sport_id
           WHERE r.student_id = %s
           ORDER BY a.session_date DESC, a.id DESC
           LIMIT 50""",
        (student_id,),
    )
    return [
        {
            **row,
            "session_date": str(row["session_date"]),
            "status": str(row["status"]).lower(),
        }
        for row in cursor.fetchall()
    ]


def student_attendance_payload(student_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            summary = _student_totals(cursor, student_id)
            summary["weekly"] = _student_week(cursor, student_id)
            summary["records"] = _student_history(cursor, student_id)
            return summary
    finally:
        db.close()


def _coach_owns_sport(cursor, coach_id, sport_id):
    cursor.execute(
                """SELECT 1 FROM coach_sports cs
                     JOIN users c ON c.id = cs.coach_id
                     WHERE cs.coach_id = %s AND cs.sport_id = %s
                         AND c.role = 'coach' AND c.coach_status = 'approved'
                         AND c.is_active = TRUE""",
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
                                             JOIN users c ON c.id = s.coach_id
                                                 AND c.role = 'coach' AND c.coach_status = 'approved'
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

    @app.route("/api/coach/attendance/summary", methods=["GET"])
    @role_required("coach")
    def coach_attendance_summary():
        """Return attendance totals for the coach's role-matched roster."""
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """SELECT
                           COUNT(*) FILTER (WHERE r.status = 'present') AS present_count,
                           COUNT(*) FILTER (
                               WHERE r.status = 'present' AND a.session_date = CURRENT_DATE
                           ) AS present_today,
                           COUNT(*) FILTER (
                               WHERE r.status = 'absent' AND a.session_date = CURRENT_DATE
                           ) AS absent_today,
                           COUNT(*) FILTER (WHERE r.status = 'late') AS late_count,
                           COUNT(*) FILTER (WHERE r.status = 'excused') AS excused_count,
                           COUNT(*) AS total_count
                       FROM attendance_records r
                       JOIN attendance_sessions a ON a.id = r.session_id
                       JOIN coach_sports cs
                         ON cs.coach_id = a.coach_id AND cs.sport_id = a.sport_id
                       JOIN student_sports ss
                         ON ss.student_id = r.student_id AND ss.sport_id = a.sport_id
                       JOIN users student
                         ON student.id = r.student_id AND student.role = 'student'
                            AND student.is_verified = TRUE
                            AND student.is_verified = TRUE AND student.is_active = TRUE
                       JOIN users coach
                         ON coach.id = a.coach_id AND coach.role = 'coach'
                            AND coach.coach_status = 'approved' AND coach.is_active = TRUE
                       WHERE a.coach_id = %s""",
                    (session.get("user_id"),),
                )
                row = cursor.fetchone() or {}
            present = int(row.get("present_count") or 0)
            total = int(row.get("total_count") or 0)
            late = int(row.get("late_count") or 0)
            excused = int(row.get("excused_count") or 0)
            eligible = total - excused
            summary = {
                "percentage": round((present + late) * 100 / eligible) if eligible else 0,
                "present_today": int(row.get("present_today") or 0),
                "absent_today": int(row.get("absent_today") or 0),
                "present": present,
                "late": late,
                "excused": excused,
                "total": total,
            }
            return jsonify({"success": True, "summary": summary}), 200
        finally:
            db.close()

    @app.route("/api/coach/sports", methods=["GET"])
    @role_required("coach")
    def coach_assigned_sports():
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """SELECT s.id, s.name FROM coach_sports cs
                       JOIN sports s ON s.id = cs.sport_id
                       JOIN users c ON c.id = cs.coach_id
                       WHERE cs.coach_id = %s AND c.role = 'coach'
                         AND c.coach_status = 'approved'
                       ORDER BY s.name""",
                    (session.get("user_id"),),
                )
                sports = cursor.fetchall()
            return jsonify({"success": True, "sports": sports}), 200
        finally:
            db.close()

    @app.route("/api/coach/attendance/students", methods=["GET"])
    @role_required("coach")
    def coach_attendance_students():
        sport_id = _as_int(request.args.get("sport_id"))
        if sport_id is None:
            return jsonify({"success": False, "message": "sport_id is required."}), 400
        db = get_db()
        try:
            with db.cursor() as cursor:
                if not _coach_owns_sport(cursor, session.get("user_id"), sport_id):
                    return jsonify({"success": False, "message": "Forbidden."}), 403
                cursor.execute(
                    """SELECT u.id, u.full_name AS name, u.email
                       FROM student_sports ss
                       JOIN users u ON u.id = ss.student_id
                       WHERE ss.sport_id = %s AND u.role = 'student'
                         AND u.is_verified = TRUE
                         AND u.is_verified = TRUE AND u.is_active = TRUE
                       ORDER BY u.full_name""",
                    (sport_id,),
                )
                students = cursor.fetchall()
            return jsonify({"success": True, "students": students}), 200
        finally:
            db.close()

    @app.route("/api/coach/attendance/records", methods=["GET"])
    @role_required("coach")
    def coach_get_attendance_records():
        sport_id = _as_int(request.args.get("sport_id"))
        session_date = _parse_date(request.args.get("session_date"))
        if sport_id is None or session_date is None:
            return jsonify({"success": False, "message": "A valid sport and date are required."}), 400
        db = get_db()
        try:
            with db.cursor() as cursor:
                if not _coach_owns_sport(cursor, session.get("user_id"), sport_id):
                    return jsonify({"success": False, "message": "Forbidden."}), 403
                cursor.execute(
                    """SELECT r.student_id, r.status
                       FROM attendance_records r
                       JOIN attendance_sessions a ON a.id = r.session_id
                       JOIN student_sports ss ON ss.student_id=r.student_id AND ss.sport_id=a.sport_id
                       JOIN users active_student ON active_student.id=r.student_id AND active_student.is_active=TRUE
                       WHERE a.coach_id = %s AND a.sport_id = %s AND a.session_date = %s""",
                    (session.get("user_id"), sport_id, session_date),
                )
                records = cursor.fetchall()
            return jsonify({"success": True, "records": records}), 200
        finally:
            db.close()

    @app.route("/api/coach/attendance/records", methods=["POST"])
    @role_required("coach")
    def coach_save_attendance():
        coach_id = session.get("user_id")
        data = request.get_json(silent=True) or {}
        sport_id = _as_int(data.get("sport_id"))
        session_date = _parse_date(data.get("session_date"))
        records = data.get("records")
        assessments = data.get("assessments")

        if sport_id is None or session_date is None or not isinstance(records, list) or not records:
            return jsonify({"success": False, "message": "A valid sport, date, and attendance list are required."}), 400
        student_ids = []
        for record in records:
            if not isinstance(record, dict):
                return jsonify({"success": False, "message": "Invalid attendance record."}), 400
            student_id = _as_int(record.get("student_id"))
            status = str(record.get("status") or "").strip().lower()
            if student_id is None or status not in ATTENDANCE_STATUSES:
                return jsonify({"success": False, "message": "Status must be present or absent; late and excused are also supported."}), 400
            student_ids.append(student_id)
        if len(set(student_ids)) != len(student_ids):
            return jsonify({"success": False, "message": "Duplicate students are not allowed."}), 400
        if assessments is not None:
            if not isinstance(assessments, list):
                return jsonify({"success": False, "message": "assessments must be a list."}), 400
            attendance_by_student = {
                _as_int(record["student_id"]): str(record["status"]).strip().lower()
                for record in records
            }
            assessment_by_student = {}
            for entry in assessments:
                if not isinstance(entry, dict):
                    return jsonify({"success": False, "message": "Invalid assessment record."}), 400
                student_id = _as_int(entry.get("student_id"))
                status = str(
                    entry.get("attendance_status") or entry.get("status") or ""
                ).strip().lower()
                if (
                    student_id is None
                    or student_id in assessment_by_student
                    or student_id not in attendance_by_student
                    or status != attendance_by_student[student_id]
                ):
                    return jsonify({
                        "success": False,
                        "message": "Assessment records must match each student's attendance status.",
                    }), 400
                assessment_by_student[student_id] = entry
            if set(assessment_by_student) != set(attendance_by_student):
                return jsonify({
                    "success": False,
                    "message": "Provide an assessment record for each student when assessments are included.",
                }), 400

        db = get_db()
        try:
            with db.cursor() as cursor:
                if not _coach_owns_sport(cursor, coach_id, sport_id):
                    return jsonify({"success": False, "message": "Forbidden."}), 403
                placeholders = ", ".join(["%s"] * len(student_ids))
                cursor.execute(
                    f"""SELECT u.id FROM student_sports ss
                        JOIN users u ON u.id = ss.student_id
                        WHERE ss.sport_id = %s AND u.role = 'student'
                          AND u.is_verified = TRUE AND u.is_active = TRUE
                          AND u.id IN ({placeholders})""",
                    (sport_id, *student_ids),
                )
                eligible_ids = {row["id"] for row in cursor.fetchall()}
                if eligible_ids != set(student_ids):
                    return jsonify({"success": False, "message": "One or more students are not assigned to this sport."}), 403
                
                cursor.execute(
                    """INSERT INTO attendance_sessions
                           (coach_id, sport_id, session_date)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (coach_id, sport_id, session_date)
                       DO NOTHING""",
                    (coach_id, sport_id, session_date),
                )
                cursor.execute(
                    "SELECT id FROM attendance_sessions WHERE coach_id = %s AND sport_id = %s AND session_date = %s",
                    (coach_id, sport_id, session_date),
                )
                session_id = cursor.fetchone()["id"]

                # Older Supabase databases use the attendance_status_type enum,
                # while fresh installs use TEXT with a CHECK constraint. A CTE
                # VALUES parameter is typed as TEXT, so cast it explicitly only
                # when the deployed column is the legacy enum.
                status_cast = ""
                if database_backend() == "postgres":
                    cursor.execute(
                        """SELECT udt_name FROM information_schema.columns
                           WHERE table_schema = current_schema()
                             AND table_name = 'attendance_records'
                             AND column_name = 'status'"""
                    )
                    status_column = cursor.fetchone()
                    status_cast = (
                        "::attendance_status_type"
                        if status_column and status_column.get("udt_name") == "attendance_status_type"
                        else "::text"
                    )
                
                for record in records:
                    cursor.execute(
                        f"""WITH attendance_input(session_id, student_id, status) AS (
                               VALUES (%s, %s, %s{status_cast})
                           )
                           INSERT INTO attendance_records
                               (session_id, student_id, status, session_date,
                                marked_by_role, marked_by_id,
                                updated_by_role, updated_by_id, updated_at)
                           SELECT attendance_input.session_id,
                                  attendance_input.student_id,
                                  attendance_input.status,
                                  attendance_session.session_date,
                                  'coach', coach_id,
                                  'coach', coach_id, CURRENT_TIMESTAMP
                           FROM attendance_input
                           JOIN attendance_sessions AS attendance_session
                             ON attendance_session.id = attendance_input.session_id
                           ON CONFLICT (session_id, student_id)
                           DO UPDATE SET
                               status = EXCLUDED.status,
                               session_date = EXCLUDED.session_date,
                               updated_by_role = EXCLUDED.updated_by_role,
                               updated_by_id = EXCLUDED.updated_by_id,
                               updated_at = CURRENT_TIMESTAMP""",
                        (
                            session_id,
                            int(record["student_id"]),
                            str(record["status"]).strip().lower(),
                        ),
                    )
                if assessments is not None:
                    try:
                        from backend.assessments import save_sport_assessment_entries
                    except ModuleNotFoundError:
                        from assessments import save_sport_assessment_entries
                    save_sport_assessment_entries(
                        cursor,
                        coach_id,
                        sport_id,
                        session_date,
                        assessments,
                    )
            db.commit()
            return jsonify({"success": True, "message": "Attendance saved"}), 200
        except ValueError as exc:
            db.rollback()
            return jsonify({"success": False, "message": str(exc)}), 400
        except Exception as e:
            db.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            db.close()

    @app.route(
        "/api/admin/fit-track/schedule/<int:schedule_id>/attendance",
        methods=["GET", "PUT"],
    )
    @role_required("admin")
    def admin_schedule_attendance(schedule_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """SELECT cs.id, cs.sport_id, cs.coach_id, cs.session_date,
                              cs.start_time, cs.end_time, cs.session_type,
                              cs.status, s.name AS sport
                       FROM coaching_sessions cs
                       JOIN sports s ON s.id = cs.sport_id
                       WHERE cs.id = %s""",
                    (schedule_id,),
                )
                scheduled = cursor.fetchone()
                if not scheduled:
                    return jsonify({"success": False, "message": "Session not found."}), 404
                scheduled_date = _parse_date(scheduled["session_date"])
                if scheduled_date is None or scheduled_date >= date.today():
                    return jsonify({
                        "success": False,
                        "message": "Attendance can only be reviewed for sessions before today.",
                    }), 400

                attendance_session = _schedule_attendance_session(cursor, scheduled)
                if request.method == "GET":
                    cursor.execute(
                        """SELECT u.id, u.full_name AS name
                           FROM student_sports ss
                           JOIN users u ON u.id = ss.student_id
                           WHERE ss.sport_id = %s AND u.role = 'student'
                             AND u.is_verified = TRUE AND u.is_active = TRUE
                           ORDER BY u.full_name""",
                        (scheduled["sport_id"],),
                    )
                    students = cursor.fetchall()
                    records = []
                    assessments = []
                    if attendance_session:
                        cursor.execute(
                            """SELECT student_id, status FROM attendance_records
                               WHERE session_id = %s ORDER BY student_id""",
                            (attendance_session["id"],),
                        )
                        records = cursor.fetchall()
                        cursor.execute(
                            """SELECT a.student_id, a.attendance_status,
                                      a.general_remarks, a.overall_score,
                                      v.field_key, v.score_value
                               FROM sport_student_assessments a
                               LEFT JOIN sport_student_assessment_values v
                                 ON v.assessment_id = a.id
                               WHERE a.sport_id = %s AND a.session_date = %s
                                 AND a.coach_id = %s
                               ORDER BY a.student_id, v.field_key""",
                            (
                                scheduled["sport_id"],
                                scheduled["session_date"],
                                attendance_session["coach_id"],
                            ),
                        )
                        assessment_rows = cursor.fetchall()
                        by_student = {}
                        for row in assessment_rows:
                            entry = by_student.setdefault(
                                row["student_id"],
                                {
                                    "student_id": row["student_id"],
                                    "attendance_status": row["attendance_status"],
                                    "remarks": row["general_remarks"] or "",
                                    "overall_score": (
                                        float(row["overall_score"])
                                        if row["overall_score"] is not None
                                        else None
                                    ),
                                    "values": {},
                                },
                            )
                            if row["field_key"] is not None:
                                entry["values"][row["field_key"]] = float(row["score_value"])
                        assessments = list(by_student.values())

                    try:
                        from backend.assessments.routes import _fetch_active_fields
                    except ModuleNotFoundError:
                        from assessments.routes import _fetch_active_fields
                    fields = _fetch_active_fields(cursor, scheduled["sport_id"])
                    return jsonify({
                        "success": True,
                        "data": {
                            "session": _row_dates(dict(scheduled)),
                            "coach_id": attendance_session["coach_id"] if attendance_session else None,
                            "attendance_taken": bool(
                                attendance_session and attendance_session["record_count"]
                            ),
                            "students": [dict(row) for row in students],
                            "records": [dict(row) for row in records],
                            "assessments": assessments,
                            "fields": fields,
                        },
                    }), 200

                if not attendance_session or not attendance_session["record_count"]:
                    return jsonify({
                        "success": False,
                        "message": "Attendance has not been submitted for this session.",
                    }), 409

                data = request.get_json(silent=True) or {}
                records = data.get("records")
                assessments = data.get("assessments")
                if not isinstance(records, list) or not records:
                    return jsonify({
                        "success": False,
                        "message": "A non-empty attendance list is required.",
                    }), 400

                clean_records = []
                student_ids = []
                for record in records:
                    if not isinstance(record, dict):
                        return jsonify({"success": False, "message": "Invalid attendance record."}), 400
                    student_id = _as_int(record.get("student_id"))
                    status = str(record.get("status") or "").strip().lower()
                    if student_id is None or status not in ATTENDANCE_STATUSES:
                        return jsonify({
                            "success": False,
                            "message": "Choose a valid attendance status for each student.",
                        }), 400
                    student_ids.append(student_id)
                    clean_records.append({"student_id": student_id, "status": status})
                if len(set(student_ids)) != len(student_ids):
                    return jsonify({"success": False, "message": "Duplicate students are not allowed."}), 400

                cursor.execute(
                    """SELECT u.id FROM student_sports ss
                       JOIN users u ON u.id = ss.student_id
                       WHERE ss.sport_id = %s AND u.role = 'student'
                         AND u.is_verified = TRUE AND u.is_active = TRUE""",
                    (scheduled["sport_id"],),
                )
                eligible_ids = {int(row["id"]) for row in cursor.fetchall()}
                if eligible_ids != set(student_ids):
                    return jsonify({
                        "success": False,
                        "message": "Attendance must include every active student assigned to this sport.",
                    }), 400

                clean_assessments = None
                if assessments is not None:
                    if not isinstance(assessments, list):
                        return jsonify({"success": False, "message": "assessments must be a list."}), 400
                    statuses = {row["student_id"]: row["status"] for row in clean_records}
                    by_student = {}
                    for entry in assessments:
                        if not isinstance(entry, dict):
                            return jsonify({"success": False, "message": "Invalid assessment record."}), 400
                        student_id = _as_int(entry.get("student_id"))
                        status = str(entry.get("attendance_status") or entry.get("status") or "").strip().lower()
                        if (
                            student_id is None
                            or student_id in by_student
                            or statuses.get(student_id) != status
                        ):
                            return jsonify({
                                "success": False,
                                "message": "Assessment records must match each student's attendance status.",
                            }), 400
                        by_student[student_id] = entry
                    if set(by_student) != set(student_ids):
                        return jsonify({
                            "success": False,
                            "message": "Provide an assessment record for each student.",
                        }), 400
                    clean_assessments = list(by_student.values())

                status_cast = ""
                if database_backend() == "postgres":
                    cursor.execute(
                        """SELECT udt_name FROM information_schema.columns
                           WHERE table_schema = current_schema()
                             AND table_name = 'attendance_records'
                             AND column_name = 'status'"""
                    )
                    status_column = cursor.fetchone()
                    status_cast = (
                        "::attendance_status_type"
                        if status_column and status_column.get("udt_name") == "attendance_status_type"
                        else "::text"
                    )
                for record in clean_records:
                    cursor.execute(
                        f"""WITH attendance_input(session_id, student_id, status) AS (
                               VALUES (%s, %s, %s{status_cast})
                           )
                           INSERT INTO attendance_records
                               (session_id, student_id, status, session_date,
                                updated_by_role, updated_by_id, updated_at)
                           SELECT attendance_input.session_id,
                                  attendance_input.student_id,
                                  attendance_input.status,
                                  attendance_session.session_date,
                                  'admin', %s, CURRENT_TIMESTAMP
                           FROM attendance_input
                           JOIN attendance_sessions attendance_session
                             ON attendance_session.id = attendance_input.session_id
                           ON CONFLICT (session_id, student_id)
                           DO UPDATE SET
                               status = EXCLUDED.status,
                               session_date = EXCLUDED.session_date,
                               updated_by_role = EXCLUDED.updated_by_role,
                               updated_by_id = EXCLUDED.updated_by_id,
                               updated_at = CURRENT_TIMESTAMP""",
                        (
                            attendance_session["id"],
                            record["student_id"],
                            record["status"],
                            session.get("user_id"),
                        ),
                    )
                if clean_assessments is not None:
                    try:
                        from backend.assessments import save_sport_assessment_entries
                    except ModuleNotFoundError:
                        from assessments import save_sport_assessment_entries
                    save_sport_assessment_entries(
                        cursor,
                        attendance_session["coach_id"],
                        scheduled["sport_id"],
                        scheduled["session_date"],
                        clean_assessments,
                    )
            db.commit()
            return jsonify({"success": True, "message": "Session attendance updated."}), 200
        except ValueError as exc:
            db.rollback()
            return jsonify({"success": False, "message": str(exc)}), 400
        except Exception as exc:
            db.rollback()
            return jsonify({"success": False, "message": str(exc)}), 500
        finally:
            db.close()

    @app.route(
        "/api/admin/fit-track/schedule/<int:schedule_id>/not-held",
        methods=["POST"],
    )
    @role_required("admin")
    def admin_mark_schedule_not_held(schedule_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT id, sport_id, session_date FROM coaching_sessions WHERE id = %s",
                    (schedule_id,),
                )
                scheduled = cursor.fetchone()
                if not scheduled:
                    return jsonify({"success": False, "message": "Session not found."}), 404
                scheduled_date = _parse_date(scheduled["session_date"])
                if scheduled_date is None or scheduled_date >= date.today():
                    return jsonify({
                        "success": False,
                        "message": "Only sessions before today can be marked not held.",
                    }), 400
                cursor.execute(
                    """SELECT 1 FROM attendance_sessions a
                       JOIN attendance_records r ON r.session_id = a.id
                       WHERE a.sport_id = %s AND a.session_date = %s LIMIT 1""",
                    (scheduled["sport_id"], scheduled["session_date"]),
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Attendance exists for this session. Edit the attendance instead.",
                    }), 409
                cursor.execute(
                    """UPDATE coaching_sessions SET status = 'Not Held',
                              updated_by = %s, updated_at = CURRENT_TIMESTAMP
                       WHERE id = %s""",
                    (session.get("user_id"), schedule_id),
                )
            db.commit()
            return jsonify({"success": True, "message": "Session marked not held."}), 200
        except Exception as exc:
            db.rollback()
            return jsonify({"success": False, "message": str(exc)}), 500
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


    @app.route("/api/admin/attendance", methods=["POST"])
    @role_required("admin")
    def admin_save_attendance():
        """Create or update student attendance from the admin portal.

        The admin UI does not ask for a coach. If a coach_id is supplied
        (for an existing attendance record), it is validated. If it is
        omitted, the endpoint resolves each student to their latest active
        coach assignment for the selected sport.
        """
        data = request.get_json(silent=True) or {}

        sport_id = _as_int(data.get("sport_id"))
        session_date = _parse_date(data.get("session_date"))
        requested_coach_id = _as_int(data.get("coach_id"))
        records = data.get("records")

        if (
            sport_id is None
            or session_date is None
            or not isinstance(records, list)
            or not records
        ):
            return jsonify({
                "success": False,
                "message": "A valid sport, date, and attendance list are required.",
            }), 400

        clean_records = []
        student_ids = []

        for record in records:
            if not isinstance(record, dict):
                return jsonify({
                    "success": False,
                    "message": "Invalid attendance record.",
                }), 400

            student_id = _as_int(record.get("student_id"))
            status = str(record.get("status") or "").strip().lower()

            if student_id is None:
                return jsonify({
                    "success": False,
                    "message": "A valid student_id is required.",
                }), 400

            if status not in ATTENDANCE_STATUSES:
                return jsonify({
                    "success": False,
                    "message": "Status must be present or absent; late and excused are also supported.",
                }), 400

            student_ids.append(student_id)
            clean_records.append({
                "student_id": student_id,
                "status": status,
            })

        if len(set(student_ids)) != len(student_ids):
            return jsonify({
                "success": False,
                "message": "Duplicate students are not allowed.",
            }), 400

        db = get_db()

        try:
            with db.cursor() as cursor:

                placeholders = ", ".join(["%s"] * len(student_ids))

                cursor.execute(
                    f"""SELECT u.id
                        FROM student_sports ss
                        JOIN users u ON u.id = ss.student_id
                        WHERE ss.sport_id = %s
                          AND u.role = 'student'
                          AND u.role = 'student' AND u.is_active = TRUE
                          AND u.is_verified = TRUE
                          AND u.id IN ({placeholders})""",
                    (sport_id, *student_ids),
                )

                eligible_ids = {
                    int(row["id"])
                    for row in cursor.fetchall()
                }

                if eligible_ids != set(student_ids):
                    return jsonify({
                        "success": False,
                        "message": "One or more students are not assigned to this sport.",
                    }), 403

                # Build coach groups. Existing records normally provide
                # coach_id; for a new record we resolve the student's
                # latest coach assignment automatically.
                coach_groups = {}

                for item in clean_records:

                    coach_id = requested_coach_id

                    if coach_id is None:
                        cursor.execute(
                            """SELECT cs.coach_id
                               FROM coach_sports cs
                               JOIN student_sports ss ON ss.sport_id=cs.sport_id
                               JOIN users c ON c.id=cs.coach_id AND c.role='coach'
                                 AND c.coach_status='approved' AND c.is_active=TRUE
                               WHERE ss.student_id=%s AND cs.sport_id=%s
                               ORDER BY cs.coach_id LIMIT 1""",
                            (item["student_id"], sport_id),
                        )
                        coach_row = cursor.fetchone()

                        if not coach_row:
                            return jsonify({
                                "success": False,
                                "message": (
                                    f"No approved coach is assigned to student "
                                    f"{item['student_id']} for this sport."
                                ),
                            }), 400

                        coach_id = int(coach_row["coach_id"])

                    cursor.execute(
                        """SELECT 1
                           FROM coach_sports cs
                           JOIN users c ON c.id = cs.coach_id
                           WHERE cs.coach_id = %s
                             AND cs.sport_id = %s
                             AND c.role = 'coach'
                             AND c.coach_status = 'approved'
                             AND c.is_active = TRUE""",
                        (coach_id, sport_id),
                    )

                    if not cursor.fetchone():
                        return jsonify({
                            "success": False,
                            "message": "The selected coach is not approved for this sport.",
                        }), 403

                    coach_groups.setdefault(coach_id, []).append(item)

                for coach_id, group in coach_groups.items():

                    cursor.execute(
                        """INSERT INTO attendance_sessions
                               (coach_id, sport_id, session_date)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (coach_id, sport_id, session_date)
                           DO UPDATE SET session_date = EXCLUDED.session_date
                           RETURNING id""",
                        (coach_id, sport_id, session_date),
                    )

                    session_row = cursor.fetchone()
                    session_id = int(session_row["id"])

                    for item in group:

                        cursor.execute(
                            """INSERT INTO attendance_records
                                   (session_id, student_id, status, session_date,
                                    marked_by_role, marked_by_id,
                                    updated_by_role, updated_by_id, updated_at)
                               VALUES (%s, %s, %s, %s,
                                       'admin', %s,
                                       'admin', %s, CURRENT_TIMESTAMP)
                               ON CONFLICT (session_id, student_id)
                               DO UPDATE SET
                                   status = EXCLUDED.status,
                                   session_date = EXCLUDED.session_date,
                                   updated_by_role = EXCLUDED.updated_by_role,
                                   updated_by_id = EXCLUDED.updated_by_id,
                                   updated_at = CURRENT_TIMESTAMP""",
                            (
                                session_id,
                                item["student_id"],
                                item["status"],
                                session_date,
                                session.get("user_id"),
                                session.get("user_id"),
                            ),
                        )

            db.commit()

            return jsonify({
                "success": True,
                "message": "Attendance saved successfully.",
            }), 200

        except Exception as exc:
            db.rollback()
            return jsonify({
                "success": False,
                "message": f"Attendance save failed: {exc}",
            }), 500

        finally:
            db.close()


    @app.route("/api/coach/attendance", methods=["GET"])
    @role_required("coach")
    def coach_list_attendance():
        coach_id = session.get("user_id")
        session_date = _parse_date(request.args.get("session_date"))
        sport_id = _as_int(request.args.get("sport_id"))

        query = """SELECT
                          r.student_id,
                          u.full_name AS student_name,
                          u.email,
                          a.coach_id,
                          a.sport_id,
                          s.name AS sport_name,
                          c.full_name AS coach_name,
                          a.session_date,
                          r.status
                   FROM attendance_records r
                   JOIN attendance_sessions a
                     ON a.id = r.session_id
                   JOIN users u
                     ON u.id = r.student_id
                   JOIN users c
                     ON c.id = a.coach_id
                   JOIN sports s
                     ON s.id = a.sport_id
                   JOIN coach_sports cs
                     ON cs.sport_id = a.sport_id AND cs.coach_id = a.coach_id
                   WHERE a.coach_id = %s AND u.role = 'student'"""
        
        conditions = []
        params = [coach_id]
        
        if session_date:
            conditions.append("a.session_date = %s")
            params.append(session_date)
        if sport_id is not None:
            conditions.append("a.sport_id = %s")
            params.append(sport_id)
            
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY a.session_date DESC, s.name, u.full_name"
        
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(query, tuple(params))
                records = cursor.fetchall()
            for record in records:
                record["session_date"] = str(record["session_date"])
            return jsonify({"success": True, "records": records}), 200
        finally:
            db.close()


    @app.route("/api/coach/request-extra-session", methods=["POST"])
    @role_required("coach")
    def request_extra_session():
        coach_id = session.get("user_id")
        data = request.get_json(silent=True) or {}
        sport_id = _as_int(data.get("sport_id"))
        requested_date = _parse_date(data.get("requested_date"))
        try:
            start_time = time.fromisoformat(str(data.get("start_time") or ""))
            end_time = time.fromisoformat(str(data.get("end_time") or ""))
        except ValueError:
            return jsonify({"success": False, "message": "Enter valid start and end times."}), 400

        if sport_id is None or requested_date is None:
            return jsonify({"success": False, "message": "All fields are required."}), 400
        if requested_date < date.today():
            return jsonify({"success": False, "message": "Choose today or a future date."}), 400
        if start_time >= end_time:
            return jsonify({"success": False, "message": "The end time must be later than the start time."}), 400

        db = get_db()
        try:
            with db.cursor() as cursor:
                if not _coach_owns_sport(cursor, coach_id, sport_id):
                    return jsonify({"success": False, "message": "Forbidden: You do not manage this sport."}), 403

                cursor.execute(
                    """INSERT INTO extra_session_requests (coach_id, sport_id, requested_date, start_time, end_time)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        coach_id,
                        sport_id,
                        requested_date,
                        start_time.isoformat(timespec="minutes"),
                        end_time.isoformat(timespec="minutes"),
                    )
                )
                db.commit()
            return jsonify({"success": True, "message": "Extra session request submitted."}), 201
        except Exception as exc:
            db.rollback()
            return jsonify({"success": False, "message": f"Request failed: {exc}"}), 500
        finally:
            db.close()

    @app.route("/api/admin/extra-session-requests", methods=["GET"])
    @role_required("admin")
    def admin_list_extra_session_requests():
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT r.*, u.full_name as coach_name, s.name as sport_name
                    FROM extra_session_requests r
                    JOIN users u ON r.coach_id = u.id
                    JOIN sports s ON r.sport_id = s.id
                    WHERE r.status = 'pending'
                    ORDER BY r.created_at DESC
                """)
                records = cursor.fetchall()
            return jsonify({"success": True, "requests": records}), 200
        finally:
            db.close()

    @app.route("/api/admin/extra-session-requests/<int:request_id>/approve", methods=["POST"])
    @role_required("admin")
    def admin_approve_extra_session(request_id):
        data = request.get_json(silent=True) or {}
        admin_notes = data.get("admin_notes")

        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM extra_session_requests WHERE id = %s",
                    (request_id,),
                )
                request_data = cursor.fetchone()
                if not request_data:
                    return jsonify({"success": False, "message": "Request not found."}), 404

                if request_data["status"] != "pending":
                    return jsonify({"success": False, "message": "This request has already been reviewed."}), 409

                if "requested_date" in data:
                    final_date = _parse_date(data["requested_date"])
                    if final_date is None:
                        return jsonify({"success": False, "message": "Enter a valid session date."}), 400
                else:
                    final_date = _parse_date(request_data["requested_date"])

                try:
                    final_start = time.fromisoformat(
                        str(data.get("start_time", request_data["start_time"]))
                    )
                    final_end = time.fromisoformat(
                        str(data.get("end_time", request_data["end_time"]))
                    )
                except ValueError:
                    return jsonify({"success": False, "message": "Enter valid start and end times."}), 400

                if final_date is None or final_date < date.today():
                    return jsonify({"success": False, "message": "The session date must be today or later."}), 400
                if final_start >= final_end:
                    return jsonify({"success": False, "message": "The end time must be later than the start time."}), 400

                cursor.execute(
                    """SELECT 1 FROM coaching_sessions
                       WHERE sport_id = %s AND session_date = %s AND status <> 'Cancelled'
                         AND start_time < %s AND end_time > %s""",
                    (
                        request_data["sport_id"],
                        final_date,
                        final_end.isoformat(timespec="minutes"),
                        final_start.isoformat(timespec="minutes"),
                    ),
                )
                if cursor.fetchone():
                    return jsonify({"success": False, "message": "This session overlaps another scheduled session for the sport."}), 409

                cursor.execute(
                    """UPDATE extra_session_requests
                       SET status = 'approved', admin_notes = %s
                       WHERE id = %s AND status = 'pending'""",
                    (admin_notes, request_id)
                )
                if cursor.rowcount != 1:
                    db.rollback()
                    return jsonify({"success": False, "message": "This request has already been reviewed."}), 409

                cursor.execute("""
                    INSERT INTO coaching_sessions
                        (sport_id, coach_id, session_date, start_time, end_time, status, session_type)
                    VALUES (%s, %s, %s, %s, %s, 'Scheduled', 'practice')
                """, (
                    request_data["sport_id"],
                    request_data["coach_id"],
                    final_date,
                    final_start.isoformat(timespec="minutes"),
                    final_end.isoformat(timespec="minutes"),
                ))
                db.commit()
            return jsonify({"success": True, "message": "Request approved and session created."}), 200
        except Exception as exc:
            db.rollback()
            return jsonify({"success": False, "message": f"Approval failed: {exc}"}), 500
        finally:
            db.close()

    @app.route("/api/admin/extra-session-requests/<int:request_id>/reject", methods=["POST"])
    @role_required("admin")
    def admin_reject_extra_session(request_id):
        data = request.get_json(silent=True) or {}
        admin_notes = data.get("admin_notes")
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """UPDATE extra_session_requests
                       SET status = 'rejected', admin_notes = %s
                       WHERE id = %s AND status = 'pending'""",
                    (admin_notes, request_id)
                )
                if cursor.rowcount != 1:
                    db.rollback()
                    return jsonify({"success": False, "message": "This request is not pending review."}), 409
                db.commit()
            return jsonify({"success": True, "message": "Request rejected."}), 200
        except Exception as exc:
            db.rollback()
            return jsonify({"success": False, "message": f"Rejection failed: {exc}"}), 500
        finally:
            db.close()

    @app.route("/api/admin/attendance", methods=["GET"])
    @role_required("admin")
    def admin_list_attendance():
        session_date = _parse_date(request.args.get("session_date"))
        sport_id = _as_int(request.args.get("sport_id"))
        query = """WITH coach_session_totals AS (
                       SELECT attendance.coach_id, COUNT(DISTINCT attendance.id) AS sessions_taken
                       FROM attendance_sessions attendance
                       JOIN coaching_sessions scheduled
                         ON scheduled.sport_id = attendance.sport_id
                        AND scheduled.session_date = attendance.session_date
                        AND (scheduled.coach_id = attendance.coach_id OR scheduled.coach_id IS NULL)
                        AND scheduled.status <> 'Cancelled'
                       WHERE EXISTS (
                           SELECT 1 FROM attendance_records coach_record
                           WHERE coach_record.session_id = attendance.id
                             AND coach_record.marked_by_role = 'coach'
                       )
                       GROUP BY attendance.coach_id
                   )
                   SELECT
                          r.student_id,
                          u.full_name AS student_name,
                          u.email,
                          a.coach_id,
                          COALESCE(coach_session_totals.sessions_taken, 0) AS coach_sessions_taken,
                          a.sport_id,
                          s.name AS sport_name,
                          c.full_name AS coach_name,
                          a.session_date,
                          r.status
                   FROM attendance_records r
                   JOIN attendance_sessions a
                     ON a.id = r.session_id
                   JOIN users u
                     ON u.id = r.student_id
                   JOIN users c
                     ON c.id = a.coach_id
                   LEFT JOIN coach_session_totals
                     ON coach_session_totals.coach_id = a.coach_id
                   JOIN sports s
                     ON s.id = a.sport_id
                   WHERE u.role = 'student'"""
        conditions = []
        params = []
        if session_date:
            conditions.append("a.session_date = %s")
            params.append(session_date)
        if sport_id is not None:
            conditions.append("a.sport_id = %s")
            params.append(sport_id)
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY a.session_date DESC, s.name, u.full_name"
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(query, tuple(params))
                records = cursor.fetchall()
            for record in records:
                record["session_date"] = str(record["session_date"])
            return jsonify({"success": True, "records": records}), 200
        finally:
            db.close()



def _eligible_students(cursor, sport_id):
    """Students who signed up for a sport."""
    cursor.execute(
        """SELECT u.id, u.full_name, u.email
           FROM student_sports ss
           JOIN users u ON u.id = ss.student_id
           WHERE ss.sport_id = %s AND u.role = 'student' AND u.is_active = TRUE
           ORDER BY u.full_name ASC""",
        (sport_id,),
    )
    return cursor.fetchall()
