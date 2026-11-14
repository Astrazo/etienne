import sqlite3
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from etienne.db import init_db


class SpeakerTimerUniquenessTests(unittest.TestCase):
    def setUp(self):
        # Keep an in-memory database alive across the application's connections.
        connect = sqlite3.connect
        uri = "file:speaker_timer_tests?mode=memory&cache=shared"
        self.connection = connect(uri, uri=True)
        self.addCleanup(self.connection.close)
        patcher = patch(
            "sqlite3.connect", side_effect=lambda path: connect(uri, uri=True)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.path = Path.cwd() / "unused-test.db"

    def insert_timer(self, speaker, action, time):
        with self.connection:
            self.connection.execute(
                "INSERT INTO speaker_timers (device_id, action, execute_at) VALUES (?, ?, ?)",
                (speaker, action, time.timestamp()),
            )

    def test_duplicate_time_is_rejected_without_replacing_original(self):
        init_db(self.path)
        time = datetime(2030, 1, 1, 20, tzinfo=UTC)
        self.insert_timer("bedroom", "pause", time)

        for action in ("pause", "resume"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.insert_timer("bedroom", action, time)

        rows = self.connection.execute(
            "SELECT device_id, action, execute_at FROM speaker_timers"
        ).fetchall()
        self.assertEqual(rows, [("bedroom", "pause", time.timestamp())])

    def test_other_speakers_and_times_are_allowed(self):
        init_db(self.path)
        time = datetime(2030, 1, 1, 20, tzinfo=UTC)
        self.insert_timer("bedroom", "pause", time)
        self.insert_timer("kitchen", "resume", time)
        self.insert_timer("bedroom", "resume", time + timedelta(hours=1))

        count = self.connection.execute(
            "SELECT COUNT(*) FROM speaker_timers"
        ).fetchone()[0]
        self.assertEqual(count, 3)

    def test_existing_table_gets_constraint_and_initialization_is_repeatable(self):
        self.connection.execute(
            "CREATE TABLE speaker_timers "
            "(id INTEGER PRIMARY KEY, device_id TEXT, action TEXT, execute_at REAL)"
        )
        time = datetime(2030, 1, 1, 20, tzinfo=UTC)
        self.insert_timer("bedroom", "pause", time)

        init_db(self.path)
        init_db(self.path)

        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_timer("bedroom", "resume", time)

    def test_existing_conflicts_are_preserved_and_reported(self):
        self.connection.execute(
            "CREATE TABLE speaker_timers "
            "(id INTEGER PRIMARY KEY, device_id TEXT, action TEXT, execute_at REAL)"
        )
        time = datetime(2030, 1, 1, 20, tzinfo=UTC)
        self.insert_timer("bedroom", "pause", time)
        self.insert_timer("bedroom", "resume", time)

        with self.assertRaises(sqlite3.IntegrityError):
            init_db(self.path)

        count = self.connection.execute(
            "SELECT COUNT(*) FROM speaker_timers"
        ).fetchone()[0]
        self.assertEqual(count, 2)
