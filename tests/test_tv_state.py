"""TV observation uses Home Assistant; controls keep their ADB connection."""

import unittest
from unittest.mock import AsyncMock, Mock

from pydantic import ValidationError

from etienne.config import HomeConfig, TVConfig
from etienne.devices import TV
from etienne.devices.models import TvState
from etienne.home import Home


class TVStateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adb = Mock(open_app=AsyncMock())
        self.ha = Mock(
            get_state=AsyncMock(
                return_value={
                    "entity_id": "media_player.living_room_tv",
                    "state": "on",
                    "attributes": {
                        "app_id": "com.netflix.ninja",
                        "app_name": "Netflix",
                    },
                    "last_updated": "2026-11-17T04:00:00+00:00",
                }
            )
        )
        self.tv = TV("living_room", self.adb, "media_player.living_room_tv", self.ha)

    async def test_each_read_validates_a_new_ha_response_without_using_adb(self):
        first = await self.tv.get_state()
        self.ha.get_state.return_value = {"state": "off"}
        second = await self.tv.get_state()

        self.assertIsInstance(first, TvState)
        self.assertEqual(first.attributes.app_id, "com.netflix.ninja")
        self.assertEqual(first.last_updated.year, 2026)
        self.assertEqual(second.state, "off")
        self.assertIsNone(second.attributes.app_id)
        self.assertEqual(self.ha.get_state.await_count, 2)
        self.ha.get_state.assert_awaited_with("media_player.living_room_tv")
        self.assertEqual(self.adb.mock_calls, [])

    async def test_ha_playback_states_and_optional_attributes(self):
        for state in (
            "idle",
            "standby",
            "playing",
            "paused",
            "buffering",
            "unknown",
            "unavailable",
        ):
            with self.subTest(state=state):
                self.ha.get_state.return_value = {
                    "state": state,
                    "attributes": {"volume_level": None},
                }
                self.assertEqual((await self.tv.get_state()).state, state)

    async def test_missing_entity_mapping_is_explicit_without_adb_fallback(self):
        tv = TV("unmapped", self.adb)
        with self.assertRaises(NotImplementedError):
            await tv.get_state()
        self.assertEqual(self.adb.mock_calls, [])
        self.ha.get_state.assert_not_awaited()

    async def test_invalid_ha_response_is_rejected(self):
        self.ha.get_state.return_value = {"state": "guessed"}
        with self.assertRaises(ValidationError):
            await self.tv.get_state()

    async def test_opening_apps_still_uses_adb(self):
        await self.tv.open_app("netflix")
        self.adb.open_app.assert_awaited_once_with("com.netflix.ninja")
        self.ha.get_state.assert_not_awaited()

    async def test_navigation_and_focus_reading_use_the_configured_adb_client(self):
        self.adb.send_key = AsyncMock()
        self.adb.get_focused_element = AsyncMock(return_value="focused item")

        for operation, key in (
            (self.tv.up, "KEYCODE_DPAD_UP"),
            (self.tv.down, "KEYCODE_DPAD_DOWN"),
            (self.tv.left, "KEYCODE_DPAD_LEFT"),
            (self.tv.right, "KEYCODE_DPAD_RIGHT"),
            (self.tv.select, "KEYCODE_DPAD_CENTER"),
            (self.tv.back, "KEYCODE_BACK"),
            (self.tv.home, "KEYCODE_HOME"),
        ):
            await operation()
            self.adb.send_key.assert_awaited_with(key)

        self.assertEqual(await self.tv.focused_element(), "focused item")
        self.adb.get_focused_element.assert_awaited_once()
        self.ha.get_state.assert_not_awaited()

    async def test_home_passes_configured_entity_and_shared_ha_client(self):
        config = HomeConfig(
            home_assistant_url="http://ha.test",
            tvs={
                "living_room": TVConfig(
                    host="tv.test", ha_entity_id="media_player.living_room_tv"
                )
            },
        )
        home = Home(self.ha, Mock(), {"living_room": self.adb}, config)
        home._init_tvs()
        inventory = await home.get_device_inventory()

        self.assertEqual(inventory[0]["source"], "Home Assistant")
        self.assertEqual(inventory[0]["state"], "on")
        self.ha.get_state.assert_awaited_once_with("media_player.living_room_tv")
