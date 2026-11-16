import os

from dotenv import load_dotenv
from spotipy import Spotify, SpotifyOAuth
from loguru import logger

from .api.app import init_app
from .assistant.laya_client import LayaClient
from .assistant.ollama_client import OllamaClient
from .config import load_config
from .home import Home
from .integrations import ADBClient, HomeAssistantClient, SpotifyClient

logger.info("Starting Etienne")

# Load env vars
load_dotenv()
try:
    config = load_config()
except FileNotFoundError as e:
    logger.error(e)
    raise SystemExit(1)
logger.info("Configuration loaded")

# Build spotify client
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
spotify_client = SpotifyClient(SPOTIFY_CLIENT)
logger.info("Spotify client configured")

# Build HA client
HOME_ASSISTANT_TOKEN = os.getenv("HA_TOKEN")
ha_client = HomeAssistantClient(config.home_assistant_url, HOME_ASSISTANT_TOKEN)
logger.info("Home Assistant client configured")

# Build ADB Clients
adb_clients = {
    name: ADBClient(tv_name=name, host=tv.host, port=tv.port)
    for name, tv in config.tvs.items()
}
logger.info("ADB clients configured")

# Build ollama client
ollama_client = OllamaClient(
    "qwen3.5:latest",
    "You're an assistant to help direct user requests to the right tool call on the server.",
    False,
)
laya_client = LayaClient()
logger.info("Ollama client configured")


# Build Home instance
home = Home(ha_client, spotify_client, adb_clients, config)
logger.info("Home instance created")

app = init_app(home, laya_client, ollama_client)
