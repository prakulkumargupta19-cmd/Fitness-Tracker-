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

    The first check verifies that the request is authenticated.  The
    second check ensures the ``session['role']`` value is within the
    allowed *roles* sequence.  A ``403`` response is returned when the role
    is insufficient.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify(success=False, message="Unauthorized"), 401
            if session.get("role") not in roles:
                return jsonify(
                    success=False,
                    message="Forbidden — insufficient privileges",
                ), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
