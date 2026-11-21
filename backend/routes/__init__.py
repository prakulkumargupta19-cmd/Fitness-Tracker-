from .chat import chat_bp
from .attendance import attendance_bp

def register_blueprints(app):
    app.register_blueprint(chat_bp)
    app.register_blueprint(attendance_bp)
