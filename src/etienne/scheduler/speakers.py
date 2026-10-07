"""_summary_"""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from loguru import logger


def save_speaker_timer(
    db_path: Path, spotify_id: str, action: Literal["resume", "pause"], time: datetime
) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO speaker_timers (device_id, action, execute_at)
                VALUES (?, ?, ?)
                """,
                (spotify_id, action, time.timestamp()),
            )

        logger.info(
            "Saved speaker timer {}: {} device {} at {}",
            cursor.lastrowid,
            action,
            spotify_id,
            time.isoformat(),
        )


def delete_speaker_timer(db_path: Path, timer_id: int) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute("DELETE FROM speaker_timers WHERE id = ?", (timer_id,))

        logger.debug("Deleted speaker timer {}", timer_id)


def get_due_speaker_timers(db_path: Path) -> list[tuple[int, str, str]]:
    with closing(sqlite3.connect(db_path)) as connection:
        due_timers = connection.execute(
            """
            SELECT id, device_id, action FROM speaker_timers
            WHERE execute_at <= ?
            ORDER BY execute_at, id
            """,
            (datetime.now(UTC).timestamp(),),
        ).fetchall()

    if due_timers:
        logger.debug("Found {} due speaker timer(s)", len(due_timers))

    return due_timers
