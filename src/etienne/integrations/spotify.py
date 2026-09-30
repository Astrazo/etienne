from typing import Literal

import spotipy
from loguru import logger
from spotipy.exceptions import SpotifyException


class SpotifyClient:
    def __init__(self, spotify: spotipy.Spotify):
        self.spotify_client = spotify

    def start_playback(
        self,
        device_id: str,
        *,
        track_uris: list[str] | None = None,
        context_uri: str | None = None,
        offset_uri: str | None = None,
    ) -> None:
        """Start or resume playback on a Spotify Connect device.

        - Provide `tracks` (name, artist) to play an explicit sequence of tracks.
        - Provide `context_uri` to play an album, artist, or playlist.
        - Provide neither to resume the current playback.

        Args:
            device_id (str): ID of the Spotify Connect device that should play.
            context_uri (str | None, optional): Spotify URI of an album, artist, or
                playlist to play. Defaults to None.
            track_uris (list[str] | None, optional): Spotify track URIs to play as an
                explicit sequence. Defaults to None.
            offset_uri (str | None, optional): Track URI at which to begin within an
                album or playlist context. Defaults to None.

        Raises:
            ValueError: If both `context_uri` and `track_uris` are provided.
            ValueError: If `offset_uri` is provided without `context_uri`.
        """
        if context_uri is not None and track_uris is not None:
            raise ValueError("Provide either a context or tracks, not both")

        if offset_uri is not None and context_uri is None:
            raise ValueError("An offset requires a playback context")

        offset = None

        if offset_uri is not None:
            offset = {"uri": offset_uri}

        logger.info("Starting playback with tracks: {}", track_uris)
        try:
            self.spotify_client.start_playback(
                device_id=device_id,
                context_uri=context_uri,
                uris=track_uris,
                offset=offset,
            )
        except SpotifyException as e:
            logger.warning(f"Failed to start Spotify playback: {e}")

    def play_tracks(self, device_id: str, tracks: list[tuple[str,str]]):
        track_uris: list[str] = []
        if tracks:
            for name, artist in tracks:
                track = self._find_track(name, artist)
                if track is None:
                    logger.warning("Track not found: {} by {}", name, artist)
                    continue
                track_uris.append(track["uri"])
        
        self.start_playback(
            device_id,
            track_uris=track_uris
        )

    def play_album(
        self,
        device_id: str,
        album_name: str,
        artist: str | None = None,
    ) -> None:
        album = self._find_album(album_name, artist)

        if album is None:
            logger.warning("Album not found: {}", album_name)
            return

        self.start_playback(
            device_id,
            context_uri=album["uri"],
        )


    def play_artist(
        self,
        device_id: str,
        artist_name: str,
    ) -> None:
        artist = self._find_artist(artist_name)

        if artist is None:
            logger.warning("Artist not found: {}", artist_name)
            return

        self.start_playback(
            device_id,
            context_uri=artist["uri"],
        )


    def play_playlist(
        self,
        device_id: str,
        playlist_name: str,
    ) -> None:
        playlist = self._find_playlist(playlist_name)

        if playlist is None:
            logger.warning("Playlist not found: {}", playlist_name)
            return

        self.start_playback(
            device_id,
            context_uri=playlist["uri"],
        )

    def pause_playback(self, device_id: str) -> None:
        self.spotify_client.pause_playback(device_id=device_id)

    def _find_track(
        self,
        song: str,
        artist: str | None = None,
    ) -> dict | None:
        query = f'track:"{song}"'

        if artist:
            query += f' artist:"{artist}"'

        results = self.spotify_client.search(
            q=query,
            type="track",
            limit=1,
        )

        tracks = results["tracks"]["items"]

        if not tracks:
            return None

        return tracks[0]  # return top track

    def _find_album(
        self,
        album_name: str,
        artist: str | None = None,
    ) -> dict | None:
        query = f'album:"{album_name}"'

        if artist is not None:
            query += f' artist:"{artist}"'

        results = self.spotify_client.search(
            q=query,
            type="album",
            limit=1,
        )

        albums = results["albums"]["items"]

        if not albums:
            return None

        return albums[0]


    def _find_artist(self, artist_name: str) -> dict | None:
        results = self.spotify_client.search(
            q=f'artist:"{artist_name}"',
            type="artist",
            limit=1,
        )

        artists = results["artists"]["items"]

        if not artists:
            return None

        return artists[0]

    
    def _find_playlist(self, name: str) -> dict | None:
        results = self.spotify_client.current_user_playlists(limit=50)

        while results:
            for playlist in results["items"]:
                if playlist["name"].lower() == name.lower():
                    return playlist

            if results["next"] is None:
                return None

            results = self.spotify_client.next(results)

    def add_to_playback_queue(self, device_id: str, track_uri: str) -> None:
        self.spotify_client.add_to_queue(track_uri, device_id)
    
    def set_repeat(self, device_id: str, state: Literal["track", "context", "off"]):
        self.spotify_client.repeat(state, device_id=device_id)

    def set_shuffle(self, device_id: str, state: bool) -> None:
        self.spotify_client.shuffle(state=state, device_id=device_id)

    def _find_device(self, device_id: str) -> dict | None:
        devices = self.spotify.devices()["devices"]

        for device in devices:
            if device["id"] == device_id:
                return device

        return None
