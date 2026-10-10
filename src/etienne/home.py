import asyncio
from pathlib import Path
from typing import Literal

from .devices import TV, Light, Speaker
from .integrations import ADBClient, HomeAssistantClient, SpotifyClient

DeviceCollection = Literal["speakers", "lights", "tvs"]


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

    @property
    def active_spotify_speaker(self) -> Speaker | None:
        return next(
            (speaker for speaker in self.speakers.values() if speaker.state.is_active),
            None,
        )

    async def initialise(self, db_path: Path):
        # Connect to Tvs via all adb clients
        await self.adb_client_living_room.connect()

        # Build Etienne owned objects
        self._init_lights()
        self._init_speakers(db_path)
        self._init_tvs()

        # Build the initial state for integrations that support state refreshes.
        await self.refresh_home_state({"speakers"})

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

        self.speakers["josh_pc"] = Speaker(
            name="josh_pc",
            spotify_id="ddd4b2e1a53f188886d633437586b9dd59047661",
            spotify_client=self.spotify_client,
            db_path=db_path,
        )

    def _init_tvs(self):
        self.tvs["living_room"] = TV(
            "living_room", adb_client=self.adb_client_living_room
        )

    async def refresh_home_state(
        self,
        device_types: set[DeviceCollection],
    ) -> None:
        """Refresh state for the requested device collections."""
        unsupported_types = device_types - {"speakers"}
        if unsupported_types:
            names = ", ".join(sorted(unsupported_types))
            raise NotImplementedError(f"State refresh is not implemented for: {names}")

        refresh_tasks = []

        if "speakers" in device_types:
            refresh_tasks.append(self._refresh_speaker_states())

        await asyncio.gather(*refresh_tasks)

    async def _refresh_speaker_states(self) -> None:

        snapshot = await asyncio.to_thread(self.spotify_client.get_status_snapshot)

        spotify_devices = snapshot["devices"]
        current_playback = snapshot["current_playback"]

        for speaker in self.speakers.values():
            # Get the device info
            spotify_device = next(
                (
                    device
                    for device in spotify_devices
                    if device.get("id") == speaker.spotify_id
                ),
                None,
            )

            is_active = spotify_device is not None and spotify_device.get(
                "is_active", False
            )
            speaker_playback = current_playback if is_active else None

            speaker.refresh_state(spotify_device, speaker_playback)

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

    def get_home_state(self) -> dict:
        return {
            "spotify": self._get_spotify_state(),
            # "lights": ...,
            # "tvs": ...,
        }

    def _get_spotify_state(self) -> dict:
        active_speaker = self.active_spotify_speaker

        if active_speaker is None:
            return {
                "active_speaker": None,
                "playback": None,
            }

        return {
            "active_speaker": active_speaker.name,
            "playback": active_speaker.state.model_dump(mode="json"),
        }
