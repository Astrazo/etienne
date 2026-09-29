"""Code to handle external integrations i.e providers"""

from .adb import ADBClient
from .home_assistant import HomeAssistantClient
from .spotify import SpotifyClient

__all__ = ["ADBClient", "HomeAssistantClient", "SpotifyClient"]
