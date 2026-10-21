import os

from dotenv import load_dotenv
from spotipy import Spotify, SpotifyOAuth

from .api.app import init_app
from .assistant.laya_client import LayaClient
from .assistant.ollama_client import OllamaClient
from .config import load_config
from .home import Home
from .integrations import ADBClient, HomeAssistantClient, SpotifyClient

load_dotenv()
config = load_config()


HOME_ASSISTANT_TOKEN = os.getenv("HA_TOKEN")

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

ha_client = HomeAssistantClient(config.home_assistant_url, HOME_ASSISTANT_TOKEN)
spotify_client = SpotifyClient(SPOTIFY_CLIENT)
adb_clients = {
    name: ADBClient(tv.host, port=tv.port) for name, tv in config.tvs.items()
}

home = Home(ha_client, spotify_client, adb_clients, config)
laya_client = LayaClient()
ollama_client = OllamaClient(
    "qwen3.5:latest",
    "You're an assistant to help direct user requests to the right tool call on the server.",
    False,
)

app = init_app(home, laya_client, ollama_client)
