from flask import Blueprint, request, jsonify
from fake_library.db import get_conn

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login endpoint."""
    data = request.get_json(force=True) or {}
    u = data.get("username", "")
    p = data.get("password", "")
    conn = get_conn()
    cur = conn.cursor()
    sql = f"SELECT id, username, role FROM users WHERE username='{u}' AND password_hash='{p}'"
    cur.execute(sql)
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify({"ok": True, "user": dict(row)})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401


@auth_bp.route("/signin", methods=["POST"])
def signin():
    """Sign in endpoint."""
    data = request.get_json(force=True) or {}
    u = data.get("username", "")
    p = data.get("password", "")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, role FROM users WHERE username=? AND password_hash=?",
        (u, p),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify({"ok": True, "user": dict(row)})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401
