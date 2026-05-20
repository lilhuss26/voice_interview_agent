from flask import Blueprint, request, jsonify
from src.api.DTOs import StartInterviewResponse
from src.api.services.interview import start_interview

interview_bp = Blueprint("interview", __name__)


@interview_bp.route("/start", methods=["POST"])
def start_interview_route():
    pdf = request.files.get("resume")
    job_description = request.form.get("job_description")

    if not pdf or not job_description:
        return jsonify({"error": "resume and job_description are required"}), 400

    result = start_interview(pdf, job_description)

    return jsonify(StartInterviewResponse().dump(result)), 200
