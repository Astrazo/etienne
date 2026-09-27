from .devices import Light, Speaker
from .integrations import HomeAssistantClient, SpotifyClient


class Home:
    def __init__(
        self,
        ha: HomeAssistantClient,
        spotify: SpotifyClient,
    ):
        self.ha = ha
        self.spotify = spotify

        self.lights: dict[str, Light] = {}
        self.speakers: dict[str, Speaker] = {}

    async def initialise(self):
        self.lights["office"] = Light(
            entity_id="light.josh_office",
            ha=self.ha,
        )

        self.lights["living_room_1"] = Light(
            entity_id="light.living_room_1",
            ha=self.ha,
        )

        self.lights["living_room_2"] = Light(
            entity_id="light.living_room_2",
            ha=self.ha,
        )

        self.lights["living_room_3"] = Light(
            entity_id="light.living_room_3",
            ha=self.ha,
        )

        self.lights["kitchen"] = Light(
            entity_id="light.kitchen",
            ha=self.ha,
        )