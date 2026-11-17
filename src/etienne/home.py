import asyncio
from pathlib import Path
from typing import Literal

import httpx
from loguru import logger
from pydantic import ValidationError
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from .config import HomeConfig
from .devices import TV, Device, Light, Speaker
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

    async def initialise(self, db_path: Path):
        # Connect to Tvs via all adb clients
        logger.info("Connecting to {} TVs", len(self.adb_clients))
        for adb_client in self.adb_clients.values():
            await adb_client.connect()

        # Build Etienne owned objects
        self._init_lights()
        self._init_speakers(db_path)
        self._init_tvs()
        logger.info(
            "Home devices initialised: {} lights, {} speakers, {} TVs",
            len(self.lights),
            len(self.speakers),
            len(self.tvs),
        )

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
        for name, config in self.config.tvs.items():
            self.tvs[name] = TV(
                name,
                adb_client=self.adb_clients[name],
                ha_entity_id=config.ha_entity_id,
                ha_client=self.ha_client,
            )

    async def close(self) -> None:
        await self.ha_client.close()

    def get_device_map(self) -> dict[str, Device]:
        """Return the initialized devices by their canonical category:name keys."""
        devices = {}

        # For each device type
        for device_type in ("speakers", "tvs", "lights"):
            # Grab the dictionary lookup for each this device type
            device_group = getattr(self, device_type)

            # For each device name and object in the dicionary
            for device_name, device in device_group.items():
                # Create the key (speaker:bedroom) for example
                key = f"{device_type}:{device_name}"

                # Create a key pair linking that key to the specific device so functions can be called on it
                devices[key] = device

        return devices

    async def get_home_state(
        self,
        device_types: set[Literal["speakers", "lights", "tvs"]] | None = None,
    ) -> dict[str, dict]:
        """Read live state for the requested device types, or all types if omitted."""

        # Refresh everything if no device types are sent
        if device_types is None:
            device_types = {"speakers", "lights", "tvs"}

        # Check the requested types before making any device calls.
        for device_type in device_types:
            if device_type not in ("speakers", "lights", "tvs"):
                raise ValueError(f"Unknown device type: {device_type}")

        home_state = {}

        # Speakers share one Spotify response for this request.
        if "speakers" in device_types and self.speakers:
            speaker_states = await self._read_speaker_states()
            home_state.update(speaker_states)

        # Read each registered light directly from Home Assistant.
        if "lights" in device_types:
            for name, light in self.lights.items():
                home_state[f"lights:{name}"] = await self._read_device_state(light)

        # Read each registered TV directly from Home Assistant.
        if "tvs" in device_types:
            for name, tv in self.tvs.items():
                home_state[f"tvs:{name}"] = await self._read_device_state(tv)

        return home_state

    async def _read_speaker_states(self) -> dict[str, dict]:
        """Fetch Spotify once, then read each registered speaker from that response."""
        try:
            async with asyncio.timeout(10):
                snapshot = await asyncio.to_thread(
                    self.spotify_client.get_status_snapshot
                )
        except SpotifyException, RequestException, TimeoutError:
            logger.warning("Could not read current Spotify state")
            speaker_states = {}
            for name in self.speakers:
                speaker_states[f"speakers:{name}"] = {
                    "state": "unavailable",
                    "error": "Could not read current Spotify state.",
                }
            return speaker_states

        # Convert the response to each speaker's current playback details.
        speaker_states = {}
        for name, speaker in self.speakers.items():
            state = await speaker.get_state(snapshot) # Get state requires a snapshot to extract data from
            speaker_states[f"speakers:{name}"] = state.model_dump(mode="json")

        return speaker_states

    async def _read_device_state(self, device: Light | TV) -> dict:
        """Read a device without letting an offline device fail the whole request."""
        try:
            async with asyncio.timeout(10):
                state = await device.get_state()
                return state.model_dump(mode="json")
        except NotImplementedError:
            return {
                "state": "unknown",
                "error": "Live state reading is not configured for this device.",
            }
        except (
            httpx.HTTPError,
            RequestException,
            TimeoutError,
            ValidationError,
        ):
            logger.warning("Could not read current state for {}", device.name)
            return {
                "state": "unavailable",
                "error": "Could not read the device's current state.",
            }

    async def get_device_inventory(self) -> list[dict]:
        """Read live state and build the device cards returned to the UI and API."""
        home_state = await self.get_home_state()
        devices = self.get_device_map()
        inventory = []

        for device_id, device in devices.items():
            snapshot = home_state[device_id]

            # Identify the device type and the integration behind it.
            if isinstance(device, Speaker):
                device_type = "speaker"
                source = "Spotify"
            elif isinstance(device, Light):
                device_type = "light"
                source = "Home Assistant"
            elif isinstance(device, TV):
                device_type = "tv"
                source = "Home Assistant"
            else:
                raise TypeError(f"Unsupported registered device: {device_id}")

            # Lights and TVs report a state label directly. Spotify reports flags.
            state = snapshot.get("state", "unknown")
            if isinstance(device, Speaker) and "error" not in snapshot:
                if not snapshot["available"]:
                    state = "unavailable"
                elif not snapshot["is_active"]:
                    state = "idle"
                elif snapshot["is_playing"]:
                    state = "playing"
                else:
                    state = "paused"

            # Build the card data from this device and its live reading.
            entry = {
                "id": device_id,
                "name": device.name.replace("_", " ").title(),
                "type": device_type,
                "state": state,
                "source": source,
            }

            # Include read failures so the UI can explain unavailable state.
            if "error" in snapshot:
                entry["error"] = snapshot["error"]

            inventory.append(entry)

        return inventory
