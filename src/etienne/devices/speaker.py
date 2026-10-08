"""Controls playback on a speaker."""

import asyncio
from collections.abc import Callable
from typing import Literal

from ..integrations import HomeAssistantClient, SpotifyClient
from .models import TrackInput

from pydantic import validate_call


class Speaker:
    """Controls music playback on a speaker."""

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

    @validate_call
    async def play_tracks(
        self,
        tracks: list[TrackInput],
    ) -> None:
        """Play one or more specific tracks.

        Args:
            tracks (list[TrackInput]): Tracks to play, including each track name and optional artist.
        """
       
        spotify_tracks = [(track.song, track.artist) for track in tracks]
        await asyncio.to_thread(
            self.spotify_client.play_tracks,
            self.spotify_id,
            spotify_tracks,
        )

    async def play_album(
        self,
        album_name: str,
        artist_name: str | None = None,
    ) -> None:
        """Play an album.

        Args:
            album_name (str): Name of the album to play.
            artist_name (str | None, optional): Artist of the album if specified by the user. Defaults to None.
        """
        await asyncio.to_thread(
            self.spotify_client.play_album, self.spotify_id, album_name, artist_name
        )

    async def play_artist(self, artist_name: str) -> None:
        """Play music by an artist.

        Args:
            artist_name (str): Name of the artist to play.
        """
        await asyncio.to_thread(
            self.spotify_client.play_artist,
            self.spotify_id,
            artist_name,
        )

    async def play_playlist(self, playlist_name: str) -> None:
        """Play a playlist.

        Args:
            playlist_name (str): Name of the playlist to play.
        """
        await asyncio.to_thread(
            self.spotify_client.play_playlist, self.spotify_id, playlist_name
        )

    async def resume(self) -> None:
        """Resume the currently paused playback."""
        await asyncio.to_thread(
            self.spotify_client.start_playback,
            self.spotify_id,
        )

    async def pause(self) -> None:
        """Pause the current playback."""
        await asyncio.to_thread(self.spotify_client.pause_playback, self.spotify_id)

    async def repeat(self, state: Literal["track", "context", "off"]) -> None:
        """Set the repeat mode for playback.

        Args:
            state (Literal["track", "context", "off"]):
                Use "track" to repeat the current track,
                or "context" to repeat the current album or playlist,
                or "off" to disable repeat.
        """
        await asyncio.to_thread(
            self.spotify_client.set_repeat,
            self.spotify_id,
            state,
        )

    async def shuffle(self, state: bool) -> None:
        """Enable or disable shuffle for the current playback.

        Args:
            state (bool): True to enable shuffle, or False to disable it.
        """
        await asyncio.to_thread(
            self.spotify_client.set_shuffle,
            self.spotify_id,
            state,
        )

    @validate_call
    async def add_to_playback_queue(self, tracks_input: list[TrackInput]) -> None:
        """Add one or more tracks to the playback queue.

        Args:
            tracks_input (list[TrackInput]): Tracks to add to queue, including each track name and optional artist.
        """
        tracks = [(track.song, track.artist) for track in tracks_input]
        await asyncio.to_thread(
            self.spotify_client.add_to_playback_queue,
            self.spotify_id,
            tracks,
        )

    async def navigate_queue(self, direction: Literal["next", "previous"]) -> None:
        """_summary_

        Args:
            direction (Literal["next", "previous"]): Use "next" for the next track or "previous" for the
                previous track.
        """
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

    def get_tools(self) -> list[Callable]:
        """Return the speaker operations available to ollama."""
        return [
            self.play_tracks,
            self.play_album,
            self.play_artist,
            self.play_playlist,
            self.pause,
            self.resume,
        ]
