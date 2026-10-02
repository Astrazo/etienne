from typing import Literal

from etienne.integrations import HomeAssistantClient, SpotifyClient


class Speaker:
    def __init__(
        self,
        name: str,
        spotify_id: str,
        spotify_client: SpotifyClient,
        ha_entity_id: str | None = None,
        ha_client: HomeAssistantClient | None = None,
    ):
        self.name = name
        self.ha_entity_id = ha_entity_id
        self.ha_client = ha_client
        self.spotify_id = spotify_id
        self.spotify_client = spotify_client

    def play_tracks(
        self,
        tracks: list[tuple[str, str | None]],
    ) -> None:
        self.spotify_client.play_tracks(
            self.spotify_id,
            tracks,
        )

    def play_album(
        self,
        album_name: str,
        artist_name: str | None = None,
    ) -> None:
        self.spotify_client.play_album(
            self.spotify_id,
            album_name,
            artist_name,
        )

    def play_artist(self, artist_name: str) -> None:
        self.spotify_client.play_artist(
            self.spotify_id,
            artist_name,
        )

    def play_playlist(self, playlist_name: str) -> None:
        self.spotify_client.play_playlist(
            self.spotify_id,
            playlist_name,
        )

    def resume(self) -> None:
        self.spotify_client.start_playback(self.spotify_id)

    def pause(self) -> None:
        self.spotify_client.pause_playback(self.spotify_id)

    def repeat(self, state: Literal["track", "context", "off"]) -> None:
        self.spotify_client.set_repeat(self.spotify_id, state)

    def shuffle(self, state: bool) -> None:
        self.spotify_client.set_shuffle(self.spotify_id, state)

    def navigate_queue(self, direction: Literal["next", "previous"]) -> None:
        if direction == "next":
            self.spotify_client.play_next_track(self.spotify_id)
        elif direction == "previous":
            self.spotify_client.play_previous_track(self.spotify_id)
