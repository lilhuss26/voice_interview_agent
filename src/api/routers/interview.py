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

    # Clamp the requested question count to a safe range; default to 5 on missing/invalid.
    try:
        num_questions = int(request.form.get("num_questions", 5))
    except (TypeError, ValueError):
        num_questions = 5
    num_questions = max(3, min(15, num_questions))

    result = start_interview(pdf, job_description, num_questions)

    return jsonify(StartInterviewResponse().dump(result)), 200
