"""Code to handle external integrations i.e providers
"""
from .home_assistant import HomeAssistantClient
from .spotify import SpotifyClient
from .adb import ADBClient

__all__ = [
    "HomeAssistantClient",
    "SpotifyClient",
    "ADBClient"
]