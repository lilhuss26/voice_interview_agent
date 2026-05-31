from flask import Blueprint, jsonify
from src.api.session_store import session_store
from src.api.DTOs import ReportResponse

report_bp = Blueprint("report", __name__)


@report_bp.route("/<session_id>/report", methods=["GET"])
def get_report(session_id):
    session = session_store.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404

    state = session["graph"].get_state(session["config"]).values
    result = {
        "final_report": state.get("final_report"),
        "coaching_notes": state.get("coaching_notes"),
    }
    return jsonify(ReportResponse().dump(result)), 200
