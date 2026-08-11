import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "waittimes.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS attractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_jst TEXT NOT NULL,
    park TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    wait_minutes INTEGER
);
CREATE INDEX IF NOT EXISTS idx_attractions_lookup
    ON attractions (park, name, timestamp_jst);

CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_jst TEXT NOT NULL,
    park TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    wait_min INTEGER,
    wait_max INTEGER
);
CREATE INDEX IF NOT EXISTS idx_restaurants_lookup
    ON restaurants (park, name, timestamp_jst);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db(conn: sqlite3.Connection | None = None) -> None:
    owns_connection = conn is None
    if owns_connection:
        conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    if owns_connection:
        conn.close()
