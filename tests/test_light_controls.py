"""Light controls use the same registered methods as the assistant, without hardware."""

import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from nicegui import helpers, ui
from nicegui.storage import Storage
from nicegui.testing import user_simulation
from pydantic import ValidationError

from etienne.config import HomeConfig
from etienne.devices import Light, LightGroup
from etienne.devices.models import LightState
from etienne.home import Home
from etienne.web import devices as devices_page
from etienne.web.devices import build_devices


class LightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ha = Mock(call_service=AsyncMock(), get_state=AsyncMock())
        self.light = Light("desk", "light.desk", self.ha)

    async def test_state_validates_nested_attributes_and_ha_timestamps(self):
        self.ha.get_state.return_value = {
            "entity_id": "light.desk",
            "state": "on",
            "attributes": {
                "brightness": 128,
                "rgb_color": [255, 0, 0],
                "effect": "Rainbow",
                "effect_list": ["Rainbow"],
                "friendly_name": "Desk",
            },
            "last_updated": "2026-11-17T01:00:00+00:00",
            "context": {"id": "ha-context"},
        }

        state = await self.light.get_state()

        self.assertIsInstance(state, LightState)
        self.assertEqual(state.attributes.rgb_color, (255, 0, 0))
        self.assertEqual(state.attributes.brightness, 128)
        self.assertEqual(state.attributes.effect_list, ["Rainbow"])
        self.assertEqual(state.last_updated.year, 2026)
        self.assertEqual(
            state.model_dump(mode="json")["attributes"]["rgb_color"], [255, 0, 0]
        )

    async def test_missing_or_null_light_attributes_do_not_imply_off(self):
        for label in ("off", "unknown", "unavailable"):
            self.ha.get_state.return_value = {
                "state": label,
                "attributes": {"brightness": None, "effect_list": None},
            }

            state = await self.light.get_state()

            self.assertEqual(state.state, label)
            self.assertIsNone(state.attributes.brightness)
            self.assertIsNone(state.attributes.rgb_color)

    async def test_invalid_ha_state_is_rejected(self):
        self.ha.get_state.return_value = {
            "state": "on",
            "attributes": {"brightness": 500},
        }
        with self.assertRaises(ValidationError):
            await self.light.get_state()

        self.ha.get_state.return_value = {"attributes": {}}
        with self.assertRaises(ValidationError):
            await self.light.get_state()

    async def test_turn_on_passes_options_to_home_assistant(self):
        await self.light.turn_on(colour="red", effect="Rainbow", flash="short")
        self.ha.call_service.assert_awaited_once_with(
            "light",
            "turn_on",
            {
                "entity_id": "light.desk",
                "rgb_color": [255, 0, 0],
                "effect": "Rainbow",
                "flash": "short",
            },
        )
        self.assertIn(self.light.turn_on, self.light.get_tools())

    async def test_blank_options_are_not_added_and_off_has_no_on_options(self):
        await self.light.turn_on()
        self.ha.call_service.assert_awaited_with(
            "light", "turn_on", {"entity_id": "light.desk"}
        )
        await self.light.turn_off()
        self.ha.call_service.assert_awaited_with(
            "light", "turn_off", {"entity_id": "light.desk"}
        )

    async def test_invalid_colour_or_flash_does_not_send_a_command(self):
        with self.assertRaises(ValueError):
            await self.light.turn_on(colour="not a colour")
        with self.assertRaises(ValidationError):
            await self.light.turn_on(flash="forever")
        self.ha.call_service.assert_not_awaited()

    async def test_home_reads_live_light_state_without_storing_it(self):
        home = Home(
            self.ha, Mock(), {}, HomeConfig(home_assistant_url="http://ha.test")
        )
        home.lights["desk"] = self.light
        self.ha.get_state.return_value = {"state": "on"}
        state = await home.get_home_state({"lights"})
        self.assertEqual(state["lights:desk"]["state"], "on")
        self.ha.get_state.return_value = {"state": "off"}
        inventory = await home.get_device_inventory()
        self.assertEqual(inventory[0]["state"], "off")
        self.assertFalse(hasattr(self.light, "state"))


class LightControlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.object(helpers, "is_pytest", return_value=True))
        temporary = self.enterContext(TemporaryDirectory())
        self.enterContext(patch.object(Storage, "path", Path(temporary)))
        self.ha = Mock(call_service=AsyncMock(), get_state=AsyncMock())
        self.ha.get_state.return_value = {
            "state": "off",
            "attributes": {"effect_list": ["Rainbow"]},
        }
        home = Home(
            self.ha, Mock(), {}, HomeConfig(home_assistant_url="http://ha.test")
        )
        self.light = Light("desk", "light.desk", self.ha)
        home.lights["desk"] = self.light
        home.light_groups["office"] = LightGroup(
            "office", {"main": self.light}, display_name="Office Lights"
        )
        api = FastAPI()
        api.state.home = home
        self.settings = {}

        def page():
            refresh = build_devices(api, self.settings)
            ui.timer(0, refresh, once=True)

        self.user = await self.enterAsyncContext(user_simulation(root=page))
        await self.user.open("/")
        await self.user.should_see(marker="power-lights:desk", retries=10)
        self.ha.get_state.reset_mock()

    async def wait_for_power(self, expected):
        # Assert observable state and readiness, rather than success-message text.
        for _ in range(100):
            power = next(iter(self.user.find(marker="power-lights:desk").elements))
            if (
                power.value is expected
                and power.enabled
                and next(
                    iter(self.user.find(marker="device-state-lights:desk").elements)
                ).text
                == ("on" if expected else "off")
            ):
                return
            await asyncio.sleep(0.02)
        self.fail(f"Toggle did not settle at {expected}")

    async def test_group_card_opens_for_one_light_and_tracks_confirmed_state(self):
        group = next(iter(self.user.find(marker="light-group-office").elements))
        self.assertTrue(group.value)
        self.assertEqual(group._props["caption"], "0 of 1 lights on")

        self.ha.get_state.return_value = {"state": "on"}
        self.user.find(marker="power-lights:desk").click()
        await self.wait_for_power(True)

        group = next(iter(self.user.find(marker="light-group-office").elements))
        self.assertEqual(group._props["caption"], "1 of 1 lights on")
        self.ha.call_service.assert_awaited_once_with(
            "light", "turn_on", {"entity_id": "light.desk"}
        )

    async def test_refresh_preserves_collapsed_group_without_sending_commands(self):
        group = next(iter(self.user.find(marker="light-group-office").elements))
        group.set_value(False)
        await asyncio.sleep(0)
        self.user.find("Refresh states").click()
        await asyncio.sleep(0.1)

        group = next(iter(self.user.find(marker="light-group-office").elements))
        self.assertFalse(group.value)
        self.ha.call_service.assert_not_awaited()

    async def test_settings_save_without_actions_then_toggle_forwards_options(self):
        self.user.find(marker="settings-lights:desk").click()
        await self.user.should_see("Desk settings", retries=10)
        await self.user.should_not_see("Loading available effects…", retries=10)
        self.user.find("Colour (optional)").type("red")
        self.user.find("Effect (optional)").type("Rainbow")
        self.user.find("Flash").click()
        self.user.find("Short flash").click()
        self.user.find("Save settings").click()
        self.ha.call_service.assert_not_awaited()
        self.assertEqual(
            self.settings["light_settings"]["lights:desk"],
            {
                "colour": "red",
                "effect": "Rainbow",
                "flash": "short",
            },
        )
        self.ha.get_state.return_value = {"state": "on", "attributes": {}}
        self.user.find(marker="power-lights:desk").click()
        await self.wait_for_power(True)
        self.ha.call_service.assert_awaited_once_with(
            "light",
            "turn_on",
            {
                "entity_id": "light.desk",
                "rgb_color": [255, 0, 0],
                "effect": "Rainbow",
                "flash": "short",
            },
        )
        self.ha.get_state.return_value = {"state": "off", "attributes": {}}
        self.user.find(marker="power-lights:desk").click()
        await self.wait_for_power(False)
        self.ha.call_service.assert_awaited_with(
            "light", "turn_off", {"entity_id": "light.desk"}
        )

    async def test_toggle_works_without_opening_settings(self):
        self.ha.get_state.return_value = {"state": "on", "attributes": {}}
        self.user.find(marker="power-lights:desk").click()
        await self.wait_for_power(True)
        self.ha.call_service.assert_awaited_once_with(
            "light", "turn_on", {"entity_id": "light.desk"}
        )
        self.assertFalse(next(iter(self.user.find(ui.dialog).elements)).value)
        await self.user.should_not_see(marker="light-error-lights:desk")
        await self.user.should_not_see("Command sent")

    async def test_refresh_reads_external_switch_changes_without_sending_commands(self):
        self.ha.get_state.return_value = {"state": "on"}
        self.user.find("Refresh states").click()
        await self.wait_for_power(True)
        self.ha.call_service.assert_not_awaited()
        self.ha.get_state.assert_awaited_once_with("light.desk")

    async def test_retry_clears_previous_error_after_success(self):
        self.ha.call_service.side_effect = httpx.ConnectError("HA is unreachable")
        self.user.find(marker="power-lights:desk").click()
        await self.user.should_see(marker="light-error-lights:desk", retries=10)
        self.ha.get_state.assert_not_awaited()

        self.ha.call_service.side_effect = None
        self.ha.get_state.return_value = {"state": "on"}
        self.user.find(marker="power-lights:desk").click()
        await self.wait_for_power(True)
        await self.user.should_not_see(marker="light-error-lights:desk")

    async def test_one_click_waits_for_delayed_on_and_off_state(self):
        self.ha.get_state.side_effect = [
            {"state": "off"},
            {"state": "off"},
            {"state": "on"},
        ]
        self.user.find(marker="power-lights:desk").click()
        await self.wait_for_power(True)
        self.assertTrue(
            next(iter(self.user.find(marker="power-lights:desk").elements)).value
        )
        self.ha.call_service.assert_awaited_once_with(
            "light", "turn_on", {"entity_id": "light.desk"}
        )

        self.ha.get_state.side_effect = [
            {"state": "on"},
            {"state": "on"},
            {"state": "off"},
        ]
        self.user.find(marker="power-lights:desk").click()
        await self.wait_for_power(False)
        self.assertFalse(
            next(iter(self.user.find(marker="power-lights:desk").elements)).value
        )
        self.assertEqual(self.ha.call_service.await_count, 2)

    async def test_refresh_keeps_requested_position_until_state_is_confirmed(self):
        confirm = asyncio.Event()
        read_started = asyncio.Event()

        async def delayed_state(*args):
            read_started.set()
            await confirm.wait()
            return {"state": "on"}

        self.ha.get_state.side_effect = delayed_state
        self.user.find(marker="power-lights:desk").click()
        await asyncio.wait_for(read_started.wait(), timeout=2)
        self.user.find("Refresh states").click()
        await asyncio.sleep(0)
        power = next(iter(self.user.find(marker="power-lights:desk").elements))
        self.assertTrue(power.value)
        self.assertFalse(power.enabled)
        confirm.set()
        await self.wait_for_power(True)
        self.ha.call_service.assert_awaited_once()

    async def test_unconfirmed_state_stops_waiting_without_resending_command(self):
        self.enterContext(
            patch.object(devices_page, "STATE_CONFIRMATION_TIMEOUT", 0.05)
        )
        self.enterContext(patch.object(devices_page, "STATE_POLL_INTERVAL", 0.01))
        self.user.find(marker="power-lights:desk").click()
        await self.user.should_see(
            "Command sent, but the requested state hasn’t been confirmed yet.",
            retries=10,
        )
        power = next(iter(self.user.find(marker="power-lights:desk").elements))
        self.assertFalse(power.value)
        self.assertTrue(power.enabled)
        self.ha.call_service.assert_awaited_once()

    async def test_settings_are_restored_after_reload_without_turning_on(self):
        self.settings["light_settings"] = {
            "lights:desk": {"colour": "blue", "effect": "Rainbow", "flash": "long"}
        }
        await self.user.open("/")
        await self.user.should_see(marker="settings-lights:desk", retries=10)
        self.user.find(marker="settings-lights:desk").click()
        await self.user.should_see("Desk settings", retries=10)
        await self.user.should_not_see("Loading available effects…", retries=10)
        colour = next(iter(self.user.find("Colour (optional)").elements))
        effect = next(iter(self.user.find("Effect (optional)").elements))
        flash = next(iter(self.user.find("Flash").elements))
        self.assertEqual(colour.value, "blue")
        self.assertEqual(effect.value, "Rainbow")
        self.assertEqual(flash.value, "long")
        self.ha.call_service.assert_not_awaited()

    async def test_successful_command_is_distinguished_from_failed_state_read(self):
        self.ha.get_state.side_effect = httpx.ConnectError("HA is unreachable")
        self.user.find(marker="power-lights:desk").click()
        await self.user.should_see(
            "Command sent, but the state couldn’t be refreshed.", retries=10
        )
        self.ha.call_service.assert_awaited_once()
        # Failed reads are explicit, rather than falling back to an old device cache.
        self.assertEqual(
            next(iter(self.user.find(marker="device-state-lights:desk").elements)).text,
            "unavailable",
        )
