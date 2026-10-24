"""Persistent announcement APIs for the dashboard announcement cards."""

from flask import jsonify, request, session
from pathlib import Path
import os
from uuid import uuid4
from werkzeug.utils import secure_filename

try:
    from backend.db import get_db
    from backend.auth.decorators import role_required
except ModuleNotFoundError:
    from db import get_db
    from auth.decorators import role_required


ALL_USERS = role_required("admin", "coach", "student")
STAFF = role_required("admin", "coach")
UPLOAD_ROOT = Path(os.getenv("FIT_TRACK_UPLOAD_ROOT", Path(__file__).resolve().parents[2] / "static" / "uploads"))
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def _row(row):
    if row is None:
        return None
    return {key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in row.items()}


def register_announcement_routes(app):
    """Register announcement list/create/delete routes."""

    @app.route("/api/fit-track/announcements", methods=["GET", "POST"])
    @app.route("/api/announcements", methods=["GET", "POST"])
    @ALL_USERS
    def announcements():
        if request.method == "POST":
            if session.get("role") not in {"admin", "coach"}:
                return jsonify(success=False, message="Only admins and coaches can publish announcements."), 403
            data = request.get_json(silent=True) or {}
            title = str(data.get("title") or "").strip()
            message = str(data.get("message") or "").strip()
            if not title or not message:
                return jsonify(success=False, message="title and message are required."), 400
            if len(title) > 180:
                return jsonify(success=False, message="title must be 180 characters or fewer."), 400
            db = get_db()
            try:
                with db.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO announcements (title, message, image_path, created_by) VALUES (%s,%s,%s,%s) RETURNING *",
                        (title, message, data.get("image_path"), session.get("user_id")),
                    )
                    record = _row(cursor.fetchone())
                db.commit()
                return jsonify(success=True, data=record), 201
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM announcements WHERE active=TRUE ORDER BY created_at DESC, id DESC"
                )
                records = cursor.fetchall()
            return jsonify(success=True, data=[_row(record) for record in records])
        finally:
            db.close()

    @app.route("/api/fit-track/announcements/upload", methods=["POST"])
    @STAFF
    def upload_announcement():
        title = (request.form.get("title") or "").strip()
        message = (request.form.get("message") or "").strip()
        if not title or not message:
            return jsonify(success=False, message="title and message are required."), 400
        if len(title) > 180:
            return jsonify(success=False, message="title must be 180 characters or fewer."), 400

        image_path = None
        uploaded = request.files.get("image")
        if uploaded and uploaded.filename:
            filename = secure_filename(uploaded.filename)
            if "." not in filename or filename.rsplit(".", 1)[1].lower() not in IMAGE_EXTENSIONS:
                return jsonify(success=False, message="Unsupported announcement image type."), 400
            extension = filename.rsplit(".", 1)[1].lower()
            target_dir = UPLOAD_ROOT / "announcements"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{uuid4().hex}.{extension}"
            uploaded.save(target)
            image_path = str(Path("uploads") / "announcements" / target.name).replace("\\", "/")

        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO announcements (title, message, image_path, created_by) VALUES (%s,%s,%s,%s) RETURNING *",
                    (title, message, image_path, session.get("user_id")),
                )
                record = _row(cursor.fetchone())
            db.commit()
            return jsonify(success=True, data=record), 201
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @app.route("/api/fit-track/announcements/<int:announcement_id>", methods=["DELETE"])
    @app.route("/api/announcements/<int:announcement_id>", methods=["DELETE"])
    @STAFF
    def delete_announcement(announcement_id):
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "UPDATE announcements SET active=FALSE WHERE id=%s AND active=TRUE",
                    (announcement_id,),
                )
                deleted = cursor.rowcount > 0
            db.commit()
            if not deleted:
                return jsonify(success=False, message="Announcement not found."), 404
            return jsonify(success=True)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()