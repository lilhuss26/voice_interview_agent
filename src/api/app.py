from flask import Flask
from src.api.routers.interview import interview_bp
from src.api.routers.report import report_bp
from src.api.sockets.interview import socketio


def create_app():
    app = Flask(__name__)
    app.register_blueprint(interview_bp, url_prefix="/api/interview")
    app.register_blueprint(report_bp, url_prefix="/api/interview")
    socketio.init_app(app, cors_allowed_origins="*")
    return app
