"""One polling task for home schedules. Run only one scheduler per database."""

import asyncio
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from .home import Home


def _due_speaker_timers(db_path: Path) -> list[tuple[int, str, str]]:
    with closing(sqlite3.connect(db_path)) as connection:
        return connection.execute(
            """
            SELECT id, device_id, action FROM speaker_timers
            WHERE execute_at <= ?
            ORDER BY execute_at, id
            """,
            (datetime.now(UTC).timestamp(),),
        ).fetchall()


def _delete_speaker_timer(db_path: Path, timer_id: int) -> None:
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("DELETE FROM speaker_timers WHERE id = ?", (timer_id,))


async def process_speaker_timers(home: Home, db_path: Path) -> None:
    timers = await asyncio.to_thread(_due_speaker_timers, db_path)
    speakers = {speaker.spotify_id: speaker for speaker in home.speakers.values()}

    for timer_id, device_id, action in timers:
        try:
            speaker = speakers[device_id]
            if action == "pause":
                await speaker.pause()
            elif action == "resume":
                await speaker.resume()
            else:
                raise ValueError(f"Unknown speaker action: {action}")

            await asyncio.to_thread(_delete_speaker_timer, db_path, timer_id)
        except Exception:  # noqa: BLE001 - isolate device failures
            logger.exception("Speaker timer {} failed; keeping it for retry", timer_id)


async def run_scheduler(home: Home, db_path: Path) -> None:
    """Execute due timers immediately, then check again every 60 seconds."""
    while True:
        try:
            await process_speaker_timers(home, db_path)
        except Exception:  # noqa: BLE001 - keep polling after failures
            logger.exception("Could not process speaker timers; retrying next poll")

        # Add other table handlers here, such as process_tv_schedule(...).
        await asyncio.sleep(60)
