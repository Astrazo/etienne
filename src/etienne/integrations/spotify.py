import unicodedata
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

        if track_uris:
            logger.info(
                "Starting Spotify playback on device {} with tracks: {}",
                device_id,
                track_uris,
            )
        elif context_uri:
            logger.info(
                "Starting Spotify playback on device {} with context: {}",
                device_id,
                context_uri,
            )

        try:
            self.spotify_client.start_playback(
                device_id=device_id,
                context_uri=context_uri,
                uris=track_uris,
                offset=offset,
            )
        except SpotifyException as error:
            logger.warning(
                "Failed to start Spotify playback on device {}: {}",
                device_id,
                error,
            )

    def play_tracks(self, device_id: str, tracks: list[tuple[str, str]]):
        track_uris: list[str] = []
        if tracks:
            for name, artist in tracks:
                track = self._find_track(name, artist)
                if track is None:
                    logger.warning("Track not found: {} by {}", name, artist)
                    continue
                track_uris.append(track["uri"])

        self.start_playback(device_id, track_uris=track_uris)

    def _find_track(
        self,
        track_name: str,
        artist: str | None = None,
    ) -> dict | None:
        query = f'track:"{track_name}"'

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

        # Normalise name, and compare to all returned normalised names
        requested_name = self._normalise_name(track_name)
        for track in tracks:
            if self._normalise_name(track["name"]) == requested_name:
                return track

        logger.warning(
            "No normalised track match found: {} by {}",
            requested_name,
            artist,
        )

        return tracks[0]  # return top track

    def play_album(
        self,
        device_id: str,
        album_name: str,
        artist: str | None = None,
    ) -> None:
        album = self._find_album(album_name, artist)

        if album is None:
            logger.warning("Album not found: {} by {}", album_name, artist)
            return

        self.start_playback(
            device_id,
            context_uri=album["uri"],
        )

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
            limit=10,
        )

        albums = results["albums"]["items"]
        if not albums:
            return None

        # Normalise name, and compare to all returned normalised names
        requested_name = self._normalise_name(album_name)
        for album in albums:
            if self._normalise_name(album["name"]) == requested_name:
                return album

        logger.warning(
            "No normalised album match found: {} by {}",
            requested_name,
            artist,
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

    def _find_artist(self, artist_name: str) -> dict | None:
        results = self.spotify_client.search(
            q=f'artist:"{artist_name}"',
            type="artist",
            limit=10,
        )

        artists = results["artists"]["items"]
        if not artists:
            return None

        # Normalise name, and compare to all returned normalised names
        requested_name = self._normalise_name(artist_name)
        for artist in artists:
            if self._normalise_name(artist["name"]) == requested_name:
                return artist

        logger.warning(
            "No normalised artist match found: {}",
            requested_name,
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

    def _find_playlist(self, name: str) -> dict | None:
        results = self.spotify_client.current_user_playlists(limit=50)
        matches = []

        # Loop through results
        while results:
            for playlist in results["items"]:
                if self._normalise_name(playlist["name"]) == self._normalise_name(name):
                    return playlist

            if results["next"] is None:
                return None

            results = self.spotify_client.next(results)

        # If user has duplicate playlist names, could return multiple
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            logger.warning(
                "Multiple playlists matched: {}",
                name,
            )
        return None

    def pause_playback(self, device_id: str) -> None:
        self.spotify_client.pause_playback(device_id=device_id)

    def add_to_playback_queue(self, device_id: str, track_uri: str) -> None:
        self.spotify_client.add_to_queue(track_uri, device_id)

    def set_repeat(self, device_id: str, state: Literal["track", "context", "off"]):
        logger.info("Setting repeat on device {}: {}", device_id, state)
        self.spotify_client.repeat(state, device_id=device_id)

    def set_shuffle(self, device_id: str, state: bool) -> None:
        self.spotify_client.shuffle(state=state, device_id=device_id)

    def play_next_track(self, device_id: str) -> None:
        """Play next track.  Overwrites any track repeat setting.

        Args:
            device_id (str): _description_
        """
        logger.info("Playing next track on device {}", device_id)
        self.spotify_client.next_track(device_id)

    def play_previous_track(self, device_id: str) -> None:
        """Play previous track.  Overwrites any track repeat setting.

        Args:
            device_id (str): _description_
        """
        logger.info("Playing previous track on device {}", device_id)
        self.spotify_client.previous_track(device_id)

    def _normalise_name(self, value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = "".join(
            character for character in value if not unicodedata.combining(character)
        )
        return " ".join(value.casefold().split())

    # Not currently used
    def _find_device(self, device_id: str) -> dict | None:
        devices = self.spotify.devices()["devices"]

        for device in devices:
            if device["id"] == device_id:
                return device

        return None
