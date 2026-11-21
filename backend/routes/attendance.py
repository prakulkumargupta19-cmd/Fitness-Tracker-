from flask import Blueprint, jsonify, request, session
try:
    from backend.db import get_db
except ModuleNotFoundError:
    from db import get_db
try:
    from backend.auth.decorators import login_required, role_required
except ModuleNotFoundError:
    from auth.decorators import login_required, role_required

attendance_bp = Blueprint('attendance', __name__)

# Helper functions
ATTENDANCE_STATUSES = ("present", "absent", "late", "excused")

def _parse_date(value):
    from datetime import datetime
    text = str(value or "").strip()
    if not text: return None
    try: return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError: return None

def _as_int(value):
    try: return int(value)
    except (TypeError, ValueError): return None

def _coach_owns_sport(cursor, coach_id, sport_id):
    cursor.execute("SELECT 1 FROM coach_sports WHERE coach_id = %s AND sport_id = %s", (coach_id, sport_id))
    return cursor.fetchone() is not None

# Feature: Attendance History
@attendance_bp.route("/history", methods=["GET"])
@role_required("coach", "admin")
def get_attendance_history():
    sport_id = _as_int(request.args.get("sport_id"))
    session_date = _parse_date(request.args.get("session_date"))
    
    db = get_db()
    try:
        with db.cursor() as cursor:
            query = """
                SELECT r.session_id, r.student_id, u.full_name AS student_name, r.status, s.session_date
                FROM attendance_records r
                JOIN attendance_sessions s ON r.session_id = s.id
                JOIN users u ON r.student_id = u.id
                WHERE 1=1
            """
            params = []
            if sport_id:
                query += " AND s.sport_id = %s"
                params.append(sport_id)
            if session_date:
                query += " AND s.session_date = %s"
                params.append(session_date)
            
            cursor.execute(query, tuple(params))
            records = cursor.fetchall()
            
            for rec in records:
                if 'session_date' in rec:
                    rec['session_date'] = str(rec['session_date'])
                    
            return jsonify(success=True, records=records), 200
    finally:
        db.close()

# Feature: Edit Attendance
@attendance_bp.route("/record/<int:session_id>/<int:student_id>", methods=["PATCH"])
@role_required("coach", "admin")
def update_attendance_record(session_id, student_id):
    data = request.get_json()
    new_status = data.get("status")
    
    if new_status not in ATTENDANCE_STATUSES:
        return jsonify(success=False, message="Invalid status"), 400
    
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("UPDATE attendance_records SET status = %s WHERE session_id = %s AND student_id = %s", (new_status, session_id, student_id))
            db.commit()
            return jsonify(success=True, message="Record updated"), 200
    finally:
        db.close()

# Feature: Delete Attendance
@attendance_bp.route("/record/<int:session_id>/<int:student_id>", methods=["DELETE"])
@role_required("coach", "admin")
def delete_attendance_record(session_id, student_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM attendance_records WHERE session_id = %s AND student_id = %s", (session_id, student_id))
            db.commit()
            return jsonify(success=True, message="Record deleted"), 200
    finally:
        db.close()

# Coach routes
@attendance_bp.route("/api/coach/sports", methods=["GET"])
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

@attendance_bp.route("/api/coach/attendance/students", methods=["GET"])
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
                     AND u.is_active = TRUE
                   ORDER BY u.full_name""",
                (sport_id,),
            )
            students = cursor.fetchall()
        return jsonify({"success": True, "students": students}), 200
    finally:
        db.close()

 

@attendance_bp.route("/api/coach/attendance/sessions", methods=["GET"])
@role_required("coach")
def coach_get_attendance_sessions():
    sport_id = _as_int(request.args.get("sport_id"))
    db = get_db()
    try:
        with db.cursor() as cursor:
            if not _coach_owns_sport(cursor, session.get("user_id"), sport_id):
                return jsonify({"success": False, "message": "Forbidden."}), 403
            cursor.execute(
                "SELECT id, session_date FROM attendance_sessions WHERE coach_id = %s AND sport_id = %s ORDER BY session_date DESC",
                (session.get("user_id"), sport_id),
            )
            sessions = cursor.fetchall()
            for s in sessions:
                s["session_date"] = str(s["session_date"])
            return jsonify({"success": True, "sessions": sessions}), 200
    finally:
        db.close()

@attendance_bp.route("/coach/records", methods=["GET"])
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

@attendance_bp.route("/coach/records", methods=["POST"])
@role_required("coach")
def coach_save_attendance():
    coach_id = session.get("user_id")
    data = request.get_json(silent=True) or {}
    sport_id = _as_int(data.get("sport_id"))
    session_date = _parse_date(data.get("session_date"))
    records = data.get("records")

    if sport_id is None or session_date is None or not isinstance(records, list) or not records:
        return jsonify({"success": False, "message": "A valid sport, date, and attendance list are required."}), 400
    
    db = get_db()
    try:
        with db.cursor() as cursor:
            if not _coach_owns_sport(cursor, coach_id, sport_id):
                return jsonify({"success": False, "message": "Forbidden."}), 403
            
            cursor.execute("SELECT id FROM attendance_sessions WHERE coach_id = %s AND sport_id = %s AND session_date = %s", (coach_id, sport_id, session_date))
            row = cursor.fetchone()
            if row:
                session_id = row["id"]
            else:
                cursor.execute("INSERT INTO attendance_sessions (coach_id, sport_id, session_date) VALUES (%s, %s, %s) RETURNING id", (coach_id, sport_id, session_date))
                session_id = cursor.fetchone()["id"]
            
            for item in records:
                student_id = _as_int(item.get("student_id"))
                status = str(item.get("status") or "").strip().lower()
                if student_id is None or status not in ATTENDANCE_STATUSES:
                    continue
                
                cursor.execute("""
                    INSERT INTO attendance_records (session_id, student_id, status)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (session_id, student_id)
                    DO UPDATE SET status = EXCLUDED.status
                """, (session_id, student_id, status))
            
            db.commit()
            return jsonify({"success": True, "message": "Attendance saved successfully."}), 200
    except Exception as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"Attendance save failed: {exc}"}), 500
    finally:
        db.close()


# Admin routes
@attendance_bp.route("/api/admin/attendance", methods=["GET"])
@role_required("admin")
def admin_list_attendance():
    session_date = _parse_date(request.args.get("session_date"))
    sport_id = _as_int(request.args.get("sport_id"))
    query = """SELECT
                      r.student_id, r.session_id,
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

@attendance_bp.route("/api/admin/students/<int:student_id>/attendance", methods=["GET"])
@role_required("admin")
def admin_student_attendance(student_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT s.session_date, r.status
                   FROM attendance_records r
                   JOIN attendance_sessions s ON s.id = r.session_id
                   WHERE r.student_id = %s
                   ORDER BY s.session_date DESC""",
                (student_id,),
            )
            records = cursor.fetchall()
            for record in records:
                record["session_date"] = str(record["session_date"])
            return jsonify({"success": True, "records": records}), 200
    finally:
        db.close()

# Student routes
@attendance_bp.route("/api/student/attendance", methods=["GET"])
@role_required("student")
def student_get_attendance():
    student_id = session.get("user_id")
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT s.session_date, r.status
                   FROM attendance_records r
                   JOIN attendance_sessions s ON s.id = r.session_id
                   WHERE r.student_id = %s
                   ORDER BY s.session_date DESC""",
                (student_id,),
            )
            records = cursor.fetchall()
            for record in records:
                record["session_date"] = str(record["session_date"])
            return jsonify({"success": True, "records": records}), 200
    finally:
        db.close()

