import sqlite3
from datetime import datetime, timezone

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    minecraft_name TEXT NOT NULL UNIQUE,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def user_count() -> int:
    row = get_db().execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return int(row["total"])


def create_user(email: str, password_hash: str, minecraft_name: str, is_admin: bool) -> int:
    cursor = get_db().execute(
        """
        INSERT INTO users (email, password_hash, minecraft_name, is_admin, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (email.lower(), password_hash, minecraft_name, int(is_admin), utcnow()),
    )
    get_db().commit()
    return int(cursor.lastrowid)


def get_user_by_email(email: str):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()


def get_user(user_id: int):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users():
    return get_db().execute("SELECT * FROM users ORDER BY is_admin DESC, created_at ASC").fetchall()


def set_admin(user_id: int, is_admin: bool) -> None:
    get_db().execute("UPDATE users SET is_admin = ? WHERE id = ?", (int(is_admin), user_id))
    get_db().commit()
