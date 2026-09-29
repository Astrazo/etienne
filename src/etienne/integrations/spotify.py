import spotipy
from spotipy.exceptions import SpotifyException


class SpotifyClient:
    def __init__(self, spotify: spotipy.Spotify):
        self.spotify_client = spotify

    def start_playback(
        self, device_id: str, song: str | None = None, artist: str | None = None
    ) -> None:

        # IF no track passed in, resume playback
        if song is None:
            self.spotify_client.start_playback(device_id=device_id)
            return

        # Otherwise find track
        track = self._find_track(song=song, artist=artist)

        if track is None:
            raise ValueError(f"Track not found: {song}")
        try:
            self.spotify_client.start_playback(device_id=device_id, uris=[track["uri"]])
        except SpotifyException as e:
            print(e)

        playback = self.spotify_client.current_playback()
        print("is_playing:", playback["is_playing"])
        print("device:", playback["device"]["name"])
        print("track:", playback["item"]["name"])
        print("artist:", playback["item"]["artists"][0]["name"])
        print("progress:", playback["progress_ms"])

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

        return tracks[0]

    def _find_device(self, device_id: str) -> dict | None:
        devices = self.spotify.devices()["devices"]

        for device in devices:
            if device["id"] == device_id:
                return device

        return None
