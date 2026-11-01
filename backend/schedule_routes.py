"""Compatibility redirects for the canonical, role-scoped schedule API."""

from flask import redirect


def register_schedule_routes(app):
    """Keep legacy URLs working without retaining the old unscoped handlers."""

    @app.route("/api/schedule", methods=["GET", "POST"])
    def legacy_schedule_collection():
        return redirect("/api/fit-track/schedule", code=307)

    @app.route("/api/schedule/<int:session_id>", methods=["PUT", "PATCH", "DELETE"])
    def legacy_schedule_item(session_id):
        return redirect(f"/api/fit-track/schedule/{session_id}", code=307)

    @app.route("/api/schedule/<int:session_id>/delete", methods=["POST"])
    def legacy_schedule_delete(session_id):
        return redirect(f"/api/fit-track/schedule/{session_id}/delete", code=307)
