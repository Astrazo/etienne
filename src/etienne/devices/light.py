import webcolors

from etienne.integrations.home_assistant import HomeAssistantClient


class Light:
    def __init__(
        self,
        entity_id: str,
        ha: HomeAssistantClient,
    ):
        self.entity_id = entity_id
        self.ha = ha

    async def turn_on(
        self,
        effect: str | None = None,
        colour: str | None = None,
        flash: str | None = None,
    ) -> None:
        body = {"entity_id": self.entity_id}

        if effect is not None:
            body["effect"] = effect

        if colour is not None:
            rgb = webcolors.name_to_rgb(colour)
            body["rgb_color"] = [rgb.red, rgb.green, rgb.blue]

        if flash is not None:
            body["flash"] = flash

        await self.ha.call_service(
            "light",
            "turn_on",
            body,
        )

    async def turn_off(self) -> None:
        await self.ha.call_service(
            "light",
            "turn_off",
            {"entity_id": self.entity_id},
        )

    async def get_state(self) -> dict:
        return await self.ha.get_state(self.entity_id)