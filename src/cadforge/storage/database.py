import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS revisions (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    label TEXT NOT NULL, recipe TEXT NOT NULL, artifact TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
PRAGMA user_version = 1;
"""


def connect(path):
    db = sqlite3.connect(Path(path), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, 1):
        db.close()
        raise ValueError(f"Unsupported database version {version}.")
    db.executescript(SCHEMA)
    return db
