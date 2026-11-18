"""_summary_"""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from loguru import logger


def save_speaker_timer(
    db_path: Path, device_id: str, action: Literal["resume", "pause"], time: datetime
) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO speaker_timers (device_id, action, execute_at)
                    VALUES (?, ?, ?)
                    """,
                    (device_id, action, time.timestamp()),
                )
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorcode != sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                    raise

                # Raise back to the model that there already exists a timer at this time.
                raise ValueError(
                    f"A timer already exists for speaker '{device_id}' at {time.isoformat()}. "
                    "The user needs to remove this timer first, or change the time of their new timer. "
                    "The existing timer is unchanged."
                ) from error

        logger.info(
            "Saved speaker timer {}: {} device {} at {}",
            cursor.lastrowid,
            action,
            device_id,
            time.isoformat(),
        )


def delete_speaker_timers(db_path: Path, timer_ids: list[int]) -> int:
    """Delete the selected timers in one transaction and return the number deleted."""
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            cursor = connection.executemany(
                "DELETE FROM speaker_timers WHERE id = ?",
                [(timer_id,) for timer_id in timer_ids],
            )

        logger.debug("Deleted {} speaker timer(s)", cursor.rowcount)
        return cursor.rowcount


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


def get_active_timers(
    db_path: Path,
    device_id: str | None = None,
    action: Literal["resume", "pause"] | None = None,
    time: datetime | None = None,
) -> list[tuple[int, str, str, float]]:
    """Return stored timers matching all supplied filters, or all timers if omitted."""
    conditions: list[str] = []
    parameters: list[str | float] = []

    if device_id is not None:
        conditions.append("device_id = ?")
        parameters.append(device_id)

    if action is not None:
        conditions.append("action = ?")
        parameters.append(action)

    if time is not None:
        conditions.append("execute_at = ?")
        parameters.append(time.timestamp())

    query = "SELECT id, device_id, action, execute_at FROM speaker_timers"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY execute_at, id"

    with closing(sqlite3.connect(db_path)) as connection:
        timers = connection.execute(query, parameters).fetchall()

    if timers:
        logger.debug("Found {} matching speaker timer(s)", len(timers))

    return timers
