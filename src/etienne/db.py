"""SQLite setup. Timer deadlines are stored as UTC Unix timestamps in seconds."""

import sqlite3
from contextlib import closing
from pathlib import Path


def init_db(path: str | Path | None = None) -> Path:
    """Create the database and missing tables without clearing existing timers."""
    db_path = (
        Path(path if path is not None else "data/etienne.db").expanduser().resolve()
    )
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Equivilant to
    # with closing as connection:
    #    with connection:
    #        connection.execute()
    with closing(sqlite3.connect(db_path)) as connection, connection:
        # Speaker timer table
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS speaker_timers (
                id INTEGER PRIMARY KEY,
                device_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('pause', 'resume')),
                execute_at REAL NOT NULL CHECK (execute_at >= 0)
            )
            """
        )

    return db_path
