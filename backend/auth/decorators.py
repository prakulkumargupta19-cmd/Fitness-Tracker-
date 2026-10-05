"""Decorator utilities for authentication.

This module contains the two decorators that were previously defined in
``backend.app``:

* :func:`login_required` – ensures the request is authenticated.
* :func:`role_required` – ensures the authenticated user has one of the
  required roles.

The implementations are identical to the original definitions so that
behaviour such as session keys, status codes, CSRF handling and the
``functools.wraps`` wrapper are preserved.

The file purposely does *not* import :mod:`backend.app` or the top‑level
``app`` instance to avoid circular imports.
"""

from functools import wraps

from flask import session, jsonify

try:
    from backend.auth.helpers import get_user_by_id
except ModuleNotFoundError:
    from auth.helpers import get_user_by_id


def login_required(f):
    """Decorator that ensures a request is authenticated.

    The decorated view will return a ``401`` response with a JSON body if
    ``session['user_id']`` is not present.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(success=False, message="Unauthorized — please log in"), 401
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    """Decorator that ensures a request is authenticated **and** the user
    role is in *roles*.

    The first check verifies that the request is authenticated. The user's
    current role is then loaded from the database rather than trusting the
    client session's cached role. A ``403`` response is returned when the
    role is insufficient.
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return jsonify(success=False, message="Unauthorized"), 401

            user = get_user_by_id(user_id)
            if not user:
                session.clear()
                return jsonify(success=False, message="Unauthorized"), 401

            user_role = user["role"]
            session["role"] = user_role
            if user_role in ("coach", "student") and not user.get("is_active", True):
                return jsonify(success=False, message="This account is inactive. Contact an administrator."), 403
            if user_role == "coach" and user.get("coach_status") != "approved":
                return jsonify(
                    success=False,
                    message="Your coach account is not approved for dashboard access.",
                ), 403
            if user_role not in roles:
                return (
                    jsonify(
                        success=False,
                        message="Forbidden — insufficient privileges",
                    ),
                    403,
                )
            return f(*args, **kwargs)

        return decorated

    return decorator
