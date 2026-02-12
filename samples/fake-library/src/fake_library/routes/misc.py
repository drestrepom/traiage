from flask import Blueprint, jsonify

misc_bp = Blueprint("misc", __name__)


@misc_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@misc_bp.route("/version", methods=["GET"])
def version():
    return jsonify({"version": "1.0.0"})
