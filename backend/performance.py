"""Database-backed assessment, training, goal, and feedback APIs."""

from flask import jsonify, request, session

try:
    from backend.db import get_db
    from backend.auth.decorators import role_required
except ModuleNotFoundError:
    from db import get_db
    from auth.decorators import role_required


RESOURCES = {
    "assessments": {
        "table": "physical_assessments",
        "fields": ("assessment_date", "speed", "strength", "endurance", "agility", "flexibility", "reaction_time", "overall_score", "notes"),
        "required": ("assessment_date",),
    },
    "training-sessions": {
        "table": "training_sessions",
        "fields": ("sport_id", "session_date", "training_type", "duration_minutes", "description", "performance_notes"),
        "required": ("sport_id", "session_date", "training_type", "duration_minutes"),
    },
    "goals": {
        "table": "goals",
        "fields": ("title", "description", "target_value", "current_value", "start_date", "target_date", "status"),
        "required": ("title",),
    },
    "feedback": {
        "table": "coach_feedback",
        "fields": ("feedback", "rating"),
        "required": ("feedback",),
    },
}


def _assigned_student(cursor, coach_id, student_id, sport_id=None):
    sport_filter = " AND ss.sport_id=%s" if sport_id is not None else ""
    params = [student_id, coach_id]
    if sport_id is not None:
        params.append(sport_id)
    cursor.execute(f"""SELECT 1 FROM student_sports ss
        JOIN users student ON student.id=ss.student_id
        JOIN coach_sports cs ON cs.sport_id=ss.sport_id
        JOIN users coach ON coach.id=cs.coach_id
        WHERE ss.student_id=%s AND cs.coach_id=%s AND student.role='student'
          AND student.is_verified=TRUE AND coach.role='coach'
          AND coach.coach_status='approved' AND coach.is_active=TRUE{sport_filter}""", tuple(params))
    return cursor.fetchone() is not None


def _json_rows(rows):
    for row in rows:
        for key, value in row.items():
            if value is not None and hasattr(value, "isoformat"):
                row[key] = value.isoformat()
            elif value is not None and value.__class__.__name__ == "Decimal":
                row[key] = float(value)
    return rows


def register_performance_routes(app):
    for resource, spec in RESOURCES.items():
        table = spec["table"]
        fields = spec["fields"]
        required = spec["required"]

        def list_records(resource=resource, table=table, fields=fields):
            user_id = session.get("user_id")
            role = session.get("role")
            db = get_db()
            try:
                with db.cursor() as cursor:
                    if role == "student":
                        if resource == "feedback":
                            cursor.execute(
                                """SELECT feedback.*, coach.full_name AS coach_name,
                                          coach.specialization AS coach_specialization
                                   FROM coach_feedback feedback
                                   LEFT JOIN users coach ON coach.id = feedback.coach_id
                                   WHERE feedback.student_id = %s
                                   ORDER BY feedback.created_at DESC, feedback.id DESC""",
                                (user_id,),
                            )
                        else:
                            cursor.execute(f"SELECT * FROM {table} WHERE student_id = %s ORDER BY created_at DESC, id DESC", (user_id,))
                    elif role == "coach":
                        sport_filter = " AND ss.sport_id = r.sport_id" if resource == "training-sessions" else ""
                        cursor.execute(
                            f"""SELECT r.* FROM {table} r
                                WHERE r.coach_id = %s
                                  AND EXISTS (
                                    SELECT 1 FROM student_sports ss
                                    JOIN coach_sports cs ON cs.sport_id=ss.sport_id
                                    JOIN users st ON st.id=ss.student_id
                                    JOIN users ch ON ch.id=cs.coach_id
                                    WHERE ss.student_id=r.student_id AND cs.coach_id=%s
                                      AND st.is_verified=TRUE AND ch.coach_status='approved'
                                      AND ch.is_active=TRUE
                                      {sport_filter}
                                  ) ORDER BY r.created_at DESC""",
                            (user_id, user_id),
                        )
                    else:
                        cursor.execute(f"SELECT * FROM {table} ORDER BY created_at DESC")
                    records = _json_rows(cursor.fetchall())
                return jsonify({"success": True, "data": records}), 200
            finally:
                db.close()

        def create_record(resource=resource, table=table, fields=fields, required=required):
            if session.get("role") != "coach":
                return jsonify({"success": False, "message": "Coach access required."}), 403
            data = request.get_json(silent=True) or {}
            student_id = data.get("student_id")
            sport_id = data.get("sport_id") if resource == "training-sessions" else None
            if not student_id or any(data.get(key) in (None, "") for key in required):
                return jsonify({"success": False, "message": "Required record fields are missing."}), 400
            if resource == "feedback":
                feedback_text = str(data.get("feedback") or "").strip()
                if not feedback_text:
                    return jsonify({"success": False, "message": "Write feedback before saving."}), 400
                if len(feedback_text) > 2000:
                    return jsonify({"success": False, "message": "Feedback must be 2,000 characters or fewer."}), 400
                raw_rating = data.get("rating")
                if raw_rating not in (None, ""):
                    try:
                        rating = int(raw_rating)
                    except (TypeError, ValueError):
                        return jsonify({"success": False, "message": "Choose a whole-number rating from 1 to 5."}), 400
                    if rating < 1 or rating > 5:
                        return jsonify({"success": False, "message": "Choose a rating from 1 to 5."}), 400
                else:
                    rating = None
            db = get_db()
            try:
                with db.cursor() as cursor:
                    if not _assigned_student(cursor, session.get("user_id"), student_id, sport_id):
                        return jsonify({"success": False, "message": "Student is not assigned to this coach and sport."}), 403
                    values = (
                        {"feedback": feedback_text, "rating": rating}
                        if resource == "feedback"
                        else {key: data[key] for key in fields if key in data}
                    )
                    columns = ["student_id", "coach_id", *values]
                    params = [student_id, session.get("user_id"), *values.values()]
                    placeholders = ", ".join(["%s"] * len(columns))
                    cursor.execute(
                        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING id",
                        tuple(params),
                    )
                    record_id = cursor.fetchone()["id"]
                db.commit()
                return jsonify({"success": True, "id": record_id}), 201
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        def get_record(record_id, table=table, resource=resource):
            user_id = session.get("user_id")
            role = session.get("role")
            db = get_db()
            try:
                with db.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (record_id,))
                    record = cursor.fetchone()
                    if not record:
                        return jsonify({"success": False, "message": "Record not found."}), 404
                    allowed = role == "admin" or (role == "student" and record["student_id"] == user_id)
                    if role == "coach" and record["coach_id"] == user_id:
                        sport_id = record.get("sport_id") if resource == "training-sessions" else None
                        allowed = _assigned_student(cursor, user_id, record["student_id"], sport_id)
                    if not allowed:
                        return jsonify({"success": False, "message": "Forbidden."}), 403
                return jsonify({"success": True, "data": _json_rows([record])[0]}), 200
            finally:
                db.close()

        def update_record(record_id, table=table, fields=fields, resource=resource):
            if session.get("role") != "coach":
                return jsonify({"success": False, "message": "Coach access required."}), 403
            data = request.get_json(silent=True) or {}
            db = get_db()
            try:
                with db.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (record_id,))
                    record = cursor.fetchone()
                    if not record:
                        return jsonify({"success": False, "message": "Record not found."}), 404
                    if record["coach_id"] != session.get("user_id"):
                        return jsonify({"success": False, "message": "Forbidden."}), 403
                    sport_id = data.get("sport_id", record.get("sport_id")) if resource == "training-sessions" else None
                    if not _assigned_student(cursor, session.get("user_id"), record["student_id"], sport_id):
                        return jsonify({"success": False, "message": "Student is not assigned to this coach and sport."}), 403
                    values = {key: data[key] for key in fields if key in data}
                    if not values:
                        return jsonify({"success": False, "message": "No editable fields supplied."}), 400
                    assignments = ", ".join(f"{key} = %s" for key in values)
                    cursor.execute(f"UPDATE {table} SET {assignments} WHERE id = %s", (*values.values(), record_id))
                db.commit()
                return jsonify({"success": True}), 200
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        def delete_record(record_id, table=table):
            if session.get("role") != "coach":
                return jsonify({"success": False, "message": "Coach access required."}), 403
            db = get_db()
            try:
                with db.cursor() as cursor:
                    cursor.execute(
                        f"SELECT * FROM {table} WHERE id = %s AND coach_id = %s",
                        (record_id, session.get("user_id")),
                    )
                    record = cursor.fetchone()
                    if not record:
                        return jsonify({"success": False, "message": "Record not found or forbidden."}), 404
                    sport_id = record.get("sport_id") if table == "training_sessions" else None
                    if not _assigned_student(cursor, session.get("user_id"), record["student_id"], sport_id):
                        return jsonify({"success": False, "message": "Student is no longer assigned to this coach."}), 403
                    cursor.execute(f"DELETE FROM {table} WHERE id = %s", (record_id,))
                db.commit()
                return jsonify({"success": True}), 200
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        route = f"/api/{resource}"
        endpoint = resource.replace("-", "_")
        app.add_url_rule(route, f"{endpoint}_list", role_required("student", "coach", "admin")(list_records), methods=["GET"])
        app.add_url_rule(route, f"{endpoint}_create", role_required("student", "coach", "admin")(create_record), methods=["POST"])
        app.add_url_rule(f"{route}/<int:record_id>", f"{endpoint}_get", role_required("student", "coach", "admin")(get_record), methods=["GET"])
        app.add_url_rule(f"{route}/<int:record_id>", f"{endpoint}_update", role_required("student", "coach", "admin")(update_record), methods=["PUT"])
        app.add_url_rule(f"{route}/<int:record_id>", f"{endpoint}_delete", role_required("student", "coach", "admin")(delete_record), methods=["DELETE"])
