"""One polling task for home schedules.
Calls SQL functions from other sub modules, and executes the appropriate lower level functions.
"""

import asyncio
from pathlib import Path

from loguru import logger

from ..home import Home
from .speakers import delete_speaker_timer, get_due_speaker_timers

POLL_INTERVAL_SECONDS = 60


async def run_scheduler(home: Home, db_path: Path) -> None:
    """Execute due timers immediately, then check again every 60 seconds."""
    logger.info(
        "Scheduler started; checking for due timers every {} seconds",
        POLL_INTERVAL_SECONDS,
    )

    while True:
        try:
            await _process_speaker_timers(home, db_path)
            # Add more devices to monitor here
        except Exception:  # noqa: BLE001 - keep polling after failures
            logger.exception("Could not process speaker timers; retrying next poll")

        # Add other table handlers here, such as process_tv_schedule(...).
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _process_speaker_timers(home: Home, db_path: Path) -> None:
    due_timers = await asyncio.to_thread(get_due_speaker_timers, db_path)
    speakers = {speaker.spotify_id: speaker for speaker in home.speakers.values()}

    for timer_id, device_id, action in due_timers:
        try:
            speaker = speakers[device_id]
            if action == "pause":
                await speaker.pause()
            elif action == "resume":
                await speaker.resume()
            else:
                raise ValueError(f"Unknown speaker action: {action}")

            logger.info(
                "Triggered speaker timer {}: {} speaker {} ({})",
                timer_id,
                action,
                speaker.name,
                device_id,
            )

            # Delete the timer after it's been triggered
            await asyncio.to_thread(delete_speaker_timer, db_path, timer_id)

            # Update home state
            await home.refresh_home_state({"speakers"})

        except Exception:  # noqa: BLE001 - isolate device failures
            logger.exception("Speaker timer {} failed; keeping it for retry", timer_id)
