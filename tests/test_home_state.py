"""Reads reflect external changes and never rely on state retained by Etienne."""

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from etienne.api.routes.ui import ui_router
from etienne.config import HomeConfig
from etienne.devices import TV, Light, Speaker
from etienne.home import Home


class HomeStateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.external = {"light.desk": "on", "light.kitchen": "off"}
        self.ha = Mock(
            get_state=AsyncMock(
                side_effect=lambda entity: {"state": self.external[entity]}
            )
        )
        self.spotify = Mock()
        self.spotify.get_status_snapshot.return_value = {
            "devices": [
                {"id": "bedroom-id", "is_active": True},
                {"id": "living-id", "is_active": False},
            ],
            "current_playback": {"is_playing": True, "item": {"name": "Current song"}},
        }
        self.home = Home(
            self.ha, self.spotify, {}, HomeConfig(home_assistant_url="http://ha.test")
        )
        self.home.lights = {
            "desk": Light("desk", "light.desk", self.ha),
            "kitchen": Light("kitchen", "light.kitchen", self.ha),
        }
        self.home.speakers = {
            "bedroom": Speaker(
                "bedroom", "bedroom-id", self.spotify, Path("unused.db")
            ),
            "living": Speaker("living", "living-id", self.spotify, Path("unused.db")),
        }
        self.tv_ha = Mock(
            get_state=AsyncMock(
                return_value={
                    "state": "on",
                    "attributes": {"app_id": "com.netflix.ninja"},
                    "last_updated": "2026-11-17T04:00:00+00:00",
                }
            )
        )
        self.adb = Mock()
        self.home.tvs = {
            "living": TV("living", self.adb, "media_player.living", self.tv_ha)
        }

    async def test_external_light_switch_changes_appear_on_the_next_read(self):
        first = await self.home.get_home_state({"lights"})
        self.external["light.desk"] = "off"
        second = await self.home.get_home_state({"lights"})
        self.assertEqual(first["lights:desk"]["state"], "on")
        self.assertEqual(second["lights:desk"]["state"], "off")
        self.assertEqual(self.ha.get_state.await_count, 4)
        self.assertFalse(hasattr(self.home.lights["desk"], "state"))

    async def test_targeted_read_does_not_contact_other_devices_or_spotify(self):
        state = await self.home.lights["kitchen"].get_state()
        self.assertEqual(state.state, "off")
        self.ha.get_state.assert_awaited_once_with("light.kitchen")
        self.spotify.get_status_snapshot.assert_not_called()

    async def test_speakers_share_one_fresh_spotify_read_per_request(self):
        first = await self.home.get_home_state({"speakers"})
        self.assertTrue(first["speakers:bedroom"]["is_active"])
        self.assertFalse(first["speakers:living"]["is_active"])
        self.assertEqual(self.spotify.get_status_snapshot.call_count, 1)
        self.ha.get_state.assert_not_awaited()

        # A phone moves playback to another speaker, without any Etienne command.
        self.spotify.get_status_snapshot.return_value = {
            "devices": [
                {"id": "bedroom-id", "is_active": False},
                {"id": "living-id", "is_active": True},
            ],
            "current_playback": {"is_playing": False},
        }
        second = await self.home.get_home_state({"speakers"})
        self.assertFalse(second["speakers:bedroom"]["is_active"])
        self.assertTrue(second["speakers:living"]["is_active"])
        self.assertFalse(second["speakers:living"]["is_playing"])
        self.assertEqual(self.spotify.get_status_snapshot.call_count, 2)
        self.assertFalse(hasattr(self.home.speakers["living"], "state"))

    async def test_direct_speaker_read_is_also_live_and_does_not_store_state(self):
        speaker = self.home.speakers["bedroom"]
        first = await speaker.get_state()
        self.spotify.get_status_snapshot.return_value = {
            "devices": [],
            "current_playback": None,
        }
        second = await speaker.get_state()
        self.assertTrue(first.available)
        self.assertFalse(second.available)
        self.assertFalse(hasattr(speaker, "state"))

    async def test_failed_read_is_explicit_and_does_not_reuse_last_success(self):
        await self.home.get_home_state({"lights"})

        async def get_state(entity):
            if entity == "light.desk":
                raise httpx.ConnectError("No connection")
            return {"state": "off"}

        self.ha.get_state.side_effect = get_state
        state = await self.home.get_home_state({"lights"})
        self.assertEqual(state["lights:desk"]["state"], "unavailable")
        self.assertIn("error", state["lights:desk"])
        self.assertEqual(state["lights:kitchen"]["state"], "off")

    async def test_tv_state_comes_from_ha_and_serializes_for_home(self):
        state = await self.home.get_home_state({"tvs"})
        self.assertEqual(state["tvs:living"]["state"], "on")
        self.assertEqual(
            state["tvs:living"]["attributes"]["app_id"], "com.netflix.ninja"
        )
        self.assertIsInstance(state["tvs:living"]["last_updated"], str)
        self.tv_ha.get_state.assert_awaited_once_with("media_player.living")
        self.adb.shell.assert_not_called()

    async def test_tv_ha_failure_reports_unavailable_not_off(self):
        self.tv_ha.get_state.side_effect = httpx.ConnectError("Disconnected")
        state = await self.home.get_home_state({"tvs"})
        self.assertEqual(state["tvs:living"]["state"], "unavailable")
        self.assertIn("error", state["tvs:living"])

    async def test_inventory_api_reads_live_state_on_each_request(self):
        app = FastAPI()
        app.state.home = self.home
        app.include_router(ui_router)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.get("/api/devices")
            self.external["light.desk"] = "off"
            second = await client.get("/api/devices")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_devices = {item["id"]: item for item in first.json()["devices"]}
        second_devices = {item["id"]: item for item in second.json()["devices"]}
        self.assertEqual(first_devices["lights:desk"]["state"], "on")
        self.assertEqual(second_devices["lights:desk"]["state"], "off")
        self.assertEqual(set(second_devices), set(self.home.get_device_map()))

    async def test_unknown_device_type_is_rejected_before_reading_anything(self):
        with self.assertRaisesRegex(ValueError, "Unknown device type"):
            await self.home.get_home_state({"missing"})
        self.ha.get_state.assert_not_awaited()
        self.spotify.get_status_snapshot.assert_not_called()
