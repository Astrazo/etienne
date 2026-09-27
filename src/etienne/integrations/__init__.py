"""Code to handle external integrations i.e providers
"""
from .home_assistant import HomeAssistantClient
from .spotify import SpotifyClient

__all__ = [
    "HomeAssistantClient",
    "SpotifyClient",
]