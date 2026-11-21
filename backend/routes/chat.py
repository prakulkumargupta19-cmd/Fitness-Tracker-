from flask import Blueprint, jsonify, request, session
from backend.auth.decorators import role_required
from backend.db import get_db
from backend.core_features import (_commit,_body,_coach_can_access_student,_required,_row,_rows)

chat_bp = Blueprint('chat', __name__)
ALL_USERS = role_required("admin", "coach", "student")

def _can_message_user(cursor, sender_id, sender_role, receiver_id):
    if sender_role == "admin": return True
    cursor.execute("SELECT role FROM users WHERE id = %s", (receiver_id,))
    receiver = cursor.fetchone()
    if not receiver: return False
    if sender_role == "student":
        cursor.execute("SELECT 1 FROM coach_sports cs JOIN student_sports ss ON ss.sport_id = cs.sport_id JOIN users u ON u.id = cs.coach_id WHERE ss.student_id = %s AND cs.coach_id = %s AND u.role = 'coach' AND u.coach_status = 'approved'", (sender_id, receiver_id))
        return receiver["role"] == "coach" and cursor.fetchone() is not None
    if sender_role == "coach":
        return receiver["role"] == "student" and _coach_can_access_student(cursor, sender_id, receiver_id)
    return False

@chat_bp.route("/api/chat/contacts", methods=["GET"])
@ALL_USERS
def fit_track_chat_contacts():
    user_id = session.get("user_id"); role = session.get("role")
    search = f"%{request.args.get('q', '').strip()}%"; db = get_db()
    try:
        with db.cursor() as cursor:
            if role == "student":
                cursor.execute("SELECT u.id, u.full_name, u.role FROM users u WHERE u.role = 'coach' AND u.is_active = TRUE AND u.coach_status = 'approved' AND LOWER(u.full_name) LIKE LOWER(%s) AND EXISTS (SELECT 1 FROM coach_sports cs JOIN student_sports ss ON ss.sport_id = cs.sport_id WHERE cs.coach_id = u.id AND ss.student_id = %s) ORDER BY u.full_name", (search, user_id))
            elif role == "coach":
                cursor.execute("SELECT u.id, u.full_name, u.role FROM users u WHERE u.role = 'student' AND u.is_active = TRUE AND LOWER(u.full_name) LIKE LOWER(%s) AND (EXISTS (SELECT 1 FROM coach_sports cs JOIN student_sports ss ON ss.sport_id = cs.sport_id WHERE cs.coach_id = %s AND ss.student_id = u.id) OR EXISTS (SELECT 1 FROM enrollments e JOIN programmes p ON p.id = e.programme_id WHERE p.coach_id = %s AND e.student_id = u.id)) ORDER BY u.full_name", (search, user_id, user_id))
            else:
                cursor.execute("SELECT id, full_name, role FROM users WHERE is_active = TRUE AND LOWER(full_name) LIKE LOWER(%s) ORDER BY full_name", (search,))
            return jsonify(success=True, data=_rows(cursor.fetchall()))
    finally: db.close()

@chat_bp.route("/api/fit-track/messages", methods=["GET", "POST"])
@chat_bp.route("/api/chat/messages", methods=["GET", "POST"])
@ALL_USERS
def fit_track_messages():
    user_id = session.get("user_id"); db = get_db()
    try:
        with db.cursor() as cursor:
            if request.method == "POST":
                data = _body(); error = _required(data, "receiver_user_id", "message")
                if error: return error
                if not _can_message_user(cursor, user_id, session.get("role"), data["receiver_user_id"]):
                    return jsonify(success=False, message="You may only message an administrator or an assigned coach/athlete."), 403
                cursor.execute("INSERT INTO messages (sender_user_id, receiver_user_id, message) VALUES (%s,%s,%s) RETURNING *", (user_id, data["receiver_user_id"], data["message"].strip()))
                row = _row(cursor.fetchone()); _commit(db)
                return jsonify(success=True, data=row), 201
            other = request.args.get("with_user_id")
            if other:
                if not _can_message_user(cursor, user_id, session.get("role"), other):
                    return jsonify(success=False, message="That conversation is outside your allowed contacts."), 403
                cursor.execute("SELECT m.*, s.full_name AS sender_name, r.full_name AS receiver_name FROM messages m JOIN users s ON s.id=m.sender_user_id JOIN users r ON r.id=m.receiver_user_id WHERE (m.sender_user_id=%s AND m.receiver_user_id=%s) OR (m.sender_user_id=%s AND m.receiver_user_id=%s) ORDER BY m.created_at", (user_id, other, other, user_id))
            else:
                cursor.execute("SELECT m.*, s.full_name AS sender_name, r.full_name AS receiver_name FROM messages m JOIN users s ON s.id=m.sender_user_id JOIN users r ON r.id=m.receiver_user_id WHERE m.sender_user_id=%s OR m.receiver_user_id=%s ORDER BY m.created_at DESC", (user_id, user_id))
            return jsonify(success=True, data=_rows(cursor.fetchall()))
    finally: db.close()
