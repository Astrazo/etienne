"""Nested config builds individual devices before groups reference them."""

import tomllib
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from etienne.config import HomeConfig
from etienne.home import Home

CONFIG = """
home_assistant_url = "http://ha.test"

[lights.living_room]
display_name = "Living Room Lights"
[lights.living_room.devices.main]
display_name = "Sofa Lamp"
ha_entity_id = "light.sofa"
[lights.living_room.devices.second]
display_name = "Reading Lamp"
ha_entity_id = "light.reading"

[lights.kitchen]
display_name = "Kitchen Lights"
[lights.kitchen.devices.main]
display_name = "Kitchen Ceiling"
ha_entity_id = "light.kitchen"

[speakers.living_room]
display_name = "Lounge Speaker"
spotify_id = "spotify-lounge"

[tvs.living_room]
display_name = "Lounge TV"
host = "tv.test"
ha_entity_id = "media_player.lounge"
"""


class HomeInitialisationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = HomeConfig.model_validate(tomllib.loads(CONFIG))
        self.ha = Mock(get_state=AsyncMock(return_value={"state": "off"}))
        self.spotify = Mock()
        self.spotify.get_status_snapshot.return_value = {
            "devices": [],
            "current_playback": None,
        }
        self.adb = Mock(connect=AsyncMock())
        self.home = Home(self.ha, self.spotify, {"living_room": self.adb}, self.config)
        await self.home.initialise(Path("unused.db"))

    async def test_groups_reference_the_registered_lights_with_room_scoped_ids(self):
        living_room = self.home.light_groups["living_room"]
        kitchen = self.home.light_groups["kitchen"]

        self.assertEqual(len(self.home.lights), 3)
        self.assertEqual(list(living_room.devices), ["main", "second"])
        self.assertIs(
            living_room.devices["main"], self.home.lights["living_room.devices.main"]
        )
        self.assertIs(kitchen.devices["main"], self.home.lights["kitchen.devices.main"])
        self.assertIsNot(living_room.devices["main"], kitchen.devices["main"])
        self.assertEqual(living_room.display_name, "Living Room Lights")
        self.assertEqual(living_room.group_id, "living_room")
        self.assertEqual(living_room.devices["main"].device_id, "main")
        self.assertEqual(kitchen.devices["main"].device_id, "main")
        self.assertEqual(
            living_room.devices["main"].device_key, "living_room.devices.main"
        )
        self.assertEqual(kitchen.devices["main"].device_key, "kitchen.devices.main")
        self.assertEqual(living_room.devices["main"].ha_entity_id, "light.sofa")
        self.assertIs(living_room.devices["main"].ha_client, self.ha)
        self.adb.connect.assert_awaited_once()
        self.ha.get_state.assert_not_awaited()
        self.spotify.get_status_snapshot.assert_not_called()

    async def test_speaker_and_tv_receive_configured_identity_and_clients(self):
        speaker = self.home.speakers["living_room"]
        tv = self.home.tvs["living_room"]

        self.assertEqual(speaker.device_id, "living_room")
        self.assertEqual(speaker.display_name, "Lounge Speaker")
        self.assertEqual(speaker.spotify_id, "spotify-lounge")
        self.assertIs(speaker.spotify_client, self.spotify)
        self.assertEqual(tv.display_name, "Lounge TV")
        self.assertEqual(tv.ha_entity_id, "media_player.lounge")
        self.assertIs(tv.adb_client, self.adb)

    async def test_inventory_shows_display_names_and_keeps_unique_device_keys(self):
        inventory = await self.home.get_device_inventory()
        names = {}
        for device in inventory:
            names[device["id"]] = device["name"]

        self.assertEqual(names["lights:living_room.devices.main"], "Sofa Lamp")
        self.assertEqual(names["lights:kitchen.devices.main"], "Kitchen Ceiling")
        self.assertEqual(names["speakers:living_room"], "Lounge Speaker")
        self.assertEqual(names["tvs:living_room"], "Lounge TV")
        self.assertEqual(set(names), set(self.home.get_device_map()))
