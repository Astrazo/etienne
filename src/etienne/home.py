from pathlib import Path

from .devices import TV, Light, Speaker
from .integrations import ADBClient, HomeAssistantClient, SpotifyClient


class Home:
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        spotify_client: SpotifyClient,
        adb_client_living_room: ADBClient,
    ):
        self.ha_client = ha_client
        self.spotify_client = spotify_client
        self.adb_client_living_room = adb_client_living_room

        self.lights: dict[str, Light] = {}
        self.speakers: dict[str, Speaker] = {}
        self.tvs: dict[str, TV] = {}

    async def initialise(self, db_path: Path):
        # Connect to Tvs via all adb clients
        await self.adb_client_living_room.connect()

        # Build Etienne owned objects
        self._init_lights()
        self._init_speakers(db_path)
        self._init_tvs()

    def _init_lights(self):
        self.lights["josh_office"] = Light(
            name="josh_office",
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

    def _init_speakers(self, db_path: Path):
        self.speakers["bedroom"] = Speaker(
            name="bedroom",
            spotify_id="bd524fff21a112e1753ff548259324df1c639ec3",
            spotify_client=self.spotify_client,
            db_path=db_path,
        )

        self.speakers["living_room"] = Speaker(
            name="living_room",
            spotify_id="c2f34440bf4982af8a18286dcf308c48dfb7b416",
            spotify_client=self.spotify_client,
            db_path=db_path,
        )

    def _init_tvs(self):
        self.tvs["living_room"] = TV(
            "living_room", adb_client=self.adb_client_living_room
        )

    async def close(self) -> None:
        await self.ha_client.close()

    def get_device_map(self) -> dict[str, object]:
        """Used to build a static lookup of devices that can be passed to Ollama

        Returns:
            dict[str, object]: _description_
        """
        return {
            f"{device_type}:{device_name}": device
            for device_type in ("speakers", "tvs", "lights")
            for device_name, device in getattr(self, device_type).items()
        }
