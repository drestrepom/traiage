import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path("/tmp/fake-library.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );

        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT,
            available INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            loaned_at TEXT NOT NULL DEFAULT (datetime('now')),
            returned_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
    """)

    def pw(s: str) -> str:
        return hashlib.sha256(s.encode()).hexdigest()

    # Seed users
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            [
                ("alice", pw("alice123"), "user"),
                ("bob", pw("bob456"), "cashier"),
                ("carol", pw("carol789"), "admin"),
            ],
        )

    # Seed books
    cur.execute("SELECT COUNT(*) FROM books")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO books (title, author, isbn, available) VALUES (?, ?, ?, ?)",
            [
                ("Clean Code", "Robert C. Martin", "978-0132350884", 1),
                ("The Pragmatic Programmer", "David Thomas", "978-0135957059", 1),
                ("Design Patterns", "Gang of Four", "978-0201633610", 0),
                ("Introduction to Algorithms", "Cormen et al.", "978-0262033848", 1),
                ("Python Cookbook", "David Beazley", "978-1449340377", 1),
            ],
        )

    conn.commit()
    conn.close()
