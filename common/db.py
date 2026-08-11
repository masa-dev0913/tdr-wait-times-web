import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "waittimes.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS attractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_jst TEXT NOT NULL,
    park TEXT NOT NULL,
    area TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    wait_minutes INTEGER
);
CREATE INDEX IF NOT EXISTS idx_attractions_lookup
    ON attractions (park, name, timestamp_jst);
CREATE INDEX IF NOT EXISTS idx_attractions_period
    ON attractions (park, timestamp_jst);

CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_jst TEXT NOT NULL,
    park TEXT NOT NULL,
    area TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    wait_min INTEGER,
    wait_max INTEGER
);
CREATE INDEX IF NOT EXISTS idx_restaurants_lookup
    ON restaurants (park, name, timestamp_jst);
CREATE INDEX IF NOT EXISTS idx_restaurants_period
    ON restaurants (park, timestamp_jst);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _ensure_area_column(conn: sqlite3.Connection, table: str) -> None:
    """areaカラム追加前に作られた既存DBのための軽量マイグレーション。"""
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    if "area" not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN area TEXT NOT NULL DEFAULT ''")


def init_db(conn: sqlite3.Connection | None = None) -> None:
    owns_connection = conn is None
    if owns_connection:
        conn = get_connection()
    conn.executescript(SCHEMA)
    _ensure_area_column(conn, "attractions")
    _ensure_area_column(conn, "restaurants")
    conn.commit()
    if owns_connection:
        conn.close()
