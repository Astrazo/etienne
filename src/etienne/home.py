import asyncio
from pathlib import Path
from typing import Literal

from .config import HomeConfig
from .devices import TV, Light, Speaker
from .integrations import ADBClient, HomeAssistantClient, SpotifyClient


class Home:
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        spotify_client: SpotifyClient,
        adb_clients: dict[str, ADBClient],
        config: HomeConfig,
    ):
        self.ha_client = ha_client
        self.spotify_client = spotify_client
        self.adb_clients = adb_clients
        self.config = config

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
        for adb_client in self.adb_clients.values():
            await adb_client.connect()

        # Build Etienne owned objects
        self._init_lights()
        self._init_speakers(db_path)
        self._init_tvs()

        # Build the initial state for integrations that support state refreshes.
        await self.refresh_home_state({"speakers"})

    def _init_lights(self):
        for name, entity_id in self.config.lights.items():
            self.lights[name] = Light(
                name=name,
                ha_entity_id=entity_id,
                ha_client=self.ha_client,
            )

    def _init_speakers(self, db_path: Path):
        for name, spotify_id in self.config.speakers.items():
            self.speakers[name] = Speaker(
                name=name,
                spotify_id=spotify_id,
                spotify_client=self.spotify_client,
                db_path=db_path,
            )

    def _init_tvs(self):
        for name in self.config.tvs:
            self.tvs[name] = TV(name, adb_client=self.adb_clients[name])

    async def refresh_home_state(
        self,
        device_types: set[Literal["speakers", "lights", "tvs"]],
    ) -> None:
        """Refresh state for the requested device collections."""
        unsupported_types = device_types - {"speakers"}
        if unsupported_types:
            names = ", ".join(sorted(unsupported_types))
            raise NotImplementedError(f"State refresh is not implemented for: {names}")

        refresh_tasks = []

        if "speakers" in device_types:
            refresh_tasks.append(self._refresh_speaker_states())
        if "lights" in device_types:
            pass
        if "tvs" in device_types:
            pass

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
