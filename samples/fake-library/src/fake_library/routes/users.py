from flask import Blueprint, request, jsonify
from fake_library.db import get_conn

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/search", methods=["GET"])
def search():
    """Search users."""
    q = request.args.get("q", "")
    conn = get_conn()
    cur = conn.cursor()
    sql = "SELECT id, username, role FROM users WHERE username LIKE '%" + q + "%'"
    cur.execute(sql)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@users_bp.route("/find", methods=["GET"])
def find():
    """Find users."""
    q = request.args.get("q", "")
    q = q[:50]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, role FROM users WHERE username LIKE ?",
        (f"%{q}%",),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@users_bp.route("/by_id", methods=["GET"])
def by_id():
    """Fetch user by id."""
    try:
        user_id = int(request.args["id"])
    except (KeyError, ValueError):
        return jsonify({"error": "id must be an integer"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT id, username, role FROM users WHERE id = {user_id}")
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": "not found"}), 404
