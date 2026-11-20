"""Exercise the debugging API over HTTP without contacting real devices."""

import sqlite3
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from ollama import ResponseError
from requests.exceptions import RequestException

from etienne.api.routes import assistant_router, lights_router, speaker_router
from etienne.api.routes.ui import ui_router
from etienne.config import HomeConfig
from etienne.devices import Speaker, TrackInput
from etienne.devices.models import SpeakerState
from etienne.home import Home


class ApiRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use real light/group registration, with only external calls mocked.
        self.ha = Mock(
            call_service=AsyncMock(), get_state=AsyncMock(return_value={"state": "on"})
        )
        config = HomeConfig(
            home_assistant_url="http://ha.test",
            lights={
                "office": {
                    "devices": {
                        "desk": {"ha_entity_id": "light.desk"},
                        "ceiling": {"ha_entity_id": "light.ceiling"},
                    }
                }
            },
        )
        self.home = Home(self.ha, Mock(), {}, config)
        self.home._init_lights()
        self.home._init_light_groups()
        self.speaker = Mock(spec=Speaker)
        self.home.speakers["office"] = self.speaker

        # Mount the real routers without the production lifespan or NiceGUI.
        self.app = FastAPI()
        self.app.state.home = self.home
        self.app.state.ollama_client = Mock()
        for router in (lights_router, speaker_router, assistant_router, ui_router):
            self.app.include_router(router)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_individual_and_group_light_controls_use_configured_entities(self):
        response = await self.client.post(
            "/lights/office.devices.desk/on",
            params={"colour": "red", "effect": "Rainbow", "flash": "short"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "submitted")
        self.ha.call_service.assert_awaited_with(
            "light",
            "turn_on",
            {
                "entity_id": "light.desk",
                "rgb_color": [255, 0, 0],
                "effect": "Rainbow",
                "flash": "short",
            },
        )

        response = await self.client.post("/lights/office/off")
        self.assertEqual(response.status_code, 200)
        self.ha.call_service.assert_awaited_with(
            "light", "turn_off", {"entity_id": ["light.desk", "light.ceiling"]}
        )
        response = await self.client.get("/lights/office/state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()["devices"]), {"desk", "ceiling"})

    async def test_invalid_light_requests_do_not_send_commands(self):
        for path, params, expected in (
            ("/lights/missing/on", {}, 404),
            ("/lights/office.devices.missing/off", {}, 404),
            ("/lights/office/on", {"colour": "not-a-colour"}, 422),
            ("/lights/office/on", {"flash": "forever"}, 422),
        ):
            with self.subTest(path=path, params=params):
                response = await self.client.post(path, params=params)
                self.assertEqual(response.status_code, expected)
        self.ha.call_service.assert_not_awaited()

    async def test_speaker_operations_return_the_actual_method_result(self):
        tracks = [{"song": "Example", "artist": "Artist"}]
        cases = (
            (
                "play/tracks",
                "play_tracks",
                {},
                tracks,
                ([TrackInput(**tracks[0])],),
                {},
            ),
            (
                "play/album",
                "play_album",
                {"album": "Album"},
                None,
                (),
                {"album_name": "Album", "artist_name": None},
            ),
            (
                "play/artist",
                "play_artist",
                {"artist": "Artist"},
                None,
                (),
                {"artist_name": "Artist"},
            ),
            (
                "play/playlist",
                "play_playlist",
                {"playlist": "Playlist"},
                None,
                (),
                {"playlist_name": "Playlist"},
            ),
            ("pause", "pause", {}, None, (), {}),
            ("resume", "resume", {}, None, (), {}),
            ("repeat", "repeat", {"state": "context"}, None, (), {"state": "context"}),
            ("shuffle", "shuffle", {"state": "false"}, None, (), {"state": False}),
            (
                "queue/add",
                "add_to_playback_queue",
                {},
                tracks,
                ([TrackInput(**tracks[0])],),
                {},
            ),
            (
                "queue/navigate",
                "navigate_queue",
                {"direction": "previous"},
                None,
                ("previous",),
                {},
            ),
        )
        for path, name, params, body, args, kwargs in cases:
            with self.subTest(path=path):
                operation = getattr(self.speaker, name)
                operation.return_value = "Device result, including any missing matches"
                response = await self.client.post(
                    f"/speakers/office/{path}", params=params, json=body
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["result"], operation.return_value)
                operation.assert_awaited_once_with(*args, **kwargs)

    async def test_speaker_state_and_unknown_ids(self):
        self.speaker.get_state.return_value = SpeakerState(
            available=True, is_playing=False
        )
        for path in ("state", "status"):
            response = await self.client.get(f"/speakers/office/{path}")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["is_playing"])
        for method, path in (("GET", "state"), ("POST", "pause"), ("DELETE", "timers")):
            response = await self.client.request(method, f"/speakers/missing/{path}")
            self.assertEqual(response.status_code, 404)
        self.speaker.pause.assert_not_awaited()

    async def test_timer_creation_filters_and_ambiguous_cancellation(self):
        self.speaker.set_timer.return_value = "Timer scheduled"
        response = await self.client.post(
            "/speakers/office/timer", json={"action": "pause", "timer_minutes": 5}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Timer scheduled")
        self.speaker.set_timer.assert_awaited_once_with(
            action="pause", timer_minutes=5, trigger_time=None
        )

        scheduled = datetime.now(UTC) + timedelta(hours=1)
        params = {"action": "pause", "trigger_time": scheduled.isoformat()}
        self.speaker.get_timers.return_value = "Matching timers"
        response = await self.client.get("/speakers/office/timers", params=params)
        self.assertEqual(response.json()["result"], "Matching timers")
        self.speaker.get_timers.assert_awaited_once_with(
            action="pause", trigger_time=scheduled
        )

        self.speaker.cancel_timer.return_value = (
            "Multiple timers match. No timers were cancelled."
        )
        response = await self.client.delete("/speakers/office/timers")
        self.assertIn("No timers were cancelled", response.json()["result"])
        self.speaker.cancel_timer.assert_awaited_once_with(
            action=None, trigger_time=None, cancel_all=False
        )
        response = await self.client.delete(
            "/speakers/office/timers", params={**params, "cancel_all": "true"}
        )
        self.assertEqual(response.status_code, 200)
        self.speaker.cancel_timer.assert_awaited_with(
            action="pause", trigger_time=scheduled, cancel_all=True
        )

    async def test_timer_validation_and_storage_failure(self):
        for timer in (
            {"action": "pause"},
            {"action": "pause", "timer_minutes": 0},
            {"action": "pause", "trigger_time": "2020-01-01T00:00:00Z"},
            {"action": "pause", "trigger_time": "2099-01-01T00:00:00"},
            {
                "action": "pause",
                "timer_minutes": 1,
                "trigger_time": "2099-01-01T00:00:00Z",
            },
        ):
            response = await self.client.post("/speakers/office/timer", json=timer)
            self.assertEqual(response.status_code, 422, response.text)
        self.speaker.set_timer.assert_not_awaited()
        self.speaker.get_timers.side_effect = sqlite3.OperationalError("offline")
        self.assertEqual(
            (await self.client.get("/speakers/office/timers")).status_code, 500
        )

    async def test_upstream_device_failures_have_http_errors(self):
        self.ha.call_service.side_effect = httpx.ConnectError("offline")
        response = await self.client.post("/lights/office/on")
        self.assertEqual(response.status_code, 502)
        self.speaker.pause.side_effect = RequestException("offline")
        response = await self.client.post("/speakers/office/pause")
        self.assertEqual(response.status_code, 502)

    async def test_assistant_forwards_to_shared_service_and_rejects_blank_input(self):
        with patch(
            "etienne.api.routes.assistant.process_utterance", new_callable=AsyncMock
        ) as process:
            process.return_value = {"assistant_response": "Hello", "actions": []}
            response = await self.client.post(
                "/assistant/utterance", params={"utterance": " hello "}
            )
            self.assertEqual(response.json(), process.return_value)
            process.assert_awaited_once_with(
                "hello", self.home, self.app.state.ollama_client
            )
            response = await self.client.post(
                "/assistant/utterance", params={"utterance": "   "}
            )
            self.assertEqual(response.status_code, 422)
            self.assertEqual(process.await_count, 1)
            for error, status in (
                (ResponseError("model unavailable"), 502),
                (httpx.ConnectError("offline"), 502),
                (TimeoutError(), 504),
            ):
                process.side_effect = error
                response = await self.client.post(
                    "/assistant/utterance", params={"utterance": "hello"}
                )
                self.assertEqual(response.status_code, status)

    async def test_inventory_and_filtered_home_state_use_current_home_methods(self):
        # Use real Home methods to catch stale method names and key formats.
        self.home.speakers.clear()
        response = await self.client.get("/api/devices")
        self.assertEqual(response.status_code, 200)
        ids = {device["id"] for device in response.json()["devices"]}
        self.assertEqual(
            ids, {"lights:office.devices.desk", "lights:office.devices.ceiling"}
        )
        response = await self.client.get(
            "/api/state", params={"device_types": "lights"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), ids)
        self.home.spotify_client.get_status_snapshot.assert_not_called()
        response = await self.client.get(
            "/api/state", params={"device_types": "invalid"}
        )
        self.assertEqual(response.status_code, 422)

    async def test_debugging_endpoints_are_exposed_in_openapi(self):
        response = await self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for path in (
            "/api/devices",
            "/api/state",
            "/lights/{device_key}/on",
            "/speakers/{device_id}/timers",
            "/assistant/utterance",
        ):
            self.assertIn(path, paths)
