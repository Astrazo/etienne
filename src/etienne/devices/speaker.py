from etienne.integrations import HomeAssistantClient, SpotifyClient


class Speaker:
    def __init__(
        self,
        name: str,
        spotify_id: str,
        spotify_client: SpotifyClient,
        ha_entity_id: str | None = None,
        ha_client: HomeAssistantClient | None = None
    ):
        self.name = name
        self.ha_entity_id = ha_entity_id
        self.ha_client = ha_client
        self.spotify_id = spotify_id
        self.spotify_client = spotify_client


    def play(
        self,
        song: str | None = None,
        artist: str | None = None
    ) -> None:
        self.spotify_client.start_playback(self.spotify_id, song, artist)

    def pause(self) -> None:
        self.spotify_client.pause_playback(self.spotify_id)