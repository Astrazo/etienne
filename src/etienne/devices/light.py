from collections.abc import Callable
from typing import Literal

import webcolors
from pydantic import validate_call

from etienne.integrations.home_assistant import HomeAssistantClient

from .models import LightState


class Light:
    def __init__(
        self,
        device_id: str,
        ha_entity_id: str,
        ha_client: HomeAssistantClient,
        display_name: str | None = None,
        device_key: str | None = None,
    ):
        self.device_id = device_id  # Config member key, such as "main".
        self.device_key = device_key or device_id  # Home lookup, such as "kitchen.devices.main".
        self.display_name = display_name or device_id.replace("_", " ").title()
        self.ha_entity_id = ha_entity_id
        self.ha_client = ha_client

    @validate_call
    async def turn_on(
        self,
        effect: str | None = None,
        colour: str | None = None,
        flash: Literal["short", "long"] | None = None,
    ) -> None:
        """Turn on this light with optional effects.

        Args:
            effect (str | None, optional): Effect for the light. Defaults to None.
            colour (str | None, optional): Colour of the light. Defaults to None.
            flash (str | None, optional): If the light should be flashing. Defaults to None.
        """
        # Build request body
        body = {"entity_id": self.ha_entity_id}

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
        """Turn off this light."""

        # Build request body
        body = {"entity_id": self.ha_entity_id}

        # Call HA service
        await self.ha_client.call_service(
            "light",
            "turn_off",
            body,
        )

    async def get_state(self) -> LightState:
        """Fetch HA's latest known state and validate the light-specific fields."""
        if self.ha_client is None or self.ha_entity_id is None:
            raise NotImplementedError("Light state reading requires an HA entity")

        response = await self.ha_client.get_state(self.ha_entity_id)
        return LightState.model_validate(response)

    def get_tools(self) -> list[Callable]:
        """Return the light operations available to ollama."""
        return [self.turn_on, self.turn_off]
