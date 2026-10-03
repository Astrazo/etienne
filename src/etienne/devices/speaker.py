import asyncio
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
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

    async def play_tracks(
        self,
        tracks: list[tuple[str, str | None]],
    ) -> None:
        await asyncio.to_thread(
            self.spotify_client.play_tracks,
            self.spotify_id,
            tracks,
        )

    async def play_album(
        self,
        album_name: str,
        artist_name: str | None = None,
    ) -> None:
        await asyncio.to_thread(
            self.spotify_client.play_album, self.spotify_id, album_name, artist_name
        )

    async def play_artist(self, artist_name: str) -> None:
        await asyncio.to_thread(
            self.spotify_client.play_artist,
            self.spotify_id,
            artist_name,
        )

    async def play_playlist(self, playlist_name: str) -> None:
        await asyncio.to_thread(
            self.spotify_client.play_playlist, self.spotify_id, playlist_name
        )

    async def resume(self) -> None:
        await asyncio.to_thread(
            self.spotify_client.start_playback,
            self.spotify_id,
        )

    async def pause(self) -> None:
        await asyncio.to_thread(self.spotify_client.pause_playback, self.spotify_id)

    async def repeat(self, state: Literal["track", "context", "off"]) -> None:
        await asyncio.to_thread(
            self.spotify_client.set_repeat,
            self.spotify_id,
            state,
        )

    async def shuffle(self, state: bool) -> None:
        await asyncio.to_thread(
            self.spotify_client.set_shuffle,
            self.spotify_id,
            state,
        )

    async def add_to_playback_queue(self, track_uri: str) -> None:
        await asyncio.to_thread(
            self.spotify_client.add_to_playback_queue,
            self.spotify_id,
            track_uri,
        )

    async def navigate_queue(self, direction: Literal["next", "previous"]) -> None:
        if direction == "next":
            await asyncio.to_thread(
                self.spotify_client.play_next_track,
                self.spotify_id,
            )
        elif direction == "previous":
            await asyncio.to_thread(
                self.spotify_client.play_previous_track,
                self.spotify_id,
            )

    async def set_sleep_timer(self, time: datetime, db_path: Path) -> None:
        """Save a pause deadline for the scheduler to execute."""

        def save_timer():
            with closing(sqlite3.connect(db_path)) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO speaker_timers (device_id, action, execute_at)
                    VALUES (?, ?, ?)
                    """,
                    (self.spotify_id, "pause", time.timestamp()),
                )

        await asyncio.to_thread(save_timer)
