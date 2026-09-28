from .devices import Light, Speaker
from .integrations import HomeAssistantClient, SpotifyClient


class Home:
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        spotify_client: SpotifyClient,
    ):
        self.ha_client = ha_client
        self.spotify_client = spotify_client

        self.lights: dict[str, Light] = {}
        self.speakers: dict[str, Speaker] = {}

    async def initialise(self):
        self._init_lights()
        self._init_speakers()
        

    def _init_lights(self):
        self.lights["office"] = Light(
            name="office",
            ha_entity_id="light.josh_office",
            ha_client=self.ha_client,
        )

        self.lights["living_room_1"] = Light(
            name="living_room_1",
            ha_entity_id="light.living_room_1",
            ha_client=self.ha_client,
        )

        self.lights["living_room_2"] = Light(
            name="living_room_2",
            ha_entity_id="light.living_room_2",
            ha_client=self.ha_client,
        )

        self.lights["living_room_3"] = Light(
            name="living_room_3",
            ha_entity_id="light.living_room_3",
            ha_client=self.ha_client,
        )

        self.lights["kitchen"] = Light(
            name="kitchen",
            ha_entity_id="light.kitchen",
            ha_client=self.ha_client,
        )

    def _init_speakers(self):
        self.speakers["bedroom"] = Speaker(
            name="bedroom",
            spotify_id="bd524fff21a112e1753ff548259324df1c639ec3",
            spotify_client=self.spotify_client
        )

    async def close(self) -> None:
        await self.ha_client.close()