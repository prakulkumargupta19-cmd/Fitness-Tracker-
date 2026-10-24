"""Persistent dashboard events and event registration APIs."""

from datetime import datetime

from flask import jsonify, request, session

try:
    from backend.db import get_db
    from backend.auth.decorators import role_required
except ModuleNotFoundError:
    from db import get_db
    from auth.decorators import role_required


ALL_USERS = role_required("admin", "coach", "student")
STAFF = role_required("admin", "coach")


def _clean_row(row):
    if row is None:
        return None
    return {key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in row.items()}


def register_dashboard_event_routes(app):
    @app.route("/api/dashboard/events", methods=["GET", "POST"])
    @ALL_USERS
    def dashboard_events():
        if request.method == "POST":
            if session.get("role") not in {"admin", "coach"}:
                return jsonify(success=False, message="Only admins and coaches can add events."), 403
            data = request.get_json(silent=True) or {}
            title = str(data.get("title") or "").strip()
            description = str(data.get("description") or "").strip()
            venue = str(data.get("venue") or "").strip()
            date_value = str(data.get("event_date") or "").strip()
            if not title or not description or not date_value:
                return jsonify(success=False, message="Title, description and event date are required."), 400
            if len(title) > 180 or len(venue) > 255:
                return jsonify(success=False, message="Title or venue is too long."), 400
            try:
                event_date = datetime.fromisoformat(date_value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return jsonify(success=False, message="Enter a valid event date and time."), 400
            db = get_db()
            try:
                with db.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO dashboard_events (title,description,event_date,venue,created_by) "
                        "VALUES (%s,%s,%s,%s,%s) RETURNING *",
                        (title, description, event_date, venue or None, session.get("user_id")),
                    )
                    event = _clean_row(cursor.fetchone())
                db.commit()
                return jsonify(success=True, data=event), 201
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT e.*, (SELECT COUNT(*) FROM dashboard_event_registrations r "
                    "WHERE r.event_id=e.id) AS registration_count FROM dashboard_events e "
                    "WHERE e.active=TRUE ORDER BY e.event_date ASC, e.id DESC"
                )
                events = cursor.fetchall()
                if session.get("role") in {"admin", "coach"}:
                    for event in events:
                        cursor.execute(
                            "SELECT id,full_name,email,contact_number,registered_at "
                            "FROM dashboard_event_registrations WHERE event_id=%s ORDER BY registered_at DESC",
                            (event["id"],),
                        )
                        event["registrants"] = [_clean_row(row) for row in cursor.fetchall()]
                else:
                    cursor.execute(
                        "SELECT event_id FROM dashboard_event_registrations WHERE student_id=%s",
                        (session.get("user_id"),),
                    )
                    registered_ids = {row["event_id"] for row in cursor.fetchall()}
                    for event in events:
                        event["registered"] = event["id"] in registered_ids
            return jsonify(success=True, data=[_clean_row(event) for event in events])
        finally:
            db.close()

    @app.route("/api/dashboard/events/<int:event_id>", methods=["DELETE"])
    @STAFF
    def delete_dashboard_event(event_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("UPDATE dashboard_events SET active=FALSE WHERE id=%s AND active=TRUE", (event_id,))
                deleted = cursor.rowcount > 0
            db.commit()
            if not deleted:
                return jsonify(success=False, message="Event not found."), 404
            return jsonify(success=True)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @app.route("/api/dashboard/events/<int:event_id>/register", methods=["POST"])
    @role_required("student")
    def register_for_dashboard_event(event_id):
        data = request.get_json(silent=True) or {}
        student_id = session.get("user_id")
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT u.full_name, u.email, u.contact_number FROM users u WHERE u.id=%s AND u.role='student'",
                    (student_id,),
                )
                student = cursor.fetchone()
                if not student:
                    return jsonify(success=False, message="Student account was not found."), 404
                full_name = str(data.get("full_name") or student["full_name"]).strip()
                email = str(data.get("email") or student["email"]).strip()
                contact = str(data.get("contact_number") or student.get("contact_number") or "").strip()
                if not full_name or not email or "@" not in email:
                    return jsonify(success=False, message="A valid name and email are required."), 400
                if len(full_name) > 150 or len(email) > 150 or len(contact) > 30:
                    return jsonify(success=False, message="One or more registration fields are too long."), 400
                cursor.execute("SELECT id FROM dashboard_events WHERE id=%s AND active=TRUE", (event_id,))
                if not cursor.fetchone():
                    db.rollback()
                    return jsonify(success=False, message="Event not found."), 404
                cursor.execute(
                    "INSERT INTO dashboard_event_registrations "
                    "(event_id,student_id,full_name,email,contact_number) VALUES (%s,%s,%s,%s,%s) "
                    "ON CONFLICT (event_id,student_id) DO UPDATE SET full_name=EXCLUDED.full_name, "
                    "email=EXCLUDED.email, contact_number=EXCLUDED.contact_number RETURNING *",
                    (event_id, student_id, full_name, email, contact or None),
                )
                registration = _clean_row(cursor.fetchone())
            db.commit()
            return jsonify(success=True, data=registration), 201
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()