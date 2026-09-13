"""Common authentication utilities.

This module contains the CSRF validation logic that was previously
implemented directly in :mod:`backend.app`.  The logic is extracted to
avoid duplication and to keep the main application module focused on
routing and configuration.

The module intentionally does **not** import :mod:`backend.app` or the
top‑level :mod:`app` wrapper to prevent circular imports.
"""

from flask import request, session, jsonify
import secrets

# Exempt paths for CSRF validation – identical to the original set in
# ``backend.app``.
CSRF_EXEMPT_PATHS = {
    "/api/csrf-token",
    "/api/register",
    "/api/admin-signup",
    "/api/account-verification/send",
    "/api/account-verification/resend",
    "/api/account-verification/verify",
    "/api/admin-signup/resend-otp",
    "/api/admin-signup/verify-otp",
    "/api/login",
    "/api/admin-login",
    "/api/admin-login/verify-otp",
    "/api/admin-login/resend-otp",
    "/api/admin/coach-approve",
    "/api/admin/coach-reject",
    "/api/forgot-password",
    "/api/forgot-password/resend-otp",
    "/api/forgot-password/verify-otp",
    "/api/verify-otp",
    "/api/verify-otp/resend",
    "/api/reset-password",
}


def validate_csrf_token():
    """Validate CSRF token for non‑GET API requests.

    The function mirrors the original implementation in
    :mod:`backend.app`.  It returns ``None`` to allow the request to
    proceed or a Flask response object with a 403 status code when the
    token is missing or invalid.
    """
    # Skip CSRF checks for safe methods or non‑API routes.
    if request.method in {"GET", "HEAD", "OPTIONS"} or not request.path.startswith("/api/"):
        return None
    # Skip exempt paths.
    if request.path in CSRF_EXEMPT_PATHS:
        return None
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        return jsonify(success=False, message="Missing or invalid CSRF token."), 403
    return None
