from flask import Blueprint, request, jsonify
from fake_library.db import get_conn
from fake_library.security import ALLOWED_SORT_COLUMNS

books_bp = Blueprint("books", __name__, url_prefix="/books")

BOOK_CATALOG: dict[str, str] = {
    "clean_code": "Clean Code",
    "pragmatic_programmer": "The Pragmatic Programmer",
    "design_patterns": "Design Patterns",
    "intro_algorithms": "Introduction to Algorithms",
    "python_cookbook": "Python Cookbook",
}


@books_bp.route("/create", methods=["POST"])
def create():
    """Create a new book."""
    data = request.get_json(force=True) or {}
    title = data.get("title", "")
    author = data.get("author", "")
    isbn = data.get("isbn", "")
    if not title or not author:
        return jsonify({"error": "title and author required"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO books (title, author, isbn) VALUES (?, ?, ?)",
        (title, author, isbn),
    )
    conn.commit()
    book_id = cur.lastrowid
    conn.close()
    return jsonify({"id": book_id}), 201


@books_bp.route("/list", methods=["GET"])
def list_books():
    """List books."""
    sort = request.args.get("sort", "title")
    conn = get_conn()
    cur = conn.cursor()
    sql = f"SELECT id, title, author, isbn, available, created_at FROM books ORDER BY {sort}"
    cur.execute(sql)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@books_bp.route("/browse", methods=["GET"])
def browse():
    """Browse books."""
    sort = request.args.get("sort", "title")
    if sort not in ALLOWED_SORT_COLUMNS:
        sort = "title"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, title, author, isbn, available, created_at FROM books ORDER BY {sort}"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@books_bp.route("/detail", methods=["GET"])
def detail():
    """Fetch book detail by catalog key."""
    key = request.args.get("key", "")
    title = BOOK_CATALOG.get(key)
    if not title:
        return jsonify({"error": "unknown catalog key"}), 404
    conn = get_conn()
    cur = conn.cursor()
    sql = f"SELECT id, title, author, isbn, available FROM books WHERE title = '{title}'"
    cur.execute(sql)
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": "not found"}), 404
