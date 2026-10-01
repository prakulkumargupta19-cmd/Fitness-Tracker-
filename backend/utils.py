"""Utility helpers for backend response handling.

This module centralizes the construction of JSON responses that are
used throughout the code base.  The original code directly constructed
``jsonify({"success": False, ...})`` in many places.  By moving that logic
to a small set of helpers we:

1. Reduce duplication.
2. Make it easier to adjust the response format (e.g. adding timestamps)
   in a single location.
3. Keep the view functions focused on business logic.

Only the :func:`json_response` helper is public; it accepts the data you want
to expose and handles both the HTTP status code and the ``success`` field.
For common use‑cases a short‑hand :func:`error_response` is provided.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import make_response, jsonify

__all__ = ["json_response", "error_response", "success_response"]


def _build_body(success: bool, message: Optional[str] = None, data: Any | None = None) -> Dict[str, Any]:
    """Return a json‑serialisable body.

    Parameters
    ----------
    success:
        Boolean status value.
    message:
        Optional human‑readable message.  ``None`` omits the key.
    data:
        Arbitrary JSON‑serialisable payload.  ``None`` omits the key.
    """

    body: Dict[str, Any] = {"success": success}
    if message is not None:
        body["message"] = message
    if data is not None:
        body["data"] = data
    return body


def json_response(
    success: bool,
    message: Optional[str] = None,
    data: Any | None = None,
    status_code: int = 200,
):
    """Return a Flask :class:`flask.Response` with a JSON body.

    The function mirrors the behaviour of the original code but gives a
    consistent API.  It is intentionally lightweight so that importing it
    has no side effects.
    """

    body = _build_body(success, message, data)
    response = make_response(jsonify(body), status_code)
    return response


def error_response(message: str, status_code: int = 400):
    """Return a JSON error response.

    Parameters
    ----------
    message: str
        Human‑readable error message.
    status_code: int, default ``400``
        HTTP status code to return.
    """

    return json_response(False, message=message, status_code=status_code)


def success_response(message: str | None = None, data: Any | None = None, status_code: int = 200):
    """Return a JSON success response.

    Parameters
    ----------
    message: str | None, default ``None``
        Optional success message.
    data: Any | None, default ``None``
        Payload to return.
    status_code: int, default ``200``
        The HTTP status code.
    """

    return json_response(True, message=message, data=data, status_code=status_code)
