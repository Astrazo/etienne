import os

from dotenv import load_dotenv
from spotipy import Spotify, SpotifyOAuth

from .api.app import init_app
from .home import Home
from .integrations import (
    HomeAssistantClient,
    SpotifyClient,
)

load_dotenv()


HOME_ASSISTANT_URL = "http://homeassistant.local"
HOME_ASSISTANT_TOKEN = os.getenv("HA_TOKEN")

SPOTIFY_CLIENT = Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=(
            "user-read-playback-state "
            "user-modify-playback-state "
            "playlist-read-private"
        ),
    )
)

ha_client = HomeAssistantClient(HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN)
spotify_client = SpotifyClient(SPOTIFY_CLIENT)

home = Home(ha_client, spotify_client)

app = init_app(home)
