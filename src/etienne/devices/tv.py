import asyncio
from collections.abc import Callable
from typing import Literal

from ..integrations import ADBClient, HomeAssistantClient
from ..integrations.adb import UIElement

TVApp = Literal[
    "disney",
    "netflix",
    "crunchyroll",
    "youtube",
]


class TV:
    def __init__(
        self,
        name: str,
        adb_client: ADBClient,
        ha_entity_id: str | None = None,
        ha_client: HomeAssistantClient | None = None,
    ):
        self.name = name
        self.adb_client = adb_client
        self.ha_entity_id = ha_entity_id
        self.ha_client = ha_client

        self.APP_PACKAGES = {
            "disney": "com.disney.disneyplus",
            "netflix": "com.netflix.ninja",
            "crunchyroll": "com.crunchyroll.crunchyroid",
            "youtube": "com.google.android.youtube.tv",
        }

    async def up(self) -> None:
        await self.adb.send_key("KEYCODE_DPAD_UP")

    async def down(self) -> None:
        await self.adb.send_key("KEYCODE_DPAD_DOWN")

    async def left(self) -> None:
        await self.adb.send_key("KEYCODE_DPAD_LEFT")

    async def right(self) -> None:
        await self.adb.send_key("KEYCODE_DPAD_RIGHT")

    async def select(self) -> None:
        await self.adb.send_key("KEYCODE_DPAD_CENTER")

    async def back(self) -> None:
        await self.adb.send_key("KEYCODE_BACK")

    async def home(self) -> None:
        await self.adb.send_key("KEYCODE_HOME")

    async def open_app(self, app: TVApp) -> None:
        """Open an installed app

        Args:
            app (TVApp): _description_
        """
        package = self.APP_PACKAGES[app]

        await self.adb_client.open_app(package)

    async def play_show(
        self,
        app: str,
        show: str,
    ) -> None:
        await self.open_app(app)

        await asyncio.sleep(2)

        if app == "disney" and show == "family-guy":
            await self.adb_client.send_key("KEYCODE_DPAD_DOWN")
            await self.adb_client.send_key("KEYCODE_DPAD_DOWN")
            await self.adb_client.send_key("KEYCODE_DPAD_CENTER")
            await self.adb_client.send_key("KEYCODE_DPAD_CENTER")

    async def focused_element(self) -> UIElement | None:
        return await self.adb.get_focused_element()

    def get_tools(self) -> list[Callable]:
        """Return the light operations available to ollama."""
        return []
