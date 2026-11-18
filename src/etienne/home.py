import asyncio
from pathlib import Path
from typing import Literal

import httpx
from loguru import logger
from pydantic import ValidationError
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException

from .config import HomeConfig
from .devices import TV, Device, Light, LightGroup, Speaker
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
        self.light_groups: dict[str, LightGroup] = {}

    async def initialise(self, db_path: Path):
        # Connect to Tvs via all adb clients
        logger.info("Connecting to {} TVs", len(self.adb_clients))
        for adb_client in self.adb_clients.values():
            await adb_client.connect()

        # Build Etienne owned objects
        self._init_lights()
        self._init_speakers(db_path)
        self._init_tvs()

        # Groups reference the devices created above; they don't create copies.
        self._init_light_groups()
        logger.info(
            "Home devices initialised: {} lights, {} speakers, {} TVs, {} light groups",
            len(self.lights),
            len(self.speakers),
            len(self.tvs),
            len(self.light_groups),
        )

    def _init_lights(self):
        for group_id, group_config in self.config.lights.items():
            for device_id, light_config in group_config.devices.items():
                # Include the group so IDs like "main" can appear in several rooms.
                device_key = f"{group_id}.devices.{device_id}"
                self.lights[device_key] = Light(
                    device_id=device_id,
                    ha_entity_id=light_config.ha_entity_id,
                    ha_client=self.ha_client,
                    display_name=light_config.display_name,
                )

    def _init_speakers(self, db_path: Path):
        for device_id, speaker_config in self.config.speakers.items():
            self.speakers[device_id] = Speaker(
                device_id=device_id,
                spotify_id=speaker_config.spotify_id,
                spotify_client=self.spotify_client,
                db_path=db_path,
                display_name=speaker_config.display_name,
            )

    def _init_tvs(self):
        for device_id, config in self.config.tvs.items():
            self.tvs[device_id] = TV(
                device_id=device_id,
                adb_client=self.adb_clients[device_id],
                ha_entity_id=config.ha_entity_id,
                ha_client=self.ha_client,
                display_name=config.display_name,
            )

    def _init_light_groups(self):
        for group_id, group_config in self.config.lights.items():
            devices = {}
            for device_id in group_config.devices:
                device_key = f"{group_id}.devices.{device_id}"
                devices[device_id] = self.lights[device_key]

            self.light_groups[group_id] = LightGroup(
                group_id=group_id,
                ha_client=self.ha_client,
                devices=devices,
                display_name=group_config.display_name,
            )

    async def close(self) -> None:
        await self.ha_client.close()

    def get_device_map(self) -> dict[str, Device]:
        """Return devices by keys such as lights:kitchen.devices.main."""
        devices = {}

        # For each device type
        for device_type in ("speakers", "tvs", "lights", "light_groups"):
            # Grab the dictionary lookup for each this device type
            device_group = getattr(self, device_type)

            # For each device identifier and object in the dictionary
            for device_key, device in device_group.items():
                # Create the key (speaker:bedroom) for example
                key = f"{device_type}:{device_key}"

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
            for device_key, light in self.lights.items():
                home_state[f"lights:{device_key}"] = await self._read_device_state(light)

        # Read each registered TV directly from Home Assistant.
        if "tvs" in device_types:
            for device_id, tv in self.tvs.items():
                home_state[f"tvs:{device_id}"] = await self._read_device_state(tv)

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
            for device_id in self.speakers:
                speaker_states[f"speakers:{device_id}"] = {
                    "state": "unavailable",
                    "error": "Could not read current Spotify state.",
                }
            return speaker_states

        # Convert the response to each speaker's current playback details.
        speaker_states = {}
        for device_id, speaker in self.speakers.items():
            state = await speaker.get_state(snapshot) # Get state requires a snapshot to extract data from
            speaker_states[f"speakers:{device_id}"] = state.model_dump(mode="json")

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
            logger.warning("Could not read current state for {}", device.device_id)
            return {
                "state": "unavailable",
                "error": "Could not read the device's current state.",
            }

    async def get_device_display_data(self) -> list[dict]:
        """Read live state and build the device cards returned to the UI and API."""
        home_state = await self.get_home_state()
        devices = self.get_device_map()
        inventory = []

        for device_key, device in devices.items():

            # Skip light groups as they don't contribute to inventory
            if isinstance(device, LightGroup):
                continue

            snapshot = home_state[device_key]

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
                raise TypeError(f"Unsupported registered device: {device_key}")

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
                "id": device_key,
                "name": device.display_name,
                "type": device_type,
                "state": state,
                "source": source,
            }

            # Include read failures so the UI can explain unavailable state.
            if "error" in snapshot:
                entry["error"] = snapshot["error"]

            inventory.append(entry)

        return inventory
