"""A named group referencing individually registered lights."""

from collections.abc import Callable
from typing import Literal

import webcolors
from pydantic import validate_call

from etienne.devices.models import LightGroupState
from etienne.integrations.home_assistant import HomeAssistantClient

from .light import Light


class LightGroup:
    def __init__(
        self,
        group_id: str,
        devices: dict[str, Light],
        display_name: str | None = None,
        ha_client: HomeAssistantClient | None = None,
    ):
        self.group_id = group_id
        self.display_name = display_name or group_id.replace("_", " ").title()
        self.ha_client = ha_client
        self.devices = devices

    @property
    def group_ha_ids(self) -> list[str]:
        ha_ids = []
        for light in self.devices.values():
            ha_ids.append(light.ha_entity_id)
        return ha_ids

    @validate_call
    async def turn_on(
        self,
        effect: str | None = None,
        colour: str | None = None,
        flash: Literal["short", "long"] | None = None,
    ) -> None:
        """Turn on this light group with optional effects.

        Args:
            effect (str | None, optional): Effect for the light group. Defaults to None.
            colour (str | None, optional): Colour of the light group. Defaults to None.
            flash (str | None, optional): If the light group should be flashing. Defaults to None.
        """

        # Build request body
        body = {"entity_id": self.group_ha_ids}

        if effect is not None:
            body["effect"] = effect

        if colour is not None:
            rgb = webcolors.name_to_rgb(colour)
            body["rgb_color"] = [rgb.red, rgb.green, rgb.blue]

        if flash is not None:
            body["flash"] = flash

        # Call HA service
        await self.ha_client.call_service(
            "light",
            "turn_on",
            body,
        )

    async def turn_off(self) -> None:
        """Turn off this group."""

        # Build request body
        body = {"entity_id": self.group_ha_ids}

        # Call HA service
        await self.ha_client.call_service(
            "light",
            "turn_off",
            body,
        )

    async def get_state(self) -> LightGroupState:
        """Read the current state of each light in this group."""
        devices = {}

        for device_id, light in self.devices.items():
            devices[device_id] = await light.get_state()

        return LightGroupState(devices=devices)

    def get_tools(self) -> list[Callable]:
        """Return the light group operations available to ollama."""
        return [self.turn_on, self.turn_off]
