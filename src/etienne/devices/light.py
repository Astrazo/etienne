import webcolors

from etienne.integrations.home_assistant import HomeAssistantClient


class Light:
    def __init__(
        self,
        name: str,
        ha_entity_id: str,
        ha_client: HomeAssistantClient,
    ):
        self.name = name
        self.ha_entity_id = ha_entity_id
        self.ha_client = ha_client

    async def turn_on(
        self,
        effect: str | None = None,
        colour: str | None = None,
        flash: str | None = None,
    ) -> None:
        body = {"entity_id": self.ha_entity_id}

        if effect is not None:
            body["effect"] = effect

        if colour is not None:
            rgb = webcolors.name_to_rgb(colour)
            body["rgb_color"] = [rgb.red, rgb.green, rgb.blue]

        if flash is not None:
            body["flash"] = flash

        await self.ha_client.call_service(
            "light",
            "turn_on",
            body,
        )

    async def turn_off(self) -> None:
        await self.ha_client.call_service(
            "light",
            "turn_off",
            {"entity_id": self.ha_entity_id},
        )

    async def get_state(self) -> dict:
        return await self.ha_client.get_state(self.ha_entity_id)
