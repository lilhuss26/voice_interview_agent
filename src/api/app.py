from flask import Flask, jsonify
from src.api.routers.interview import interview_bp

def create_app():
    app = Flask(__name__)
    app.config["APP_NAME"] = "Interview Agent API"
    app.register_blueprint(interview_bp, url_prefix="/api/interview")
    return app

