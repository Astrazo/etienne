from collections.abc import Callable

import webcolors
from pydantic import BaseModel

from etienne.integrations.home_assistant import HomeAssistantClient


class LightState(BaseModel):
    on: bool | None = None
    colour: str | None = None


class Light:
    def __init__(
        self,
        name: str,
        ha_entity_id: str,
        ha_client: HomeAssistantClient,
    ):
        self.name = name
        self.state = LightState()
        self.ha_entity_id = ha_entity_id
        self.ha_client = ha_client

    async def turn_on(
        self,
        effect: str | None = None,
        colour: str | None = None,
        flash: str | None = None,
    ) -> None:
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

        # Build request body
        body = {"entity_id": self.ha_entity_id}

        # Call HA service
        await self.ha_client.call_service(
            "light",
            "turn_off",
            body,
        )

    async def get_ha_state(self) -> dict:
        """Get the state of the light as reported by HA.

        Returns:
            dict: HA state dictionary.
        """
        return await self.ha_client.get_state(self.ha_entity_id)

    def get_tools(self) -> list[Callable]:
        """Return the light operations available to ollama."""
        return [self.turn_on, self.turn_off]
