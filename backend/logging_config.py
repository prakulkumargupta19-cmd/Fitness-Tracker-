"""Safe structured logging for the Flask application."""

import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format application log records as JSON without serializing request data."""

    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event_data = getattr(record, "event_data", {})
        if isinstance(event_data, dict):
            for key in (
                "request_id",
                "route",
                "method",
                "status",
                "duration_ms",
                "user_id",
                "error_type",
            ):
                if key in event_data:
                    payload[key] = event_data[key]
        return json.dumps(payload, default=str)


def configure_logging(app):
    """Configure stdout logging suitable for local development and Vercel."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not any(getattr(item, "_fitness_json_handler", False) for item in root_logger.handlers):
        handler._fitness_json_handler = True
        root_logger.addHandler(handler)

    app.logger.handlers.clear()
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = True
