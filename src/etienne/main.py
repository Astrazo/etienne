import os

from dotenv import load_dotenv
from spotipy import Spotify, SpotifyOAuth

from .api.app import init_app
from .assistant.laya_client import LayaClient
from .assistant.ollama_client import OllamaClient
from .home import Home
from .integrations import ADBClient, HomeAssistantClient, SpotifyClient

load_dotenv()


HOME_ASSISTANT_URL = "http://homeassistant.local"
HOME_ASSISTANT_TOKEN = os.getenv("HA_TOKEN")
LIVING_ROOM_TV_IP = os.getenv("LIVING_ROOM_TV_IP")
PLATFORM_TOOLS_PATH = os.getenv("PLATFORM_TOOLS_PATH")

SPOTIFY_CLIENT = Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=(
            "user-read-playback-state user-modify-playback-state playlist-read-private"
        ),
    )
)

ha_client = HomeAssistantClient(HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN)
spotify_client = SpotifyClient(SPOTIFY_CLIENT)
adb_client_living_room = ADBClient(LIVING_ROOM_TV_IP)

home = Home(ha_client, spotify_client, adb_client_living_room)
laya_client = LayaClient()
ollama_client = OllamaClient(
    "qwen3.5:latest",
    "Call the correct tool with the appropriate arguments to assist with the user's request.",
    False,
)

app = init_app(home, laya_client, ollama_client)
