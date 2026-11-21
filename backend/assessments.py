"""Sport-specific assessment fields and coach session assessments.

Workflow:
    * Admin defines dynamic assessment fields when creating/editing a sport
      (removed fields are soft-deactivated so submitted data is never lost).
    * Coach marks attendance per scheduled class; for ``present``/``late``
      students every active field must be scored 0-10 plus feedback, for
      ``absent``/``excused`` no assessment form is stored.
    * Overall score is the automatic average of the field scores.
    * Coach can edit their own submissions; admin can view, edit and delete.
"""

from datetime import datetime

from flask import jsonify, request, session

try:
    from backend.db import get_db
except ModuleNotFoundError:
    from db import get_db

try:
    from backend.auth.decorators import login_required, role_required
except ModuleNotFoundError:
    from auth.decorators import login_required, role_required


ASSESSMENT_STATUSES = ("present", "absent", "late", "excused")
REQUIRES_FORM = ("present", "late")
FIELD_TYPES = ("rating", "number", "text")


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_fields(raw_fields):
    """Validate and normalize assessment field definitions from admin payload."""
    if raw_fields is None:
        return []
    if not isinstance(raw_fields, list):
        raise ValueError("assessment_fields must be a list.")

    normalized = []
    seen_keys = set()
    for index, item in enumerate(raw_fields):
        if not isinstance(item, dict):
            raise ValueError("Each assessment field must be an object.")
        field_key = str(item.get("field_key") or "").strip().lower().replace(" ", "_")
        field_label = str(item.get("field_label") or "").strip()
        field_type = str(item.get("field_type") or "rating").strip().lower()
        if not field_key or not field_label:
            raise ValueError("Each assessment field needs field_key and field_label.")
        if field_type not in FIELD_TYPES:
            raise ValueError("Unsupported field_type '%s'." % field_type)
        if field_key in seen_keys:
            raise ValueError("Duplicate field_key '%s'." % field_key)
        seen_keys.add(field_key)
        try:
            max_score = float(item.get("max_score", item.get("max_value", 10)))
        except (TypeError, ValueError):
            raise ValueError("max_score for '%s' must be a number." % field_key)
        if max_score <= 0:
            raise ValueError("max_score for '%s' must be greater than 0." % field_key)
        sort_order = _as_int(item.get("sort_order", index)) or index
        normalized.append({
            "field_key": field_key,
            "field_label": field_label,
            "field_type": field_type,
            "max_score": max_score,
            "sort_order": sort_order,
        })
    return normalized


def _validate_scores(status, scores, fields):
    """Validate scores for a record. Returns (numeric_scores, overall, error)."""
    required_keys = [f["field_key"] for f in fields]
    max_by_key = {f["field_key"]: f["max_score"] for f in fields}
    if status not in REQUIRES_FORM:
        return {}, None, None
    missing = [k for k in required_keys if k not in scores]
    if missing:
        return None, None, (
            "Complete every assessment field before saving (missing: %s)."
            % ", ".join(missing)
        )
    numeric = {}
    for key in required_keys:
        try:
            value = float(scores.get(key))
        except (TypeError, ValueError):
            return None, None, "Score for '%s' must be a number." % key
        max_score = max_by_key.get(key, 10)
        if value < 0 or value > max_score:
            return None, None, (
                "Score for '%s' must be between 0 and %s." % (key, max_score)
            )
        numeric[key] = value
    overall = round(sum(numeric.values()) / len(numeric), 2) if numeric else None
    return numeric, overall, None


def _replace_field_set(cursor, sport_id, fields):
    """Soft-deactivate removed fields, upsert kept/added ones. No data loss."""
    incoming_keys = {f["field_key"] for f in fields}
    cursor.execute(
        "SELECT id, field_key FROM sport_assessment_fields "
        "WHERE sport_id = %s AND is_active = TRUE",
        (sport_id,),
    )
    for row in cursor.fetchall():
        if row["field_key"] not in incoming_keys:
            cursor.execute(
                "UPDATE sport_assessment_fields SET is_active = FALSE WHERE id = %s",
                (row["id"],),
            )
    for field in fields:
        cursor.execute(
            """UPDATE sport_assessment_fields
               SET field_label = %s, field_type = %s, max_score = %s,
                   sort_order = %s, is_active = TRUE
               WHERE sport_id = %s AND field_key = %s""",
            (
                field["field_label"],
                field["field_type"],
                field["max_score"],
                field["sort_order"],
                sport_id,
                field["field_key"],
            ),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                """INSERT INTO sport_assessment_fields
                   (sport_id, field_key, field_label, field_type, max_score, sort_order, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, TRUE)""",
                (
                    sport_id,
                    field["field_key"],
                    field["field_label"],
                    field["field_type"],
                    field["max_score"],
                    field["sort_order"],
                ),
            )


def _fetch_active_fields(cursor, sport_id):
    cursor.execute(
        """SELECT id, sport_id, field_key, field_label, field_type, max_score, sort_order
           FROM sport_assessment_fields
           WHERE sport_id = %s AND is_active = TRUE
           ORDER BY sort_order ASC, id ASC""",
        (sport_id,),
    )
    rows = cursor.fetchall() or []
    for row in rows:
        if row.get("max_score") is not None:
            row["max_score"] = float(row["max_score"])
    return rows


def _coach_owns_sport(cursor, coach_id, sport_id):
    cursor.execute(
        """SELECT 1
           FROM coach_sports cs
           JOIN users c ON c.id = cs.coach_id
           WHERE cs.coach_id = %s AND cs.sport_id = %s
             AND c.role = 'coach' AND c.coach_status = 'approved'
             AND c.is_active = TRUE""",
        (coach_id, sport_id),
    )
    return cursor.fetchone() is not None


def sync_sport_assessment_fields(cursor, sport_id, raw_fields):
    """Public helper used by admin sport create/update handlers."""
    fields = _normalize_fields(raw_fields)
    _replace_field_set(cursor, sport_id, fields)
    return fields


def register_assessment_routes(app):
    """Register sport-assessment APIs. Does not own /api/assessments."""

    @app.route("/api/admin/sports/<int:sport_id>/assessment-fields", methods=["GET"])
    @role_required("admin")
    def admin_get_assessment_fields(sport_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT id, name FROM sports WHERE id = %s", (sport_id,))
                sport = cursor.fetchone()
                if not sport:
                    return jsonify({"success": False, "message": "Sport not found."}), 404
                fields = _fetch_active_fields(cursor, sport_id)
            return jsonify({"success": True, "sport": sport, "fields": fields}), 200
        except Exception as exc:
            return jsonify({
                "success": False,
                "message": (
                    "Assessment fields are unavailable. Apply the sport assessment "
                    "schema migration first. (%s)" % exc
                ),
            }), 503
        finally:
            db.close()

    @app.route("/api/admin/sports/<int:sport_id>/assessment-fields", methods=["PUT", "PATCH"])
    @role_required("admin")
    def admin_put_assessment_fields(sport_id):
        data = request.get_json(silent=True) or {}
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT id, name FROM sports WHERE id = %s", (sport_id,))
                sport = cursor.fetchone()
                if not sport:
                    return jsonify({"success": False, "message": "Sport not found."}), 404
                try:
                    fields = sync_sport_assessment_fields(
                        cursor, sport_id, data.get("assessment_fields", data.get("fields"))
                    )
                except ValueError as exc:
                    return jsonify({"success": False, "message": str(exc)}), 400
                db.commit()
                saved = _fetch_active_fields(cursor, sport_id)
            return jsonify({
                "success": True,
                "message": "Assessment fields updated.",
                "fields": saved or fields,
            }), 200
        except Exception as exc:
            db.rollback()
            return jsonify({"success": False, "message": str(exc)}), 500
        finally:
            db.close()

    @app.route("/api/coach/sports/<int:sport_id>/assessment-fields", methods=["GET"])
    @role_required("coach")
    def coach_get_assessment_fields(sport_id):
        coach_id = session.get("user_id")
        db = get_db()
        try:
            with db.cursor() as cursor:
                if not _coach_owns_sport(cursor, coach_id, sport_id):
                    return jsonify({
                        "success": False,
                        "message": "This sport is not assigned to you.",
                    }), 403
                fields = _fetch_active_fields(cursor, sport_id)
            return jsonify({"success": True, "fields": fields}), 200
        except Exception as exc:
            return jsonify({
                "success": False,
                "message": (
                    "Assessment fields are unavailable. Apply the sport assessment "
                    "schema migration first. (%s)" % exc
                ),
            }), 503
        finally:
            db.close()

    @app.route("/api/coach/sport-assessments", methods=["POST"])
    @role_required("coach")
    def coach_save_sport_assessments():
        data = request.get_json(silent=True) or {}
        sport_id = _as_int(data.get("sport_id"))
        session_date = str(data.get("session_date") or "").strip()
        assessments = data.get("assessments")
        if sport_id is None or not session_date:
            return jsonify({
                "success": False,
                "message": "sport_id and session_date are required.",
            }), 400
        if not isinstance(assessments, list) or not assessments:
            return jsonify({
                "success": False,
                "message": "assessments must be a non-empty list.",
            }), 400
        try:
            datetime.strptime(session_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "success": False,
                "message": "session_date must be YYYY-MM-DD.",
            }), 400

        coach_id = session.get("user_id")
        db = get_db()
        try:
            with db.cursor() as cursor:
                if not _coach_owns_sport(cursor, coach_id, sport_id):
                    return jsonify({
                        "success": False,
                        "message": "This sport is not assigned to you.",
                    }), 403
                fields = _fetch_active_fields(cursor, sport_id)
                saved_ids = []
                for entry in assessments:
                    if not isinstance(entry, dict):
                        return jsonify({
                            "success": False,
                            "message": "Each assessment entry must be an object.",
                        }), 400
                    student_id = _as_int(entry.get("student_id"))
                    status = str(
                        entry.get("attendance_status") or entry.get("status") or "present"
                    ).strip().lower()
                    if student_id is None:
                        return jsonify({
                            "success": False,
                            "message": "student_id is required for each assessment.",
                        }), 400
                    if status not in ASSESSMENT_STATUSES:
                        return jsonify({
                            "success": False,
                            "message": "Invalid attendance_status '%s'." % status,
                        }), 400
                    cursor.execute(
                        """SELECT 1 FROM student_sports ss
                           JOIN users u ON u.id = ss.student_id
                           WHERE ss.student_id = %s AND ss.sport_id = %s
                             AND u.role = 'student' AND u.is_verified = TRUE AND u.is_active = TRUE""",
                        (student_id, sport_id),
                    )
                    if cursor.fetchone() is None:
                        return jsonify({
                            "success": False,
                            "message": (
                                "Student %s is not enrolled in this sport." % student_id
                            ),
                        }), 400

                    scores = entry.get("values") or entry.get("scores") or {}
                    if not isinstance(scores, dict):
                        return jsonify({
                            "success": False,
                            "message": "values must be an object of field scores.",
                        }), 400
                    numeric, overall, error = _validate_scores(status, scores, fields)
                    if error:
                        return jsonify({"success": False, "message": error}), 400

                    remarks = entry.get("remarks") or entry.get("coach_feedback") or None
                    cursor.execute(
                        """INSERT INTO sport_student_assessments
                              (student_id, sport_id, coach_id, session_date,
                               attendance_status, general_remarks, overall_score)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (student_id, sport_id, session_date)
                           DO UPDATE SET
                              coach_id = EXCLUDED.coach_id,
                              attendance_status = EXCLUDED.attendance_status,
                              general_remarks = EXCLUDED.general_remarks,
                              overall_score = EXCLUDED.overall_score,
                              updated_at = CURRENT_TIMESTAMP
                           RETURNING id""",
                        (
                            student_id,
                            sport_id,
                            coach_id,
                            session_date,
                            status,
                            remarks,
                            overall,
                        ),
                    )
                    assessment_id = cursor.fetchone()["id"]
                    cursor.execute(
                        "DELETE FROM sport_student_assessment_values WHERE assessment_id = %s",
                        (assessment_id,),
                    )
                    for field_key, score_value in numeric.items():
                        cursor.execute(
                            """INSERT INTO sport_student_assessment_values
                                  (assessment_id, field_key, score_value)
                               VALUES (%s, %s, %s)""",
                            (assessment_id, field_key, score_value),
                        )
                    saved_ids.append(assessment_id)
                db.commit()
            return jsonify({
                "success": True,
                "message": "Sport assessments saved.",
                "assessment_ids": saved_ids,
            }), 201
        except Exception as exc:
            db.rollback()
            return jsonify({
                "success": False,
                "message": (
                    "Could not save sport assessments. Ensure the assessment "
                    "schema migration has been applied. (%s)" % exc
                ),
            }), 500
        finally:
            db.close()
