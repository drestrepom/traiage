import os
import subprocess
from flask import Blueprint, request, jsonify
from fake_library.security import ALLOWED_REPORTS

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/run_report", methods=["POST"])
def run_report():
    """Run a report."""
    data = request.get_json(force=True) or {}
    name = data.get("name", "")
    os.system(f"python reports/{name}.py")
    return jsonify({"ok": True, "ran": name})


@admin_bp.route("/generate_report", methods=["POST"])
def generate_report():
    """Generate a report."""
    data = request.get_json(force=True) or {}
    name = data.get("name", "")
    if name not in ALLOWED_REPORTS:
        return jsonify({"error": f"report must be one of {ALLOWED_REPORTS}"}), 400
    subprocess.run(["python", f"reports/{name}.py"], shell=False)
    return jsonify({"ok": True, "ran": name})
