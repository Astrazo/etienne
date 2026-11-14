import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError

from etienne.devices.speaker import Speaker


class CancelSpeakerTimerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.speaker = Speaker("bedroom", "spotify-id", Mock(), Path("unused.db"))
        self.time = datetime(2030, 1, 1, 20, tzinfo=UTC)
        self.lookup = patch("etienne.scheduler.speakers.get_active_timers").start()
        self.delete = patch("etienne.scheduler.speakers.delete_speaker_timers").start()
        self.delete.return_value = 1
        self.addCleanup(patch.stopall)

    async def test_no_match_does_not_delete(self):
        self.lookup.return_value = []

        message = await self.speaker.cancel_timer(action="pause")

        self.assertIn("No timers match", message)
        self.lookup.assert_called_once_with(
            db_path=self.speaker.db_path,
            speaker_name="bedroom",
            action="pause",
            time=None,
        )
        self.delete.assert_not_called()

    async def test_single_match_is_deleted_and_described(self):
        self.lookup.return_value = [(42, "bedroom", "pause", self.time.timestamp())]

        message = await self.speaker.cancel_timer()

        self.delete.assert_called_once_with(self.speaker.db_path, [42])
        self.assertIn("pause timer", message)
        self.assertIn(self.time.isoformat(), message)
        self.assertIn("has been cancelled", message)

    async def test_multiple_matches_require_clarification(self):
        for count in (2, 3):
            with self.subTest(count=count):
                self.lookup.return_value = [
                    (index, "bedroom", "pause", self.time.timestamp() + index * 60)
                    for index in range(count)
                ]

                message = await self.speaker.cancel_timer()

                self.delete.assert_not_called()
                self.assertIn("No timers were cancelled", message)
                for row in self.lookup.return_value:
                    self.assertIn(
                        datetime.fromtimestamp(row[3], UTC).isoformat(), message
                    )

    async def test_timezone_aware_filter_is_forwarded(self):
        self.lookup.return_value = []
        local_time = self.time.astimezone(timezone(timedelta(hours=11)))

        await self.speaker.cancel_timer(action="resume", trigger_time=local_time)

        self.assertEqual(self.lookup.call_args.kwargs["time"], local_time)
        self.assertEqual(self.lookup.call_args.kwargs["action"], "resume")

    async def test_invalid_filters_are_rejected_before_lookup(self):
        for arguments in (
            {"trigger_time": "2030-01-01T20:00:00"},
            {"action": "stop"},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValidationError):
                await self.speaker.cancel_timer(**arguments)
        self.lookup.assert_not_called()
        self.delete.assert_not_called()

    async def test_delete_failure_propagates_for_tool_wrapper(self):
        self.lookup.return_value = [(42, "bedroom", "pause", self.time.timestamp())]
        self.delete.side_effect = RuntimeError("Database unavailable")

        with self.assertRaisesRegex(RuntimeError, "Database unavailable"):
            await self.speaker.cancel_timer()

    def test_cancel_timer_is_exposed_to_agent(self):
        self.assertIn(self.speaker.cancel_timer, self.speaker.get_tools())
